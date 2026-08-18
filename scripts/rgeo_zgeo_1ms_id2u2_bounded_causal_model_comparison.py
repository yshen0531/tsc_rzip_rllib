#!/usr/bin/env python3
"""ID-2U2 bounded, development-only causal model comparison."""

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
CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id2u2_bounded_causal_model_comparison.json"
CONFIG_SHA256 = "a7e8c628afeb5335baf3ed321bdf1361883ca104e3daa5731fd76036d649b681"
SCHEMA = "rgeo-zgeo-1ms-id2u2-bounded-causal-model-comparison-result-v1"
MODEL_SCHEMA = "rgeo-zgeo-1ms-id2u2-causal-model-payload-v1"
CANDIDATES = ("stable_local_event_mixture", "stable_local_event_gru_residual")
STATE_SCALE = np.asarray([1.0e-3, 1.0e-3, 100.0], dtype=np.float64)


class IntegrityError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def inside(path: Path, label: str) -> Path:
    value = path.resolve()
    try:
        value.relative_to(ROOT)
    except ValueError as exc:
        raise IntegrityError(f"{label} escapes repository root: {value}") from exc
    return value


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise IntegrityError(f"not a JSON object: {path}")
    return value


def write_new(path: Path, value: Any) -> None:
    target = inside(path, "output")
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise IntegrityError(f"refusing overwrite: {target}")
    target.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def compact_inventory(paths: Sequence[Path]) -> tuple[int, int, str]:
    digest = hashlib.sha256()
    total = 0
    for path in sorted(paths, key=lambda item: item.name):
        payload = path.read_bytes()
        item_sha = hashlib.sha256(payload).hexdigest()
        total += len(payload)
        digest.update(f"{path.name}\t{len(payload)}\t{item_sha}\n".encode("utf-8"))
    return len(paths), total, digest.hexdigest()


def _exact(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise IntegrityError(f"{label} changed: {actual!r} != {expected!r}")


def load_stage(path: Path = CONFIG) -> dict[str, Any]:
    path = inside(path, "stage config")
    if path == CONFIG and sha256(path) != CONFIG_SHA256:
        raise IntegrityError("stage config SHA changed")
    stage = read_json(path)
    _exact(stage.get("schema_version"), "rgeo-zgeo-1ms-id2u2-bounded-causal-model-comparison-v1", "schema")
    _exact(stage.get("execution_contract"), "server_only_zero_new_tsc_two_candidate_development_comparison", "execution contract")
    _exact(tuple(stage.get("candidate_order", [])), CANDIDATES, "candidate set")
    _exact(stage.get("development_family_ids"), ["u00", "u02", "u04", "u06"], "development families")
    _exact(stage.get("unopened_calibration_family_ids"), ["u01", "u03"], "calibration families")
    _exact(stage.get("unopened_blind_holdout_family_ids"), ["u05", "u07"], "blind families")
    _exact(stage["prediction_horizons_ms"], list(range(1, 9)), "horizons")
    _exact(stage["stable_local_event_gru_residual"]["hidden_width"], 3, "GRU width")
    _exact(stage["fit_and_execution_counts"]["new_tsc_calls"], 0, "TSC count")
    _exact(stage["fit_and_execution_counts"]["calibration_records_read"], 0, "calibration read count")
    _exact(stage["fit_and_execution_counts"]["blind_holdout_records_read"], 0, "holdout read count")
    for value in stage["source"].values():
        if isinstance(value, dict) and "path" in value:
            evidence = inside(ROOT / value["path"], "source evidence")
            if sha256(evidence) != value["sha256"]:
                raise IntegrityError(f"source evidence SHA changed: {value['path']}")
    return stage


@dataclass(frozen=True)
class Cell:
    cell_id: str
    family_id: str
    kind: str
    direction: str | None
    sign: str | None
    nominal_level: int
    probe_issue: int
    states: np.ndarray
    currents: np.ndarray
    issued: np.ndarray


@dataclass(frozen=True)
class Dataset:
    cells: tuple[Cell, ...]
    families: tuple[str, ...]
    baselines: dict[str, Cell]
    action_basis: np.ndarray
    source_state: np.ndarray
    source_current: np.ndarray


def _stable_basis(vectors: np.ndarray) -> np.ndarray:
    _, singular, vt = np.linalg.svd(vectors, full_matrices=False)
    rank = int(np.linalg.matrix_rank(vectors, tol=1.0e-10))
    if rank != 3 or singular[rank - 1] <= 0.0:
        raise IntegrityError(f"executed residual action rank changed: {rank}")
    basis = vt[:rank].copy()
    for index in range(rank):
        pivot = int(np.argmax(np.abs(basis[index])))
        if basis[index, pivot] < 0.0:
            basis[index] *= -1.0
    return basis


def load_dataset(stage: dict[str, Any]) -> Dataset:
    source = stage["source"]
    folder = inside(ROOT / source["directory"], "ID2U1 compact directory")
    all_json = sorted(folder.glob("*.json"), key=lambda item: item.name)
    count, _, digest = compact_inventory(all_json)
    _exact(count, source["tracked_compact_inventory_files"], "compact inventory count")
    _exact(digest, source["tracked_compact_inventory_digest"], "compact inventory digest")

    primary = read_json(inside(ROOT / source["id2u1_result"]["path"], "ID2U1 result"))
    audit = read_json(inside(ROOT / source["id2u1_independent"]["path"], "ID2U1 audit"))
    if not primary.get("passed") or not primary.get("development_fit_data_eligible"):
        raise IntegrityError("ID2U1 primary is not fit eligible")
    _exact(primary.get("route"), source["id2u1_result"]["required_route"], "ID2U1 route")
    if not audit.get("audit_passed"):
        raise IntegrityError("ID2U1 independent raw audit did not pass")
    _exact(primary.get("calibration_or_holdout_records_read"), 0, "ID2U1 calibration/holdout read count")

    files = sorted(folder.glob(source["trajectory_file_glob"]), key=lambda item: item.name)
    _exact(len(files), source["required_trajectory_files"], "trajectory file count")
    forbidden = set(stage["unopened_calibration_family_ids"] + stage["unopened_blind_holdout_family_ids"])
    rows = [read_json(path) for path in files]
    probe_issue_by_family: dict[str, int] = {}
    level_by_family: dict[str, int] = {}
    for row in rows:
        family = str(row["group_id"])
        if family in forbidden or row.get("role") != "development" or not row.get("passed"):
            raise IntegrityError(f"forbidden or ineligible compact row: {row.get('cell_id')}")
        level_by_family[family] = int(row["nominal_level_at_probe"])
        if row["cell_kind"] == "probe":
            probe_issue_by_family[family] = int(row["probe_issue_step"])
    _exact(sorted(probe_issue_by_family), sorted(stage["development_family_ids"]), "family probe metadata")

    cells: list[Cell] = []
    for row in rows:
        family = str(row["group_id"])
        states = np.asarray([[s["r_geo_m"], s["z_geo_m"], s["ip_a"]] for s in row["states"]], dtype=np.float64)
        currents = np.asarray([[float(v) for v in s["actual_current_decimal_a_tsc"]] for s in row["states"]], dtype=np.float64)
        issued = np.asarray([[float(v) for v in a["target_current_a_tsc"]] for a in row["actions"]], dtype=np.float64)
        if states.shape != (41, 3) or currents.shape != (41, 14) or issued.shape != (40, 14):
            raise IntegrityError(f"invalid compact shapes: {row['cell_id']}")
        if not np.all(np.isfinite(states)) or not np.all(np.isfinite(currents)) or not np.all(np.isfinite(issued)):
            raise IntegrityError(f"non-finite compact values: {row['cell_id']}")
        if any(len(s.get("wire_current_a", [])) != 48 for s in row["states"]):
            raise IntegrityError(f"incomplete diagnostic wire state: {row['cell_id']}")
        cells.append(Cell(
            cell_id=str(row["cell_id"]), family_id=family, kind=str(row["cell_kind"]),
            direction=row.get("direction_id"), sign=row.get("sign"),
            nominal_level=level_by_family[family], probe_issue=probe_issue_by_family[family],
            states=states, currents=currents, issued=issued,
        ))
    families = tuple(sorted({cell.family_id for cell in cells}))
    _exact(list(families), stage["development_family_ids"], "loaded families")
    baselines = {cell.family_id: cell for cell in cells if cell.kind == "baseline"}
    if len(baselines) != 4 or any(sum(cell.family_id == family for cell in cells) != 5 for family in families):
        raise IntegrityError("family/cell multiplicity changed")
    source_state = cells[0].states[0].copy()
    source_current = cells[0].currents[0].copy()
    for cell in cells:
        if not np.array_equal(cell.states[0], source_state) or not np.array_equal(cell.currents[0], source_current):
            raise IntegrityError("fixed source changed")
        baseline = baselines[cell.family_id]
        if not np.array_equal(cell.states[: cell.probe_issue + 1], baseline.states[: cell.probe_issue + 1]):
            raise IntegrityError(f"matched state prefix changed: {cell.cell_id}")
        if not np.array_equal(cell.issued[: cell.probe_issue], baseline.issued[: cell.probe_issue]):
            raise IntegrityError(f"matched action prefix changed: {cell.cell_id}")

    vectors: list[np.ndarray] = []
    for cell in cells:
        if cell.kind != "probe":
            continue
        baseline = baselines[cell.family_id]
        for delta in cell.issued - baseline.issued:
            if np.linalg.norm(delta) > 1.0e-12:
                vectors.append(delta)
    action_basis = _stable_basis(np.asarray(vectors))
    return Dataset(tuple(cells), families, baselines, action_basis, source_state, source_current)


def action_coordinates(current: np.ndarray, data: Dataset) -> np.ndarray:
    return np.asarray(current, dtype=np.float64) @ data.action_basis.T


def _velocity(states: np.ndarray, issue: int, lag: int) -> np.ndarray:
    start = max(0, issue - lag)
    width = max(1, issue - start)
    return (states[issue] - states[start]) / float(width)


def _memory(cell: Cell, issue: int, data: Dataset, poles: Sequence[float]) -> np.ndarray:
    deltas = np.zeros((issue, 3), dtype=np.float64)
    previous = data.source_current
    for index in range(issue):
        deltas[index] = action_coordinates(cell.issued[index] - previous, data)
        previous = cell.issued[index]
    rows = []
    for pole in poles:
        value = np.zeros(3, dtype=np.float64)
        for delta in deltas:
            value = float(pole) * value + delta
        rows.append(value)
    return np.concatenate(rows)


def causal_prefix_feature(cell: Cell, issue: int, data: Dataset, stage: dict[str, Any]) -> np.ndarray:
    if not 0 <= issue < 40:
        raise IntegrityError(f"invalid issue: {issue}")
    state = (cell.states[issue] - data.source_state) / STATE_SCALE
    velocity = np.concatenate([_velocity(cell.states, issue, lag) / STATE_SCALE for lag in (1, 2, 4)])
    current = action_coordinates(cell.currents[issue] - data.source_current, data)
    memory = _memory(cell, issue, data, stage["stable_local_event_mixture"]["fixed_action_memory_poles"])
    last_change = 0
    previous = data.source_current
    for index in range(issue):
        if np.max(np.abs(cell.issued[index] - previous)) > 1.0e-12:
            last_change = index
        previous = cell.issued[index]
    age = float(issue - last_change)
    return np.concatenate((
        np.asarray([(issue - 24.0) / 8.0, (cell.nominal_level - 20.0) / 4.0, age / 16.0]),
        state, velocity, current / 2.0, memory / 2.0,
    ))


def _future_action_feature(cell: Cell, origin: int, data: Dataset) -> np.ndarray:
    rows = []
    previous = cell.currents[origin]
    for issue in range(origin, origin + 8):
        target = cell.issued[issue]
        rows.append(action_coordinates(target - previous, data))
        previous = target
    return np.concatenate(rows) / 0.5


def baseline_query_feature(cell: Cell, origin: int, data: Dataset, stage: dict[str, Any]) -> np.ndarray:
    return np.concatenate((causal_prefix_feature(cell, origin, data, stage), _future_action_feature(cell, origin, data)))


def _response_key(cell: Cell, baseline: Cell) -> tuple[float, ...]:
    origin = cell.probe_issue
    delta = cell.issued[origin : origin + 4] - baseline.issued[origin : origin + 4]
    return tuple(np.round(delta, decimals=12).reshape(-1).tolist())


def _scaler(rows: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    center = np.mean(rows, axis=0)
    scale = np.std(rows, axis=0)
    scale = np.where(scale > 1.0e-8, scale, 1.0)
    return center, scale


def _weights(query: np.ndarray, rows: np.ndarray, center: np.ndarray, scale: np.ndarray,
             count: int, floor: float, ridge: float) -> tuple[np.ndarray, np.ndarray]:
    distance = np.linalg.norm((rows - query) / scale, axis=1)
    order = np.argsort(distance, kind="stable")[:count]
    selected = distance[order]
    weight = 1.0 / (np.maximum(selected, floor) ** 2 + ridge)
    weight /= np.sum(weight)
    return order, weight


class LocalEventModel:
    def __init__(self, train_families: Sequence[str], data: Dataset, stage: dict[str, Any]):
        self.train_families = tuple(sorted(train_families))
        self.data = data
        self.stage = stage
        self.baseline_rows: list[tuple[str, int, np.ndarray, np.ndarray]] = []
        for family in self.train_families:
            cell = data.baselines[family]
            for origin in range(16, 33):
                feature = baseline_query_feature(cell, origin, data, stage)
                increments = np.diff(cell.states[origin : origin + 9], axis=0)
                self.baseline_rows.append((family, origin, feature, increments))
        self.baseline_features = np.asarray([row[2] for row in self.baseline_rows])
        self.baseline_center, self.baseline_scale = _scaler(self.baseline_features)

        self.response_rows: list[tuple[str, tuple[float, ...], np.ndarray, np.ndarray]] = []
        for cell in data.cells:
            if cell.family_id not in self.train_families or cell.kind != "probe":
                continue
            baseline = data.baselines[cell.family_id]
            origin = cell.probe_issue
            context = causal_prefix_feature(cell, origin, data, stage)
            response = cell.states[origin : origin + 9] - baseline.states[origin : origin + 9]
            increments = np.diff(response, axis=0)
            self.response_rows.append((cell.family_id, _response_key(cell, baseline), context, increments))
        self.response_features = np.asarray([row[2] for row in self.response_rows])
        self.response_center, self.response_scale = _scaler(self.response_features)
        self.support_threshold = self._support_threshold()
        normalized = (self.response_features - self.response_center) / self.response_scale
        singular = np.linalg.svd(normalized, compute_uv=False)
        rank = int(np.linalg.matrix_rank(normalized))
        self.feature_rank = rank
        self.feature_condition = float(singular[0] / singular[rank - 1]) if rank else math.inf

    def _support_threshold(self) -> float:
        contexts: dict[str, np.ndarray] = {}
        for family in self.train_families:
            cell = next(cell for cell in self.data.cells if cell.family_id == family and cell.kind == "probe")
            contexts[family] = causal_prefix_feature(cell, cell.probe_issue, self.data, self.stage)
        rows = np.asarray(list(contexts.values()))
        scale = self.response_scale
        distances = []
        for family, value in contexts.items():
            others = np.asarray([other for key, other in contexts.items() if key != family])
            distances.append(float(np.min(np.linalg.norm((others - value) / scale, axis=1))))
        multiplier = float(self.stage["stable_local_event_mixture"]["support_multiplier_over_training_leave_one_family_out_max"])
        return multiplier * max(distances)

    def support_distance(self, cell: Cell) -> float:
        query = causal_prefix_feature(cell, cell.probe_issue, self.data, self.stage)
        by_family = []
        for family in self.train_families:
            row = next(row for row in self.response_rows if row[0] == family)
            by_family.append(row[2])
        rows = np.asarray(by_family)
        return float(np.min(np.linalg.norm((rows - query) / self.response_scale, axis=1)))

    def baseline_steps(self, cell: Cell, origin: int) -> np.ndarray:
        query = baseline_query_feature(cell, origin, self.data, self.stage)
        cfg = self.stage["stable_local_event_mixture"]
        order, weight = _weights(query, self.baseline_features, self.baseline_center, self.baseline_scale,
                                 int(cfg["neighbor_count"]), float(cfg["distance_floor"]), float(cfg["ridge"]))
        return np.sum(np.asarray([self.baseline_rows[index][3] for index in order]) * weight[:, None, None], axis=0)

    def response_steps(self, cell: Cell) -> np.ndarray:
        baseline = self.data.baselines[cell.family_id]
        key = _response_key(cell, baseline)
        matches = [index for index, row in enumerate(self.response_rows) if row[1] == key]
        if len(matches) != len(self.train_families):
            raise IntegrityError(f"action signature support changed: {cell.cell_id}")
        query = causal_prefix_feature(cell, cell.probe_issue, self.data, self.stage)
        rows = self.response_features[matches]
        cfg = self.stage["stable_local_event_mixture"]
        order, weight = _weights(query, rows, self.response_center, self.response_scale,
                                 min(int(cfg["neighbor_count"]), len(matches)),
                                 float(cfg["distance_floor"]), float(cfg["ridge"]))
        return np.sum(np.asarray([self.response_rows[matches[index]][3] for index in order]) * weight[:, None, None], axis=0)

    def predict(self, cell: Cell, origin: int) -> np.ndarray:
        baseline = self.data.baselines[cell.family_id]
        base_steps = self.baseline_steps(baseline, origin)
        steps = base_steps if cell.kind == "baseline" else base_steps + self.response_steps(cell)
        return cell.states[origin] + np.cumsum(steps, axis=0)

    def payload(self) -> dict[str, Any]:
        return {
            "kind": CANDIDATES[0], "train_families": list(self.train_families),
            "action_basis": self.data.action_basis.tolist(),
            "baseline_center": self.baseline_center.tolist(), "baseline_scale": self.baseline_scale.tolist(),
            "response_center": self.response_center.tolist(), "response_scale": self.response_scale.tolist(),
            "support_threshold": self.support_threshold, "feature_rank": self.feature_rank,
            "feature_condition": self.feature_condition,
            "baseline_library": [{"family": f, "origin": o, "feature": x.tolist(), "increments": y.tolist()}
                                 for f, o, x, y in self.baseline_rows],
            "response_library": [{"family": f, "action_key": list(k), "context": x.tolist(), "increments": y.tolist()}
                                 for f, k, x, y in self.response_rows],
        }


class ResidualGRU(nn.Module):
    def __init__(self, width: int, input_width: int, cap: np.ndarray):
        super().__init__()
        self.gru = nn.GRU(input_width, width, batch_first=True)
        self.head = nn.Linear(width, 3)
        self.register_buffer("cap", torch.as_tensor(cap, dtype=torch.float32))

    def forward(self, x: torch.Tensor, lengths: torch.Tensor) -> torch.Tensor:
        packed = nn.utils.rnn.pack_padded_sequence(x, lengths.cpu(), batch_first=True, enforce_sorted=False)
        packed_out, _ = self.gru(packed)
        out, _ = nn.utils.rnn.pad_packed_sequence(packed_out, batch_first=True, total_length=x.shape[1])
        return torch.tanh(self.head(out)) * self.cap


def _step_input(cell: Cell, issue: int, state: np.ndarray, previous_state: np.ndarray,
                current: np.ndarray, data: Dataset) -> np.ndarray:
    target = cell.issued[issue]
    previous_target = data.source_current if issue == 0 else cell.issued[issue - 1]
    state_feature = (state - data.source_state) / STATE_SCALE
    velocity = (state - previous_state) / STATE_SCALE
    actual_coord = action_coordinates(current - data.source_current, data) / 2.0
    target_coord = action_coordinates(target - data.source_current, data) / 2.0
    delta_coord = action_coordinates(target - previous_target, data) / 0.5
    changed = float(np.max(np.abs(target - previous_target)) > 1.0e-12)
    return np.concatenate((
        np.asarray([(issue - 24.0) / 8.0, (cell.nominal_level - 20.0) / 4.0, changed]),
        state_feature, velocity, actual_coord, target_coord, delta_coord,
    ))


def _residual_sequence(cell: Cell, origin: int, base_prediction: np.ndarray, data: Dataset) -> np.ndarray:
    rows: list[np.ndarray] = []
    for issue in range(origin):
        previous_state = cell.states[max(0, issue - 1)]
        rows.append(_step_input(cell, issue, cell.states[issue], previous_state, cell.currents[issue], data))
    future_states = np.vstack((cell.states[origin], base_prediction))
    for offset, issue in enumerate(range(origin, origin + 8)):
        state = future_states[offset]
        previous_state = future_states[max(0, offset - 1)] if offset else cell.states[max(0, origin - 1)]
        current = cell.currents[origin] if offset == 0 else cell.issued[issue - 1]
        rows.append(_step_input(cell, issue, state, previous_state, current, data))
    return np.asarray(rows, dtype=np.float64)


@dataclass
class GRUEventModel:
    base: LocalEventModel
    members: list[ResidualGRU]
    input_center: np.ndarray
    input_scale: np.ndarray

    def predict(self, cell: Cell, origin: int) -> np.ndarray:
        base_prediction = self.base.predict(cell, origin)
        sequence = (_residual_sequence(cell, origin, base_prediction, self.base.data) - self.input_center) / self.input_scale
        x = torch.as_tensor(sequence[None], dtype=torch.float32)
        length = torch.as_tensor([len(sequence)], dtype=torch.int64)
        residual = []
        with torch.no_grad():
            for member in self.members:
                value = member(x, length)[0, origin : origin + 8].cpu().numpy().astype(np.float64) * STATE_SCALE
                residual.append(value)
        steps = np.diff(np.vstack((cell.states[origin], base_prediction)), axis=0) + np.mean(residual, axis=0)
        return cell.states[origin] + np.cumsum(steps, axis=0)

    def support_distance(self, cell: Cell) -> float:
        return self.base.support_distance(cell)

    @property
    def support_threshold(self) -> float:
        return self.base.support_threshold

    @property
    def feature_condition(self) -> float:
        return self.base.feature_condition

    def payload(self) -> dict[str, Any]:
        return {
            "kind": CANDIDATES[1], "base": self.base.payload(),
            "input_center": self.input_center.tolist(), "input_scale": self.input_scale.tolist(),
            "members": [{name: tensor.detach().cpu().numpy().tolist() for name, tensor in member.state_dict().items()}
                        for member in self.members],
        }


def _seed_all(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.use_deterministic_algorithms(True)
    torch.set_num_threads(1)


def _training_samples(train_families: Sequence[str], data: Dataset, stage: dict[str, Any]) -> list[tuple[np.ndarray, np.ndarray, int]]:
    samples: list[tuple[np.ndarray, np.ndarray, int]] = []
    for family in train_families:
        inner = [other for other in train_families if other != family]
        if len(inner) < 2:
            raise IntegrityError("insufficient inner families for residual training")
        base = LocalEventModel(inner, data, stage)
        baseline = data.baselines[family]
        selected: list[tuple[Cell, int]] = [(baseline, origin) for origin in range(16, 33)]
        selected += [(cell, cell.probe_issue) for cell in data.cells if cell.family_id == family and cell.kind == "probe"]
        for cell, origin in selected:
            prediction = base.predict(cell, origin)
            sequence = _residual_sequence(cell, origin, prediction, data)
            predicted_steps = np.diff(np.vstack((cell.states[origin], prediction)), axis=0)
            true_steps = np.diff(cell.states[origin : origin + 9], axis=0)
            residual = (true_steps - predicted_steps) / STATE_SCALE
            samples.append((sequence, residual, origin))
    return samples


def fit_gru(train_families: Sequence[str], data: Dataset, stage: dict[str, Any]) -> GRUEventModel:
    base = LocalEventModel(train_families, data, stage)
    samples = _training_samples(train_families, data, stage)
    concatenated = np.concatenate([row[0] for row in samples], axis=0)
    center = np.mean(concatenated, axis=0)
    scale = np.std(concatenated, axis=0)
    scale = np.where(scale > 1.0e-8, scale, 1.0)
    lengths = torch.as_tensor([len(row[0]) for row in samples], dtype=torch.int64)
    maximum = int(torch.max(lengths).item())
    x = np.zeros((len(samples), maximum, concatenated.shape[1]), dtype=np.float32)
    y = np.zeros((len(samples), maximum, 3), dtype=np.float32)
    mask = np.zeros((len(samples), maximum, 1), dtype=np.float32)
    for index, (sequence, residual, origin) in enumerate(samples):
        normalized = (sequence - center) / scale
        x[index, : len(sequence)] = normalized.astype(np.float32)
        y[index, origin : origin + 8] = residual.astype(np.float32)
        mask[index, origin : origin + 8] = 1.0
    tx = torch.as_tensor(x)
    ty = torch.as_tensor(y)
    tm = torch.as_tensor(mask)
    cfg = stage["stable_local_event_gru_residual"]
    members: list[ResidualGRU] = []
    for seed in cfg["seeds"]:
        _seed_all(int(seed))
        member = ResidualGRU(int(cfg["hidden_width"]), x.shape[2], np.asarray(cfg["maximum_residual_increment_scaled"]))
        optimizer = torch.optim.Adam(member.parameters(), lr=float(cfg["learning_rate"]), weight_decay=float(cfg["weight_decay"]))
        for _ in range(int(cfg["epochs"])):
            optimizer.zero_grad(set_to_none=True)
            prediction = member(tx, lengths)
            loss = torch.sum(((prediction - ty) * tm) ** 2) / torch.sum(tm)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(member.parameters(), float(cfg["gradient_norm_cap"]))
            optimizer.step()
        member.eval()
        members.append(member)
    return GRUEventModel(base, members, center, scale)


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    denominator = float(np.linalg.norm(a) * np.linalg.norm(b))
    return float(np.dot(a, b) / denominator) if denominator > 0.0 else -1.0


def _ranking_regret(true: np.ndarray, predicted: np.ndarray) -> float:
    maximum = 0.0
    for angle in np.linspace(0.0, 2.0 * math.pi, 16, endpoint=False):
        direction = np.asarray([math.cos(angle), math.sin(angle)])
        truth_utility = np.max(true[:, :, :2] @ direction, axis=1)
        predicted_utility = np.max(predicted[:, :, :2] @ direction, axis=1)
        chosen = int(np.argmax(predicted_utility))
        best = float(np.max(truth_utility))
        scale = max(abs(best), float(np.ptp(truth_utility)), 2.0e-5)
        maximum = max(maximum, (best - float(truth_utility[chosen])) / scale)
    return float(maximum)


def evaluate(model: LocalEventModel | GRUEventModel, held_family: str, data: Dataset,
             stage: dict[str, Any]) -> dict[str, Any]:
    baseline = data.baselines[held_family]
    probes = sorted(
        [cell for cell in data.cells if cell.family_id == held_family and cell.kind == "probe"],
        key=lambda cell: cell.cell_id,
    )
    support_rows = []
    true_responses = []
    predicted_responses = []
    cosines = []
    base_prediction = model.predict(baseline, baseline.probe_issue)
    for cell in probes:
        distance = model.support_distance(cell)
        supported = bool(distance <= model.support_threshold)
        support_rows.append({"cell_id": cell.cell_id, "distance": distance, "threshold": model.support_threshold, "supported": supported})
        prediction = model.predict(cell, cell.probe_issue)
        true = cell.states[cell.probe_issue + 1 : cell.probe_issue + 9] - baseline.states[cell.probe_issue + 1 : cell.probe_issue + 9]
        predicted = prediction - base_prediction
        true_responses.append(true)
        predicted_responses.append(predicted)
        peak = int(np.argmax(np.linalg.norm(true[:, :2], axis=1)))
        cosines.append(_cosine(true[peak, :2], predicted[peak, :2]))
    true_array = np.asarray(true_responses)
    predicted_array = np.asarray(predicted_responses)
    response_scale = np.asarray([
        stage["evaluation"]["response_scale"]["r_geo_m"],
        stage["evaluation"]["response_scale"]["z_geo_m"],
        stage["evaluation"]["response_scale"]["ip_a"],
    ])
    denominator = float(np.mean((true_array / response_scale) ** 2))
    response_nrmse = math.sqrt(float(np.mean(((predicted_array - true_array) / response_scale) ** 2)) / denominator)

    errors: list[list[np.ndarray]] = [[] for _ in range(8)]
    unique_max = np.zeros(3, dtype=np.float64)
    for origin in range(16, 33):
        prediction = model.predict(baseline, origin)
        error = prediction - baseline.states[origin + 1 : origin + 9]
        for horizon in range(8):
            errors[horizon].append(error[horizon])
        unique_max = np.maximum(unique_max, np.max(np.abs(error), axis=0))
    for cell in probes:
        origin = cell.probe_issue
        error = model.predict(cell, origin) - cell.states[origin + 1 : origin + 9]
        for horizon in range(8):
            errors[horizon].append(error[horizon])
        unique_max = np.maximum(unique_max, np.max(np.abs(error), axis=0))
    p95 = np.asarray([[np.percentile(np.abs(np.asarray(errors[h]))[:, output], 95.0) for output in range(3)] for h in range(8)])
    return {
        "held_family": held_family,
        "support": support_rows,
        "supported_probe_origins": int(sum(row["supported"] for row in support_rows)),
        "response_nrmse": response_nrmse,
        "peak_cosines": cosines,
        "positive_peak_directions": int(sum(value > 0.0 for value in cosines)),
        "time_resolved_utility_ranking_regret_fraction": _ranking_regret(true_array, predicted_array),
        "endpoint_p95_abs_by_horizon": p95.tolist(),
        "maximum_unique_event_abs_error": unique_max.tolist(),
        "all_predictions_finite": bool(np.all(np.isfinite(p95)) and np.all(np.isfinite(predicted_array))),
    }


def eligibility(metrics: dict[str, Any], model: LocalEventModel | GRUEventModel,
                stage: dict[str, Any]) -> list[str]:
    gate = stage["evaluation"]
    failures: list[str] = []
    if metrics["supported_probe_origins"] != gate["required_supported_probe_origins_per_fold"]:
        failures.append("SUPPORT")
    if not metrics["response_nrmse"] < gate["maximum_each_fold_response_nrmse"]:
        failures.append("RESPONSE")
    if metrics["positive_peak_directions"] != gate["required_positive_peak_directions_per_fold"]:
        failures.append("DIRECTION")
    if metrics["time_resolved_utility_ranking_regret_fraction"] > gate["maximum_each_fold_time_resolved_utility_ranking_regret_fraction"]:
        failures.append("RANKING")
    caps = gate["absolute_endpoint_p95_caps"]
    cap_array = np.asarray(list(zip(caps["r_geo_m"], caps["z_geo_m"], caps["ip_a"])))
    if np.any(np.asarray(metrics["endpoint_p95_abs_by_horizon"]) > cap_array):
        failures.append("ABSOLUTE_P95")
    unique_caps = np.asarray(list(gate["maximum_unique_event_abs_error"].values()))
    if np.any(np.asarray(metrics["maximum_unique_event_abs_error"]) > unique_caps):
        failures.append("UNIQUE_EVENT")
    if not metrics["all_predictions_finite"]:
        failures.append("NONFINITE")
    if model.feature_condition > stage["stable_local_event_mixture"]["maximum_scaled_feature_condition"]:
        failures.append("FEATURE_CONDITION")
    return failures


def fit_candidate(kind: str, train_families: Sequence[str], data: Dataset,
                  stage: dict[str, Any]) -> LocalEventModel | GRUEventModel:
    if kind == CANDIDATES[0]:
        return LocalEventModel(train_families, data, stage)
    if kind == CANDIDATES[1]:
        return fit_gru(train_families, data, stage)
    raise IntegrityError(f"unknown candidate: {kind}")


def compare(data: Dataset, stage: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any] | None]:
    candidate_results = []
    fitted: dict[str, LocalEventModel | GRUEventModel] = {}
    for kind in CANDIDATES:
        folds = []
        for fold in stage["whole_family_folds"]:
            held = fold["held_family_ids"][0]
            train = [family for family in data.families if family != held]
            model = fit_candidate(kind, train, data, stage)
            metrics = evaluate(model, held, data, stage)
            failures = eligibility(metrics, model, stage)
            folds.append({
                "fold_id": fold["fold_id"], "held_family_ids": [held],
                "metrics": metrics, "feature_rank": model.base.feature_rank if isinstance(model, GRUEventModel) else model.feature_rank,
                "feature_condition": model.feature_condition, "failures": failures, "eligible": not failures,
            })
        summary = {
            "mean_response_nrmse": float(np.mean([row["metrics"]["response_nrmse"] for row in folds])),
            "worst_response_nrmse": float(max(row["metrics"]["response_nrmse"] for row in folds)),
            "worst_endpoint_p95": float(np.max([row["metrics"]["endpoint_p95_abs_by_horizon"] for row in folds])),
            "minimum_peak_cosine": float(min(min(row["metrics"]["peak_cosines"]) for row in folds)),
            "maximum_ranking_regret": float(max(row["metrics"]["time_resolved_utility_ranking_regret_fraction"] for row in folds)),
        }
        candidate_results.append({"kind": kind, "eligible": all(row["eligible"] for row in folds), "folds": folds, "summary": summary})

    eligible = [row for row in candidate_results if row["eligible"]]
    selected: dict[str, Any] | None = None
    local = candidate_results[0]
    recurrent = candidate_results[1]
    if local["eligible"]:
        selected = local
        if recurrent["eligible"]:
            improvement = 1.0 - recurrent["summary"]["worst_response_nrmse"] / local["summary"]["worst_response_nrmse"]
            regression = recurrent["summary"]["worst_endpoint_p95"] / max(local["summary"]["worst_endpoint_p95"], 1.0e-15) - 1.0
            if improvement >= stage["selection"]["minimum_gru_worst_fold_response_improvement_fraction"] and regression <= stage["selection"]["maximum_gru_worst_endpoint_p95_regression_fraction"]:
                selected = recurrent
    elif recurrent["eligible"]:
        selected = recurrent

    payload = None
    if selected is not None:
        final = fit_candidate(selected["kind"], data.families, data, stage)
        fitted[selected["kind"]] = final
        payload = {
            "schema_version": MODEL_SCHEMA, "stage_config_sha256": CONFIG_SHA256,
            "selected_kind": selected["kind"], "development_families": list(data.families),
            "model": final.payload(), "claim_boundary": stage["claim_boundary"],
        }
    return {
        "candidate_results": candidate_results,
        "selected_kind": None if selected is None else selected["kind"],
        "eligible_candidate_count": len(eligible),
    }, payload


def compute(stage_path: Path = CONFIG, source_revision: str = "development") -> tuple[dict[str, Any], dict[str, Any] | None]:
    stage = load_stage(stage_path)
    data = load_dataset(stage)
    comparison, payload = compare(data, stage)
    passed = payload is not None
    result = {
        "schema_version": SCHEMA, "source_revision": source_revision,
        "stage_config_sha256": sha256(inside(stage_path, "stage config")),
        "passed": passed,
        "route": stage["routes"]["pass" if passed else "no_eligible_candidate"],
        "development_family_ids": list(data.families), "development_cells_read": len(data.cells),
        "calibration_family_ids_read": [], "blind_holdout_family_ids_read": [],
        "new_tsc_calls": 0, "reset_calls": 0, "plant_advances": 0,
        "candidate_count": 2, "candidate_fold_fits": 8, "final_full_fits": int(passed),
        "action_rank": int(data.action_basis.shape[0]), "comparison": comparison,
        "model_payload_sha256": None if payload is None else canonical_sha256(payload),
        "claim_boundary": stage["claim_boundary"],
    }
    return result, payload


def preflight(stage_path: Path = CONFIG) -> dict[str, Any]:
    stage = load_stage(stage_path)
    data = load_dataset(stage)
    return {
        "passed": True, "stage_config_sha256": sha256(inside(stage_path, "stage config")),
        "families": list(data.families), "cells": len(data.cells), "action_rank": int(data.action_basis.shape[0]),
        "candidates": list(CANDIDATES), "new_tsc_calls": 0,
    }


def execute(stage_path: Path, source_revision: str, output_dir: Path) -> dict[str, Any]:
    output = inside(output_dir, "output directory")
    if output.exists():
        raise IntegrityError(f"refusing existing output: {output}")
    result, payload = compute(stage_path, source_revision)
    output.mkdir(parents=True, exist_ok=False)
    write_new(output / "result.json", result)
    if payload is not None:
        write_new(output / "model.json", payload)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument("--source-revision", default="development")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args(argv)
    if args.preflight:
        print(json.dumps(preflight(args.config), indent=2, sort_keys=True))
        return 0
    if args.output_dir is None:
        parser.error("--output-dir is required unless --preflight is used")
    result = execute(args.config, args.source_revision, args.output_dir)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
