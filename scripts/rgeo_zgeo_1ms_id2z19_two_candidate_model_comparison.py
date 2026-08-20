#!/usr/bin/env python3
"""ID-2Z19 bounded two-candidate development model comparison."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import torch
from torch import nn


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id2z19_two_candidate_model_comparison.json"
CANDIDATES = ("stable_regularized_lpv", "stable_regularized_lpv_plus_gru4")
HORIZONS = (1, 2, 4, 8)


class IntegrityError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def inside(path: Path, label: str) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise IntegrityError(f"{label} outside repository: {resolved}") from exc
    return resolved


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise IntegrityError(f"expected JSON object: {path}")
    return value


def write_new(path: Path, value: Any) -> None:
    path = inside(path, "output")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise IntegrityError(f"refuse overwrite: {path}")
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
                    encoding="utf-8")


def exact(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise IntegrityError(f"{label}: expected {expected!r}, got {actual!r}")


def load_stage(path: Path = CONFIG) -> dict[str, Any]:
    path = inside(path, "stage config")
    if path != CONFIG.resolve():
        raise IntegrityError("alternate ID2Z19 config forbidden")
    stage = read_json(path)
    exact(stage.get("stage"), "ID-2Z19", "stage")
    exact(stage.get("execution_contract"),
          "server_only_zero_new_tsc_two_candidate_development_comparison", "execution")
    exact(tuple(stage.get("candidate_order", [])), CANDIDATES, "candidate order")
    exact(tuple(stage.get("prediction_horizons_ms", [])), HORIZONS, "horizons")
    exact(stage["fit_and_execution_counts"]["candidate_count"], 2, "candidate count")
    exact(stage["fit_and_execution_counts"]["new_tsc_calls"], 0, "TSC count")
    exact(stage["fit_and_execution_counts"]["calibration_records_read"], 0, "cal reads")
    exact(stage["fit_and_execution_counts"]["blind_holdout_records_read"], 0, "holdout reads")
    exact(stage["stable_regularized_lpv_plus_gru4"]["hidden_width"], 4, "GRU width")
    exact(stage["stable_regularized_lpv_plus_gru4"]["seeds"], [1701, 2903, 4307], "seeds")
    for key in ("future_actual_current", "wire_current", "sprsina",
                "family_pair_sign_role_or_token_labels", "future_rgeo_zgeo_ip"):
        exact(stage["allowed_inputs"][key], False, f"forbidden input {key}")
    for item in stage["source"].values():
        if isinstance(item, dict) and "path" in item:
            evidence = inside(ROOT / item["path"], "evidence")
            exact(sha256(evidence), item["sha256"], f"hash {item['path']}")
    result = read_json(ROOT / stage["source"]["id2z18_result"]["path"])
    exact(result.get("route"), stage["source"]["id2z18_result"]["required_route"], "ID2Z18 route")
    exact(result.get("models_fit_or_updated"), 0, "ID2Z18 model count")
    exact(result.get("calibration_or_holdout_records_read"), 0, "ID2Z18 held reads")
    audit = read_json(ROOT / stage["source"]["id2z18_independent"]["path"])
    exact(audit.get("audit_passed"), True, "ID2Z18 independent")
    return stage


@dataclass(frozen=True)
class Cell:
    family_id: str
    pair_id: str | None
    sign: str | None
    states: np.ndarray
    actual: np.ndarray
    active: np.ndarray
    targets: np.ndarray
    actions: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class Dataset:
    cells: dict[str, Cell]
    families: tuple[str, ...]
    source_state: np.ndarray
    source_actual: np.ndarray
    source_active: np.ndarray
    action_basis: np.ndarray
    input_files: tuple[Path, ...]
    input_digest: str


def _trajectory_inventory(files: Sequence[Path]) -> tuple[int, int, str]:
    lines, size = [], 0
    for path in sorted(files, key=lambda value: value.name):
        length = path.stat().st_size
        size += length
        lines.append(f"{path.name}:{sha256(path)}:{length}")
    payload = "\n".join(lines) + "\n"
    return len(files), size, hashlib.sha256(payload.encode()).hexdigest()


def _state(row: dict[str, Any]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    state = np.asarray([row["r_geo_m"], row["z_geo_m"], row["ip_a"]], dtype=np.float64)
    actual = np.asarray(row["actual_current_a_tsc"], dtype=np.float64)
    active = np.asarray(row["active_command_decimal_a_tsc"], dtype=np.float64)
    if state.shape != (3,) or actual.shape != (14,) or active.shape != (14,):
        raise IntegrityError("state/current width")
    if not np.all(np.isfinite(np.concatenate((state, actual, active)))):
        raise IntegrityError("non-finite state/current")
    return state, actual, active


def _target(row: dict[str, Any]) -> np.ndarray:
    target = np.asarray(row["target_current_a_tsc"], dtype=np.float64)
    if target.shape != (14,) or not np.all(np.isfinite(target)):
        raise IntegrityError("target width/non-finite")
    return target


def load_dataset(stage: dict[str, Any]) -> Dataset:
    folder = inside(ROOT / stage["source"]["directory"], "source directory")
    wanted = list(stage["development_family_ids"]) + list(stage["zero_weight_replay_ids"])
    files = tuple(folder / f"{name}.json" for name in wanted)
    if any(not path.is_file() for path in files):
        raise IntegrityError("missing trajectory compact")
    count, size, digest = _trajectory_inventory(files)
    exact(count, stage["source"]["trajectory_file_count"], "trajectory count")
    exact(size, stage["source"]["trajectory_total_bytes"], "trajectory bytes")
    exact(digest, stage["source"]["trajectory_inventory_digest"], "trajectory digest")
    cells: dict[str, Cell] = {}
    replay_payloads: dict[str, dict[str, Any]] = {}
    for path in files:
        value = read_json(path)
        family = value["family_id"]
        exact(value["passed"], True, f"{family} passed")
        states_raw, actions_raw = value["states"], value["actions"]
        exact(len(states_raw), 66, f"{family} states")
        exact(len(actions_raw), 65, f"{family} actions")
        state_rows, actual_rows, active_rows = zip(*(_state(row) for row in states_raw))
        targets = np.asarray([_target(row) for row in actions_raw])
        for issue, action in enumerate(actions_raw):
            exact(action["issue_step"], issue, f"{family} issue clock")
            exact(action["effect_state_index"], issue + 1, f"{family} effect clock")
            if float(action["maximum_issued_delta_a"]) > 0.300000000001:
                raise IntegrityError(f"{family} slew")
        payload = {
            "states": states_raw, "actions": actions_raw,
            "tokens": value.get("tokens"), "fit_weight": value.get("fit_weight")}
        if family in stage["zero_weight_replay_ids"]:
            exact(value.get("fit_weight"), 0, f"{family} replay weight")
            replay_payloads[family] = payload
            continue
        exact(value.get("fit_weight"), 1, f"{family} fit weight")
        cells[family] = Cell(
            family, value.get("pair_id"), value.get("sign"),
            np.asarray(state_rows), np.asarray(actual_rows), np.asarray(active_rows),
            targets, tuple(actions_raw))
    exact(tuple(cells), tuple(stage["development_family_ids"]), "development family order")
    source = cells[stage["development_family_ids"][0]]
    for cell in cells.values():
        if not np.array_equal(cell.states[0], source.states[0]):
            raise IntegrityError("source RZI mismatch")
        if not np.array_equal(cell.actual[0], source.actual[0]):
            raise IntegrityError("source actual-current mismatch")
        if not np.array_equal(cell.active[0], source.active[0]):
            raise IntegrityError("source active-command mismatch")
        if not np.array_equal(cell.targets[:16], source.targets[:16]):
            raise IntegrityError("exact prefix action mismatch")
    # Replays authenticate but never enter cells.
    for replay, original in (("replay_baseline_half_f", "baseline_half_f"),
                             ("replay_d00_plus", "d00_plus")):
        value = replay_payloads[replay]
        expected = read_json(folder / f"{original}.json")
        for key in ("tokens",):
            exact(value[key], expected[key], f"{replay} {key}")
    # The model coordinate is the prospectively frozen F/A/E geometry from
    # ID2Z18, not an after-the-fact SVD over both Card15 signs.  The latter has
    # a small fourth numerical direction because signed decimal targets are
    # not assumed odd.
    source_result = read_json(ROOT / stage["source"]["id2z18_result"]["path"])
    frozen_columns = np.asarray(
        source_result["scientific_metrics"]["increment_geometry"]["columns_a_tsc"],
        dtype=np.float64)
    if frozen_columns.shape != (3, 14):
        raise IntegrityError("frozen F/A/E geometry width")
    _, singular, vt = np.linalg.svd(frozen_columns, full_matrices=False)
    rank = int(np.sum(singular > singular[0] * 1.0e-10))
    exact(rank, 3, "action rank")
    basis = vt[:3].copy()
    for index in range(3):
        pivot = int(np.argmax(np.abs(basis[index])))
        if basis[index, pivot] < 0:
            basis[index] *= -1
    return Dataset(cells, tuple(cells), source.states[0], source.actual[0],
                   source.active[0], basis, files, digest)


def coord(vector: np.ndarray, data: Dataset) -> np.ndarray:
    return np.asarray(vector) @ data.action_basis.T


def action_delta(cell: Cell, issue: int, data: Dataset) -> np.ndarray:
    return coord(cell.targets[issue] - cell.active[issue], data)


def memories(cell: Cell, data: Dataset, poles: Sequence[float]) -> np.ndarray:
    out = np.zeros((66, len(poles), 3), dtype=np.float64)
    for state_index in range(1, 66):
        delta = action_delta(cell, state_index - 1, data)
        for pole_index, pole in enumerate(poles):
            out[state_index, pole_index] = pole * out[state_index - 1, pole_index] + delta
    return out


def history_step_matrix(cell: Cell, data: Dataset, stage: dict[str, Any]) -> np.ndarray:
    state_scale = np.asarray(stage["stable_regularized_lpv"]["state_scale"])
    inc_scale = np.asarray(stage["stable_regularized_lpv"]["increment_scale"])
    rows = []
    for state_index in range(66):
        previous = max(0, state_index - 1)
        velocity = (cell.states[state_index] - cell.states[previous]) / inc_scale
        actual = coord(cell.actual[state_index] - data.source_actual, data)
        active = coord(cell.active[state_index] - data.source_active, data)
        delta = np.zeros(3) if state_index == 0 else action_delta(cell, state_index - 1, data)
        rows.append(np.concatenate((
            (cell.states[state_index] - data.source_state) / state_scale,
            velocity, actual, active, delta,
            np.asarray([state_index / 65.0]))))
    return np.asarray(rows)


def future_summary(cell: Cell, origin: int, horizon: int, data: Dataset) -> np.ndarray:
    deltas = np.asarray([action_delta(cell, issue, data)
                         for issue in range(origin, origin + horizon)])
    terminal = coord(cell.targets[origin + horizon - 1] - data.source_active, data)
    cumulative = np.sum(deltas, axis=0)
    weights = np.power(0.8, np.arange(horizon - 1, -1, -1))[:, None]
    weighted = np.sum(weights * deltas, axis=0)
    return np.concatenate(([horizon / 8.0, (horizon / 8.0) ** 2],
                           terminal, cumulative, weighted))


def lpv_feature(cell: Cell, origin: int, horizon: int, data: Dataset,
                stage: dict[str, Any], memory: np.ndarray) -> np.ndarray:
    state_scale = np.asarray(stage["stable_regularized_lpv"]["state_scale"])
    inc_scale = np.asarray(stage["stable_regularized_lpv"]["increment_scale"])
    velocity1 = (cell.states[origin] - cell.states[origin - 1]) / inc_scale
    velocity4 = (cell.states[origin] - cell.states[origin - 4]) / (4.0 * inc_scale)
    current = (cell.states[origin] - data.source_state) / state_scale
    actual = coord(cell.actual[origin] - data.source_actual, data)
    active = coord(cell.active[origin] - data.source_active, data)
    return np.concatenate((
        [origin / 65.0], current, velocity1, velocity4, actual, active,
        memory[origin].reshape(-1), future_summary(cell, origin, horizon, data)))


@dataclass
class RidgeModel:
    center: np.ndarray
    scale: np.ndarray
    active_columns: np.ndarray
    coefficients: np.ndarray
    feature_rank: int
    feature_condition: float
    data: Dataset
    stage: dict[str, Any]
    memories_by_family: dict[str, np.ndarray]

    def predict(self, cell: Cell, origin: int, horizon: int) -> np.ndarray:
        raw = lpv_feature(cell, origin, horizon, self.data, self.stage,
                          self.memories_by_family[cell.family_id])
        normalized = (raw[self.active_columns] - self.center) / self.scale
        x = np.concatenate(([1.0], normalized))
        return x @ self.coefficients


def training_rows(families: Sequence[str], data: Dataset, stage: dict[str, Any]) -> tuple[np.ndarray, np.ndarray, list[tuple[str, int, int]]]:
    poles = stage["stable_regularized_lpv"]["fixed_action_memory_poles"]
    scale = np.asarray(stage["stable_regularized_lpv"]["increment_scale"])
    lo, hi = stage["origin_issue_range_inclusive"]
    x_rows, y_rows, keys = [], [], []
    for family in families:
        cell = data.cells[family]
        memory = memories(cell, data, poles)
        for origin in range(lo, hi + 1):
            for horizon in HORIZONS:
                if origin + horizon >= len(cell.states):
                    continue
                x_rows.append(lpv_feature(cell, origin, horizon, data, stage, memory))
                y_rows.append((cell.states[origin + horizon] - cell.states[origin]) / scale)
                keys.append((family, origin, horizon))
    return np.asarray(x_rows), np.asarray(y_rows), keys


def fit_ridge(families: Sequence[str], data: Dataset, stage: dict[str, Any]) -> RidgeModel:
    x, y, _ = training_rows(families, data, stage)
    deviation = np.std(x, axis=0)
    active = np.flatnonzero(deviation > 1.0e-12)
    center = np.mean(x[:, active], axis=0)
    scale = np.std(x[:, active], axis=0)
    z = (x[:, active] - center) / scale
    singular = np.linalg.svd(z, compute_uv=False)
    rank = int(np.sum(singular > singular[0] * 1.0e-10)) if singular.size else 0
    condition = float(singular[0] / singular[rank - 1]) if rank else math.inf
    design = np.column_stack((np.ones(len(z)), z))
    ridge = float(stage["stable_regularized_lpv"]["ridge_lambda"])
    penalty = np.eye(design.shape[1]) * ridge
    penalty[0, 0] = 0.0
    coefficients = np.linalg.solve(design.T @ design + penalty, design.T @ y)
    memory_map = {family: memories(cell, data, stage["stable_regularized_lpv"]["fixed_action_memory_poles"])
                  for family, cell in data.cells.items()}
    return RidgeModel(center, scale, active, coefficients, rank, condition,
                      data, stage, memory_map)


class ResidualNetwork(nn.Module):
    def __init__(self, history_width: int, hidden: int, future_width: int, cap: np.ndarray):
        super().__init__()
        self.gru = nn.GRU(history_width, hidden, batch_first=True)
        self.head = nn.Linear(hidden + future_width, 3)
        self.register_buffer("cap", torch.tensor(cap, dtype=torch.float64))

    def forward(self, histories: torch.Tensor, lengths: torch.Tensor,
                family_index: torch.Tensor, origins: torch.Tensor,
                future: torch.Tensor) -> torch.Tensor:
        packed = nn.utils.rnn.pack_padded_sequence(histories, lengths.cpu(),
                                                    batch_first=True, enforce_sorted=False)
        unpacked, _ = self.gru(packed)
        output, _ = nn.utils.rnn.pad_packed_sequence(unpacked, batch_first=True)
        hidden = output[family_index, origins]
        return torch.tanh(self.head(torch.cat((hidden, future), dim=1))) * self.cap


@dataclass
class GRUModel:
    base: RidgeModel
    networks: list[ResidualNetwork]
    history_center: np.ndarray
    history_scale: np.ndarray
    future_center: np.ndarray
    future_scale: np.ndarray
    history_by_family: dict[str, np.ndarray]

    @property
    def feature_rank(self) -> int:
        return self.base.feature_rank

    @property
    def feature_condition(self) -> float:
        return self.base.feature_condition

    def predict(self, cell: Cell, origin: int, horizon: int) -> np.ndarray:
        base = self.base.predict(cell, origin, horizon)
        history = (self.history_by_family[cell.family_id][:origin + 1] - self.history_center) / self.history_scale
        future = (future_summary(cell, origin, horizon, self.base.data) - self.future_center) / self.future_scale
        x = torch.tensor(history[None], dtype=torch.float64)
        lengths = torch.tensor([len(history)], dtype=torch.long)
        fi = torch.tensor([0], dtype=torch.long)
        oi = torch.tensor([origin], dtype=torch.long)
        f = torch.tensor(future[None], dtype=torch.float64)
        with torch.no_grad():
            residual = np.mean([network(x, lengths, fi, oi, f).numpy()[0]
                                for network in self.networks], axis=0)
        return base + residual


def seed_all(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def fit_gru(families: Sequence[str], data: Dataset, stage: dict[str, Any]) -> GRUModel:
    base = fit_ridge(families, data, stage)
    history_map = {family: history_step_matrix(data.cells[family], data, stage)
                   for family in data.families}
    train_history = np.concatenate([history_map[family] for family in families], axis=0)
    history_center = np.mean(train_history, axis=0)
    history_scale = np.std(train_history, axis=0)
    history_scale[history_scale < 1.0e-12] = 1.0
    x, y, keys = training_rows(families, data, stage)
    future_raw = np.asarray([future_summary(data.cells[f], o, h, data) for f, o, h in keys])
    future_center = np.mean(future_raw, axis=0)
    future_scale = np.std(future_raw, axis=0)
    future_scale[future_scale < 1.0e-12] = 1.0
    future_norm = (future_raw - future_center) / future_scale
    residual_target = np.asarray([y[index] - base.predict(data.cells[f], o, h)
                                  for index, (f, o, h) in enumerate(keys)])
    family_order = list(families)
    histories = np.asarray([(history_map[f] - history_center) / history_scale for f in family_order])
    lengths = torch.tensor([66] * len(family_order), dtype=torch.long)
    family_index = torch.tensor([family_order.index(f) for f, _, _ in keys], dtype=torch.long)
    origins = torch.tensor([o for _, o, _ in keys], dtype=torch.long)
    history_tensor = torch.tensor(histories, dtype=torch.float64)
    future_tensor = torch.tensor(future_norm, dtype=torch.float64)
    target_tensor = torch.tensor(residual_target, dtype=torch.float64)
    cfg = stage["stable_regularized_lpv_plus_gru4"]
    networks = []
    for seed in cfg["seeds"]:
        seed_all(int(seed))
        network = ResidualNetwork(histories.shape[2], int(cfg["hidden_width"]),
                                  future_norm.shape[1], np.asarray(cfg["maximum_residual_normalized"])).double()
        optimizer = torch.optim.Adam(network.parameters(), lr=float(cfg["learning_rate"]),
                                     weight_decay=float(cfg["weight_decay"]))
        for _ in range(int(cfg["epochs"])):
            optimizer.zero_grad(set_to_none=True)
            predicted = network(history_tensor, lengths, family_index, origins, future_tensor)
            loss = torch.mean((predicted - target_tensor) ** 2)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(network.parameters(), float(cfg["gradient_norm_cap"]))
            optimizer.step()
        networks.append(network.eval())
    return GRUModel(base, networks, history_center, history_scale,
                    future_center, future_scale, history_map)


def predict_state(model: RidgeModel | GRUModel, cell: Cell, origin: int,
                  horizon: int, stage: dict[str, Any]) -> np.ndarray:
    scale = np.asarray(stage["stable_regularized_lpv"]["increment_scale"])
    return cell.states[origin] + model.predict(cell, origin, horizon) * scale


def p95(values: Iterable[float]) -> float:
    rows = np.asarray(list(values), dtype=np.float64)
    return float(np.percentile(rows, 95)) if rows.size else math.nan


def cosine(left: np.ndarray, right: np.ndarray) -> float:
    denominator = float(np.linalg.norm(left) * np.linalg.norm(right))
    return float(np.dot(left, right) / denominator) if denominator > 1.0e-15 else 1.0


def endpoint_value(state: np.ndarray, origin_state: np.ndarray, horizon: int,
                   source: np.ndarray, stage: dict[str, Any]) -> float:
    scales = stage["evaluation"]["value_scales"]
    distance = float(np.linalg.norm(state[:2] - source[:2])) / scales["distance_m"]
    average_speed = float(np.linalg.norm(state[:2] - origin_state[:2]) / (horizon * 0.001))
    speed = average_speed / scales["average_speed_m_per_s"]
    ip = abs(float(state[2] - source[2])) / (abs(float(source[2])) * scales["ip_fraction"])
    return max(distance, speed, ip)


def evaluate(model: RidgeModel | GRUModel, held: Sequence[str], kind: str,
             data: Dataset, stage: dict[str, Any]) -> dict[str, Any]:
    scale = np.asarray(stage["stable_regularized_lpv"]["increment_scale"])
    errors = {h: [] for h in HORIZONS}
    target_energy = 0.0
    error_energy = 0.0
    lo, hi = stage["origin_issue_range_inclusive"]
    for family in held:
        cell = data.cells[family]
        for origin in range(lo, hi + 1):
            for horizon in HORIZONS:
                if origin + horizon >= len(cell.states):
                    continue
                prediction = predict_state(model, cell, origin, horizon, stage)
                truth = cell.states[origin + horizon]
                error = prediction - truth
                errors[horizon].append(np.abs(error))
                normalized_error = error / scale
                normalized_target = (truth - cell.states[origin]) / scale
                error_energy += float(normalized_error @ normalized_error)
                target_energy += float(normalized_target @ normalized_target)
    p95_by_h = {str(h): np.percentile(np.asarray(errors[h]), 95, axis=0).tolist() for h in HORIZONS}
    one_velocity = max(p95_by_h["1"][0], p95_by_h["1"][1]) / 0.001
    result: dict[str, Any] = {
        "endpoint_p95_abs_by_horizon": p95_by_h,
        "normalized_endpoint_rmse": math.sqrt(error_energy / max(target_energy, 1.0e-30)),
        "one_step_rz_velocity_error_p95_m_per_s": one_velocity,
        "all_predictions_finite": bool(all(np.all(np.isfinite(x)) for rows in errors.values() for x in rows)),
        "pair_metrics": None,
    }
    if len(held) == 2:
        plus = data.cells[next(f for f in held if f.endswith("_plus"))]
        minus = data.cells[next(f for f in held if f.endswith("_minus"))]
        divergence = next(i for i in range(16, 58) if not np.array_equal(plus.targets[i], minus.targets[i]))
        response_scale = np.asarray([
            stage["evaluation"]["paired_response_scale"]["r_geo_m"],
            stage["evaluation"]["paired_response_scale"]["z_geo_m"],
            stage["evaluation"]["paired_response_scale"]["ip_a"]])
        true_responses, predicted_responses, cosines = [], [], []
        correct, regrets = 0, []
        for horizon in HORIZONS:
            true = plus.states[divergence + horizon] - minus.states[divergence + horizon]
            predicted_plus = predict_state(model, plus, divergence, horizon, stage)
            predicted_minus = predict_state(model, minus, divergence, horizon, stage)
            predicted = predicted_plus - predicted_minus
            true_responses.append(true / response_scale)
            predicted_responses.append(predicted / response_scale)
            cosines.append(cosine(true[:2], predicted[:2]))
            true_scores = [endpoint_value(plus.states[divergence + horizon], plus.states[divergence], horizon,
                                          data.source_state, stage),
                           endpoint_value(minus.states[divergence + horizon], minus.states[divergence], horizon,
                                          data.source_state, stage)]
            predicted_scores = [endpoint_value(predicted_plus, plus.states[divergence], horizon,
                                               data.source_state, stage),
                                endpoint_value(predicted_minus, minus.states[divergence], horizon,
                                               data.source_state, stage)]
            selected = int(np.argmin(predicted_scores))
            best = int(np.argmin(true_scores))
            correct += int(selected == best)
            regrets.append((true_scores[selected] - true_scores[best]) / max(max(true_scores), 1.0e-12))
        true_array, predicted_array = np.asarray(true_responses), np.asarray(predicted_responses)
        sse = float(np.sum((predicted_array - true_array) ** 2))
        blind_sse = float(np.sum(true_array ** 2))
        result["pair_metrics"] = {
            "divergence_issue": divergence,
            "response_nrmse": math.sqrt(sse / max(blind_sse, 1.0e-30)),
            "endpoint_direction_cosines": cosines,
            "positive_endpoint_directions": sum(value > 0.0 for value in cosines),
            "correct_better_sign_rankings": correct,
            "maximum_normalized_value_regret": max(regrets),
            "action_blind_response_sse_improvement_fraction": 1.0 - sse / max(blind_sse, 1.0e-30),
        }
    return result


def failures(metrics: dict[str, Any], model: RidgeModel | GRUModel,
             stage: dict[str, Any]) -> list[str]:
    gate = stage["evaluation"]
    reasons = []
    if not metrics["all_predictions_finite"]:
        reasons.append("NONFINITE")
    if metrics["normalized_endpoint_rmse"] >= gate["maximum_each_fold_normalized_endpoint_rmse"]:
        reasons.append("ENDPOINT_NRMSE")
    if metrics["one_step_rz_velocity_error_p95_m_per_s"] > gate["maximum_one_step_rz_velocity_error_m_per_s"]:
        reasons.append("ONE_STEP_VELOCITY")
    caps = gate["endpoint_p95_caps"]
    for index, horizon in enumerate(HORIZONS):
        row = metrics["endpoint_p95_abs_by_horizon"][str(horizon)]
        if row[0] > caps["r_geo_m"][index] or row[1] > caps["z_geo_m"][index] or row[2] > caps["ip_a"][index]:
            reasons.append(f"ENDPOINT_P95_H{horizon}")
    if model.feature_condition > stage["stable_regularized_lpv"]["maximum_feature_condition"]:
        reasons.append("FEATURE_CONDITION")
    pair = metrics["pair_metrics"]
    if pair is not None:
        if pair["response_nrmse"] >= gate["maximum_each_pair_fold_response_nrmse"]:
            reasons.append("PAIR_RESPONSE_NRMSE")
        if pair["positive_endpoint_directions"] < gate["required_positive_pair_endpoint_directions"]:
            reasons.append("PAIR_DIRECTION")
        if pair["correct_better_sign_rankings"] < gate["required_correct_better_sign_rankings"]:
            reasons.append("PAIR_RANKING")
        if pair["maximum_normalized_value_regret"] > gate["maximum_normalized_value_regret"]:
            reasons.append("PAIR_VALUE_REGRET")
        if pair["action_blind_response_sse_improvement_fraction"] < gate["minimum_action_blind_response_sse_improvement_fraction"]:
            reasons.append("ACTION_BLIND_IMPROVEMENT")
    return reasons


def serialize_ridge(model: RidgeModel) -> dict[str, Any]:
    return {
        "kind": "stable_regularized_lpv",
        "center": model.center.tolist(), "scale": model.scale.tolist(),
        "active_columns": model.active_columns.tolist(),
        "coefficients": model.coefficients.tolist(),
        "feature_rank": model.feature_rank, "feature_condition": model.feature_condition,
        "action_basis": model.data.action_basis.tolist(),
    }


def serialize_gru(model: GRUModel) -> dict[str, Any]:
    networks = []
    for network in model.networks:
        networks.append({key: value.detach().cpu().numpy().tolist()
                         for key, value in network.state_dict().items()})
    return {
        "kind": "stable_regularized_lpv_plus_gru4",
        "base": serialize_ridge(model.base),
        "history_center": model.history_center.tolist(),
        "history_scale": model.history_scale.tolist(),
        "future_center": model.future_center.tolist(),
        "future_scale": model.future_scale.tolist(),
        "networks": networks,
    }


def fit_candidate(kind: str, families: Sequence[str], data: Dataset,
                  stage: dict[str, Any]) -> RidgeModel | GRUModel:
    if kind == CANDIDATES[0]:
        return fit_ridge(families, data, stage)
    if kind == CANDIDATES[1]:
        return fit_gru(families, data, stage)
    raise IntegrityError(f"unknown candidate {kind}")


def compare(data: Dataset, stage: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any] | None]:
    candidate_results = []
    for kind in CANDIDATES:
        fold_rows = []
        for fold in stage["whole_history_folds"]:
            held = tuple(fold["held_family_ids"])
            train = tuple(f for f in data.families if f not in held)
            model = fit_candidate(kind, train, data, stage)
            metrics = evaluate(model, held, kind, data, stage)
            reason = failures(metrics, model, stage)
            fold_rows.append({
                "fold_id": fold["fold_id"], "kind": fold["kind"],
                "held_family_ids": list(held), "training_family_count": len(train),
                "feature_rank": model.feature_rank, "feature_condition": model.feature_condition,
                "metrics": metrics, "failures": reason, "eligible": not reason})
        pair_nrmse = [row["metrics"]["pair_metrics"]["response_nrmse"]
                      for row in fold_rows if row["metrics"]["pair_metrics"] is not None]
        worst_p95 = max(max(max(row["metrics"]["endpoint_p95_abs_by_horizon"][str(h)])
                            for h in HORIZONS) for row in fold_rows)
        candidate_results.append({
            "candidate_id": kind, "eligible": all(row["eligible"] for row in fold_rows),
            "folds": fold_rows,
            "summary": {
                "mean_endpoint_nrmse": float(np.mean([r["metrics"]["normalized_endpoint_rmse"] for r in fold_rows])),
                "worst_endpoint_nrmse": max(r["metrics"]["normalized_endpoint_rmse"] for r in fold_rows),
                "mean_pair_response_nrmse": float(np.mean(pair_nrmse)),
                "worst_pair_response_nrmse": max(pair_nrmse),
                "worst_endpoint_p95_any_output": worst_p95,
            }})
    stable, recurrent = candidate_results
    selected: dict[str, Any] | None = None
    if stable["eligible"]:
        selected = stable
    elif recurrent["eligible"]:
        selected = recurrent
    if stable["eligible"] and recurrent["eligible"]:
        improvement = 1.0 - recurrent["summary"]["worst_pair_response_nrmse"] / max(stable["summary"]["worst_pair_response_nrmse"], 1e-30)
        regression = recurrent["summary"]["worst_endpoint_p95_any_output"] / max(stable["summary"]["worst_endpoint_p95_any_output"], 1e-30) - 1.0
        if (improvement >= stage["selection"]["minimum_gru_worst_pair_response_improvement_fraction"]
                and regression <= stage["selection"]["maximum_gru_worst_endpoint_p95_regression_fraction"]):
            selected = recurrent
    artifact = None
    if selected is not None:
        full = fit_candidate(selected["candidate_id"], data.families, data, stage)
        payload = serialize_gru(full) if isinstance(full, GRUModel) else serialize_ridge(full)
        artifact = {
            "schema_version": "rgeo-zgeo-1ms-id2z19-model-v1",
            "candidate_id": selected["candidate_id"], "model": payload,
            "source_trajectory_digest": data.input_digest,
            "stage_config_sha256": sha256(CONFIG),
            "claim_boundary": stage["claim_boundary"]}
        artifact["model_payload_sha256"] = canonical_sha256(artifact["model"])
    comparison = {
        "candidate_results": candidate_results,
        "eligible_candidate_count": sum(row["eligible"] for row in candidate_results),
        "selected_candidate_id": selected["candidate_id"] if selected else None,
    }
    return comparison, artifact


def compute(stage_path: Path = CONFIG, source_revision: str = "development") -> tuple[dict[str, Any], dict[str, Any] | None]:
    stage = load_stage(stage_path)
    data = load_dataset(stage)
    comparison, artifact = compare(data, stage)
    passed = artifact is not None
    result = {
        "schema_version": "rgeo-zgeo-1ms-id2z19-model-comparison-result-v1",
        "source_revision": source_revision,
        "stage_config_sha256": sha256(CONFIG),
        "passed": passed,
        "route": stage["routes"]["pass" if passed else "no_eligible_candidate"],
        "input_trajectory_count": len(data.input_files),
        "fit_weight_family_count": len(data.families),
        "zero_weight_replay_count": len(stage["zero_weight_replay_ids"]),
        "input_trajectory_digest": data.input_digest,
        "action_basis_rank": int(np.linalg.matrix_rank(data.action_basis)),
        "comparison": comparison,
        "candidate_count": 2,
        "candidate_fold_fits": 16,
        "new_tsc_calls": 0, "reset_calls": 0, "plant_advances": 0,
        "calibration_records_read": 0, "blind_holdout_records_read": 0,
        "claim_boundary": stage["claim_boundary"],
    }
    return result, artifact


def preflight(stage_path: Path = CONFIG) -> dict[str, Any]:
    stage = load_stage(stage_path)
    data = load_dataset(stage)
    return {
        "schema_version": "rgeo-zgeo-1ms-id2z19-preflight-v1",
        "stage_config_sha256": sha256(CONFIG),
        "passed": True, "families": list(data.families),
        "folds": stage["whole_history_folds"], "action_basis_rank": 3,
        "input_trajectory_digest": data.input_digest,
        "candidate_order": list(CANDIDATES),
        "new_tsc_calls": 0, "calibration_records_read": 0,
        "blind_holdout_records_read": 0,
    }


def execute(stage_path: Path, source_revision: str, output_dir: Path) -> dict[str, Any]:
    output = inside(output_dir, "output directory")
    if output.exists():
        raise IntegrityError(f"output exists: {output}")
    output.mkdir(parents=True)
    write_new(output / "preflight.json", preflight(stage_path))
    result, artifact = compute(stage_path, source_revision)
    write_new(output / "result.json", result)
    if artifact is not None:
        write_new(output / "selected_model.json", artifact)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument("--source-revision", default="development")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.preflight:
            print(json.dumps(preflight(args.config), indent=2, sort_keys=True))
            return 0
        if args.output is None:
            parser.error("--output required unless --preflight")
        result = execute(args.config, args.source_revision, args.output)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["passed"] else 2
    except (IntegrityError, OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"passed": False, "route": "ONE_MS_ID2Z19_INPUT_OR_CONTRACT_FAIL_NO_FIT",
                          "error": str(exc), "new_tsc_calls": 0}, indent=2, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
