"""Fit the frozen ID-2L1 structured history model comparison on the server."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import random
import sys
from typing import Any, Iterable, Sequence

import numpy as np
import torch
from torch import nn


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


CONFIG = ROOT / "configs" / "rgeo_zgeo_1ms_id2l1_structured_history_model_comparison.json"
CONFIG_SHA256 = "5480a8124472020c4069c0b0fb00e2be235c7657d01bd9a4c76946f9e2910efe"
SCHEMA = "rgeo-zgeo-1ms-id2l1-structured-history-model-result-v1"
DATASET_SCHEMA = "rgeo-zgeo-1ms-id2l1-allowed-development-dataset-v1"
MODEL_SCHEMA = "rgeo-zgeo-1ms-id2l1-selected-model-v1"


class IntegrityError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def inside(path: Path, label: str) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise IntegrityError(f"{label} escapes repository root") from exc
    return resolved


def write_new(path: Path, value: Any) -> None:
    path = inside(path, "output")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise IntegrityError(f"refusing to overwrite {path}")
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def _load_json(path: Path, expected_hash: str, label: str) -> dict[str, Any]:
    path = inside(path, label)
    if not path.is_file() or sha256(path) != expected_hash:
        raise IntegrityError(f"{label} hash mismatch")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise IntegrityError(f"{label} is not an object")
    return value


def load_stage(path: Path = CONFIG) -> dict[str, Any]:
    path = inside(path, "stage config")
    if sha256(path) != CONFIG_SHA256:
        raise IntegrityError("ID2L1 config hash mismatch")
    stage = json.loads(path.read_text(encoding="utf-8"))
    design = stage["design"]
    if sha256(inside(ROOT / design["path"], "design")) != design["sha256"]:
        raise IntegrityError("ID2L1 design hash mismatch")
    if any(int(stage[key]) != 0 for key in ("new_tsc_calls", "reset_calls", "plant_advances")):
        raise IntegrityError("zero-plant contract changed")
    source = stage["source"]
    primary = _load_json(ROOT / source["primary"], source["primary_sha256"], "ID2K1 primary")
    independent = _load_json(ROOT / source["independent"], source["independent_sha256"], "ID2K1 independent")
    if not primary.get("passed") or primary.get("route") != source["required_route"]:
        raise IntegrityError("ID2K1 primary is not fit-eligible")
    if not primary.get("development_fit_data_eligible") or not independent.get("audit_passed"):
        raise IntegrityError("ID2K1 independent/data-use gate failed")
    for key, expected in (
        ("rollouts_completed", source["required_rollouts"]),
        ("unique_cells_completed", source["required_unique_cells"]),
        ("verified_plant_advances", source["required_advances"]),
        ("required_artifact_files", source["required_artifact_files"]),
        ("required_artifact_bytes", source["required_artifact_bytes"]),
        ("required_artifact_inventory_sha256", source["required_artifact_inventory_sha256"]),
    ):
        if primary.get(key) != expected:
            raise IntegrityError(f"ID2K1 primary field changed: {key}")
    if independent.get("recomputed_inventory_sha256") != source["required_artifact_inventory_sha256"]:
        raise IntegrityError("ID2K1 independent inventory changed")
    return stage


def _compact_digest(files: Sequence[Path]) -> tuple[int, str]:
    digest = hashlib.sha256()
    total = 0
    for path in files:
        payload = path.read_bytes()
        total += len(payload)
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(payload).hexdigest().encode("ascii"))
        digest.update(b"\n")
    return total, digest.hexdigest()


@dataclass
class Cell:
    cell_id: str
    group_id: str
    cell_kind: str
    states: np.ndarray
    currents: np.ndarray
    issued: np.ndarray
    direction: str | None
    sign: str | None


@dataclass
class Dataset:
    cells: list[Cell]
    source_state: np.ndarray
    source_current: np.ndarray
    nominal_issued: np.ndarray
    action_basis: np.ndarray
    action_rank: int
    state_scale: np.ndarray
    response_scale: np.ndarray


def _target(action: dict[str, Any]) -> np.ndarray:
    value = np.asarray([float(item) for item in action["target_current_a_tsc"]], dtype=np.float64)
    if value.shape != (14,) or not np.all(np.isfinite(value)):
        raise IntegrityError("invalid issued target")
    return value


def _state(row: dict[str, Any]) -> tuple[np.ndarray, np.ndarray]:
    rzi = np.asarray([row["r_geo_m"], row["z_geo_m"], row["ip_a"]], dtype=np.float64)
    current = np.asarray([float(item) for item in row["actual_current_decimal_a_tsc"]], dtype=np.float64)
    if rzi.shape != (3,) or current.shape != (14,) or not np.all(np.isfinite(rzi)) or not np.all(np.isfinite(current)):
        raise IntegrityError("invalid compact state")
    return rzi, current


def _stable_svd_basis(vectors: np.ndarray, expected_rank: int) -> np.ndarray:
    _, singular, vt = np.linalg.svd(vectors, full_matrices=False)
    rank = int(np.linalg.matrix_rank(vectors, tol=1e-12))
    if rank != expected_rank or singular[rank - 1] <= 0:
        raise IntegrityError(f"four-primitive action rank changed: {rank}")
    basis = vt[:rank].copy()
    for index in range(rank):
        pivot = int(np.argmax(np.abs(basis[index])))
        if basis[index, pivot] < 0:
            basis[index] *= -1.0
    return basis


def extract_dataset(stage: dict[str, Any]) -> Dataset:
    source = stage["source"]
    folder = inside(ROOT / source["audit_directory"], "ID2K1 compact directory")
    files = sorted(folder.glob("h*.json"), key=lambda item: item.name)
    size, digest = _compact_digest(files)
    if len(files) != source["compact_inventory_files"] or size != source["compact_inventory_bytes"]:
        raise IntegrityError("ID2K1 compact count/bytes changed")
    if digest != source["compact_inventory_sha256"]:
        raise IntegrityError("ID2K1 compact inventory digest changed")

    rows = [json.loads(path.read_text(encoding="utf-8")) for path in files]
    if any(not row.get("passed") or row.get("source_revision") != source["implementation_revision"] for row in rows):
        raise IntegrityError("ID2K1 compact verdict/revision changed")
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row["cell_id"], []).append(row)
    if len(grouped) != source["required_unique_cells"]:
        raise IntegrityError("ID2K1 unique-cell count changed")

    cells: list[Cell] = []
    source_state: np.ndarray | None = None
    source_current: np.ndarray | None = None
    for cell_id, members in sorted(grouped.items()):
        primary = next((row for row in members if int(row["replay_index"]) == 0), None)
        if primary is None:
            raise IntegrityError(f"missing primary compact: {cell_id}")
        states = []
        currents = []
        for index, row in enumerate(primary["states"]):
            if int(row["time_ms"]) != 1100 + index:
                raise IntegrityError(f"state clock mismatch: {cell_id}:{index}")
            rzi, current = _state(row)
            states.append(rzi)
            currents.append(current)
        issued = np.asarray([_target(action) for action in primary["actions"]], dtype=np.float64)
        states_array = np.asarray(states, dtype=np.float64)
        currents_array = np.asarray(currents, dtype=np.float64)
        if states_array.shape != (35, 3) or currents_array.shape != (35, 14) or issued.shape != (34, 14):
            raise IntegrityError(f"compact shape mismatch: {cell_id}")
        if source_state is None:
            source_state = states_array[0].copy()
            source_current = currents_array[0].copy()
        if not np.array_equal(states_array[0], source_state) or not np.array_equal(currents_array[0], source_current):
            raise IntegrityError(f"source mismatch: {cell_id}")
        for replay in members:
            if int(replay["replay_index"]) == 0:
                continue
            replay_states = np.asarray([_state(row)[0] for row in replay["states"]], dtype=np.float64)
            replay_currents = np.asarray([_state(row)[1] for row in replay["states"]], dtype=np.float64)
            replay_issued = np.asarray([_target(action) for action in replay["actions"]], dtype=np.float64)
            if not (np.array_equal(states_array, replay_states) and np.array_equal(currents_array, replay_currents)
                    and np.array_equal(issued, replay_issued)):
                raise IntegrityError(f"critical replay differs: {cell_id}")
        cells.append(Cell(
            cell_id=cell_id,
            group_id=primary["group_id"],
            cell_kind=primary["cell_kind"],
            states=states_array,
            currents=currents_array,
            issued=issued,
            direction=primary.get("direction_id"),
            sign=primary.get("sign"),
        ))
    assert source_state is not None and source_current is not None
    histories = sorted({cell.group_id for cell in cells})
    if histories != stage["data_contract"]["unique_histories"]:
        raise IntegrityError("history family set changed")
    if any(sum(cell.group_id == group for cell in cells) != 5 for group in histories):
        raise IntegrityError("history family cardinality changed")

    reference = next(cell for cell in cells if cell.group_id == "h00" and cell.cell_kind == "baseline")
    nominal = reference.issued.copy()
    nominal[18:] = reference.issued[17]
    primitive = []
    for direction, sign in (("p04", "minus"), ("p04", "plus"), ("p07", "minus"), ("p07", "plus")):
        cell = next(row for row in cells if row.direction == direction and row.sign == sign)
        primitive.append(cell.issued[25] - nominal[25])
    basis = _stable_svd_basis(
        np.asarray(primitive, dtype=np.float64),
        int(stage["data_contract"]["expected_action_basis_rank"]),
    )
    maximum_residual = 0.0
    for cell in cells:
        delta = cell.issued - nominal
        coordinate = delta @ basis.T
        maximum_residual = max(maximum_residual, float(np.max(np.abs(delta - coordinate @ basis))))
    if maximum_residual > stage["data_contract"]["maximum_action_basis_reconstruction_residual_a"]:
        raise IntegrityError(f"action basis residual changed: {maximum_residual}")
    return Dataset(
        cells=cells,
        source_state=source_state,
        source_current=source_current,
        nominal_issued=nominal,
        action_basis=basis,
        action_rank=basis.shape[0],
        state_scale=np.asarray(stage["normalization"]["state_scale"], dtype=np.float64),
        response_scale=np.asarray(stage["normalization"]["response_scale"], dtype=np.float64),
    )


def dataset_payload(data: Dataset, stage: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": DATASET_SCHEMA,
        "claim_boundary": "ID2K1 development-fit fields only; forbidden as fixture, calibration or holdout.",
        "source_primary_sha256": stage["source"]["primary_sha256"],
        "source_independent_sha256": stage["source"]["independent_sha256"],
        "source_state_rzi": data.source_state.tolist(),
        "source_current_a": data.source_current.tolist(),
        "nominal_issued_a": data.nominal_issued.tolist(),
        "action_basis": data.action_basis.tolist(),
        "action_rank": data.action_rank,
        "state_scale": data.state_scale.tolist(),
        "response_scale": data.response_scale.tolist(),
        "cells": [{
            "cell_id": cell.cell_id,
            "group_id_evaluator_only": cell.group_id,
            "cell_kind_evaluator_only": cell.cell_kind,
            "direction_evaluator_only": cell.direction,
            "sign_evaluator_only": cell.sign,
            "states_rzi": cell.states.tolist(),
            "actual_current_a": cell.currents.tolist(),
            "issued_card15_a": cell.issued.tolist(),
            "unit_weight": 1.0,
        } for cell in data.cells],
    }


def action_coordinates(cell: Cell, data: Dataset, action_blind: bool = False) -> np.ndarray:
    if action_blind:
        return np.zeros((34, data.action_rank), dtype=np.float64)
    return (cell.issued - data.nominal_issued) @ data.action_basis.T


def context_matrix(cell: Cell, data: Dataset) -> np.ndarray:
    rows = []
    for issue in range(34):
        current = (cell.states[issue] - data.source_state) / data.state_scale
        previous = (cell.states[issue] - cell.states[max(0, issue - 1)]) / data.state_scale
        start = max(0, issue - 4)
        mean = (cell.states[issue] - cell.states[start]) / max(1, issue - start) / data.state_scale
        rows.append(np.clip(np.concatenate([current, previous, mean]), -20.0, 20.0))
    return np.asarray(rows, dtype=np.float64)


def memory_matrix(cell: Cell, data: Dataset, poles: Sequence[float], action_blind: bool = False) -> dict[str, np.ndarray]:
    u = action_coordinates(cell, data, action_blind)
    du = np.vstack([u[0], u[1:] - u[:-1]])
    shape = (len(poles), data.action_rank)
    level = np.zeros(shape, dtype=np.float64)
    edge = np.zeros(shape, dtype=np.float64)
    level_even = np.zeros(shape, dtype=np.float64)
    edge_even = np.zeros(shape, dtype=np.float64)
    values = {key: [] for key in ("level", "edge", "level_even", "edge_even")}
    pole_array = np.asarray(poles, dtype=np.float64)[:, None]
    for issue in range(34):
        level = pole_array * level + u[issue]
        edge = pole_array * edge + du[issue]
        level_even = pole_array * level_even + np.abs(u[issue])
        edge_even = pole_array * edge_even + np.abs(du[issue])
        values["level"].append(level.copy())
        values["edge"].append(edge.copy())
        values["level_even"].append(level_even.copy())
        values["edge_even"].append(edge_even.copy())
    return {key: np.asarray(value, dtype=np.float64) for key, value in values.items()}


def feature_matrix(cell: Cell, data: Dataset, stage: dict[str, Any], kind: str,
                   context_origin: int | None = None) -> np.ndarray:
    action_blind = kind == "action_blind"
    memory = memory_matrix(cell, data, stage["backbone"]["fixed_poles"], action_blind)
    contexts = context_matrix(cell, data)
    rows = []
    for issue in range(34):
        time = np.zeros(34, dtype=np.float64)
        time[issue] = 1.0
        if action_blind:
            rows.append(time)
            continue
        signed = np.concatenate([memory["level"][issue].reshape(-1), memory["edge"][issue].reshape(-1)])
        row = [time, signed]
        if kind in ("stable_signed_even", "stable_contextual"):
            even = np.concatenate([memory["level_even"][issue].reshape(-1), memory["edge_even"][issue].reshape(-1)])
            row.append(even)
        if kind == "stable_contextual":
            context = contexts[issue if context_origin is None else context_origin]
            last = np.concatenate([
                memory["level"][issue, -1], memory["edge"][issue, -1],
                memory["level_even"][issue, -1], memory["edge_even"][issue, -1],
            ])
            row.append(np.outer(last, context).reshape(-1))
        rows.append(np.concatenate(row))
    return np.asarray(rows, dtype=np.float64)


class RidgeModel:
    def __init__(self, kind: str, scale: np.ndarray, coefficients: np.ndarray, stage: dict[str, Any]):
        self.kind = kind
        self.scale = scale
        self.coefficients = coefficients
        self.stage = stage

    def normalized_deltas(self, cell: Cell, data: Dataset, context_origin: int | None = None) -> np.ndarray:
        features = feature_matrix(cell, data, self.stage, self.kind, context_origin)
        return (features / self.scale) @ self.coefficients

    def payload(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "feature_scale": self.scale.tolist(),
            "coefficients": self.coefficients.tolist(),
        }


def fit_ridge(kind: str, cells: Sequence[Cell], data: Dataset, stage: dict[str, Any]) -> RidgeModel:
    features = {cell.cell_id: feature_matrix(cell, data, stage, kind) for cell in cells}
    targets = {cell.cell_id: (cell.states[1:] - cell.states[:-1]) / data.response_scale for cell in cells}
    x_rows = [features[cell.cell_id] for cell in cells]
    y_rows = [targets[cell.cell_id] for cell in cells]
    by_group = {group: next(cell for cell in cells if cell.group_id == group and cell.cell_kind == "baseline")
                for group in sorted({cell.group_id for cell in cells})}
    weight = math.sqrt(float(stage["backbone"]["paired_loss_weight"]))
    start = int(stage["backbone"]["paired_loss_start_issue"])
    for cell in cells:
        if cell.cell_kind == "baseline":
            continue
        baseline = by_group[cell.group_id]
        x_rows.append(weight * (features[cell.cell_id][start:] - features[baseline.cell_id][start:]))
        y_rows.append(weight * (targets[cell.cell_id][start:] - targets[baseline.cell_id][start:]))
    x = np.concatenate(x_rows, axis=0)
    y = np.concatenate(y_rows, axis=0)
    scale = np.sqrt(np.mean(x * x, axis=0))
    scale = np.where(scale > 1e-10, scale, 1.0)
    normalized = x / scale
    ridge = float(stage["candidates"][kind]["ridge"])
    coefficients = np.linalg.solve(normalized.T @ normalized + ridge * np.eye(normalized.shape[1]), normalized.T @ y)
    if not np.all(np.isfinite(coefficients)):
        raise IntegrityError(f"non-finite ridge coefficients: {kind}")
    return RidgeModel(kind, scale, coefficients, stage)


def gru_input(cell: Cell, data: Dataset, stage: dict[str, Any], context_origin: int | None = None) -> np.ndarray:
    memory = memory_matrix(cell, data, stage["backbone"]["fixed_poles"])
    u = action_coordinates(cell, data)
    du = np.vstack([u[0], u[1:] - u[:-1]])
    contexts = context_matrix(cell, data)
    rows = []
    for issue in range(34):
        context = contexts[issue if context_origin is None else context_origin]
        rows.append(np.concatenate([
            [issue / 34.0], u[issue], du[issue],
            memory["level"][issue].reshape(-1), memory["edge"][issue].reshape(-1),
            memory["level_even"][issue].reshape(-1), memory["edge_even"][issue].reshape(-1),
            context,
        ]))
    return np.asarray(rows, dtype=np.float64)


class ResidualGRU(nn.Module):
    def __init__(self, input_width: int, hidden_width: int, cap: np.ndarray):
        super().__init__()
        self.gru = nn.GRU(input_width, hidden_width, batch_first=True)
        self.head = nn.Linear(hidden_width, 3)
        self.register_buffer("cap", torch.tensor(cap, dtype=torch.float32))

    def forward(self, value: torch.Tensor) -> torch.Tensor:
        return torch.tanh(self.head(self.gru(value)[0])) * self.cap


class GRUModel:
    def __init__(self, base: RidgeModel, modules: Sequence[ResidualGRU], mean: np.ndarray,
                 scale: np.ndarray, stage: dict[str, Any]):
        self.base = base
        self.modules = [module.eval() for module in modules]
        self.mean = mean
        self.scale = scale
        self.stage = stage

    def normalized_deltas(self, cell: Cell, data: Dataset, context_origin: int | None = None) -> np.ndarray:
        base = self.base.normalized_deltas(cell, data, context_origin)
        x = (gru_input(cell, data, self.stage, context_origin) - self.mean) / self.scale
        tensor = torch.tensor(x[None, :, :], dtype=torch.float32)
        with torch.no_grad():
            residual = np.mean([module(tensor)[0].cpu().numpy() for module in self.modules], axis=0)
        return base + residual.astype(np.float64)

    def payload(self) -> dict[str, Any]:
        members = []
        for module in self.modules:
            members.append({name: tensor.detach().cpu().numpy().tolist()
                            for name, tensor in sorted(module.state_dict().items())})
        return {
            "kind": "structured_gru_residual",
            "base": self.base.payload(),
            "input_mean": self.mean.tolist(),
            "input_scale": self.scale.tolist(),
            "members": members,
            "seeds": self.stage["candidates"]["structured_gru_residual"]["seeds"],
        }


def _seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.use_deterministic_algorithms(True)
    torch.set_num_threads(1)


def fit_gru(cells: Sequence[Cell], data: Dataset, stage: dict[str, Any]) -> GRUModel:
    cfg = stage["candidates"]["structured_gru_residual"]
    base = fit_ridge(cfg["base_candidate"], cells, data, stage)
    x_np = np.asarray([gru_input(cell, data, stage) for cell in cells], dtype=np.float64)
    mean = np.mean(x_np, axis=(0, 1))
    scale = np.std(x_np, axis=(0, 1))
    scale = np.where(scale > 1e-8, scale, 1.0)
    x = torch.tensor((x_np - mean) / scale, dtype=torch.float32)
    truth = np.asarray([(cell.states[1:] - cell.states[:-1]) / data.response_scale for cell in cells], dtype=np.float64)
    base_prediction = np.asarray([base.normalized_deltas(cell, data) for cell in cells], dtype=np.float64)
    residual_target = torch.tensor(truth - base_prediction, dtype=torch.float32)
    baseline_index = {cell.group_id: index for index, cell in enumerate(cells) if cell.cell_kind == "baseline"}
    pairs = [(index, baseline_index[cell.group_id]) for index, cell in enumerate(cells) if cell.cell_kind != "baseline"]
    cap = np.asarray(cfg["maximum_residual_delta"], dtype=np.float64) / data.response_scale
    modules = []
    for seed in cfg["seeds"]:
        _seed(int(seed))
        module = ResidualGRU(x.shape[-1], int(cfg["hidden_width"]), cap)
        optimizer = torch.optim.Adam(module.parameters(), lr=float(cfg["learning_rate"]),
                                     weight_decay=float(cfg["weight_decay"]))
        module.train()
        for _ in range(int(cfg["epochs"])):
            optimizer.zero_grad(set_to_none=True)
            prediction = module(x)
            absolute = torch.mean((prediction - residual_target) ** 2)
            paired_terms = []
            for probe, baseline in pairs:
                paired_terms.append(torch.mean(
                    ((prediction[probe, 25:] - prediction[baseline, 25:])
                     - (residual_target[probe, 25:] - residual_target[baseline, 25:])) ** 2
                ))
            paired = torch.stack(paired_terms).mean()
            loss = absolute + float(stage["backbone"]["paired_loss_weight"]) * paired
            loss.backward()
            torch.nn.utils.clip_grad_norm_(module.parameters(), float(cfg["gradient_clip"]))
            optimizer.step()
        modules.append(module.eval())
    return GRUModel(base, modules, mean, scale, stage)


def fit_candidate(kind: str, cells: Sequence[Cell], data: Dataset, stage: dict[str, Any]) -> Any:
    if kind == "structured_gru_residual":
        return fit_gru(cells, data, stage)
    return fit_ridge(kind, cells, data, stage)


def _p95(errors: Iterable[np.ndarray]) -> list[float]:
    array = np.concatenate(list(errors), axis=0)
    return np.quantile(np.abs(array), 0.95, axis=0).tolist()


def _maximum(errors: Iterable[np.ndarray]) -> list[float]:
    array = np.concatenate(list(errors), axis=0)
    return np.max(np.abs(array), axis=0).tolist()


def _predict_segment(model: Any, cell: Cell, data: Dataset, origin: int, stop: int) -> np.ndarray:
    delta = model.normalized_deltas(cell, data, context_origin=origin) * data.response_scale
    values = [cell.states[origin].copy()]
    for issue in range(origin, stop):
        values.append(values[-1] + delta[issue])
    return np.asarray(values, dtype=np.float64)


def evaluate(model: Any, held: Sequence[Cell], data: Dataset, stage: dict[str, Any]) -> dict[str, Any]:
    teacher_errors = []
    recenter_errors: dict[int, list[np.ndarray]] = {period: [] for period in stage["data_contract"]["recenter_periods_ms"]}
    free_errors = []
    free_predictions: dict[str, np.ndarray] = {}
    for cell in held:
        delta = model.normalized_deltas(cell, data) * data.response_scale
        teacher_errors.append(cell.states[:-1] + delta - cell.states[1:])
        start = int(stage["data_contract"]["recenter_evaluation_origin_state"])
        for period in recenter_errors:
            predictions = []
            truths = []
            origin = start
            while origin < 34:
                stop = min(34, origin + period)
                segment = _predict_segment(model, cell, data, origin, stop)
                predictions.append(segment[1:])
                truths.append(cell.states[origin + 1:stop + 1])
                origin = stop
            recenter_errors[period].append(np.concatenate(predictions) - np.concatenate(truths))
        free = _predict_segment(model, cell, data, 25, 34)
        free_predictions[cell.cell_id] = free
        free_errors.append(free[1:] - cell.states[26:35])

    true_response = []
    predicted_response = []
    cosines = []
    for group in sorted({cell.group_id for cell in held}):
        baseline = next(cell for cell in held if cell.group_id == group and cell.cell_kind == "baseline")
        for cell in held:
            if cell.group_id != group or cell.cell_kind == "baseline":
                continue
            truth = cell.states[26:35] - baseline.states[26:35]
            predicted = free_predictions[cell.cell_id][1:] - free_predictions[baseline.cell_id][1:]
            true_response.append(truth / data.response_scale)
            predicted_response.append(predicted / data.response_scale)
            peak = int(np.argmax(np.linalg.norm(truth[:, :2], axis=1)))
            denominator = float(np.linalg.norm(truth[peak, :2]) * np.linalg.norm(predicted[peak, :2]))
            cosines.append(float(np.dot(truth[peak, :2], predicted[peak, :2]) / denominator)
                           if denominator > 0 else -1.0)
    truth_array = np.concatenate(true_response)
    prediction_array = np.concatenate(predicted_response)
    denominator = float(np.linalg.norm(truth_array))
    response_nrmse = float(np.linalg.norm(prediction_array - truth_array) / denominator) if denominator > 0 else math.inf
    all_errors = [*teacher_errors, *free_errors]
    for values in recenter_errors.values():
        all_errors.extend(values)
    return {
        "teacher_one_step_p95_abs": _p95(teacher_errors),
        "recenter_p95_abs": {str(period): _p95(values) for period, values in recenter_errors.items()},
        "free_state25_p95_abs": _p95(free_errors),
        "maximum_abs_error": _maximum(all_errors),
        "response_nrmse": response_nrmse,
        "positive_peak_cosine_count": sum(value > 0 for value in cosines),
        "peak_cosines": cosines,
        "held_probe_count": len(cosines),
    }


def _cap_failure(values: Sequence[float], caps: Sequence[float]) -> bool:
    return any(not math.isfinite(float(value)) or float(value) > float(cap) for value, cap in zip(values, caps))


def eligibility(kind: str, folds: Sequence[dict[str, Any]], blind_mean: float,
                summaries: dict[str, Any], stage: dict[str, Any]) -> tuple[bool, list[str]]:
    gate = stage["eligibility"]
    failures = []
    recenter_caps = {
        "1": gate["recenter_1ms_p95_abs_max"],
        "2": gate["recenter_2ms_p95_abs_max"],
        "4": gate["recenter_4ms_p95_abs_max"],
    }
    for row in folds:
        fold_id = row["fold_id"]
        if _cap_failure(row["teacher_one_step_p95_abs"], gate["teacher_one_step_p95_abs_max"]):
            failures.append(f"TEACHER:{fold_id}")
        for period, caps in recenter_caps.items():
            if _cap_failure(row["recenter_p95_abs"][period], caps):
                failures.append(f"RECENTER_{period}:{fold_id}")
        if _cap_failure(row["free_state25_p95_abs"], gate["free_state25_p95_abs_max"]):
            failures.append(f"FREE:{fold_id}")
        if _cap_failure(row["maximum_abs_error"], gate["catastrophic_max_abs"]):
            failures.append(f"CATASTROPHIC:{fold_id}")
        if not float(row["response_nrmse"]) < float(gate["each_fold_response_nrmse_strict_max"]):
            failures.append(f"RESPONSE:{fold_id}")
        if int(row["positive_peak_cosine_count"]) < int(gate["minimum_positive_peak_cosine_per_fold"]):
            failures.append(f"PEAK:{fold_id}")
    mean = float(np.mean([row["response_nrmse"] for row in folds]))
    if mean > float(gate["mean_response_nrmse_max"]):
        failures.append("MEAN_RESPONSE")
    if blind_mean <= 0 or 1.0 - mean / blind_mean < float(gate["minimum_action_blind_improvement_fraction"]):
        failures.append("ACTION_BLIND_IMPROVEMENT")
    if sum(row["positive_peak_cosine_count"] for row in folds) < int(gate["minimum_positive_peak_cosine_total"]):
        failures.append("TOTAL_PEAK")
    if kind == "structured_gru_residual":
        base = summaries["stable_signed_even"]["folds"]
        cfg = stage["candidates"][kind]
        base_mean = float(np.mean([row["response_nrmse"] for row in base]))
        if base_mean <= 0 or 1.0 - mean / base_mean < float(cfg["minimum_mean_response_improvement_over_base"]):
            failures.append("GRU_MEAN_GAIN")
        for row, baseline in zip(folds, base):
            if float(row["response_nrmse"]) > float(baseline["response_nrmse"]) * (
                    1.0 + float(cfg["maximum_each_fold_response_regression_fraction"])):
                failures.append(f"GRU_FOLD_REGRESSION:{row['fold_id']}")
    return not failures, failures


def compare(data: Dataset, stage: dict[str, Any]) -> dict[str, Any]:
    kinds = ["action_blind", *stage["eligibility"]["simplicity_order"]]
    summaries: dict[str, Any] = {kind: {"folds": []} for kind in kinds}
    for fold in stage["folds"]:
        held_set = set(fold["held_histories"])
        train = [cell for cell in data.cells if cell.group_id not in held_set]
        held = [cell for cell in data.cells if cell.group_id in held_set]
        if len(train) != 30 or len(held) != 10 or len({cell.group_id for cell in held}) != 2:
            raise IntegrityError(f"fold cardinality changed: {fold['fold_id']}")
        for kind in kinds:
            model = fit_candidate(kind, train, data, stage)
            summaries[kind]["folds"].append({
                "fold_id": fold["fold_id"],
                "held_histories": fold["held_histories"],
                **evaluate(model, held, data, stage),
            })
    blind_mean = float(np.mean([row["response_nrmse"] for row in summaries["action_blind"]["folds"]]))
    eligible = []
    for kind in kinds:
        folds = summaries[kind]["folds"]
        summaries[kind]["mean_response_nrmse"] = float(np.mean([row["response_nrmse"] for row in folds]))
        summaries[kind]["total_positive_peak_cosine"] = int(sum(row["positive_peak_cosine_count"] for row in folds))
        if not stage["candidates"][kind]["selectable"]:
            summaries[kind]["eligible"] = False
            summaries[kind]["eligibility_failures"] = ["NOT_SELECTABLE"]
            continue
        passed, failures = eligibility(kind, folds, blind_mean, summaries, stage)
        summaries[kind]["eligible"] = passed
        summaries[kind]["eligibility_failures"] = failures
        if passed:
            eligible.append(kind)
    selected = next((kind for kind in stage["eligibility"]["simplicity_order"] if kind in eligible), None)
    return {
        "action_blind_mean_response_nrmse": blind_mean,
        "candidates": summaries,
        "eligible_candidates": eligible,
        "selected_candidate": selected,
        "selection_rule": "first_eligible_in_frozen_simplicity_order",
    }


def selected_model_payload(kind: str, model: Any, data: Dataset, stage: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": MODEL_SCHEMA,
        "selected_candidate": kind,
        "source_primary_sha256": stage["source"]["primary_sha256"],
        "source_independent_sha256": stage["source"]["independent_sha256"],
        "config_sha256": CONFIG_SHA256,
        "action_basis": data.action_basis.tolist(),
        "nominal_issued_a": data.nominal_issued.tolist(),
        "fixed_poles": stage["backbone"]["fixed_poles"],
        "state_scale": data.state_scale.tolist(),
        "response_scale": data.response_scale.tolist(),
        "issue_to_effect_state_offset": 1,
        "current_r_geo_z_geo_ip_observation": "exact_noiseless_rollout_origin",
        "future_actual_current": "forbidden",
        "model": model.payload(),
        "claim_boundary": stage["claim_boundary"],
    }


def execute(stage_path: Path, source_revision: str, output_dir: Path, emit_artifacts: bool = True) -> dict[str, Any]:
    stage = load_stage(stage_path)
    data = extract_dataset(stage)
    dataset = dataset_payload(data, stage)
    dataset_digest = canonical_sha256(dataset)
    comparison = compare(data, stage)
    selected = comparison["selected_candidate"]
    model_payload = None
    model_digest = None
    if selected is not None:
        model = fit_candidate(selected, data.cells, data, stage)
        model_payload = selected_model_payload(selected, model, data, stage)
        model_digest = canonical_sha256(model_payload)
    passed = selected is not None
    route = stage["routes"]["pass"] if passed else stage["routes"]["no_eligible_candidate"]
    result = {
        "schema_version": SCHEMA,
        "source_revision": source_revision,
        "stage_config_sha256": CONFIG_SHA256,
        "source_primary_sha256": stage["source"]["primary_sha256"],
        "source_independent_sha256": stage["source"]["independent_sha256"],
        "source_compact_inventory_sha256": stage["source"]["compact_inventory_sha256"],
        "dataset_sha256": dataset_digest,
        "model_payload_sha256": model_digest,
        "unique_cells": len(data.cells),
        "whole_history_families": len({cell.group_id for cell in data.cells}),
        "integrity_replays_fit_weight": 0,
        "action_basis_rank": data.action_rank,
        "id2i1_records_read": 0,
        "id2j0_records_read": 0,
        "id2c2_records_read": 0,
        "calibration_records_read": 0,
        "holdout_records_read": 0,
        "models_fit": 20 + int(selected is not None),
        "reset_calls": 0,
        "tsc_calls": 0,
        "plant_advances": 0,
        "comparison": comparison,
        "passed": passed,
        "route": route,
        "fresh_calibration_design_authorized": passed,
        "controller_authorized": False,
        "claim_boundary": stage["claim_boundary"],
    }
    if emit_artifacts:
        output_dir = inside(output_dir, "ID2L1 output directory")
        if output_dir.exists():
            raise IntegrityError("ID2L1 output directory already exists")
        output_dir.mkdir(parents=True)
        write_new(output_dir / "dataset.json", dataset)
        if model_payload is not None:
            write_new(output_dir / "selected_model.json", model_payload)
        write_new(output_dir / "result.json", result)
    return result


def preflight(stage_path: Path, source_revision: str) -> dict[str, Any]:
    stage = load_stage(stage_path)
    data = extract_dataset(stage)
    return {
        "schema_version": "rgeo-zgeo-1ms-id2l1-preflight-v1",
        "source_revision": source_revision,
        "stage_config_sha256": CONFIG_SHA256,
        "passed": True,
        "unique_cells": len(data.cells),
        "whole_history_families": len({cell.group_id for cell in data.cells}),
        "action_basis_rank": data.action_rank,
        "reset_calls": 0,
        "tsc_calls": 0,
        "plant_advances": 0,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage-config", type=Path, default=CONFIG)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.preflight:
            value = preflight(args.stage_config, args.source_revision)
        else:
            if args.output_dir is None:
                raise IntegrityError("--output-dir is required")
            value = execute(args.stage_config, args.source_revision, args.output_dir)
        print(json.dumps(value, indent=2, sort_keys=True, allow_nan=False))
        return 0 if value.get("passed", True) else 2
    except Exception as exc:
        print(json.dumps({
            "schema_version": SCHEMA,
            "source_revision": args.source_revision,
            "stage_config_sha256": CONFIG_SHA256,
            "passed": False,
            "route": "ONE_MS_ID2L1_INPUT_OR_DATA_INTEGRITY_FAIL_NO_MODEL",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "reset_calls": 0,
            "tsc_calls": 0,
            "plant_advances": 0,
        }, indent=2, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
