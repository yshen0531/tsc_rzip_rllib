"""Deterministic prospective specification for the 1 ms NR2 campaign."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from functools import lru_cache
import hashlib
from typing import Any, Sequence

import numpy as np

from tsc_rzip_rllib.core.inputa import format_number

from .rgeo_zgeo_1ms_contract import MAX_SINGLE_TURN_COIL_DELTA_A_PER_STEP, N_COILS
from .rgeo_zgeo_1ms_nr1 import (
    Card15Target,
    assert_exact_slew,
    card15_target_decimal_a,
    decimal_single_turn_currents_a,
    quantize_target,
)
from .rgeo_zgeo_contract import ContractError


NR2_1MS_CONTRACT_VERSION = "rgeo-zgeo-1ms-nr2r1-v1"
NR2_1MS_CAMPAIGN_ID = "rgeo_zgeo_1ms_nr2r1_q0_structural_residual_v1"
NR2_1MS_EXCITATION_SEED = "rgeo_zgeo_1ms_nr2_structural_residual_v1"
NR2_1MS_HORIZON_STEPS = 16
NR2_1MS_SPLIT_PAIRS = {"development": 10, "calibration": 4, "holdout": 4}
NR2_1MS_AMPLITUDE_A = {"full": Decimal("0.30"), "half": Decimal("0.15")}


@dataclass(frozen=True)
class OneMsNR2TrajectorySpec:
    trajectory_id: str
    split: str
    pair_index: int
    sign: int
    schedule_type: str
    signed_events_tsc: tuple[tuple[int, ...], ...]
    schedule: tuple[tuple[str, int | None], ...]

    def __post_init__(self) -> None:
        if self.split not in NR2_1MS_SPLIT_PAIRS or self.sign not in {-1, 1}:
            raise ContractError("invalid 1 ms NR2 split or sign")
        if self.schedule_type not in {"impulse", "dwell", "switch"}:
            raise ContractError("invalid 1 ms NR2 schedule type")
        if len(self.schedule) != NR2_1MS_HORIZON_STEPS:
            raise ContractError("1 ms NR2 schedule must contain sixteen targets")
        for event in self.signed_events_tsc:
            if len(event) != N_COILS or any(value not in {-1, 1} for value in event):
                raise ContractError("1 ms NR2 events must be signed 14-vectors")
        for amplitude, event_index in self.schedule:
            if amplitude not in {"zero", "full", "half"}:
                raise ContractError("invalid 1 ms NR2 schedule amplitude")
            if amplitude == "zero":
                if event_index is not None:
                    raise ContractError("zero target cannot reference an event")
            elif event_index is None or not 0 <= event_index < len(self.signed_events_tsc):
                raise ContractError("nonzero target must reference a valid event")

    def to_dict(self) -> dict[str, Any]:
        return {
            "trajectory_id": self.trajectory_id,
            "split": self.split,
            "pair_index": self.pair_index,
            "sign": self.sign,
            "schedule_type": self.schedule_type,
            "signed_events_tsc": [list(value) for value in self.signed_events_tsc],
            "schedule": [[amplitude, event] for amplitude, event in self.schedule],
        }


def _direction(split: str, pair_index: int, event_index: int) -> tuple[int, ...]:
    values = []
    for coil_index in range(N_COILS):
        token = (
            f"{NR2_1MS_EXCITATION_SEED}:{split}:{pair_index}:{event_index}:{coil_index}"
        ).encode()
        values.append(1 if hashlib.sha256(token).digest()[0] & 1 else -1)
    return tuple(values)


def _schedule(kind: str) -> tuple[tuple[str, int | None], ...]:
    if kind == "impulse":
        rows: list[tuple[str, int | None]] = [("zero", None)] * 16
        for event, step in enumerate((1, 5, 9, 13)):
            rows[step] = ("full", event)
        return tuple(rows)
    if kind == "dwell":
        return tuple(
            [("zero", None)]
            + [("half", 0)] * 4
            + [("zero", None)] * 4
            + [("half", 1)] * 4
            + [("zero", None)] * 3
        )
    return tuple(
        [("zero", None)]
        + [("half", event) for event in range(6) for _ in range(2)]
        + [("zero", None)] * 3
    )


def build_one_ms_nr2_specs() -> tuple[OneMsNR2TrajectorySpec, ...]:
    specs: list[OneMsNR2TrajectorySpec] = []
    kinds = ("impulse", "dwell", "switch")
    event_counts = {"impulse": 4, "dwell": 2, "switch": 6}
    for split, pair_count in NR2_1MS_SPLIT_PAIRS.items():
        for pair_index in range(pair_count):
            kind = kinds[pair_index % len(kinds)]
            directions = tuple(
                _direction(split, pair_index, event)
                for event in range(event_counts[kind])
            )
            for sign in (1, -1):
                signed = tuple(
                    tuple(sign * value for value in direction) for direction in directions
                )
                specs.append(
                    OneMsNR2TrajectorySpec(
                        trajectory_id=(
                            f"{split}_p{pair_index:02d}_{'plus' if sign > 0 else 'minus'}"
                        ),
                        split=split,
                        pair_index=pair_index,
                        sign=sign,
                        schedule_type=kind,
                        signed_events_tsc=signed,
                        schedule=_schedule(kind),
                    )
                )
    return tuple(specs)


@lru_cache(maxsize=None)
def _lattice_target(
    q0_a: Decimal, source_a: Decimal, turn: Decimal, sign: int, limit_a: Decimal
) -> tuple[str, Decimal]:
    candidates: dict[str, Decimal] = {}
    for unit in range(1, 6001):
        request = q0_a + Decimal(sign * unit) * Decimal("0.00005")
        field = format_number(float(request * turn / Decimal("1000")))
        value = Decimal(field.strip()) * Decimal("1000") / turn
        delta = value - q0_a
        if (
            delta * sign > 0
            and abs(delta) <= limit_a
            and abs(value - source_a) <= MAX_SINGLE_TURN_COIL_DELTA_A_PER_STEP
        ):
            candidates[field] = value
    if not candidates:
        raise ContractError("no nonzero Card15 target exists in the 1 ms NR2 envelope")
    return max(candidates.items(), key=lambda item: abs(item[1] - q0_a))


def build_one_ms_nr2_targets(
    spec: OneMsNR2TrajectorySpec,
    *,
    source_current_a_tsc: Sequence[Any],
    turns_tsc: Sequence[Any],
) -> tuple[Card15Target, ...]:
    source = tuple(Decimal(str(value)) for value in source_current_a_tsc)
    turns = tuple(Decimal(str(value)) for value in turns_tsc)
    if len(source) != N_COILS or len(turns) != N_COILS:
        raise ContractError("1 ms NR2 target construction requires fourteen coils")
    q0 = quantize_target(tuple(float(value) for value in source), tuple(float(x) for x in turns))
    q0_a = card15_target_decimal_a(q0, turns, name="nr2.q0")
    assert_exact_slew(source, q0_a, name="nr2.source_to_q0")
    cache: dict[tuple[str, tuple[int, ...]], Card15Target] = {}
    output: list[Card15Target] = []
    for amplitude, event_index in spec.schedule:
        if amplitude == "zero":
            output.append(q0)
            continue
        signs = spec.signed_events_tsc[int(event_index)]
        key = (amplitude, signs)
        if key not in cache:
            fields: list[str] = []
            values: list[float] = []
            for center, actual, turn, sign in zip(q0_a, source, turns, signs):
                field, value = _lattice_target(
                    center, actual, turn, sign, NR2_1MS_AMPLITUDE_A[amplitude]
                )
                fields.append(field)
                values.append(float(value))
            cache[key] = Card15Target(tuple(fields), tuple(values))
        output.append(cache[key])
    previous = q0_a
    for step, target in enumerate(output):
        target_a = card15_target_decimal_a(target, turns, name=f"nr2.target.{step}")
        assert_exact_slew(previous, target_a, name=f"nr2.command.{step}")
        previous = target_a
    return tuple(output)


def validate_one_ms_nr2_specs(
    specs: tuple[OneMsNR2TrajectorySpec, ...],
    *,
    source_current_a_tsc: Sequence[Any],
    turns_tsc: Sequence[Any],
) -> dict[str, Any]:
    expected = 2 * sum(NR2_1MS_SPLIT_PAIRS.values())
    if len(specs) != expected or len({value.trajectory_id for value in specs}) != expected:
        raise ContractError("1 ms NR2 spec identity/count mismatch")
    split_rows: dict[str, Any] = {}
    digest_rows: list[str] = []
    for split, pair_count in NR2_1MS_SPLIT_PAIRS.items():
        selected = tuple(value for value in specs if value.split == split)
        if len(selected) != 2 * pair_count:
            raise ContractError(f"1 ms NR2 {split} count mismatch")
        quantized_rows: list[list[float]] = []
        for pair_index in range(pair_count):
            plus = next(x for x in selected if x.pair_index == pair_index and x.sign == 1)
            minus = next(x for x in selected if x.pair_index == pair_index and x.sign == -1)
            if np.any(np.asarray(plus.signed_events_tsc) != -np.asarray(minus.signed_events_tsc)):
                raise ContractError("1 ms NR2 sign mates are not exact event antipodes")
        q0 = quantize_target(source_current_a_tsc, turns_tsc)
        q0_a = np.asarray(q0.current_a_tsc)
        for spec in selected:
            targets = build_one_ms_nr2_targets(
                spec, source_current_a_tsc=source_current_a_tsc, turns_tsc=turns_tsc
            )
            for target in targets:
                delta = np.asarray(target.current_a_tsc) - q0_a
                if np.any(delta):
                    quantized_rows.append(delta.tolist())
                digest_rows.append(spec.trajectory_id + ":" + "|".join(target.card15_fields))
        rank = int(np.linalg.matrix_rank(np.asarray(quantized_rows)))
        if rank != N_COILS:
            raise ContractError(f"1 ms NR2 {split} quantized rank is {rank}, expected 14")
        split_rows[split] = {
            "pair_count": pair_count,
            "trajectory_count": len(selected),
            "plant_advances": len(selected) * NR2_1MS_HORIZON_STEPS,
            "quantized_action_rank": rank,
        }
    return {
        "schema_version": NR2_1MS_CONTRACT_VERSION,
        "campaign_id": NR2_1MS_CAMPAIGN_ID,
        "trajectory_count": len(specs),
        "plant_advances": len(specs) * NR2_1MS_HORIZON_STEPS,
        "splits": split_rows,
        "action_stream_sha256": hashlib.sha256("\n".join(digest_rows).encode()).hexdigest(),
    }
