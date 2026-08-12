"""Deterministic prospective NR2 trajectory specification."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any

import numpy as np

from .rgeo_zgeo_contract import ContractError, N_COILS


NR2_CONTRACT_VERSION = "rgeo-zgeo-nr2-v1"
NR2_CAMPAIGN_ID = "rgeo_zgeo_nr2_causal_models_v1"
NR2_HORIZON_STEPS = 8
NR2_SPLIT_PAIRS = {"development": 16, "calibration": 6, "holdout": 8}
NR2_AMPLITUDES = (0.20, 0.35)


@dataclass(frozen=True)
class NR2TrajectorySpec:
    trajectory_id: str
    split: str
    pair_index: int
    sign: int
    pulse_width: int
    normalized_amplitude: float
    normalized_actions_tsc: tuple[tuple[float, ...], ...]

    def __post_init__(self) -> None:
        if self.split not in NR2_SPLIT_PAIRS:
            raise ContractError("invalid NR2 split")
        if self.sign not in {-1, 1} or self.pulse_width not in {1, 2}:
            raise ContractError("invalid NR2 sign or pulse width")
        if self.normalized_amplitude not in NR2_AMPLITUDES:
            raise ContractError("invalid NR2 amplitude")
        if len(self.normalized_actions_tsc) != NR2_HORIZON_STEPS:
            raise ContractError("NR2 trajectory must have eight actions")
        for action in self.normalized_actions_tsc:
            if len(action) != N_COILS or not np.all(np.isfinite(action)):
                raise ContractError("NR2 action must be a finite 14-vector")
            if max(abs(value) for value in action) > max(NR2_AMPLITUDES):
                raise ContractError("NR2 action exceeds frozen amplitude")

    def to_dict(self) -> dict[str, Any]:
        return {
            "trajectory_id": self.trajectory_id,
            "split": self.split,
            "pair_index": self.pair_index,
            "sign": self.sign,
            "pulse_width": self.pulse_width,
            "normalized_amplitude": self.normalized_amplitude,
            "normalized_actions_tsc": [list(action) for action in self.normalized_actions_tsc],
        }


def _direction(split: str, pair_index: int, event_index: int) -> np.ndarray:
    values = []
    for coil_index in range(N_COILS):
        token = f"{NR2_CAMPAIGN_ID}:{split}:{pair_index}:{event_index}:{coil_index}".encode()
        values.append(1.0 if hashlib.sha256(token).digest()[0] & 1 else -1.0)
    return np.asarray(values, dtype=float)


def build_nr2_specs() -> tuple[NR2TrajectorySpec, ...]:
    specs: list[NR2TrajectorySpec] = []
    for split, pair_count in NR2_SPLIT_PAIRS.items():
        for pair_index in range(pair_count):
            pulse_width = 1 if pair_index % 2 == 0 else 2
            amplitude = NR2_AMPLITUDES[pair_index % len(NR2_AMPLITUDES)]
            event_count = 4 if pulse_width == 1 else 2
            directions = [_direction(split, pair_index, event) for event in range(event_count)]
            for sign in (1, -1):
                actions: list[tuple[float, ...]] = []
                if pulse_width == 1:
                    for direction in directions:
                        actions.append(tuple(float(sign * amplitude * value) for value in direction))
                        actions.append((0.0,) * N_COILS)
                else:
                    for direction in directions:
                        action = tuple(float(sign * amplitude * value) for value in direction)
                        actions.extend((action, action, (0.0,) * N_COILS, (0.0,) * N_COILS))
                specs.append(
                    NR2TrajectorySpec(
                        trajectory_id=f"{split}_p{pair_index:02d}_{'plus' if sign > 0 else 'minus'}",
                        split=split,
                        pair_index=pair_index,
                        sign=sign,
                        pulse_width=pulse_width,
                        normalized_amplitude=amplitude,
                        normalized_actions_tsc=tuple(actions),
                    )
                )
    return tuple(specs)


def validate_nr2_specs(specs: tuple[NR2TrajectorySpec, ...]) -> dict[str, Any]:
    expected_count = 2 * sum(NR2_SPLIT_PAIRS.values())
    if len(specs) != expected_count or len({spec.trajectory_id for spec in specs}) != expected_count:
        raise ContractError("NR2 spec count or identity mismatch")
    split_rows: dict[str, Any] = {}
    for split, pair_count in NR2_SPLIT_PAIRS.items():
        selected = [spec for spec in specs if spec.split == split]
        if len(selected) != 2 * pair_count:
            raise ContractError(f"NR2 {split} trajectory count mismatch")
        matrix = np.asarray(
            [action for spec in selected for action in spec.normalized_actions_tsc if any(action)],
            dtype=float,
        )
        rank = int(np.linalg.matrix_rank(matrix))
        if rank != N_COILS:
            raise ContractError(f"NR2 {split} action directions have rank {rank}, expected 14")
        for pair_index in range(pair_count):
            plus = next(spec for spec in selected if spec.pair_index == pair_index and spec.sign == 1)
            minus = next(spec for spec in selected if spec.pair_index == pair_index and spec.sign == -1)
            if not np.array_equal(
                np.asarray(plus.normalized_actions_tsc), -np.asarray(minus.normalized_actions_tsc)
            ):
                raise ContractError("NR2 paired action streams are not exact negatives")
        split_rows[split] = {
            "pair_count": pair_count,
            "trajectory_count": len(selected),
            "action_rank": rank,
            "plant_advances": len(selected) * NR2_HORIZON_STEPS,
        }
    digest_payload = "\n".join(
        f"{spec.trajectory_id}:" + ",".join(
            ";".join(f"{value:.17g}" for value in action)
            for action in spec.normalized_actions_tsc
        )
        for spec in specs
    ).encode()
    return {
        "schema_version": NR2_CONTRACT_VERSION,
        "campaign_id": NR2_CAMPAIGN_ID,
        "trajectory_count": len(specs),
        "plant_advances": len(specs) * NR2_HORIZON_STEPS,
        "splits": split_rows,
        "action_stream_sha256": hashlib.sha256(digest_payload).hexdigest(),
    }
