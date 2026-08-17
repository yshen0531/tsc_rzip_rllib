"""ID-2G1 grouped causal development-model comparison (zero new TSC)."""

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

from scripts.rgeo_zgeo_1ms_id0_vector_tail_independent import _state  # noqa: E402
from scripts.rgeo_zgeo_1ms_id2f1_repeated_context_development import (  # noqa: E402
    campaign_streams,
    load as load_id2f1,
)


SCHEMA = "rgeo-zgeo-1ms-id2g1-grouped-causal-model-result-v1"
DATASET_SCHEMA = "rgeo-zgeo-1ms-id2g1-allowed-causal-dataset-v1"
CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id2g1_grouped_causal_model_comparison.json"
CONFIG_SHA256 = "aa2c11478ea5157e03702ebe1202a39bcf58245a20adb0a9afba4aa95916a6bd"
SOURCE_CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id2f1r1_repeated_context_development.json"
SOURCE_CONFIG_SHA256 = "2c97be4f3adbc684bcb7ed7782d76822e8071c919f92882e3141b3bf934e1831"
DESIGN_SHA256 = "9612e93eba25172017ab68dfdab43419ef2682a300b634e00c3970d0219d1fa0"
FEATURE_NAMES = (
    "rzi_relative_0", "rzi_relative_1", "rzi_relative_2",
    "last_delta_0", "last_delta_1", "last_delta_2",
    "current_card15_span_0", "current_card15_span_1", "current_card15_span_2",
    "issued_card15_span_0", "issued_card15_span_1", "issued_card15_span_2",
    "issued_minus_current_0", "issued_minus_current_1", "issued_minus_current_2",
    "time", "causal_history_fraction",
)


class IntegrityError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inside(path: Path, label: str) -> Path:
    value = path.resolve()
    try:
        value.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise IntegrityError(f"{label} leaves repository root") from exc
    return value


def write_new(path: Path, value: Any) -> None:
    path = inside(path, "output")
    if path.exists():
        raise FileExistsError(str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def _load_json(path: Path, expected_hash: str, label: str) -> dict[str, Any]:
    path = inside(path, label)
    if sha256(path) != expected_hash:
        raise IntegrityError(f"{label} hash mismatch")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise IntegrityError(f"{label} is not an object")
    return value


def load_stage(path: Path = CONFIG) -> dict[str, Any]:
    stage = _load_json(path, CONFIG_SHA256, "ID2G1 config")
    design = stage["design"]
    if design["sha256"] != DESIGN_SHA256:
        raise IntegrityError("design hash declaration changed")
    _load_json(ROOT / stage["source_run"]["primary_path"],
               stage["source_run"]["primary_sha256"], "ID2F1R1 primary")
    independent = _load_json(ROOT / stage["source_run"]["independent_path"],
                             stage["source_run"]["independent_sha256"], "ID2F1R1 independent")
    primary = json.loads((ROOT / stage["source_run"]["primary_path"]).read_text(encoding="utf-8"))
    if not primary.get("passed") or not primary.get("model_fit_data_eligible"):
        raise IntegrityError("ID2F1R1 primary is not fit eligible")
    if not independent.get("audit_passed") or not independent.get("model_fit_data_eligible"):
        raise IntegrityError("ID2F1R1 independent is not fit eligible")
    source = stage["source_run"]
    required = {
        "rollouts_completed": source["required_rollouts"],
        "unique_cells_completed": source["required_unique_cells"],
        "verified_plant_advances": source["required_advances"],
        "required_artifact_files": source["required_artifact_files"],
        "required_artifact_bytes": source["required_artifact_bytes"],
        "required_artifact_inventory_sha256": source["required_inventory_sha256"],
    }
    for key, expected in required.items():
        if primary.get(key) != expected:
            raise IntegrityError(f"ID2F1R1 primary field mismatch: {key}")
    if independent.get("raw_states") != source["required_states"]:
        raise IntegrityError("ID2F1R1 state count mismatch")
    if independent.get("recomputed_inventory_sha256") != source["required_inventory_sha256"]:
        raise IntegrityError("ID2F1R1 independent inventory mismatch")
    if int(independent.get("id2c2_records_read", -1)) != 0:
        raise IntegrityError("ID2C2 was read")
    if sha256(ROOT / design["path"]) != design["sha256"]:
        raise IntegrityError("ID2G1 design hash mismatch")
    if sha256(SOURCE_CONFIG) != SOURCE_CONFIG_SHA256:
        raise IntegrityError("ID2F1R1 source config hash mismatch")
    if stage["new_tsc_calls"] != 0 or stage["reset_calls"] != 0 or stage["plant_advances"] != 0:
        raise IntegrityError("zero-plant contract changed")
    return stage


@dataclass
class Cell:
    cell_id: str
    context_id: str
    cell_kind: str
    states: np.ndarray          # [35, 3], physical units
    currents: np.ndarray        # [35, 3], Card15-span coordinates
    issued: np.ndarray          # [34, 3], Card15-span coordinates
    direction_id: str | None
    sign: str | None
    duration: int


@dataclass
class AllowedDataset:
    cells: list[Cell]
    source_rzi: np.ndarray
    state_scale: np.ndarray
    response_scale: np.ndarray
    basis: np.ndarray
    q0: np.ndarray
    maximum_projection_residual_a: float


def _float_target(target: Sequence[Any]) -> np.ndarray:
    payload = target.current_a_tsc if hasattr(target, "current_a_tsc") else target
    value = np.asarray([float(item) for item in payload], dtype=np.float64)
    if value.shape != (14,) or not np.all(np.isfinite(value)):
        raise IntegrityError("invalid Card15 target")
    return value


def _projection(vector: np.ndarray, basis: np.ndarray) -> tuple[np.ndarray, float]:
    coordinate, *_ = np.linalg.lstsq(basis, vector, rcond=None)
    residual = float(np.max(np.abs(vector - basis @ coordinate)))
    return coordinate, residual


def extract_dataset(stage: dict[str, Any]) -> AllowedDataset:
    source_stage, cfg, targets, id2c1_stage = load_id2f1(SOURCE_CONFIG)
    streams = campaign_streams(source_stage, cfg, targets, id2c1_stage)
    run_dir = inside(ROOT / stage["source_run"]["path"], "ID2F1R1 raw run")
    if not run_dir.is_dir():
        raise IntegrityError("ID2F1R1 raw run is absent")
    by_id = {row["rollout_id"]: row for row in streams}
    if len(by_id) != stage["source_run"]["required_rollouts"]:
        raise IntegrityError("source rollout matrix changed")

    baseline = next(row for row in streams if row["cell_id"] == "none__baseline")
    q0 = _float_target(baseline["targets"][0])
    p03 = _float_target(baseline["targets"][16]) - q0
    p04_stream = next(row for row in streams if row["cell_id"] == "none__p04_plus_i22_d1")
    p07_stream = next(row for row in streams if row["cell_id"] == "none__p07_plus_i22_d1")
    p04 = _float_target(p04_stream["targets"][22]) - _float_target(baseline["targets"][22])
    p07 = _float_target(p07_stream["targets"][22]) - _float_target(baseline["targets"][22])
    basis = np.column_stack([p03, p04, p07])
    if np.linalg.matrix_rank(basis) != 3:
        raise IntegrityError("Card15 source-local span is not rank three")

    raw_rows: dict[str, dict[str, Any]] = {}
    maximum_residual = 0.0
    for rollout_id, stream in by_id.items():
        folder = run_dir / "rollouts" / rollout_id
        records = []
        for index in range(35):
            record = _state(folder / f"{1100 + index}ms", cfg)
            if record["time_ms"] != 1100 + index:
                raise IntegrityError(f"state clock mismatch: {rollout_id}:{index}")
            records.append(record)
        state_values = np.asarray([[row[key] for key in ("r_geo_m", "z_geo_m", "ip_a")]
                                   for row in records], dtype=np.float64)
        current_values = np.asarray([[float(value) for value in row["actual_current_decimal_a_tsc"]]
                                     for row in records], dtype=np.float64)
        if state_values.shape != (35, 3) or current_values.shape != (35, 14):
            raise IntegrityError(f"raw shape mismatch: {rollout_id}")
        current_origin = current_values[0]
        current_coordinates = []
        for value in current_values:
            coordinate, residual = _projection(value - current_origin, basis)
            maximum_residual = max(maximum_residual, residual)
            current_coordinates.append(coordinate)
        issued_coordinates = []
        for issue, target in enumerate(stream["targets"]):
            coordinate, residual = _projection(_float_target(target) - q0, basis)
            maximum_residual = max(maximum_residual, residual)
            issued_coordinates.append(coordinate)
            if list(records[issue]["active_command_card15_fields"]) != stream["actions"][issue]["expected_card15_fields"]:
                raise IntegrityError(f"issued Card15 mismatch: {rollout_id}:{issue}")
        raw_rows[rollout_id] = {
            "stream": stream,
            "states": state_values,
            "currents": np.asarray(current_coordinates, dtype=np.float64),
            "issued": np.asarray(issued_coordinates, dtype=np.float64),
        }
    cap = float(stage["data_contract"]["maximum_card15_projection_residual_a"])
    if maximum_residual > cap:
        raise IntegrityError(f"Card15-span projection residual {maximum_residual} exceeds {cap}")

    cells: list[Cell] = []
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in raw_rows.values():
        grouped.setdefault(row["stream"]["cell_id"], []).append(row)
    if len(grouped) != stage["source_run"]["required_unique_cells"]:
        raise IntegrityError("unique cell count changed")
    for cell_id, members in sorted(grouped.items()):
        if len(members) != stage["data_contract"]["replays_per_cell"]:
            raise IntegrityError(f"replay count mismatch: {cell_id}")
        for key in ("states", "currents", "issued"):
            if not np.array_equal(members[0][key], members[1][key]):
                raise IntegrityError(f"non-exact replay: {cell_id}:{key}")
        stream = members[0]["stream"]
        cells.append(Cell(
            cell_id=cell_id,
            context_id=stream["context_id"],
            cell_kind=stream["cell_kind"],
            states=np.mean([row["states"] for row in members], axis=0),
            currents=np.mean([row["currents"] for row in members], axis=0),
            issued=np.mean([row["issued"] for row in members], axis=0),
            direction_id=stream["direction_id"], sign=stream["sign"],
            duration=int(stream["probe_duration_issues"]),
        ))
    contexts = sorted({cell.context_id for cell in cells})
    if sorted(stage["data_contract"]["contexts"]) != contexts:
        raise IntegrityError("context set changed")
    source_rzi = next(cell.states[0] for cell in cells if cell.cell_id == "none__baseline").copy()
    if any(not np.array_equal(cell.states[0], source_rzi) for cell in cells):
        raise IntegrityError("source state differs across cells")
    return AllowedDataset(
        cells=cells, source_rzi=source_rzi,
        state_scale=np.asarray(stage["normalization"]["state_scale"], dtype=np.float64),
        response_scale=np.asarray(stage["normalization"]["response_scale"], dtype=np.float64),
        basis=basis, q0=q0, maximum_projection_residual_a=maximum_residual,
    )


def dataset_payload(data: AllowedDataset) -> dict[str, Any]:
    return {
        "schema_version": DATASET_SCHEMA,
        "claim_boundary": "Allowed causal development fields only; forbidden as a fixture, calibration or holdout.",
        "feature_names": list(FEATURE_NAMES),
        "source_rzi": data.source_rzi.tolist(),
        "state_scale": data.state_scale.tolist(),
        "response_scale": data.response_scale.tolist(),
        "card15_basis_a": data.basis.tolist(),
        "q0_a": data.q0.tolist(),
        "maximum_projection_residual_a": data.maximum_projection_residual_a,
        "cells": [{
            "cell_id": cell.cell_id,
            "context_id": cell.context_id,
            "cell_kind": cell.cell_kind,
            "direction_id_evaluator_only": cell.direction_id,
            "sign_evaluator_only": cell.sign,
            "duration_evaluator_only": cell.duration,
            "states_rzi": cell.states.tolist(),
            "current_card15_span": cell.currents.tolist(),
            "issued_card15_span": cell.issued.tolist(),
            "unit_weight": 1.0,
        } for cell in data.cells],
    }


def frame(cell: Cell, issue: int, data: AllowedDataset,
          current_state: np.ndarray | None = None, previous_state: np.ndarray | None = None,
          current_coordinate: np.ndarray | None = None,
          issued_coordinate: np.ndarray | None = None, action_blind: bool = False) -> np.ndarray:
    current_state = cell.states[issue] if current_state is None else current_state
    if previous_state is None:
        previous_state = cell.states[max(0, issue - 1)]
    current_coordinate = cell.currents[issue] if current_coordinate is None else current_coordinate
    issued_coordinate = cell.issued[issue] if issued_coordinate is None else issued_coordinate.copy()
    if action_blind:
        issued_coordinate = issued_coordinate.copy()
        issued_coordinate[1:] = 0.0
    return np.concatenate([
        (current_state - data.source_rzi) / data.state_scale,
        (current_state - previous_state) / data.state_scale,
        current_coordinate,
        issued_coordinate,
        issued_coordinate - current_coordinate,
        np.asarray([issue / 34.0, min(issue, 16) / 16.0]),
    ]).astype(np.float64)


def teacher_arrays(cells: Sequence[Cell], data: AllowedDataset,
                   action_blind: bool = False) -> tuple[np.ndarray, np.ndarray]:
    x = np.asarray([[frame(cell, issue, data, action_blind=action_blind) for issue in range(34)]
                    for cell in cells], dtype=np.float64)
    y = np.asarray([[(cell.states[issue + 1] - cell.states[issue]) / data.state_scale
                     for issue in range(34)] for cell in cells], dtype=np.float64)
    return x, y


def _pole_states(cell: Cell, poles: Sequence[float], action_blind: bool,
                 currents: np.ndarray | None = None) -> np.ndarray:
    currents = cell.currents if currents is None else currents
    values = np.zeros((34, len(poles), 3), dtype=np.float64)
    memory = np.zeros((len(poles), 3), dtype=np.float64)
    for issue in range(34):
        target = cell.issued[issue].copy()
        if action_blind:
            target[1:] = 0.0
        delta = target - currents[issue]
        memory = np.asarray(poles)[:, None] * memory + delta[None, :]
        values[issue] = memory
    return values


def structured_features(cell: Cell, data: AllowedDataset, poles: Sequence[float],
                        action_blind: bool = False,
                        states_override: np.ndarray | None = None,
                        currents_override: np.ndarray | None = None) -> np.ndarray:
    states = cell.states if states_override is None else states_override
    currents = cell.currents if currents_override is None else currents_override
    pole_values = _pole_states(cell, poles, action_blind, currents)
    rows = []
    for issue in range(34):
        target = cell.issued[issue].copy()
        if action_blind:
            target[1:] = 0.0
        state = (states[issue] - data.source_rzi) / data.state_scale
        previous = states[max(0, issue - 1)]
        velocity = (states[issue] - previous) / data.state_scale
        current = currents[issue]
        interaction = np.outer(state, target).reshape(-1)
        rows.append(np.concatenate([
            [1.0, issue / 34.0, (issue / 34.0) ** 2], state, velocity,
            current, target, target - current, pole_values[issue].reshape(-1), interaction,
        ]))
    return np.asarray(rows, dtype=np.float64)


class StructuredModel:
    def __init__(self, coefficients: np.ndarray, poles: Sequence[float], action_blind: bool = False):
        self.coefficients = coefficients
        self.poles = tuple(float(value) for value in poles)
        self.action_blind = action_blind

    def teacher(self, cell: Cell, data: AllowedDataset) -> np.ndarray:
        return structured_features(cell, data, self.poles, self.action_blind) @ self.coefficients

    def recursive(self, cell: Cell, data: AllowedDataset, origin: int = 16) -> np.ndarray:
        states = cell.states.copy()
        currents = cell.currents.copy()
        # Pole features depend only on the issued/current action history and are causal.
        for issue in range(origin, 34):
            features = structured_features(cell, data, self.poles, self.action_blind,
                                           states_override=states, currents_override=currents)
            delta = features[issue] @ self.coefficients
            states[issue + 1] = states[issue] + delta * data.state_scale
            currents[issue + 1] = cell.issued[issue]
        return states[origin + 1:35]


def fit_structured(cells: Sequence[Cell], data: AllowedDataset, cfg: dict[str, Any],
                   action_blind: bool = False) -> StructuredModel:
    poles = cfg["poles"]
    x_rows = []
    y_rows = []
    for cell in cells:
        x_rows.append(structured_features(cell, data, poles, action_blind))
        y_rows.append((cell.states[1:] - cell.states[:-1]) / data.state_scale)
    # A paired-response loss prevents nominal drift from erasing the action channel.
    by_context = {context: next(cell for cell in cells if cell.context_id == context and cell.cell_kind == "baseline")
                  for context in {cell.context_id for cell in cells}}
    for cell in cells:
        if cell.cell_kind == "baseline":
            continue
        baseline = by_context[cell.context_id]
        weight = math.sqrt(2.0)
        x_rows.append(weight * (structured_features(cell, data, poles, action_blind)[22:]
                                - structured_features(baseline, data, poles, action_blind)[22:]))
        y_cell = (cell.states[1:] - cell.states[:-1]) / data.state_scale
        y_base = (baseline.states[1:] - baseline.states[:-1]) / data.state_scale
        y_rows.append(weight * (y_cell[22:] - y_base[22:]))
    x = np.concatenate(x_rows, axis=0)
    y = np.concatenate(y_rows, axis=0)
    ridge = float(cfg["ridge"])
    coefficients = np.linalg.solve(x.T @ x + ridge * np.eye(x.shape[1]), x.T @ y)
    return StructuredModel(coefficients, poles, action_blind)


class GRUDelta(nn.Module):
    def __init__(self, width: int):
        super().__init__()
        self.gru = nn.GRU(len(FEATURE_NAMES), width, batch_first=True)
        self.head = nn.Linear(width, 3)

    def forward(self, value: torch.Tensor) -> torch.Tensor:
        return self.head(self.gru(value)[0])


class CausalTCNDelta(nn.Module):
    def __init__(self, width: int, dilations: Sequence[int], kernel_size: int):
        super().__init__()
        self.input = nn.Linear(len(FEATURE_NAMES), width)
        self.layers = nn.ModuleList([
            nn.Conv1d(width, width, kernel_size, dilation=int(dilation)) for dilation in dilations
        ])
        self.dilations = tuple(int(value) for value in dilations)
        self.kernel_size = int(kernel_size)
        self.head = nn.Linear(width, 3)

    def forward(self, value: torch.Tensor) -> torch.Tensor:
        hidden = torch.relu(self.input(value)).transpose(1, 2)
        for layer, dilation in zip(self.layers, self.dilations):
            pad = dilation * (self.kernel_size - 1)
            update = torch.relu(layer(torch.nn.functional.pad(hidden, (pad, 0))))
            hidden = hidden + update
        return self.head(hidden.transpose(1, 2))


class NeuralModel:
    def __init__(self, module: nn.Module):
        self.module = module.eval()

    def teacher(self, cell: Cell, data: AllowedDataset) -> np.ndarray:
        x, _ = teacher_arrays([cell], data)
        with torch.no_grad():
            return self.module(torch.tensor(x, dtype=torch.float32)).cpu().numpy()[0].astype(np.float64)

    def recursive(self, cell: Cell, data: AllowedDataset, origin: int = 16) -> np.ndarray:
        states = cell.states.copy()
        currents = cell.currents.copy()
        frames = [frame(cell, issue, data) for issue in range(origin)]
        for issue in range(origin, 34):
            previous = states[max(0, issue - 1)]
            frames.append(frame(cell, issue, data, current_state=states[issue], previous_state=previous,
                                current_coordinate=currents[issue], issued_coordinate=cell.issued[issue]))
            sequence = torch.tensor(np.asarray(frames)[None, :, :], dtype=torch.float32)
            with torch.no_grad():
                delta = self.module(sequence)[0, -1].cpu().numpy().astype(np.float64)
            states[issue + 1] = states[issue] + delta * data.state_scale
            currents[issue + 1] = cell.issued[issue]
        return states[origin + 1:35]


def _seed(value: int) -> None:
    random.seed(value)
    np.random.seed(value)
    torch.manual_seed(value)
    torch.use_deterministic_algorithms(True)
    torch.set_num_threads(1)


def fit_neural(kind: str, cells: Sequence[Cell], data: AllowedDataset,
               cfg: dict[str, Any], seed: int) -> NeuralModel:
    _seed(seed)
    if kind == "small_gru":
        module: nn.Module = GRUDelta(int(cfg["hidden_width"]))
    elif kind == "causal_tcn":
        module = CausalTCNDelta(int(cfg["hidden_width"]), cfg["dilations"], int(cfg["kernel_size"]))
    else:
        raise ValueError(kind)
    x_np, y_np = teacher_arrays(cells, data)
    x = torch.tensor(x_np, dtype=torch.float32)
    y = torch.tensor(y_np, dtype=torch.float32)
    optimizer = torch.optim.Adam(module.parameters(), lr=float(cfg["learning_rate"]),
                                 weight_decay=float(cfg["weight_decay"]))
    context_baseline = {
        context: index for index, cell in enumerate(cells)
        if cell.cell_kind == "baseline" for context in [cell.context_id]
    }
    action_pairs = [(index, context_baseline[cell.context_id]) for index, cell in enumerate(cells)
                    if cell.cell_kind != "baseline"]
    module.train()
    for _ in range(int(cfg["epochs"])):
        optimizer.zero_grad(set_to_none=True)
        prediction = module(x)
        absolute = torch.mean((prediction - y) ** 2, dim=(1, 2)).mean()
        paired_terms = []
        for action_index, baseline_index in action_pairs:
            paired_terms.append(torch.mean(
                ((prediction[action_index, 22:] - prediction[baseline_index, 22:])
                 - (y[action_index, 22:] - y[baseline_index, 22:])) ** 2
            ))
        paired = torch.stack(paired_terms).mean() if paired_terms else torch.zeros((), dtype=x.dtype)
        loss = absolute + 2.0 * paired
        loss.backward()
        torch.nn.utils.clip_grad_norm_(module.parameters(), float(cfg["gradient_clip"]))
        optimizer.step()
    return NeuralModel(module)


def _mean_prediction(models: Sequence[Any], method: str, cell: Cell,
                     data: AllowedDataset) -> tuple[np.ndarray, np.ndarray]:
    values = np.asarray([getattr(model, method)(cell, data) for model in models], dtype=np.float64)
    return np.mean(values, axis=0), values


def _quantile_abs(values: list[np.ndarray], quantile: float = 0.95) -> list[float]:
    array = np.concatenate(values, axis=0)
    return np.quantile(np.abs(array), quantile, axis=0).tolist()


def evaluate(models: Sequence[Any], held: Sequence[Cell], data: AllowedDataset,
             response_scale: np.ndarray, ensemble_floor: np.ndarray | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    rolling_errors: list[np.ndarray] = []
    recursive_errors: list[np.ndarray] = []
    predictions: dict[str, np.ndarray] = {}
    member_predictions: dict[str, np.ndarray] = {}
    for cell in held:
        teacher, _ = _mean_prediction(models, "teacher", cell, data)
        rolling_next = cell.states[:-1] + teacher * data.state_scale
        rolling_errors.append(rolling_next - cell.states[1:])
        recursive, members = _mean_prediction(models, "recursive", cell, data)
        predictions[cell.cell_id] = recursive
        member_predictions[cell.cell_id] = members
        recursive_errors.append(recursive - cell.states[17:35])
    baseline = next(cell for cell in held if cell.cell_kind == "baseline")
    true_response_rows = []
    predicted_response_rows = []
    positive = 0
    cosines = []
    for cell in held:
        if cell.cell_kind == "baseline":
            continue
        true = cell.states[23:35] - baseline.states[23:35]
        predicted = predictions[cell.cell_id][6:] - predictions[baseline.cell_id][6:]
        true_response_rows.append(true / response_scale)
        predicted_response_rows.append(predicted / response_scale)
        norms = np.linalg.norm(true[:, :2], axis=1)
        peak = int(np.argmax(norms))
        left = true[peak, :2]
        right = predicted[peak, :2]
        denominator = float(np.linalg.norm(left) * np.linalg.norm(right))
        cosine = float(np.dot(left, right) / denominator) if denominator > 0 else -1.0
        cosines.append(cosine)
        positive += int(cosine > 0)
    true_array = np.concatenate(true_response_rows, axis=0)
    pred_array = np.concatenate(predicted_response_rows, axis=0)
    denominator = float(np.linalg.norm(true_array))
    response_nrmse = float(np.linalg.norm(pred_array - true_array) / denominator) if denominator > 0 else math.inf
    metrics: dict[str, Any] = {
        "one_step_p95_abs": _quantile_abs(rolling_errors),
        "recursive_p95_abs": _quantile_abs(recursive_errors),
        "response_nrmse": response_nrmse,
        "positive_peak_cosine_count": positive,
        "peak_cosines": cosines,
    }
    diagnostics: dict[str, Any] = {"predictions": predictions, "members": member_predictions}
    if ensemble_floor is not None:
        coverage_rows = []
        half_width_rows = []
        for cell in held:
            members = member_predictions[cell.cell_id]
            spread = np.std(members, axis=0, ddof=0)
            half_width = 1.6448536269514722 * np.sqrt(spread ** 2 + ensemble_floor[None, :] ** 2)
            truth = cell.states[17:35]
            coverage_rows.append(np.abs(truth - predictions[cell.cell_id]) <= half_width)
            half_width_rows.append(half_width)
        coverage = np.mean(np.concatenate(coverage_rows, axis=0), axis=0)
        half_width = np.quantile(np.concatenate(half_width_rows, axis=0), 0.95, axis=0)
        metrics["marginal_coverage"] = coverage.tolist()
        metrics["p95_half_width"] = half_width.tolist()
    return metrics, diagnostics


def _training_residual_floor(models: Sequence[Any], cells: Sequence[Cell], data: AllowedDataset) -> np.ndarray:
    errors = []
    for cell in cells:
        teacher, _ = _mean_prediction(models, "teacher", cell, data)
        errors.append((cell.states[:-1] + teacher * data.state_scale) - cell.states[1:])
    return np.sqrt(np.mean(np.concatenate(errors, axis=0) ** 2, axis=0))


def _eligible(candidate: str, folds: Sequence[dict[str, Any]], blind_mean: float,
              stage: dict[str, Any]) -> tuple[bool, list[str]]:
    gate = stage["eligibility"]
    failures = []
    for fold in folds:
        if any(value > cap for value, cap in zip(fold["one_step_p95_abs"], gate["one_step_p95_abs_max"])):
            failures.append(f"ONE_STEP:{fold['fold_id']}")
        if any(value > cap for value, cap in zip(fold["recursive_p95_abs"], gate["recursive_p95_abs_max"])):
            failures.append(f"RECURSIVE:{fold['fold_id']}")
        if not fold["response_nrmse"] < gate["each_fold_response_nrmse_strict_max"]:
            failures.append(f"RESPONSE:{fold['fold_id']}")
        if fold["positive_peak_cosine_count"] < gate["minimum_positive_peak_cosine_per_fold"]:
            failures.append(f"PEAK:{fold['fold_id']}")
    mean_response = float(np.mean([fold["response_nrmse"] for fold in folds]))
    if mean_response > gate["mean_response_nrmse_max"]:
        failures.append("MEAN_RESPONSE")
    if blind_mean <= 0 or 1.0 - mean_response / blind_mean < gate["minimum_action_blind_improvement_fraction"]:
        failures.append("ACTION_BLIND_IMPROVEMENT")
    if sum(fold["positive_peak_cosine_count"] for fold in folds) < gate["minimum_positive_peak_cosine_total"]:
        failures.append("TOTAL_PEAK")
    if candidate == "probabilistic_ensemble":
        for fold in folds:
            if any(value < gate["ensemble_minimum_marginal_coverage"] for value in fold["marginal_coverage"]):
                failures.append(f"COVERAGE:{fold['fold_id']}")
            if any(value > cap for value, cap in zip(fold["p95_half_width"], gate["ensemble_p95_half_width_max"])):
                failures.append(f"WIDTH:{fold['fold_id']}")
    return not failures, failures


def compare(stage: dict[str, Any], data: AllowedDataset) -> dict[str, Any]:
    candidates: dict[str, list[dict[str, Any]]] = {
        name: [] for name in ("action_blind", "stable_lpv", "small_gru", "causal_tcn", "probabilistic_ensemble")
    }
    for fold in stage["folds"]:
        held_context = fold["held_context"]
        train = [cell for cell in data.cells if cell.context_id != held_context]
        held = [cell for cell in data.cells if cell.context_id == held_context]
        if len(train) != 26 or len(held) != 13:
            raise IntegrityError(f"fold cardinality changed: {fold['fold_id']}")
        blind = fit_structured(train, data, stage["candidates"]["stable_lpv"], action_blind=True)
        structured = fit_structured(train, data, stage["candidates"]["stable_lpv"])
        gru = [fit_neural("small_gru", train, data, stage["candidates"]["small_gru"], seed)
               for seed in stage["candidates"]["small_gru"]["seeds"]]
        tcn = [fit_neural("causal_tcn", train, data, stage["candidates"]["causal_tcn"], seed)
               for seed in stage["candidates"]["causal_tcn"]["seeds"]]
        deterministic = {
            "action_blind": [blind], "stable_lpv": [structured],
            "small_gru": gru, "causal_tcn": tcn,
        }
        for name, models in deterministic.items():
            metrics, _ = evaluate(models, held, data, data.response_scale)
            candidates[name].append({"fold_id": fold["fold_id"], "held_context": held_context, **metrics})
        ensemble_models = [structured, *gru, *tcn]
        floor = _training_residual_floor(ensemble_models, train, data)
        metrics, _ = evaluate(ensemble_models, held, data, data.response_scale, ensemble_floor=floor)
        candidates["probabilistic_ensemble"].append({
            "fold_id": fold["fold_id"], "held_context": held_context,
            "training_residual_floor": floor.tolist(), **metrics,
        })

    blind_mean = float(np.mean([row["response_nrmse"] for row in candidates["action_blind"]]))
    summaries = {}
    eligible_names = []
    for name, folds in candidates.items():
        mean_response = float(np.mean([row["response_nrmse"] for row in folds]))
        eligible = False
        failures = ["NOT_SELECTABLE"]
        if stage["candidates"][name]["selectable"]:
            eligible, failures = _eligible(name, folds, blind_mean, stage)
        summaries[name] = {
            "folds": folds,
            "mean_response_nrmse": mean_response,
            "action_blind_improvement_fraction": 1.0 - mean_response / blind_mean if blind_mean > 0 else -math.inf,
            "eligible": eligible,
            "eligibility_failures": failures,
        }
        if eligible:
            eligible_names.append(name)
    selected = None
    if eligible_names:
        best = min(summaries[name]["mean_response_nrmse"] for name in eligible_names)
        tied = [name for name in eligible_names
                if summaries[name]["mean_response_nrmse"] <= best * (1.0 + stage["eligibility"]["simplicity_tie_fraction"])]
        selected = next(name for name in stage["eligibility"]["simplicity_order"] if name in tied)
    return {
        "action_blind_mean_response_nrmse": blind_mean,
        "candidates": summaries,
        "selected_candidate": selected,
    }


def refit_selected(selected: str, stage: dict[str, Any], data: AllowedDataset, output: Path) -> dict[str, Any]:
    output = inside(output, "model artifact")
    if output.exists():
        raise FileExistsError(str(output))
    artifact: dict[str, Any] = {"selected_candidate": selected, "feature_names": list(FEATURE_NAMES)}
    if selected == "stable_lpv":
        model = fit_structured(data.cells, data, stage["candidates"]["stable_lpv"])
        artifact["poles"] = list(model.poles)
        artifact["coefficients"] = model.coefficients.tolist()
        write_new(output, artifact)
    else:
        modules: dict[str, list[dict[str, torch.Tensor]]] = {}
        if selected in ("small_gru", "probabilistic_ensemble"):
            modules["small_gru"] = [
                fit_neural("small_gru", data.cells, data, stage["candidates"]["small_gru"], seed).module.state_dict()
                for seed in stage["candidates"]["small_gru"]["seeds"]
            ]
        if selected in ("causal_tcn", "probabilistic_ensemble"):
            modules["causal_tcn"] = [
                fit_neural("causal_tcn", data.cells, data, stage["candidates"]["causal_tcn"], seed).module.state_dict()
                for seed in stage["candidates"]["causal_tcn"]["seeds"]
            ]
        if selected == "probabilistic_ensemble":
            structured = fit_structured(data.cells, data, stage["candidates"]["stable_lpv"])
            artifact["structured_poles"] = list(structured.poles)
            artifact["structured_coefficients"] = structured.coefficients.tolist()
        output.parent.mkdir(parents=True, exist_ok=True)
        torch.save({"metadata": artifact, "state_dicts": modules}, output)
    return {"path": str(output.relative_to(ROOT)), "sha256": sha256(output), "bytes": output.stat().st_size}


def execute(stage_path: Path, source_revision: str, output: Path,
            emit_artifacts: bool = True) -> dict[str, Any]:
    stage = load_stage(stage_path)
    output = inside(output, "ID2G1 output")
    if emit_artifacts and output.exists():
        raise FileExistsError(str(output))
    data = extract_dataset(stage)
    payload = dataset_payload(data)
    comparison = compare(stage, data)
    selected = comparison["selected_candidate"]
    route = stage["routes"]["pass"] if selected is not None else stage["routes"]["no_eligible_candidate"]
    result: dict[str, Any] = {
        "schema_version": SCHEMA,
        "source_revision": source_revision,
        "stage_config_sha256": CONFIG_SHA256,
        "source_primary_sha256": stage["source_run"]["primary_sha256"],
        "source_independent_sha256": stage["source_run"]["independent_sha256"],
        "source_inventory_sha256": stage["source_run"]["required_inventory_sha256"],
        "dataset_sha256": hashlib.sha256((json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()).hexdigest(),
        "unique_cells": len(data.cells),
        "contexts": sorted({cell.context_id for cell in data.cells}),
        "replays_counted_as_independent_samples": False,
        "maximum_card15_projection_residual_a": data.maximum_projection_residual_a,
        "id2c2_records_read": 0,
        "calibration_records_read": 0,
        "holdout_records_read": 0,
        "reset_calls": 0,
        "tsc_calls": 0,
        "plant_advances": 0,
        "comparison": comparison,
        "passed": selected is not None,
        "route": route,
        "fresh_calibration_design_authorized": selected is not None,
        "controller_authorized": False,
        "claim_boundary": "Finite three-context grouped development model comparison; not calibration, holdout, controller, tube or control qualification.",
    }
    if emit_artifacts:
        output.mkdir(parents=True, exist_ok=False)
        dataset_path = output / "allowed_causal_dataset.json"
        dataset_path.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
        result["dataset_artifact"] = {"path": str(dataset_path.relative_to(ROOT)),
                                      "sha256": sha256(dataset_path), "bytes": dataset_path.stat().st_size,
                                      "fixture_use_forbidden": True}
        if selected is not None:
            suffix = ".json" if selected == "stable_lpv" else ".pt"
            result["model_artifact"] = refit_selected(selected, stage, data, output / f"selected_model{suffix}")
        result_path = output / "result.json"
        result_path.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    return result


def preflight(stage_path: Path, source_revision: str) -> dict[str, Any]:
    stage = load_stage(stage_path)
    run = inside(ROOT / stage["source_run"]["path"], "ID2F1R1 raw run")
    rollout_root = run / "rollouts"
    rollouts = len([path for path in rollout_root.iterdir() if path.is_dir()]) if rollout_root.is_dir() else 0
    return {
        "schema_version": "rgeo-zgeo-1ms-id2g1-preflight-v1",
        "source_revision": source_revision,
        "stage_config_sha256": CONFIG_SHA256,
        "source_run_present": run.is_dir(),
        "raw_rollout_directories": rollouts,
        "required_raw_rollouts": stage["source_run"]["required_rollouts"],
        "passed": run.is_dir() and rollouts == stage["source_run"]["required_rollouts"],
        "reset_calls": 0, "tsc_calls": 0, "plant_advances": 0,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("preflight", "run"):
        item = sub.add_parser(name)
        item.add_argument("--stage-config", type=Path, default=CONFIG)
        item.add_argument("--source-revision", required=True)
        item.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "preflight":
            value = preflight(args.stage_config, args.source_revision)
            write_new(args.output, value)
            print(json.dumps(value, indent=2, sort_keys=True))
            return 0 if value["passed"] else 2
        value = execute(args.stage_config, args.source_revision, args.output, emit_artifacts=True)
        print(json.dumps(value, indent=2, sort_keys=True))
        return 0 if value["passed"] else 2
    except Exception as exc:
        route_key = "input_or_data_integrity_fail" if isinstance(exc, (IntegrityError, FileNotFoundError)) \
            else "training_or_reproducibility_fail"
        try:
            stage = json.loads(inside(args.stage_config, "ID2G1 config").read_text(encoding="utf-8"))
            route = stage.get("routes", {}).get(route_key, "ONE_MS_ID2G1_INPUT_OR_DATA_INTEGRITY_FAIL_NO_MODEL")
        except Exception:
            route = "ONE_MS_ID2G1_INPUT_OR_DATA_INTEGRITY_FAIL_NO_MODEL"
        failure = {
            "schema_version": SCHEMA,
            "source_revision": args.source_revision,
            "stage_config_sha256": CONFIG_SHA256,
            "passed": False,
            "route": route,
            "failure_type": type(exc).__name__,
            "failure": str(exc),
            "reset_calls": 0, "tsc_calls": 0, "plant_advances": 0,
            "fresh_calibration_design_authorized": False,
            "controller_authorized": False,
        }
        try:
            if args.command == "run":
                output = inside(args.output, "ID2G1 failure output")
                output.mkdir(parents=True, exist_ok=False)
                (output / "result.json").write_text(
                    json.dumps(failure, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
            else:
                write_new(args.output, failure)
        except Exception:
            pass
        print(json.dumps(failure, indent=2, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
