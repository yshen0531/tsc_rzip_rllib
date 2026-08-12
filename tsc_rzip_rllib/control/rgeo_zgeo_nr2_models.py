"""Fair finite NR2 causal dynamics candidates and recursive evaluation."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Sequence

import numpy as np
import torch
from torch import nn


STATE_DIM = 17
ACTION_DIM = 14
INPUT_DIM = STATE_DIM + ACTION_DIM + 1
OUTPUT_SCALES = np.asarray([0.005, 0.005, 500.0] + [1.0] * ACTION_DIM, dtype=float)
POINT_SCALES = OUTPUT_SCALES[:3]
HISTORY_STEPS = 4


@dataclass(frozen=True)
class Normalizer:
    state_mean: tuple[float, ...]
    state_scale: tuple[float, ...]
    action_mean: tuple[float, ...]
    action_scale: tuple[float, ...]

    @classmethod
    def fit(cls, states: np.ndarray, actions: np.ndarray) -> "Normalizer":
        state_values = np.asarray(states, dtype=float).reshape(-1, STATE_DIM)
        action_values = np.asarray(actions, dtype=float).reshape(-1, ACTION_DIM)
        state_mean = state_values.mean(axis=0)
        state_scale = np.maximum(state_values.std(axis=0), np.asarray([1e-6, 1e-6, 1.0] + [1e-3] * ACTION_DIM))
        action_mean = action_values.mean(axis=0)
        action_scale = np.maximum(action_values.std(axis=0), 1e-3)
        return cls(tuple(state_mean), tuple(state_scale), tuple(action_mean), tuple(action_scale))

    def encode(self, state: np.ndarray, action: np.ndarray, time_fraction: float) -> np.ndarray:
        state_n = (np.asarray(state) - np.asarray(self.state_mean)) / np.asarray(self.state_scale)
        action_n = (np.asarray(action) - np.asarray(self.action_mean)) / np.asarray(self.action_scale)
        return np.concatenate((state_n, action_n, [float(time_fraction)]))

    def to_dict(self) -> dict[str, Any]:
        return {key: list(getattr(self, key)) for key in ("state_mean", "state_scale", "action_mean", "action_scale")}

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Normalizer":
        return cls(**{key: tuple(map(float, payload[key])) for key in ("state_mean", "state_scale", "action_mean", "action_scale")})


class ARXModel:
    def __init__(self, normalizer: Normalizer, coefficient: np.ndarray):
        self.normalizer = normalizer
        self.coefficient = np.asarray(coefficient, dtype=float)

    def predict_delta(self, history: Sequence[tuple[np.ndarray, np.ndarray, float]]) -> np.ndarray:
        features = history_feature(history, self.normalizer)
        normalized_delta = np.concatenate(([1.0], features)) @ self.coefficient
        return normalized_delta * OUTPUT_SCALES


def history_feature(history: Sequence[tuple[np.ndarray, np.ndarray, float]], normalizer: Normalizer) -> np.ndarray:
    if not history:
        raise ValueError("causal history cannot be empty")
    selected = list(history[-HISTORY_STEPS:])
    while len(selected) < HISTORY_STEPS:
        selected.insert(0, selected[0])
    return np.concatenate([normalizer.encode(state, action, time_fraction) for state, action, time_fraction in selected])


def fit_arx(trajectories: Sequence[dict[str, Any]], normalizer: Normalizer, ridge: float, indices: Sequence[int] | None = None) -> ARXModel:
    rows: list[np.ndarray] = []
    targets: list[np.ndarray] = []
    selected = range(len(trajectories)) if indices is None else indices
    for trajectory_index in selected:
        trajectory = trajectories[trajectory_index]
        history: list[tuple[np.ndarray, np.ndarray, float]] = []
        for step, action in enumerate(trajectory["actions"]):
            state = np.asarray(trajectory["states"][step], dtype=float)
            history.append((state, np.asarray(action, dtype=float), step / 8.0))
            rows.append(np.concatenate(([1.0], history_feature(history, normalizer))))
            targets.append((np.asarray(trajectory["states"][step + 1]) - state) / OUTPUT_SCALES)
    design = np.asarray(rows)
    target = np.asarray(targets)
    penalty = np.eye(design.shape[1]) * float(ridge)
    penalty[0, 0] = 0.0
    coefficient = np.linalg.lstsq(design.T @ design + penalty, design.T @ target, rcond=None)[0]
    return ARXModel(normalizer, coefficient)


class RecurrentDeltaModel(nn.Module):
    def __init__(self, kind: str, width: int):
        super().__init__()
        if kind == "gru":
            self.sequence = nn.GRU(INPUT_DIM, width, batch_first=True)
        elif kind == "lstm":
            self.sequence = nn.LSTM(INPUT_DIM, width, batch_first=True)
        else:
            raise ValueError("recurrent kind must be gru or lstm")
        self.head = nn.Linear(width, STATE_DIM)

    def forward(self, values: torch.Tensor) -> torch.Tensor:
        sequence, _ = self.sequence(values)
        return self.head(sequence)


class CausalTCNDeltaModel(nn.Module):
    def __init__(self, width: int):
        super().__init__()
        self.conv1 = nn.Conv1d(INPUT_DIM, width, kernel_size=2, dilation=1)
        self.conv2 = nn.Conv1d(width, width, kernel_size=2, dilation=2)
        self.head = nn.Linear(width, STATE_DIM)

    def forward(self, values: torch.Tensor) -> torch.Tensor:
        x = values.transpose(1, 2)
        x = torch.nn.functional.pad(x, (1, 0))
        x = torch.tanh(self.conv1(x))
        x = torch.nn.functional.pad(x, (2, 0))
        x = torch.tanh(self.conv2(x)).transpose(1, 2)
        return self.head(x)


def build_neural(kind: str, width: int) -> nn.Module:
    return CausalTCNDeltaModel(width) if kind == "tcn" else RecurrentDeltaModel(kind, width)


def parameter_count(model: nn.Module) -> int:
    return sum(parameter.numel() for parameter in model.parameters())


def teacher_forced_tensors(trajectories: Sequence[dict[str, Any]], normalizer: Normalizer) -> tuple[torch.Tensor, torch.Tensor]:
    inputs = []
    targets = []
    for trajectory in trajectories:
        inputs.append([
            normalizer.encode(np.asarray(trajectory["states"][step]), np.asarray(action), step / 8.0)
            for step, action in enumerate(trajectory["actions"])
        ])
        targets.append([
            (np.asarray(trajectory["states"][step + 1]) - np.asarray(trajectory["states"][step])) / OUTPUT_SCALES
            for step in range(8)
        ])
    return torch.tensor(np.asarray(inputs), dtype=torch.float32), torch.tensor(np.asarray(targets), dtype=torch.float32)


def fit_neural(kind: str, width: int, trajectories: Sequence[dict[str, Any]], normalizer: Normalizer, seed: int,
               max_epochs: int = 2000, patience: int = 200) -> nn.Module:
    torch.manual_seed(int(seed))
    torch.use_deterministic_algorithms(True)
    model = build_neural(kind, width)
    if parameter_count(model) > 10_000:
        raise ValueError("neural candidate exceeds 10,000 parameters")
    inputs, targets = teacher_forced_tensors(trajectories, normalizer)
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    best_loss = math.inf
    best_state = None
    stale = 0
    for _ in range(max_epochs):
        optimizer.zero_grad()
        prediction = model(inputs)
        loss = torch.mean((prediction - targets) ** 2)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        value = float(loss.detach())
        if value < best_loss - 1e-8:
            best_loss = value
            best_state = {key: tensor.detach().clone() for key, tensor in model.state_dict().items()}
            stale = 0
        else:
            stale += 1
        if stale >= patience:
            break
    if best_state is None:
        raise RuntimeError("neural fitting produced no finite state")
    model.load_state_dict(best_state)
    model.eval()
    return model


def neural_delta(model: nn.Module, history: Sequence[tuple[np.ndarray, np.ndarray, float]], normalizer: Normalizer) -> np.ndarray:
    encoded = np.asarray([[normalizer.encode(state, action, time_fraction) for state, action, time_fraction in history]], dtype=np.float32)
    with torch.no_grad():
        prediction = model(torch.tensor(encoded))
    return prediction[0, -1].numpy().astype(float) * OUTPUT_SCALES


def recursive_rollout(model: Any, trajectory: dict[str, Any], normalizer: Normalizer, neural: bool) -> np.ndarray:
    state = np.asarray(trajectory["states"][0], dtype=float).copy()
    output = [state.copy()]
    history: list[tuple[np.ndarray, np.ndarray, float]] = []
    for step, action in enumerate(trajectory["actions"]):
        action_array = np.asarray(action, dtype=float)
        history.append((state.copy(), action_array, step / 8.0))
        delta = neural_delta(model, history, normalizer) if neural else model.predict_delta(history)
        state = state + delta
        output.append(state.copy())
    return np.asarray(output)


def recursive_errors(prediction: np.ndarray, trajectory: dict[str, Any]) -> dict[str, Any]:
    actual = np.asarray(trajectory["states"], dtype=float)
    difference = prediction[1:] - actual[1:]
    scaled = np.abs(difference[:, :3]) / POINT_SCALES
    current = np.max(np.abs(difference[:, 3:]), axis=1)
    return {
        "scaled": scaled,
        "current_max_abs_a": current,
        "finite": bool(np.all(np.isfinite(prediction))),
    }
