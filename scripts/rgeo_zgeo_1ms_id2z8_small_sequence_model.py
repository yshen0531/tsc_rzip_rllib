#!/usr/bin/env python3
"""Fit and evaluate the frozen ID-2Z8 two-candidate development models."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import torch
from torch import nn


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.rgeo_zgeo_1ms_id0_vector_tail import (  # noqa: E402
    InputIntegrityError, sha256, write_new,
)


CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id2z8_small_sequence_model.json"
CONFIG_SHA256 = "9d08a97a39f9f1369ded81d412c5db1dde9ea312a7c3738341d3fd74e879a55a"
SCHEMA = "rgeo-zgeo-1ms-id2z8-small-sequence-model-result-v1"
SCALES = np.asarray([0.001, 0.001, 100.0], dtype=np.float64)
POLES = np.asarray([0.0, 0.5, 0.8, 0.95], dtype=np.float64)


def inside(path: Path, label: str) -> Path:
    value = path.resolve()
    try:
        value.relative_to(ROOT)
    except ValueError as exc:
        raise InputIntegrityError(f"{label} leaves repository") from exc
    return value


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise InputIntegrityError(f"object required: {path}")
    return value


def fields_to_float(fields: Sequence[str]) -> np.ndarray:
    value = np.asarray([float(item.strip()) for item in fields], dtype=np.float64)
    if value.shape != (14,) or not np.isfinite(value).all():
        raise InputIntegrityError("invalid Card15 vector")
    return value


@dataclass
class Context:
    context_id: str
    decision: int
    rows: dict[str, dict[str, Any]]
    horizons: list[int]


def require(stage: dict[str, Any]) -> None:
    if stage.get("schema_version") != "rgeo-zgeo-1ms-id2z8-small-sequence-model-v1":
        raise InputIntegrityError("schema changed")
    if stage.get("identity") != stage.get("schema_version") or stage.get("stage") != "ID-2Z8":
        raise InputIntegrityError("identity changed")
    if stage.get("decision_contexts") != [
            {"context_id": "state49", "decision_state_index": 49,
             "source": "id2z6_round0"},
            {"context_id": "state53", "decision_state_index": 53,
             "source": "id2z7_round1"},
            {"context_id": "state57", "decision_state_index": 57,
             "source": "id2z7_round2"}]:
        raise InputIntegrityError("contexts changed")
    if stage.get("arm_ids") != ["hold4", "b4", "f4", "b2f2", "f2b2"]:
        raise InputIntegrityError("arms changed")
    if stage.get("nonhold_arm_ids") != ["b4", "f4", "b2f2", "f2b2"]:
        raise InputIntegrityError("evaluation arms changed")
    if stage.get("response_horizons_by_context") != {
            "state49": list(range(1, 21)), "state53": list(range(1, 17)),
            "state57": list(range(1, 13))}:
        raise InputIntegrityError("horizons changed")
    if (stage.get("common_response_terminal_state_index") != 69
            or stage.get("response_scale") != {
                "r_geo_m": 0.001, "z_geo_m": 0.001, "ip_a": 100.0}
            or stage.get("history_steps") != 8
            or stage.get("whole_context_folds") is not True
            or stage.get("sibling_split_forbidden") is not True
            or stage.get("future_actual_current_forbidden") is not True
            or stage.get("future_truth_forbidden") is not True):
        raise InputIntegrityError("causal evaluation contract changed")
    if stage.get("candidate_specs") != [
            {"candidate_id": "stable_local_memory",
             "stable_action_memory_poles": [0.0, 0.5, 0.8, 0.95],
             "fold_local_context_pca_dimensions": 1,
             "ridge_lambda": 1.0, "intercept": False},
            {"candidate_id": "stable_local_memory_plus_gru4",
             "backbone": "stable_local_memory", "hidden_size": 4,
             "layers": 1, "seeds": [17, 29, 43], "epochs": 300,
             "learning_rate": 0.01, "weight_decay": 0.01,
             "residual_bound_scaled": [1.0, 1.0, 1.0]}]:
        raise InputIntegrityError("candidate specification changed")
    if stage.get("selection_gates") != {
            "maximum_response_nrmse_each_fold": 0.75,
            "maximum_r_p95_m": 0.0003,
            "maximum_z_p95_m": 0.0003,
            "maximum_ip_p95_a": 50.0,
            "minimum_peak_vector_cosine_each_cell_exclusive": 0.0,
            "maximum_best_arm_normalized_score_regret_each_fold": 0.1,
            "nrmse_tie_margin": 0.01,
            "tie_preference": "stable_local_memory",
            "all_three_folds_required": True,
            "all_predictions_finite": True}:
        raise InputIntegrityError("selection gates changed")
    if stage.get("data_contract") != {
            "fit_weight_windows": 15, "independent_causal_contexts": 3,
            "siblings_per_context": 5, "nonhold_evaluation_cells": 12,
            "matched_hold_response_baseline": True,
            "current_rgeo_zgeo_ip_exact_before_issue": True,
            "models_fit_only_on_training_contexts": True,
            "normalization_and_pca_fold_local": True,
            "model_artifact_only_if_eligible": True,
            "development_only": True}:
        raise InputIntegrityError("data contract changed")
    if any(stage.get(key) != 0 for key in (
            "critical_replay_fit_and_evaluation_weight",
            "interrupted_id2z6_round1_weight", "id2z5_weight",
            "calibration_holdout_expert_bc_dagger_rl_weight")):
        raise InputIntegrityError("forbidden data weight changed")


def _same_prefix(left: dict[str, Any], right: dict[str, Any], decision: int) -> bool:
    state_keys = (
        "time_ms", "r_geo_m", "z_geo_m", "r_mid_m", "ip_a",
        "actual_current_decimal_a_tsc", "wire_current_a",
        "active_command_card15_fields")
    semantic = ("inputa", "geqdsk", "coil_currents.csv", "wire_currents.csv")
    for a, b in zip(left["states"][:decision + 1], right["states"][:decision + 1]):
        if any(a.get(key) != b.get(key) for key in state_keys):
            return False
        if any(a.get("artifact_sha256", {}).get(name)
               != b.get("artifact_sha256", {}).get(name) for name in semantic):
            return False
    return ([row.get("expected_card15_fields") for row in left["actions"][:decision]]
            == [row.get("expected_card15_fields")
                for row in right["actions"][:decision]])


def load(path: Path = CONFIG) -> tuple[dict[str, Any], list[Context]]:
    path = inside(path, "config")
    if sha256(path) != CONFIG_SHA256:
        raise InputIntegrityError("config hash mismatch")
    stage = load_json(path)
    require(stage)
    for name, spec in stage["evidence"].items():
        evidence = inside(ROOT / spec["path"], name)
        if sha256(evidence) != spec["sha256"]:
            raise InputIntegrityError(f"evidence mismatch: {name}")
    result = load_json(ROOT / stage["evidence"]["id2z7_result"]["path"])
    audit = load_json(ROOT / stage["evidence"]["id2z7_independent"]["path"])
    if (result.get("passed") is not True
            or result.get("route") != (
                "ONE_MS_ID2Z7_BRANCH_CONTINUATION_PASS_REPLAY_RECOURSE_AND_SMALL_MODEL_DESIGN_ONLY")
            or result.get("scientific_metrics", {}).get(
                "complete_fit_weight_windows") != 15
            or audit.get("audit_passed") is not True
            or audit.get("primary_sha256")
            != stage["evidence"]["id2z7_result"]["sha256"]):
        raise InputIntegrityError("ID2Z7 result is ineligible")
    contexts: list[Context] = []
    for spec in stage["decision_contexts"]:
        context_id = spec["context_id"]
        decision = int(spec["decision_state_index"])
        rows: dict[str, dict[str, Any]] = {}
        for arm_id in stage["arm_ids"]:
            cell = stage["context_cells"][context_id][arm_id]
            cell_path = inside(ROOT / cell["path"], f"{context_id}:{arm_id}")
            if sha256(cell_path) != cell["sha256"]:
                raise InputIntegrityError(f"cell hash mismatch: {context_id}:{arm_id}")
            row = load_json(cell_path)
            if (row.get("passed") is not True or int(row.get("fit_weight", 0)) != 1
                    or row.get("arm_id") != arm_id
                    or len(row.get("states", [])) != 70
                    or len(row.get("actions", [])) != 69):
                raise InputIntegrityError(f"cell contract: {context_id}:{arm_id}")
            rows[arm_id] = row
        hold = rows["hold4"]
        if not all(_same_prefix(hold, rows[arm], decision)
                   for arm in stage["arm_ids"]):
            raise InputIntegrityError(f"sibling prefix mismatch: {context_id}")
        horizons = list(stage["response_horizons_by_context"][context_id])
        if decision + horizons[-1] != 69:
            raise InputIntegrityError(f"terminal mismatch: {context_id}")
        contexts.append(Context(context_id, decision, rows, horizons))
    return stage, contexts


def state_y(state: dict[str, Any]) -> np.ndarray:
    return np.asarray(
        [state["r_geo_m"], state["z_geo_m"], state["ip_a"]], dtype=np.float64)


def token_values(tokens: str, length: int) -> np.ndarray:
    if len(tokens) != 4 or any(token not in "HBF" for token in tokens):
        raise InputIntegrityError("invalid macro tokens")
    values = np.zeros((length, 2), dtype=np.float64)
    for index, token in enumerate(tokens):
        if token == "B":
            values[index, 0] = 1.0
        elif token == "F":
            values[index, 1] = 1.0
    return values


def action_memory(tokens: str, length: int) -> np.ndarray:
    issues = token_values(tokens, length)
    memory = np.zeros((2, len(POLES)), dtype=np.float64)
    rows = []
    for index in range(length):
        memory = memory * POLES[None, :] + issues[index, :, None]
        rows.append(memory.reshape(-1).copy())
    return np.asarray(rows)


def action_basis(contexts: Sequence[Context]) -> np.ndarray:
    values = []
    for context in contexts:
        d = context.decision
        hold = fields_to_float(context.rows["hold4"]["actions"][d][
            "expected_card15_fields"])
        b = fields_to_float(context.rows["b4"]["actions"][d][
            "expected_card15_fields"]) - hold
        f = fields_to_float(context.rows["f4"]["actions"][d][
            "expected_card15_fields"]) - hold
        values.append(np.column_stack([b, f]))
    if any(np.max(np.abs(value - values[0])) > 1e-9 for value in values[1:]):
        raise InputIntegrityError("B/F action basis changed across contexts")
    basis = values[0]
    if np.linalg.matrix_rank(basis) != 2:
        raise InputIntegrityError("B/F basis rank")
    return basis


def project(vector: np.ndarray, basis: np.ndarray) -> np.ndarray:
    return np.linalg.lstsq(basis, vector, rcond=None)[0]


def root_vector(context: Context) -> np.ndarray:
    d = context.decision
    states = context.rows["hold4"]["states"]
    source = state_y(states[0])
    current = state_y(states[d])
    one = current - state_y(states[d - 1])
    four = current - state_y(states[d - 4])
    current_coils = np.asarray(
        [float(value) for value in states[d]["actual_current_decimal_a_tsc"]])
    source_coils = np.asarray(
        [float(value) for value in states[0]["actual_current_decimal_a_tsc"]])
    return np.concatenate([(current - source) / SCALES, one / SCALES,
                           four / SCALES, current_coils - source_coils])


def context_transform(train: Sequence[Context]) -> dict[str, np.ndarray]:
    roots = np.asarray([root_vector(value) for value in train])
    mean = roots.mean(axis=0)
    scale = roots.std(axis=0)
    scale[scale < 1e-9] = 1.0
    normalized = (roots - mean) / scale
    _, _, vh = np.linalg.svd(normalized, full_matrices=False)
    component = vh[0]
    train_scores = normalized @ component
    score_scale = float(np.std(train_scores))
    if score_scale < 1e-9:
        score_scale = 1.0
    return {"mean": mean, "scale": scale, "component": component,
            "score_scale": np.asarray(score_scale)}


def context_score(context: Context, transform: dict[str, np.ndarray]) -> float:
    normalized = (root_vector(context) - transform["mean"]) / transform["scale"]
    return float(normalized @ transform["component"] / transform["score_scale"])


def response(context: Context, arm: str) -> np.ndarray:
    hold = context.rows["hold4"]["states"]
    row = context.rows[arm]["states"]
    return np.asarray([
        (state_y(row[context.decision + horizon])
         - state_y(hold[context.decision + horizon])) / SCALES
        for horizon in context.horizons])


def design_rows(context: Context, arm: str, score: float) -> np.ndarray:
    memory = action_memory(context.rows[arm]["tokens"], len(context.horizons))
    return np.concatenate([memory, memory * score], axis=1)


def fit_backbone(train: Sequence[Context], ridge_lambda: float = 1.0) -> dict[str, Any]:
    transform = context_transform(train)
    xs, ys = [], []
    for context in train:
        score = context_score(context, transform)
        for arm in ("b4", "f4", "b2f2", "f2b2"):
            xs.append(design_rows(context, arm, score))
            ys.append(response(context, arm))
    x = np.concatenate(xs)
    y = np.concatenate(ys)
    column_scale = np.sqrt(np.mean(x * x, axis=0))
    column_scale[column_scale < 1e-9] = 1.0
    xn = x / column_scale
    gram = xn.T @ xn + ridge_lambda * np.eye(xn.shape[1])
    weights = np.linalg.solve(gram, xn.T @ y)
    return {"transform": transform, "column_scale": column_scale,
            "weights": weights, "feature_rank": int(np.linalg.matrix_rank(xn)),
            "feature_condition": float(np.linalg.cond(xn)),
            "parameter_count": int(weights.size)}


def predict_backbone(model: dict[str, Any], context: Context, arm: str) -> np.ndarray:
    score = context_score(context, model["transform"])
    x = design_rows(context, arm, score) / model["column_scale"]
    return x @ model["weights"]


def history_future_input(context: Context, arm: str, basis: np.ndarray,
                         backbone: np.ndarray) -> np.ndarray:
    d = context.decision
    states = context.rows["hold4"]["states"]
    root = state_y(states[d])
    rows: list[np.ndarray] = []
    for index in range(d - 7, d + 1):
        y = state_y(states[index])
        dy = y - state_y(states[index - 1])
        actual = np.asarray([float(value) for value in states[index][
            "actual_current_decimal_a_tsc"]])
        root_actual = np.asarray([float(value) for value in states[d][
            "actual_current_decimal_a_tsc"]])
        active = fields_to_float(states[index]["active_command_card15_fields"])
        previous = fields_to_float(states[index - 1]["active_command_card15_fields"])
        rows.append(np.concatenate([
            [0.0], (y - root) / SCALES, dy / SCALES,
            project(actual - root_actual, basis), project(active - previous, basis),
            np.zeros(8), np.zeros(3)]))
    issues = token_values(context.rows[arm]["tokens"], len(context.horizons))
    cumulative = np.zeros(2)
    memory = action_memory(context.rows[arm]["tokens"], len(context.horizons))
    for index in range(len(context.horizons)):
        cumulative += issues[index]
        rows.append(np.concatenate([
            [1.0], np.zeros(6), cumulative, issues[index], memory[index],
            backbone[index]]))
    value = np.asarray(rows, dtype=np.float64)
    if value.shape[1] != 22:
        raise AssertionError(value.shape)
    return value


class ResidualGRU(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.gru = nn.GRU(22, 4, batch_first=True)
        self.head = nn.Linear(4, 3)

    def forward(self, value: torch.Tensor) -> torch.Tensor:
        hidden, _ = self.gru(value)
        return torch.tanh(self.head(hidden))


def fit_gru(train: Sequence[Context], backbone_model: dict[str, Any],
            basis: np.ndarray, seed: int) -> dict[str, Any]:
    sequences, targets, masks = [], [], []
    max_length = 8 + max(len(context.horizons) for context in train)
    for context in train:
        for arm in ("b4", "f4", "b2f2", "f2b2"):
            base = predict_backbone(backbone_model, context, arm)
            sequence = history_future_input(context, arm, basis, base)
            target = response(context, arm) - base
            padded = np.zeros((max_length, 22), dtype=np.float64)
            padded[:len(sequence)] = sequence
            padded_target = np.zeros((max_length, 3), dtype=np.float64)
            padded_target[8:8 + len(target)] = target
            mask = np.zeros((max_length, 1), dtype=np.float64)
            mask[8:8 + len(target)] = 1.0
            sequences.append(padded)
            targets.append(padded_target)
            masks.append(mask)
    x = np.asarray(sequences)
    y = np.asarray(targets)
    mask = np.asarray(masks)
    flat = np.concatenate([
        history_future_input(context, arm, basis,
                             predict_backbone(backbone_model, context, arm))
        for context in train for arm in ("b4", "f4", "b2f2", "f2b2")])
    mean = flat.mean(axis=0)
    scale = flat.std(axis=0)
    scale[scale < 1e-9] = 1.0
    x = (x - mean) / scale
    torch.manual_seed(seed)
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    model = ResidualGRU().double()
    optimizer = torch.optim.Adam(
        model.parameters(), lr=0.01, weight_decay=0.01)
    tx = torch.from_numpy(x)
    ty = torch.from_numpy(y)
    tm = torch.from_numpy(mask)
    for _ in range(300):
        optimizer.zero_grad(set_to_none=True)
        prediction = model(tx)
        loss = (((prediction - ty) * tm) ** 2).sum() / tm.sum()
        loss.backward()
        optimizer.step()
    return {"model": model, "mean": mean, "scale": scale,
            "training_loss": float(loss.detach()),
            "parameter_count": sum(value.numel() for value in model.parameters())}


def predict_gru(model: dict[str, Any], context: Context, arm: str,
                basis: np.ndarray, backbone: np.ndarray) -> np.ndarray:
    sequence = history_future_input(context, arm, basis, backbone)
    x = (sequence - model["mean"]) / model["scale"]
    with torch.no_grad():
        prediction = model["model"](torch.from_numpy(x[None]))[0, 8:]
    return backbone + prediction.numpy()


def terminal_score(context: Context, arm: str, prediction: np.ndarray | None) -> float:
    hold = context.rows["hold4"]["states"]
    truth = context.rows[arm]["states"]
    source = state_y(truth[0])
    states: dict[int, np.ndarray] = {}
    for offset, horizon in enumerate(context.horizons):
        index = context.decision + horizon
        states[index] = (state_y(truth[index]) if prediction is None else
                         state_y(hold[index]) + prediction[offset] * SCALES)
    distances, speeds, ipf = [], [], []
    for index in range(64, 70):
        current = states[index]
        previous = states[index - 1]
        distances.append(float(np.linalg.norm(current[:2] - source[:2])))
        speeds.append(float(np.linalg.norm(current[:2] - previous[:2]) / 0.001))
        ipf.append(abs(float(current[2] - source[2])) / abs(float(source[2])))
    return max(max(distances) / 0.025, max(speeds) / 0.1, max(ipf) / 0.05)


def fold_metrics(context: Context, predictions: dict[str, np.ndarray],
                 seed_spread: dict[str, np.ndarray] | None = None) -> dict[str, Any]:
    truths = {arm: response(context, arm) for arm in predictions}
    error = np.concatenate([predictions[arm] - truths[arm] for arm in predictions])
    truth = np.concatenate(list(truths.values()))
    nrmse = math.sqrt(float(np.sum(error * error) / max(np.sum(truth * truth), 1e-18)))
    physical = np.abs(error * SCALES)
    cosines: dict[str, float] = {}
    for arm in predictions:
        actual = truths[arm][:, :2] * SCALES[:2]
        predicted = predictions[arm][:, :2] * SCALES[:2]
        peak = int(np.argmax(np.linalg.norm(actual, axis=1)))
        denominator = np.linalg.norm(actual[peak]) * np.linalg.norm(predicted[peak])
        cosines[arm] = (float(actual[peak] @ predicted[peak] / denominator)
                        if denominator > 1e-18 else -1.0)
    true_scores = {arm: terminal_score(context, arm, None) for arm in predictions}
    predicted_scores = {
        arm: terminal_score(context, arm, predictions[arm]) for arm in predictions}
    predicted_best = min(predicted_scores, key=lambda arm: (predicted_scores[arm], arm))
    true_best = min(true_scores, key=lambda arm: (true_scores[arm], arm))
    regret = float(true_scores[predicted_best] - true_scores[true_best])
    value = {
        "context_id": context.context_id,
        "response_nrmse": nrmse,
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
        "true_best_arm": true_best,
        "predicted_best_arm": predicted_best,
        "best_arm_normalized_score_regret": regret,
    }
    if seed_spread:
        value["maximum_seed_std_scaled"] = float(max(
            np.max(seed_spread[arm]) for arm in seed_spread))
    return value


def eligible(folds: Sequence[dict[str, Any]], gates: dict[str, Any]) -> bool:
    return bool(len(folds) == 3 and all(
        value["response_nrmse"] <= gates["maximum_response_nrmse_each_fold"]
        and value["r_p95_m"] <= gates["maximum_r_p95_m"]
        and value["z_p95_m"] <= gates["maximum_z_p95_m"]
        and value["ip_p95_a"] <= gates["maximum_ip_p95_a"]
        and value["minimum_peak_vector_cosine"]
        > gates["minimum_peak_vector_cosine_each_cell_exclusive"]
        and value["best_arm_normalized_score_regret"]
        <= gates["maximum_best_arm_normalized_score_regret_each_fold"]
        for value in folds))


def serialize_backbone(model: dict[str, Any]) -> dict[str, Any]:
    return {
        "context_mean": model["transform"]["mean"].tolist(),
        "context_scale": model["transform"]["scale"].tolist(),
        "context_component": model["transform"]["component"].tolist(),
        "context_score_scale": float(model["transform"]["score_scale"]),
        "column_scale": model["column_scale"].tolist(),
        "weights": model["weights"].tolist(),
        "feature_rank": model["feature_rank"],
        "feature_condition": model["feature_condition"],
        "parameter_count": model["parameter_count"],
    }


def serialize_gru(model: dict[str, Any]) -> dict[str, Any]:
    return {
        "input_mean": model["mean"].tolist(),
        "input_scale": model["scale"].tolist(),
        "training_loss": model["training_loss"],
        "parameter_count": model["parameter_count"],
        "state_dict": {name: value.detach().numpy().tolist()
                       for name, value in model["model"].state_dict().items()},
    }


def execute(path: Path, source_revision: str,
            output: Path | None = None) -> tuple[dict[str, Any], dict[str, Any] | None]:
    stage, contexts = load(path)
    basis = action_basis(contexts)
    candidate_results: list[dict[str, Any]] = []
    candidate_predictions: dict[str, list[dict[str, Any]]] = {}
    for candidate_id in ("stable_local_memory", "stable_local_memory_plus_gru4"):
        fold_values = []
        prediction_records = []
        diagnostics = []
        for held in contexts:
            train = [value for value in contexts if value.context_id != held.context_id]
            backbone = fit_backbone(train)
            predictions: dict[str, np.ndarray] = {}
            spread: dict[str, np.ndarray] | None = None
            if candidate_id == "stable_local_memory":
                for arm in stage["nonhold_arm_ids"]:
                    predictions[arm] = predict_backbone(backbone, held, arm)
            else:
                ensembles: dict[str, list[np.ndarray]] = {
                    arm: [] for arm in stage["nonhold_arm_ids"]}
                seed_diagnostics = []
                for seed in (17, 29, 43):
                    residual = fit_gru(train, backbone, basis, seed)
                    seed_diagnostics.append({
                        "seed": seed, "training_loss": residual["training_loss"],
                        "parameter_count": residual["parameter_count"]})
                    for arm in stage["nonhold_arm_ids"]:
                        base = predict_backbone(backbone, held, arm)
                        ensembles[arm].append(
                            predict_gru(residual, held, arm, basis, base))
                spread = {}
                for arm, values in ensembles.items():
                    stacked = np.asarray(values)
                    predictions[arm] = stacked.mean(axis=0)
                    spread[arm] = stacked.std(axis=0)
                diagnostics.append({"context_id": held.context_id,
                                    "seeds": seed_diagnostics})
            metrics = fold_metrics(held, predictions, spread)
            transform = backbone["transform"]
            normalized_root = ((root_vector(held) - transform["mean"])
                               / transform["scale"])
            train_roots = [((root_vector(value) - transform["mean"])
                            / transform["scale"]) for value in train]
            metrics.update({
                "root_support_distance": float(min(
                    np.linalg.norm(normalized_root - value)
                    / math.sqrt(len(normalized_root)) for value in train_roots)),
                "backbone_feature_rank": backbone["feature_rank"],
                "backbone_feature_condition": backbone["feature_condition"],
                "backbone_parameter_count": backbone["parameter_count"],
            })
            fold_values.append(metrics)
            prediction_records.append({
                "context_id": held.context_id,
                "predictions_scaled": {arm: predictions[arm].tolist()
                                       for arm in predictions},
            })
        is_eligible = eligible(fold_values, stage["selection_gates"])
        candidate_results.append({
            "candidate_id": candidate_id,
            "eligible": is_eligible,
            "mean_response_nrmse": float(np.mean([
                value["response_nrmse"] for value in fold_values])),
            "maximum_response_nrmse": max(
                value["response_nrmse"] for value in fold_values),
            "maximum_r_p95_m": max(value["r_p95_m"] for value in fold_values),
            "maximum_z_p95_m": max(value["z_p95_m"] for value in fold_values),
            "maximum_ip_p95_a": max(value["ip_p95_a"] for value in fold_values),
            "minimum_peak_vector_cosine": min(
                value["minimum_peak_vector_cosine"] for value in fold_values),
            "maximum_best_arm_normalized_score_regret": max(
                value["best_arm_normalized_score_regret"] for value in fold_values),
            "folds": fold_values,
            "diagnostics": diagnostics,
        })
        candidate_predictions[candidate_id] = prediction_records
    eligible_rows = [row for row in candidate_results if row["eligible"]]
    eligible_rows.sort(key=lambda row: (
        row["mean_response_nrmse"],
        0 if row["candidate_id"] == "stable_local_memory" else 1))
    winner = eligible_rows[0]["candidate_id"] if eligible_rows else None
    if len(eligible_rows) == 2 and abs(
            eligible_rows[0]["mean_response_nrmse"]
            - eligible_rows[1]["mean_response_nrmse"]) <= 0.01:
        winner = "stable_local_memory"
    route = (stage["routes"]["pass"] if winner is not None
             else stage["routes"]["small_model_fail"])
    artifact: dict[str, Any] | None = None
    if winner is not None:
        full_backbone = fit_backbone(contexts)
        artifact = {
            "schema_version": "rgeo-zgeo-1ms-id2z8-model-artifact-v1",
            "source_revision": source_revision,
            "stage_config_sha256": CONFIG_SHA256,
            "candidate_id": winner,
            "backbone": serialize_backbone(full_backbone),
        }
        if winner == "stable_local_memory_plus_gru4":
            artifact["gru_ensemble"] = [
                {"seed": seed, **serialize_gru(
                    fit_gru(contexts, full_backbone, basis, seed))}
                for seed in (17, 29, 43)]
    result = {
        "schema_version": SCHEMA,
        "source_revision": source_revision,
        "stage_config_sha256": CONFIG_SHA256,
        "passed": winner is not None,
        "route": route,
        "winner": winner,
        "independent_causal_contexts": 3,
        "fit_weight_windows": 15,
        "nonhold_evaluation_cells": 12,
        "folds": [context.context_id for context in contexts],
        "candidate_results": candidate_results,
        "prediction_records": candidate_predictions,
        "action_basis_rank": int(np.linalg.matrix_rank(basis)),
        "action_basis_condition": float(np.linalg.cond(basis)),
        "candidate_model_classes_evaluated": 2,
        "fold_backbone_fit_operations": 6,
        "fold_gru_fit_operations": 9,
        "full_data_artifact_fit_operations": (
            0 if winner is None else
            (1 if winner == "stable_local_memory" else 4)),
        "new_tsc_or_plant_advances": 0,
        "calibration_or_holdout_records_read": 0,
        "controller_or_optimizer_runs": 0,
        "claim_boundary": (
            "Three-context development model comparison only; not fresh "
            "calibration, holdout, recovery, controller or reachability."),
    }
    if output is not None:
        output = inside(output, "output")
        if output.exists():
            raise FileExistsError(str(output))
        output.mkdir(parents=True)
        if artifact is not None:
            write_new(output / "model.json", artifact)
            result["model_sha256"] = sha256(output / "model.json")
        write_new(output / "result.json", result)
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
        result = {
            "schema_version": SCHEMA,
            "source_revision": args.source_revision,
            "stage_config_sha256": CONFIG_SHA256,
            "passed": False,
            "route": "ONE_MS_ID2Z8_INPUT_OR_CAUSALITY_FAIL_NO_MODEL",
            "failure": f"{type(exc).__name__}:{exc}",
            "new_tsc_or_plant_advances": 0,
        }
        if args.output is not None:
            output = inside(args.output, "output")
            if not output.exists():
                output.mkdir(parents=True)
            if not (output / "result.json").exists():
                write_new(output / "result.json", result)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
