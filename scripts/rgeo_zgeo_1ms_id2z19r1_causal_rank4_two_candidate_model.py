#!/usr/bin/env python3
"""ID-2Z19R1 causal rank-four two-candidate development comparison."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import torch
from torch import nn
from torch.nn import functional as torch_f


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id2z19r1_causal_rank4_two_candidate_model.json"
CANDIDATES = (
    "structured_rank4_stable_memory",
    "structured_rank4_stable_memory_plus_tcn4",
)
FIT_HORIZONS = tuple(range(1, 9))
QUALIFICATION_HORIZONS = (1, 2, 4, 8)


class IntegrityError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(payload.encode()).hexdigest()


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
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def exact(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise IntegrityError(f"{label}: expected {expected!r}, got {actual!r}")


def p95(values: Iterable[float]) -> float:
    rows = np.asarray(list(values), dtype=np.float64)
    return float(np.percentile(rows, 95)) if rows.size else math.nan


def cosine(left: np.ndarray, right: np.ndarray) -> float:
    denominator = float(np.linalg.norm(left) * np.linalg.norm(right))
    return float(np.dot(left, right) / denominator) if denominator > 1.0e-15 else math.nan


def load_stage(path: Path = CONFIG) -> dict[str, Any]:
    path = inside(path, "stage config")
    if path != CONFIG.resolve():
        raise IntegrityError("alternate ID2Z19R1 config forbidden")
    stage = read_json(path)
    exact(stage.get("stage"), "ID-2Z19R1", "stage")
    exact(
        stage.get("execution_contract"),
        "server_only_zero_new_tsc_prefit_readiness_then_two_candidate_development_comparison",
        "execution contract",
    )
    exact(tuple(stage.get("candidate_order", [])), CANDIDATES, "candidate order")
    exact(tuple(stage.get("fit_horizons_ms", [])), FIT_HORIZONS, "fit horizons")
    exact(
        tuple(stage.get("qualification_horizons_ms", [])),
        QUALIFICATION_HORIZONS,
        "qualification horizons",
    )
    counts = stage["fit_and_execution_counts"]
    for key, expected in (
        ("candidate_count", 2),
        ("folds_per_candidate", 8),
        ("maximum_candidate_fold_fits", 16),
        ("maximum_action_blind_fold_fits", 8),
        ("maximum_tcn_seed_fits", 24),
        ("maximum_final_full_fits", 1),
        ("new_tsc_calls", 0),
        ("reset_calls", 0),
        ("plant_advances", 0),
        ("calibration_records_read", 0),
        ("blind_holdout_records_read", 0),
    ):
        exact(counts[key], expected, f"count {key}")
    tcn = stage["structured_rank4_stable_memory_plus_tcn4"]
    exact(tcn["hidden_width"], 4, "TCN width")
    exact(tcn["kernel_sizes"], [3, 3], "TCN kernels")
    exact(tcn["dilations"], [1, 2], "TCN dilations")
    exact(tcn["seeds"], [1701, 2903, 4307], "TCN seeds")
    for key in (
        "future_actual_current",
        "future_recorded_active_command",
        "wire_current",
        "sprsina",
        "family_pair_sign_role_or_token_labels",
        "future_rgeo_zgeo_ip",
    ):
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
    exact(audit.get("audit_passed"), True, "ID2Z18 independent audit")
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
    action_singular_values: np.ndarray
    action_rank4_max_l2_residual_a: float
    action_rank4_max_component_residual_a: float
    superseded_rank3_max_l2_residual_a: float
    nonzero_action_rows: int
    input_files: tuple[Path, ...]
    input_digest: str


def _trajectory_inventory(files: Sequence[Path]) -> tuple[int, int, str]:
    lines: list[str] = []
    size = 0
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


def _canonical_basis(rows: np.ndarray, rank: int, tolerance: float) -> tuple[np.ndarray, np.ndarray, int]:
    _, singular, vt = np.linalg.svd(rows, full_matrices=False)
    numerical_rank = int(np.sum(singular > singular[0] * tolerance))
    if numerical_rank != rank:
        raise IntegrityError(f"signed action rank: expected {rank}, got {numerical_rank}")
    basis = vt[:rank].copy()
    for index in range(rank):
        pivot = int(np.argmax(np.abs(basis[index])))
        if basis[index, pivot] < 0:
            basis[index] *= -1
    return basis, singular, numerical_rank


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
        states_raw = value["states"]
        actions_raw = value["actions"]
        exact(len(states_raw), 66, f"{family} states")
        exact(len(actions_raw), 65, f"{family} actions")
        state_rows, actual_rows, active_rows = zip(*(_state(row) for row in states_raw))
        targets = np.asarray([_target(row) for row in actions_raw])
        for issue, action in enumerate(actions_raw):
            exact(action["issue_step"], issue, f"{family} issue clock")
            exact(action["effect_state_index"], issue + 1, f"{family} effect clock")
            if float(action["maximum_issued_delta_a"]) > 0.300000000001:
                raise IntegrityError(f"{family} slew")
        if family in stage["zero_weight_replay_ids"]:
            exact(value.get("fit_weight"), 0, f"{family} replay weight")
            replay_payloads[family] = value
            continue
        exact(value.get("fit_weight"), 1, f"{family} fit weight")
        cells[family] = Cell(
            family_id=family,
            pair_id=value.get("pair_id"),
            sign=value.get("sign"),
            states=np.asarray(state_rows),
            actual=np.asarray(actual_rows),
            active=np.asarray(active_rows),
            targets=targets,
            actions=tuple(actions_raw),
        )
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

    for replay, original in (
        ("replay_baseline_half_f", "baseline_half_f"),
        ("replay_d00_plus", "d00_plus"),
    ):
        value = replay_payloads[replay]
        expected = read_json(folder / f"{original}.json")
        exact(value.get("tokens"), expected.get("tokens"), f"{replay} tokens")
        exact(value["states"], expected["states"], f"{replay} states")
        exact(value["actions"], expected["actions"], f"{replay} actions")

    geometry = stage["action_geometry"]
    lo, hi = geometry["source_issue_range_inclusive"]
    issued_rows = []
    for cell in cells.values():
        for issue in range(lo, hi + 1):
            delta = cell.targets[issue] - cell.active[issue]
            if float(np.linalg.norm(delta)) > 1.0e-12:
                issued_rows.append(delta)
    issued = np.asarray(issued_rows)
    exact(len(issued), geometry["expected_nonzero_issue_rows"], "nonzero signed action rows")
    basis, singular, _ = _canonical_basis(
        issued,
        int(geometry["required_rank"]),
        float(geometry["rank_relative_tolerance"]),
    )
    reconstructed = (issued @ basis.T) @ basis
    residual = issued - reconstructed
    max_l2 = float(np.max(np.linalg.norm(residual, axis=1)))
    max_component = float(np.max(np.abs(residual)))
    if max_l2 > float(geometry["maximum_rank4_l2_reconstruction_error_a"]):
        raise IntegrityError(f"rank4 L2 reconstruction {max_l2}")
    if max_component > float(geometry["maximum_rank4_component_reconstruction_error_a"]):
        raise IntegrityError(f"rank4 component reconstruction {max_component}")

    offline = read_json(ROOT / stage["source"]["id2z18_offline"]["path"])
    positive = np.asarray(offline["increment_geometry"]["columns_a_tsc"], dtype=np.float64)
    _, positive_singular, positive_vt = np.linalg.svd(positive, full_matrices=False)
    positive_rank = int(np.sum(positive_singular > positive_singular[0] * 1.0e-10))
    exact(positive_rank, 3, "superseded positive action rank")
    positive_basis = positive_vt[:3]
    positive_residual = issued - (issued @ positive_basis.T) @ positive_basis
    superseded = float(np.max(np.linalg.norm(positive_residual, axis=1)))
    if superseded < float(geometry["minimum_superseded_rank3_maximum_l2_residual_a"]):
        raise IntegrityError(f"superseded rank3 residual unexpectedly small: {superseded}")

    return Dataset(
        cells=cells,
        families=tuple(cells),
        source_state=source.states[0],
        source_actual=source.actual[0],
        source_active=source.active[0],
        action_basis=basis,
        action_singular_values=singular,
        action_rank4_max_l2_residual_a=max_l2,
        action_rank4_max_component_residual_a=max_component,
        superseded_rank3_max_l2_residual_a=superseded,
        nonzero_action_rows=len(issued),
        input_files=files,
        input_digest=digest,
    )


def coord(vector: np.ndarray, data: Dataset) -> np.ndarray:
    return np.asarray(vector, dtype=np.float64) @ data.action_basis.T


def historical_action_delta(cell: Cell, issue: int, data: Dataset) -> np.ndarray:
    return coord(cell.targets[issue] - cell.active[issue], data)


def candidate_future_deltas(cell: Cell, origin: int, horizon: int, data: Dataset) -> np.ndarray:
    previous = cell.active[origin].copy()
    deltas = []
    for issue in range(origin, origin + horizon):
        target = cell.targets[issue]
        deltas.append(coord(target - previous, data))
        previous = target
    return np.asarray(deltas)


def memories(cell: Cell, data: Dataset, poles: Sequence[float]) -> np.ndarray:
    out = np.zeros((66, len(poles), data.action_basis.shape[0]), dtype=np.float64)
    for state_index in range(1, 66):
        delta = historical_action_delta(cell, state_index - 1, data)
        for pole_index, pole in enumerate(poles):
            out[state_index, pole_index] = pole * out[state_index - 1, pole_index] + delta
    return out


def future_summary(cell: Cell, origin: int, horizon: int, data: Dataset) -> np.ndarray:
    deltas = candidate_future_deltas(cell, origin, horizon, data)
    terminal = coord(cell.targets[origin + horizon - 1] - data.source_active, data)
    cumulative = np.sum(deltas, axis=0)
    weights = np.power(0.8, np.arange(horizon - 1, -1, -1))[:, None]
    weighted = np.sum(weights * deltas, axis=0)
    return np.concatenate((
        [horizon / 8.0, (horizon / 8.0) ** 2],
        terminal,
        cumulative,
        weighted,
    ))


def structured_feature(
    cell: Cell,
    origin: int,
    horizon: int,
    data: Dataset,
    stage: dict[str, Any],
    memory: np.ndarray,
    action_blind: bool = False,
) -> np.ndarray:
    cfg = stage["structured_rank4_stable_memory"]
    state_scale = np.asarray(cfg["state_scale"])
    increment_scale = np.asarray(cfg["increment_scale"])
    velocity1 = (cell.states[origin] - cell.states[origin - 1]) / increment_scale
    velocity4 = (cell.states[origin] - cell.states[origin - 4]) / (4.0 * increment_scale)
    current = (cell.states[origin] - data.source_state) / state_scale
    common = [np.asarray([origin / 65.0]), current, velocity1, velocity4]
    if action_blind:
        return np.concatenate((*common, np.asarray([horizon / 8.0, (horizon / 8.0) ** 2])))
    actual = coord(cell.actual[origin] - data.source_actual, data)
    active = coord(cell.active[origin] - data.source_active, data)
    return np.concatenate((
        *common,
        actual,
        active,
        memory[origin].reshape(-1),
        future_summary(cell, origin, horizon, data),
    ))


def history_step_matrix(cell: Cell, data: Dataset, stage: dict[str, Any]) -> np.ndarray:
    cfg = stage["structured_rank4_stable_memory"]
    state_scale = np.asarray(cfg["state_scale"])
    increment_scale = np.asarray(cfg["increment_scale"])
    rows = []
    for state_index in range(66):
        previous = max(0, state_index - 1)
        velocity = (cell.states[state_index] - cell.states[previous]) / increment_scale
        actual = coord(cell.actual[state_index] - data.source_actual, data)
        active = coord(cell.active[state_index] - data.source_active, data)
        delta = np.zeros(4) if state_index == 0 else historical_action_delta(cell, state_index - 1, data)
        rows.append(np.concatenate((
            (cell.states[state_index] - data.source_state) / state_scale,
            velocity,
            actual,
            active,
            delta,
            np.asarray([state_index / 65.0]),
        )))
    return np.asarray(rows)


def causal_mutation_invariance(data: Dataset, stage: dict[str, Any]) -> dict[str, Any]:
    cell = data.cells["d00_plus"]
    origin, horizon = 16, 8
    memory = memories(cell, data, stage["structured_rank4_stable_memory"]["fixed_action_memory_poles"])
    reference = structured_feature(cell, origin, horizon, data, stage, memory)
    reference_history = history_step_matrix(cell, data, stage)[: origin + 1]
    states = cell.states.copy()
    actual = cell.actual.copy()
    active = cell.active.copy()
    states[origin + 1 :] += np.asarray([0.123, -0.234, 5678.0])
    actual[origin + 1 :] += 1234.0
    active[origin + 1 :] -= 987.0
    mutated = replace(cell, states=states, actual=actual, active=active)
    mutated_memory = memories(mutated, data, stage["structured_rank4_stable_memory"]["fixed_action_memory_poles"])
    candidate = structured_feature(mutated, origin, horizon, data, stage, mutated_memory)
    candidate_history = history_step_matrix(mutated, data, stage)[: origin + 1]
    feature_difference = float(np.max(np.abs(candidate - reference)))
    history_difference = float(np.max(np.abs(candidate_history - reference_history)))
    return {
        "family_id": cell.family_id,
        "origin_issue": origin,
        "horizon_ms": horizon,
        "future_active_actual_rzi_mutation_feature_max_abs_difference": feature_difference,
        "future_active_actual_rzi_mutation_history_max_abs_difference": history_difference,
        "passed": feature_difference == 0.0 and history_difference == 0.0,
    }


def target_row(cell: Cell, origin: int, horizon: int, stage: dict[str, Any]) -> np.ndarray:
    output_scale = np.asarray(stage["structured_rank4_stable_memory"]["output_scale"])
    endpoint = cell.states[origin + horizon] - cell.states[origin]
    terminal = cell.states[origin + horizon] - cell.states[origin + horizon - 1]
    return np.concatenate((endpoint, terminal)) / output_scale


def training_rows(
    families: Sequence[str],
    data: Dataset,
    stage: dict[str, Any],
    action_blind: bool = False,
) -> tuple[np.ndarray, np.ndarray, list[tuple[str, int, int]]]:
    poles = stage["structured_rank4_stable_memory"]["fixed_action_memory_poles"]
    lo, hi = stage["origin_issue_range_inclusive"]
    x_rows: list[np.ndarray] = []
    y_rows: list[np.ndarray] = []
    keys: list[tuple[str, int, int]] = []
    for family in families:
        cell = data.cells[family]
        memory = memories(cell, data, poles)
        for origin in range(lo, hi + 1):
            for horizon in FIT_HORIZONS:
                if origin + horizon >= len(cell.states):
                    continue
                x_rows.append(structured_feature(
                    cell, origin, horizon, data, stage, memory, action_blind=action_blind
                ))
                y_rows.append(target_row(cell, origin, horizon, stage))
                keys.append((family, origin, horizon))
    return np.asarray(x_rows), np.asarray(y_rows), keys


@dataclass
class RidgeModel:
    center: np.ndarray
    scale: np.ndarray
    active_columns: np.ndarray
    projection: np.ndarray
    coefficients: np.ndarray
    raw_active_dimension: int
    feature_rank: int
    feature_condition: float
    support_threshold: float
    training_projected_by_horizon: dict[int, np.ndarray]
    data: Dataset
    stage: dict[str, Any]
    memories_by_family: dict[str, np.ndarray]
    action_blind: bool = False

    def raw_feature(self, cell: Cell, origin: int, horizon: int) -> np.ndarray:
        return structured_feature(
            cell,
            origin,
            horizon,
            self.data,
            self.stage,
            self.memories_by_family[cell.family_id],
            action_blind=self.action_blind,
        )

    def project(self, raw: np.ndarray) -> np.ndarray:
        normalized = (raw[self.active_columns] - self.center) / self.scale
        return normalized @ self.projection

    def predict(self, cell: Cell, origin: int, horizon: int) -> np.ndarray:
        projected = self.project(self.raw_feature(cell, origin, horizon))
        return np.concatenate(([1.0], projected)) @ self.coefficients

    def support_distance(self, cell: Cell, origin: int, horizon: int) -> float:
        point = self.project(self.raw_feature(cell, origin, horizon))
        training = self.training_projected_by_horizon[horizon]
        return float(np.min(np.linalg.norm(training - point, axis=1)))


def _cross_family_support_threshold(
    projected: np.ndarray,
    keys: Sequence[tuple[str, int, int]],
    stage: dict[str, Any],
) -> tuple[float, dict[int, np.ndarray]]:
    by_horizon: dict[int, list[int]] = {h: [] for h in FIT_HORIZONS}
    for index, (_, _, horizon) in enumerate(keys):
        by_horizon[horizon].append(index)
    distances = []
    projected_map: dict[int, np.ndarray] = {}
    for horizon, indices in by_horizon.items():
        block = projected[indices]
        projected_map[horizon] = block
        families = [keys[index][0] for index in indices]
        for local, family in enumerate(families):
            choices = [i for i, other in enumerate(families) if other != family]
            if not choices:
                raise IntegrityError("support requires another training family")
            distances.append(float(np.min(np.linalg.norm(block[choices] - block[local], axis=1))))
    support = stage["support"]
    threshold = float(np.quantile(
        np.asarray(distances),
        float(support["training_cross_family_nearest_distance_quantile"]),
    )) * float(support["threshold_multiplier"])
    if not math.isfinite(threshold) or threshold <= 0.0:
        raise IntegrityError(f"invalid support threshold {threshold}")
    return threshold, projected_map


def fit_ridge(
    families: Sequence[str],
    data: Dataset,
    stage: dict[str, Any],
    action_blind: bool = False,
) -> RidgeModel:
    x, y, keys = training_rows(families, data, stage, action_blind=action_blind)
    deviation = np.std(x, axis=0)
    active = np.flatnonzero(deviation > 1.0e-12)
    center = np.mean(x[:, active], axis=0)
    scale = np.std(x[:, active], axis=0)
    z = (x[:, active] - center) / scale
    _, singular, vt = np.linalg.svd(z, full_matrices=False)
    tolerance = float(stage["structured_rank4_stable_memory"]["svd_rank_relative_tolerance"])
    rank = int(np.sum(singular > singular[0] * tolerance)) if singular.size else 0
    if rank <= 0:
        raise IntegrityError("empty feature rank")
    projection = vt[:rank].T
    projected = z @ projection
    condition = float(singular[0] / singular[rank - 1])
    design = np.column_stack((np.ones(len(projected)), projected))
    ridge = float(stage["structured_rank4_stable_memory"]["ridge_lambda"])
    penalty = np.eye(design.shape[1]) * ridge
    penalty[0, 0] = 0.0
    coefficients = np.linalg.solve(design.T @ design + penalty, design.T @ y)
    threshold, projected_map = _cross_family_support_threshold(projected, keys, stage)
    memory_map = {
        family: memories(
            cell,
            data,
            stage["structured_rank4_stable_memory"]["fixed_action_memory_poles"],
        )
        for family, cell in data.cells.items()
    }
    return RidgeModel(
        center=center,
        scale=scale,
        active_columns=active,
        projection=projection,
        coefficients=coefficients,
        raw_active_dimension=len(active),
        feature_rank=rank,
        feature_condition=condition,
        support_threshold=threshold,
        training_projected_by_horizon=projected_map,
        data=data,
        stage=stage,
        memories_by_family=memory_map,
        action_blind=action_blind,
    )


class CausalTCNResidual(nn.Module):
    def __init__(self, history_width: int, hidden: int, future_width: int, cap: np.ndarray):
        super().__init__()
        self.conv1 = nn.Conv1d(history_width, hidden, kernel_size=3, dilation=1)
        self.conv2 = nn.Conv1d(hidden, hidden, kernel_size=3, dilation=2)
        self.head = nn.Linear(hidden + future_width, 6)
        self.register_buffer("cap", torch.tensor(cap, dtype=torch.float64))

    def forward(
        self,
        histories: torch.Tensor,
        family_index: torch.Tensor,
        origins: torch.Tensor,
        future: torch.Tensor,
    ) -> torch.Tensor:
        x = histories.transpose(1, 2)
        x = torch.tanh(self.conv1(torch_f.pad(x, (2, 0))))
        x = torch.tanh(self.conv2(torch_f.pad(x, (4, 0))))
        x = x.transpose(1, 2)
        hidden = x[family_index, origins]
        return torch.tanh(self.head(torch.cat((hidden, future), dim=1))) * self.cap


@dataclass
class TCNModel:
    base: RidgeModel
    networks: list[CausalTCNResidual]
    history_center: np.ndarray
    history_scale: np.ndarray
    future_center: np.ndarray
    future_scale: np.ndarray
    history_by_family: dict[str, np.ndarray]

    @property
    def raw_active_dimension(self) -> int:
        return self.base.raw_active_dimension

    @property
    def feature_rank(self) -> int:
        return self.base.feature_rank

    @property
    def feature_condition(self) -> float:
        return self.base.feature_condition

    @property
    def support_threshold(self) -> float:
        return self.base.support_threshold

    def support_distance(self, cell: Cell, origin: int, horizon: int) -> float:
        return self.base.support_distance(cell, origin, horizon)

    def predict(self, cell: Cell, origin: int, horizon: int) -> np.ndarray:
        base = self.base.predict(cell, origin, horizon)
        history = (self.history_by_family[cell.family_id][: origin + 1] - self.history_center) / self.history_scale
        future = (future_summary(cell, origin, horizon, self.base.data) - self.future_center) / self.future_scale
        histories = torch.tensor(history[None], dtype=torch.float64)
        family_index = torch.tensor([0], dtype=torch.long)
        origins = torch.tensor([origin], dtype=torch.long)
        future_tensor = torch.tensor(future[None], dtype=torch.float64)
        with torch.no_grad():
            residual = np.mean([
                network(histories, family_index, origins, future_tensor).numpy()[0]
                for network in self.networks
            ], axis=0)
        return base + residual


def seed_all(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def fit_tcn(
    families: Sequence[str],
    data: Dataset,
    stage: dict[str, Any],
    base: RidgeModel,
) -> TCNModel:
    history_map = {family: history_step_matrix(data.cells[family], data, stage) for family in data.families}
    train_history = np.concatenate([history_map[family] for family in families], axis=0)
    history_center = np.mean(train_history, axis=0)
    history_scale = np.std(train_history, axis=0)
    history_scale[history_scale < 1.0e-12] = 1.0
    _, y, keys = training_rows(families, data, stage)
    future_raw = np.asarray([future_summary(data.cells[f], o, h, data) for f, o, h in keys])
    future_center = np.mean(future_raw, axis=0)
    future_scale = np.std(future_raw, axis=0)
    future_scale[future_scale < 1.0e-12] = 1.0
    future_norm = (future_raw - future_center) / future_scale
    residual_target = np.asarray([
        y[index] - base.predict(data.cells[family], origin, horizon)
        for index, (family, origin, horizon) in enumerate(keys)
    ])
    family_order = list(families)
    histories = np.asarray([
        (history_map[family] - history_center) / history_scale for family in family_order
    ])
    family_index = torch.tensor([family_order.index(f) for f, _, _ in keys], dtype=torch.long)
    origins = torch.tensor([origin for _, origin, _ in keys], dtype=torch.long)
    history_tensor = torch.tensor(histories, dtype=torch.float64)
    future_tensor = torch.tensor(future_norm, dtype=torch.float64)
    target_tensor = torch.tensor(residual_target, dtype=torch.float64)
    cfg = stage["structured_rank4_stable_memory_plus_tcn4"]
    networks: list[CausalTCNResidual] = []
    for seed in cfg["seeds"]:
        seed_all(int(seed))
        network = CausalTCNResidual(
            histories.shape[2],
            int(cfg["hidden_width"]),
            future_norm.shape[1],
            np.asarray(cfg["maximum_residual_normalized"]),
        ).double()
        optimizer = torch.optim.Adam(
            network.parameters(),
            lr=float(cfg["learning_rate"]),
            weight_decay=float(cfg["weight_decay"]),
        )
        for _ in range(int(cfg["epochs"])):
            optimizer.zero_grad(set_to_none=True)
            predicted = network(history_tensor, family_index, origins, future_tensor)
            loss = torch.mean((predicted - target_tensor) ** 2)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(network.parameters(), float(cfg["gradient_norm_cap"]))
            optimizer.step()
        networks.append(network.eval())
    return TCNModel(
        base=base,
        networks=networks,
        history_center=history_center,
        history_scale=history_scale,
        future_center=future_center,
        future_scale=future_scale,
        history_by_family=history_map,
    )


Model = RidgeModel | TCNModel


def prediction_parts(model: Model, cell: Cell, origin: int, horizon: int, stage: dict[str, Any]) -> tuple[np.ndarray, np.ndarray]:
    normalized = model.predict(cell, origin, horizon)
    output_scale = np.asarray(stage["structured_rank4_stable_memory"]["output_scale"])
    physical = normalized * output_scale
    return cell.states[origin] + physical[:3], physical[3:]


def action_diagnostics(cell: Cell, origin: int, horizon: int, data: Dataset) -> tuple[float, float]:
    previous = cell.active[origin].copy()
    maximum_slew = 0.0
    maximum_excursion = 0.0
    for issue in range(origin, origin + horizon):
        target = cell.targets[issue]
        maximum_slew = max(maximum_slew, float(np.max(np.abs(target - previous))))
        maximum_excursion = max(maximum_excursion, float(np.max(np.abs(target - data.source_active))))
        previous = target
    return maximum_slew, maximum_excursion


def ledger_rows(
    candidate_id: str,
    fold: dict[str, Any],
    model: Model,
    blind: RidgeModel,
    data: Dataset,
    stage: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    lo, hi = stage["origin_issue_range_inclusive"]
    for family in fold["held_family_ids"]:
        cell = data.cells[family]
        for origin in range(lo, hi + 1):
            for horizon in FIT_HORIZONS:
                if origin + horizon >= len(cell.states):
                    continue
                predicted_state, predicted_terminal = prediction_parts(model, cell, origin, horizon, stage)
                blind_state, blind_terminal = prediction_parts(blind, cell, origin, horizon, stage)
                truth_state = cell.states[origin + horizon]
                truth_terminal = cell.states[origin + horizon] - cell.states[origin + horizon - 1]
                previous_increment = cell.states[origin] - cell.states[origin - 1]
                maximum_slew, maximum_excursion = action_diagnostics(cell, origin, horizon, data)
                distance = model.support_distance(cell, origin, horizon)
                rows.append({
                    "candidate_id": candidate_id,
                    "fold_id": fold["fold_id"],
                    "fold_kind": fold["kind"],
                    "family_id": family,
                    "pair_id": cell.pair_id,
                    "sign": cell.sign,
                    "origin_issue": origin,
                    "horizon_ms": horizon,
                    "origin_state": cell.states[origin].tolist(),
                    "previous_increment": previous_increment.tolist(),
                    "truth_state": truth_state.tolist(),
                    "predicted_state": predicted_state.tolist(),
                    "truth_terminal_increment": truth_terminal.tolist(),
                    "predicted_terminal_increment": predicted_terminal.tolist(),
                    "blind_predicted_state": blind_state.tolist(),
                    "blind_predicted_terminal_increment": blind_terminal.tolist(),
                    "support_distance": distance,
                    "support_threshold": model.support_threshold,
                    "supported": bool(distance <= model.support_threshold + 1.0e-12),
                    "candidate_maximum_slew_a": maximum_slew,
                    "candidate_maximum_current_excursion_from_source_a": maximum_excursion,
                })
    return rows


def _family_equal_rmse(rows: Sequence[dict[str, Any]], field: str, truth_field: str, scale: np.ndarray) -> float:
    energies = []
    for family in sorted({row["family_id"] for row in rows}):
        selected = [row for row in rows if row["family_id"] == family]
        errors = np.asarray([np.asarray(row[field]) - np.asarray(row[truth_field]) for row in selected]) / scale
        targets = np.asarray([np.asarray(row[truth_field]) - np.asarray(row["origin_state"])
                              if truth_field == "truth_state" else np.asarray(row[truth_field])
                              for row in selected]) / scale
        denominator = max(float(np.sum(targets ** 2)), 1.0e-30)
        energies.append(float(np.sum(errors ** 2)) / denominator)
    return math.sqrt(float(np.mean(energies)))


def endpoint_value(
    state: np.ndarray,
    terminal_increment: np.ndarray,
    current_excursion_a: float,
    source: np.ndarray,
    stage: dict[str, Any],
) -> float:
    scales = stage["evaluation"]["value_scales"]
    distance = float(np.linalg.norm(state[:2] - source[:2])) / float(scales["distance_m"])
    speed = float(np.linalg.norm(terminal_increment[:2]) / 0.001) / float(scales["terminal_speed_m_per_s"])
    ip = abs(float(state[2] - source[2])) / (abs(float(source[2])) * float(scales["ip_fraction"]))
    current = current_excursion_a / float(scales["current_excursion_a"])
    return max(distance, speed, ip, current)


def summarize_fold(rows: Sequence[dict[str, Any]], data: Dataset, stage: dict[str, Any]) -> dict[str, Any]:
    if not rows:
        raise IntegrityError("empty held ledger")
    output_scale = np.asarray(stage["structured_rank4_stable_memory"]["output_scale"])
    endpoint_scale = output_scale[:3]
    terminal_scale = output_scale[3:]
    endpoint_p95: dict[str, list[float]] = {}
    for horizon in QUALIFICATION_HORIZONS:
        selected = [row for row in rows if row["horizon_ms"] == horizon]
        errors = np.abs(np.asarray([row["predicted_state"] for row in selected]) - np.asarray([row["truth_state"] for row in selected]))
        endpoint_p95[str(horizon)] = np.percentile(errors, 95, axis=0).tolist()
    qualification = [row for row in rows if row["horizon_ms"] in QUALIFICATION_HORIZONS]
    terminal_errors = np.abs(
        np.asarray([row["predicted_terminal_increment"] for row in qualification])
        - np.asarray([row["truth_terminal_increment"] for row in qualification])
    )
    terminal_p95 = np.percentile(terminal_errors, 95, axis=0)
    support_coverage = float(np.mean([bool(row["supported"]) for row in rows]))
    all_finite = bool(all(
        np.all(np.isfinite(np.asarray(row[key], dtype=np.float64)))
        for row in rows
        for key in (
            "truth_state", "predicted_state", "truth_terminal_increment",
            "predicted_terminal_increment", "blind_predicted_state",
            "blind_predicted_terminal_increment",
        )
    ))

    consistency_rows = []
    lookup = {(row["family_id"], row["origin_issue"], row["horizon_ms"]): row for row in rows}
    for row in rows:
        horizon = int(row["horizon_ms"])
        if horizon <= 1:
            continue
        previous = lookup[(row["family_id"], row["origin_issue"], horizon - 1)]
        displacement = np.asarray(row["predicted_state"]) - np.asarray(row["origin_state"])
        previous_displacement = np.asarray(previous["predicted_state"]) - np.asarray(previous["origin_state"])
        consistency_rows.append(np.abs(
            displacement - previous_displacement - np.asarray(row["predicted_terminal_increment"])
        ))
    consistency_p95 = np.percentile(np.asarray(consistency_rows), 95, axis=0)

    persistence_errors = []
    constant_velocity_errors = []
    for row in qualification:
        origin = np.asarray(row["origin_state"])
        truth = np.asarray(row["truth_state"])
        previous_increment = np.asarray(row["previous_increment"])
        persistence_errors.append(np.abs(origin - truth))
        constant_velocity_errors.append(np.abs(origin + int(row["horizon_ms"]) * previous_increment - truth))

    result: dict[str, Any] = {
        "endpoint_p95_abs_by_horizon": endpoint_p95,
        "terminal_increment_p95_abs": terminal_p95.tolist(),
        "terminal_rz_velocity_error_p95_m_per_s": float(max(terminal_p95[:2]) / 0.001),
        "normalized_endpoint_rmse": _family_equal_rmse(rows, "predicted_state", "truth_state", endpoint_scale),
        "normalized_terminal_increment_rmse": _family_equal_rmse(
            rows, "predicted_terminal_increment", "truth_terminal_increment", terminal_scale
        ),
        "support_coverage_fraction": support_coverage,
        "maximum_support_distance": max(float(row["support_distance"]) for row in rows),
        "support_threshold": float(rows[0]["support_threshold"]),
        "cross_horizon_consistency_p95_abs": consistency_p95.tolist(),
        "persistence_endpoint_p95_abs": np.percentile(np.asarray(persistence_errors), 95, axis=0).tolist(),
        "constant_velocity_endpoint_p95_abs": np.percentile(np.asarray(constant_velocity_errors), 95, axis=0).tolist(),
        "maximum_candidate_slew_a": max(float(row["candidate_maximum_slew_a"]) for row in rows),
        "maximum_candidate_current_excursion_from_source_a": max(
            float(row["candidate_maximum_current_excursion_from_source_a"]) for row in rows
        ),
        "all_predictions_finite": all_finite,
        "pair_metrics": None,
    }

    families = sorted({row["family_id"] for row in rows})
    if len(families) == 2:
        plus_family = next(family for family in families if family.endswith("_plus"))
        minus_family = next(family for family in families if family.endswith("_minus"))
        by_key = {(row["family_id"], row["origin_issue"], row["horizon_ms"]): row for row in rows}
        response_scale = np.asarray([
            stage["evaluation"]["paired_response_scale"]["r_geo_m"],
            stage["evaluation"]["paired_response_scale"]["z_geo_m"],
            stage["evaluation"]["paired_response_scale"]["ip_a"],
        ])
        true_responses = []
        predicted_responses = []
        blind_responses = []
        cosines = []
        ranking_correct = 0
        ranking_total = 0
        always_plus_correct = 0
        regrets = []
        for origin in range(stage["origin_issue_range_inclusive"][0], stage["origin_issue_range_inclusive"][1] + 1):
            for horizon in QUALIFICATION_HORIZONS:
                plus = by_key.get((plus_family, origin, horizon))
                minus = by_key.get((minus_family, origin, horizon))
                if plus is None or minus is None:
                    continue
                true = np.asarray(plus["truth_state"]) - np.asarray(minus["truth_state"])
                predicted = np.asarray(plus["predicted_state"]) - np.asarray(minus["predicted_state"])
                blind = np.asarray(plus["blind_predicted_state"]) - np.asarray(minus["blind_predicted_state"])
                if float(np.linalg.norm(true / response_scale)) <= 1.0e-12:
                    continue
                true_responses.append(true / response_scale)
                predicted_responses.append(predicted / response_scale)
                blind_responses.append(blind / response_scale)
                if float(np.linalg.norm(true[:2])) >= float(stage["evaluation"]["minimum_rz_direction_signal_m"]):
                    cosines.append(cosine(true[:2], predicted[:2]))

                true_scores = []
                predicted_scores = []
                for item in (plus, minus):
                    true_scores.append(endpoint_value(
                        np.asarray(item["truth_state"]),
                        np.asarray(item["truth_terminal_increment"]),
                        float(item["candidate_maximum_current_excursion_from_source_a"]),
                        data.source_state,
                        stage,
                    ))
                    predicted_scores.append(endpoint_value(
                        np.asarray(item["predicted_state"]),
                        np.asarray(item["predicted_terminal_increment"]),
                        float(item["candidate_maximum_current_excursion_from_source_a"]),
                        data.source_state,
                        stage,
                    ))
                gap = abs(true_scores[0] - true_scores[1])
                if gap > float(stage["evaluation"]["ranking_tie_band_normalized"]):
                    best = int(np.argmin(true_scores))
                    selected = int(np.argmin(predicted_scores))
                    ranking_total += 1
                    ranking_correct += int(best == selected)
                    always_plus_correct += int(best == 0)
                    regrets.append((true_scores[selected] - true_scores[best]) / max(max(true_scores), 1.0e-12))
        true_array = np.asarray(true_responses)
        predicted_array = np.asarray(predicted_responses)
        blind_array = np.asarray(blind_responses)
        sse = float(np.sum((predicted_array - true_array) ** 2))
        zero_sse = float(np.sum(true_array ** 2))
        blind_sse = float(np.sum((blind_array - true_array) ** 2))
        positive = sum(math.isfinite(value) and value > 0.0 for value in cosines)
        finite_cosines = [value for value in cosines if math.isfinite(value)]
        result["pair_metrics"] = {
            "informative_row_count": len(true_responses),
            "direction_row_count": len(cosines),
            "response_nrmse": math.sqrt(sse / max(zero_sse, 1.0e-30)),
            "fitted_action_blind_response_nrmse": math.sqrt(blind_sse / max(zero_sse, 1.0e-30)),
            "action_blind_response_sse_improvement_fraction": 1.0 - sse / max(blind_sse, 1.0e-30),
            "positive_direction_count": positive,
            "positive_direction_fraction": positive / max(len(cosines), 1),
            "minimum_direction_cosine": min(finite_cosines) if finite_cosines else None,
            "ranking_non_tie_count": ranking_total,
            "ranking_correct_count": ranking_correct,
            "ranking_accuracy": ranking_correct / max(ranking_total, 1),
            "always_plus_correct_count": always_plus_correct,
            "always_plus_accuracy": always_plus_correct / max(ranking_total, 1),
            "maximum_normalized_value_regret": max(regrets, default=0.0),
        }
    return result


def failures(metrics: dict[str, Any], model: Model, stage: dict[str, Any]) -> list[str]:
    gate = stage["evaluation"]
    reasons: list[str] = []
    if not metrics["all_predictions_finite"]:
        reasons.append("NONFINITE")
    if metrics["normalized_endpoint_rmse"] >= float(gate["maximum_each_fold_normalized_endpoint_rmse"]):
        reasons.append("ENDPOINT_NRMSE")
    if metrics["normalized_terminal_increment_rmse"] >= float(gate["maximum_each_fold_normalized_terminal_increment_rmse"]):
        reasons.append("TERMINAL_INCREMENT_NRMSE")
    if metrics["terminal_rz_velocity_error_p95_m_per_s"] > float(gate["maximum_terminal_rz_velocity_error_m_per_s"]):
        reasons.append("TERMINAL_VELOCITY")
    caps = gate["endpoint_p95_caps"]
    for index, horizon in enumerate(QUALIFICATION_HORIZONS):
        row = metrics["endpoint_p95_abs_by_horizon"][str(horizon)]
        if row[0] > caps["r_geo_m"][index] or row[1] > caps["z_geo_m"][index] or row[2] > caps["ip_a"][index]:
            reasons.append(f"ENDPOINT_P95_H{horizon}")
    terminal_caps = gate["terminal_increment_p95_caps"]
    terminal = metrics["terminal_increment_p95_abs"]
    if terminal[0] > terminal_caps["r_geo_m"] or terminal[1] > terminal_caps["z_geo_m"] or terminal[2] > terminal_caps["ip_a"]:
        reasons.append("TERMINAL_INCREMENT_P95")
    consistency_caps = gate["cross_horizon_consistency_p95_caps"]
    consistency = metrics["cross_horizon_consistency_p95_abs"]
    if consistency[0] > consistency_caps["r_geo_m"] or consistency[1] > consistency_caps["z_geo_m"] or consistency[2] > consistency_caps["ip_a"]:
        reasons.append("CROSS_HORIZON_CONSISTENCY")
    if metrics["support_coverage_fraction"] < float(stage["support"]["minimum_held_row_coverage_fraction"]):
        reasons.append("HELD_SUPPORT")
    if model.feature_condition > float(stage["structured_rank4_stable_memory"]["maximum_projected_feature_condition"]):
        reasons.append("FEATURE_CONDITION")
    pair = metrics["pair_metrics"]
    if pair is not None:
        if pair["response_nrmse"] >= float(gate["maximum_each_pair_fold_response_nrmse"]):
            reasons.append("PAIR_RESPONSE_NRMSE")
        if pair["direction_row_count"] < int(gate["minimum_direction_row_count"]):
            reasons.append("PAIR_DIRECTION_SUPPORT")
        if pair["positive_direction_fraction"] < float(gate["minimum_positive_direction_fraction"]):
            reasons.append("PAIR_DIRECTION")
        if pair["action_blind_response_sse_improvement_fraction"] < float(gate["minimum_action_blind_response_sse_improvement_fraction"]):
            reasons.append("ACTION_BLIND_IMPROVEMENT")
    return list(dict.fromkeys(reasons))


def _critical_metrics(candidate: dict[str, Any]) -> dict[str, float]:
    out: dict[str, float] = {}
    for fold in candidate["folds"]:
        prefix = fold["fold_id"]
        metrics = fold["metrics"]
        for horizon, values in metrics["endpoint_p95_abs_by_horizon"].items():
            for index, name in enumerate(("r", "z", "ip")):
                out[f"{prefix}:endpoint:h{horizon}:{name}"] = float(values[index])
        for index, name in enumerate(("r", "z", "ip")):
            out[f"{prefix}:terminal:{name}"] = float(metrics["terminal_increment_p95_abs"][index])
            out[f"{prefix}:consistency:{name}"] = float(metrics["cross_horizon_consistency_p95_abs"][index])
    return out


def _serialize_ridge(model: RidgeModel) -> dict[str, Any]:
    return {
        "kind": "action_blind" if model.action_blind else CANDIDATES[0],
        "center": model.center.tolist(),
        "scale": model.scale.tolist(),
        "active_columns": model.active_columns.tolist(),
        "projection": model.projection.tolist(),
        "coefficients": model.coefficients.tolist(),
        "raw_active_dimension": model.raw_active_dimension,
        "feature_rank": model.feature_rank,
        "feature_condition": model.feature_condition,
        "support_threshold": model.support_threshold,
        "action_basis": model.data.action_basis.tolist(),
    }


def _serialize_tcn(model: TCNModel) -> dict[str, Any]:
    networks = []
    for network in model.networks:
        networks.append({key: value.detach().cpu().numpy().tolist() for key, value in network.state_dict().items()})
    return {
        "kind": CANDIDATES[1],
        "base": _serialize_ridge(model.base),
        "history_center": model.history_center.tolist(),
        "history_scale": model.history_scale.tolist(),
        "future_center": model.future_center.tolist(),
        "future_scale": model.future_scale.tolist(),
        "networks": networks,
    }


def compare(data: Dataset, stage: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any] | None]:
    candidate_results: list[dict[str, Any]] = []
    all_rows: list[dict[str, Any]] = []
    for fold in stage["whole_history_folds"]:
        held = tuple(fold["held_family_ids"])
        train = tuple(family for family in data.families if family not in held)
        base = fit_ridge(train, data, stage)
        blind = fit_ridge(train, data, stage, action_blind=True)
        tcn = fit_tcn(train, data, stage, base)
        for candidate_id, model in ((CANDIDATES[0], base), (CANDIDATES[1], tcn)):
            rows = ledger_rows(candidate_id, fold, model, blind, data, stage)
            all_rows.extend(rows)
            metrics = summarize_fold(rows, data, stage)
            reason = failures(metrics, model, stage)
            candidate = next((row for row in candidate_results if row["candidate_id"] == candidate_id), None)
            if candidate is None:
                candidate = {"candidate_id": candidate_id, "folds": []}
                candidate_results.append(candidate)
            candidate["folds"].append({
                "fold_id": fold["fold_id"],
                "kind": fold["kind"],
                "held_family_ids": list(held),
                "training_family_count": len(train),
                "raw_active_feature_dimension": model.raw_active_dimension,
                "feature_rank": model.feature_rank,
                "feature_condition": model.feature_condition,
                "support_threshold": model.support_threshold,
                "metrics": metrics,
                "failures": reason,
                "eligible": not reason,
            })

    for candidate in candidate_results:
        pair_nrmse = [
            fold["metrics"]["pair_metrics"]["response_nrmse"]
            for fold in candidate["folds"]
            if fold["metrics"]["pair_metrics"] is not None
        ]
        candidate["eligible"] = all(fold["eligible"] for fold in candidate["folds"])
        candidate["summary"] = {
            "mean_endpoint_nrmse": float(np.mean([fold["metrics"]["normalized_endpoint_rmse"] for fold in candidate["folds"]])),
            "worst_endpoint_nrmse": max(fold["metrics"]["normalized_endpoint_rmse"] for fold in candidate["folds"]),
            "mean_pair_response_nrmse": float(np.mean(pair_nrmse)),
            "worst_pair_response_nrmse": max(pair_nrmse),
            "minimum_support_coverage_fraction": min(fold["metrics"]["support_coverage_fraction"] for fold in candidate["folds"]),
        }

    structured = next(row for row in candidate_results if row["candidate_id"] == CANDIDATES[0])
    tcn_result = next(row for row in candidate_results if row["candidate_id"] == CANDIDATES[1])
    improvement = 1.0 - tcn_result["summary"]["worst_pair_response_nrmse"] / max(
        structured["summary"]["worst_pair_response_nrmse"], 1.0e-30
    )
    structured_critical = _critical_metrics(structured)
    tcn_critical = _critical_metrics(tcn_result)
    regressions = {
        key: tcn_critical[key] / max(value, 1.0e-30) - 1.0
        for key, value in structured_critical.items()
    }
    maximum_regression = max(regressions.values())
    relative_gate = (
        improvement >= float(stage["selection"]["minimum_tcn_worst_pair_response_improvement_fraction"])
        and maximum_regression <= float(stage["selection"]["maximum_tcn_componentwise_critical_metric_regression_fraction"])
    )
    selection_diagnostics = {
        "tcn_worst_pair_response_improvement_fraction": improvement,
        "tcn_maximum_componentwise_critical_metric_regression_fraction": maximum_regression,
        "tcn_relative_selection_gate_passed": relative_gate,
    }
    selected_id: str | None = None
    if structured["eligible"]:
        selected_id = CANDIDATES[0]
    if tcn_result["eligible"] and relative_gate:
        selected_id = CANDIDATES[1]

    artifact = None
    if selected_id is not None:
        full_base = fit_ridge(data.families, data, stage)
        if selected_id == CANDIDATES[0]:
            payload = _serialize_ridge(full_base)
        else:
            payload = _serialize_tcn(fit_tcn(data.families, data, stage, full_base))
        artifact = {
            "schema_version": "rgeo-zgeo-1ms-id2z19r1-shadow-model-v1",
            "candidate_id": selected_id,
            "model": payload,
            "source_trajectory_digest": data.input_digest,
            "stage_config_sha256": sha256(CONFIG),
            "claim_boundary": stage["claim_boundary"],
        }
        artifact["model_payload_sha256"] = canonical_sha256(artifact["model"])

    comparison = {
        "candidate_results": candidate_results,
        "eligible_candidate_count": sum(bool(row["eligible"]) for row in candidate_results),
        "selected_candidate_id": selected_id,
        "selection_diagnostics": selection_diagnostics,
    }
    ledger = {
        "schema_version": "rgeo-zgeo-1ms-id2z19r1-oof-predictions-v1",
        "stage_config_sha256": sha256(CONFIG),
        "rows": all_rows,
    }
    return comparison, ledger, artifact


def preflight(stage_path: Path = CONFIG) -> dict[str, Any]:
    stage = load_stage(stage_path)
    data = load_dataset(stage)
    mutation = causal_mutation_invariance(data, stage)
    passed = bool(mutation["passed"])
    return {
        "schema_version": "rgeo-zgeo-1ms-id2z19r1-prefit-readiness-v1",
        "stage_config_sha256": sha256(CONFIG),
        "passed": passed,
        "route": stage["routes"]["prefit_pass" if passed else "prefit_readiness_fail"],
        "families": list(data.families),
        "folds": stage["whole_history_folds"],
        "input_trajectory_digest": data.input_digest,
        "action_geometry": {
            "nonzero_issue_rows": data.nonzero_action_rows,
            "singular_values": data.action_singular_values.tolist(),
            "rank": int(data.action_basis.shape[0]),
            "rank4_maximum_l2_reconstruction_error_a": data.action_rank4_max_l2_residual_a,
            "rank4_maximum_component_reconstruction_error_a": data.action_rank4_max_component_residual_a,
            "superseded_rank3_maximum_l2_residual_a": data.superseded_rank3_max_l2_residual_a,
        },
        "causal_future_mutation_gate": mutation,
        "candidate_order": list(CANDIDATES),
        "new_tsc_calls": 0,
        "calibration_records_read": 0,
        "blind_holdout_records_read": 0,
    }


def compute(stage_path: Path = CONFIG, source_revision: str = "development") -> tuple[dict[str, Any], dict[str, Any], dict[str, Any] | None]:
    stage = load_stage(stage_path)
    readiness = preflight(stage_path)
    if not readiness["passed"]:
        raise IntegrityError("prefit readiness failed")
    data = load_dataset(stage)
    comparison, ledger, artifact = compare(data, stage)
    passed = artifact is not None
    result = {
        "schema_version": "rgeo-zgeo-1ms-id2z19r1-model-comparison-result-v1",
        "source_revision": source_revision,
        "stage_config_sha256": sha256(CONFIG),
        "passed": passed,
        "route": stage["routes"]["pass" if passed else "no_eligible_candidate"],
        "input_trajectory_count": len(data.input_files),
        "fit_weight_family_count": len(data.families),
        "zero_weight_replay_count": len(stage["zero_weight_replay_ids"]),
        "input_trajectory_digest": data.input_digest,
        "action_basis_rank": int(data.action_basis.shape[0]),
        "comparison": comparison,
        "oof_prediction_ledger_canonical_sha256": canonical_sha256(ledger),
        "oof_prediction_row_count": len(ledger["rows"]),
        "candidate_count": 2,
        "candidate_fold_fits": 16,
        "action_blind_fold_fits": 8,
        "tcn_seed_fits": 24,
        "new_tsc_calls": 0,
        "reset_calls": 0,
        "plant_advances": 0,
        "calibration_records_read": 0,
        "blind_holdout_records_read": 0,
        "claim_boundary": stage["claim_boundary"],
    }
    return result, ledger, artifact


def execute(stage_path: Path, source_revision: str, output_dir: Path) -> dict[str, Any]:
    output = inside(output_dir, "output directory")
    if output.exists():
        raise IntegrityError(f"output exists: {output}")
    output.mkdir(parents=True)
    readiness = preflight(stage_path)
    write_new(output / "preflight.json", readiness)
    if not readiness["passed"]:
        return readiness
    result, ledger, artifact = compute(stage_path, source_revision)
    write_new(output / "oof_predictions.json", ledger)
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
            value = preflight(args.config)
            print(json.dumps(value, indent=2, sort_keys=True))
            return 0 if value["passed"] else 2
        if args.output is None:
            parser.error("--output required unless --preflight")
        result = execute(args.config, args.source_revision, args.output)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["passed"] else 2
    except (IntegrityError, OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({
            "passed": False,
            "route": "ONE_MS_ID2Z19R1_INPUT_OR_CONTRACT_FAIL_NO_FIT",
            "error": str(exc),
            "new_tsc_calls": 0,
            "calibration_records_read": 0,
            "blind_holdout_records_read": 0,
        }, indent=2, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
