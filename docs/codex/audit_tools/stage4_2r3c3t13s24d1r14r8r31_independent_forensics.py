#!/usr/bin/env python3
"""Structurally independent zero-TSC bank/model audit for frozen R8R31."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import numpy as np

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r8r23_independent_forensics as ind23,
)
from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r8r28_independent_forensics as ind28,
)


STAGE = "Stage4.2R3c3T13S24D1R14R8R31"
IDENTITY = "aligned_explicit_four_coordinate_measurement_recentered_feedback_v1"
RUN_NAME = "stage4_2r3c3t13s24d1r14r8r31_aligned_explicit_four_coordinate_feedback_sentinel"
DECISIONS = (10, 12, 14, 16, 18, 22)
MAX_COUNTS = (2, 2, 2, 2, 4, 15)
FACTORS = np.asarray([0.03, 0.03, 10000.0, 1.0, 1.0], dtype=float)


def _root() -> Path:
    return Path(__file__).resolve().parents[3]


def _read(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
    )


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        + "\n",
        encoding="utf-8",
    )


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _stage(args: argparse.Namespace) -> Path:
    return args.run_dir.expanduser().resolve() / RUN_NAME


def _source_stage(root: Path, section: Mapping[str, Any]) -> Path:
    return root.expanduser().resolve() / str(section["stage_directory"])


def _authenticate(args: argparse.Namespace, cfg: Mapping[str, Any]) -> dict[str, Any]:
    config23 = _read((_root() / str(cfg["source_r8r23_config"])).resolve())
    transitive23 = ind23._authenticate(args, config23)
    stage23 = _source_stage(args.r8r23_run, cfg["source_r8r23"])
    paths23 = {
        "primary_detailed": stage23 / "analysis/primary_detailed.json",
        "primary_summary": stage23 / "analysis/primary_summary.json",
        "independent": stage23 / "analysis/independent.json",
        "final_report": stage23 / "analysis/final_report.json",
        "stage_manifest": stage23 / "stage_manifest.json",
        "stage_state": stage23 / "stage_state.json",
    }
    hashes23 = {name: _sha(path) for name, path in paths23.items()}
    if any(
        digest != str(cfg["source_r8r23"][f"{name}_sha256"])
        for name, digest in hashes23.items()
    ):
        raise ValueError("independent R8R31 R8R23 hash authentication failed")
    final23, state23 = _read(paths23["final_report"]), _read(paths23["stage_state"])
    if (
        args.r8r23_run.name != str(cfg["source_r8r23"]["run_name"])
        or final23.get("route") != str(cfg["source_r8r23"]["required_route"])
        or state23.get("finished") is not True
        or bool(state23.get("real_tsc_executed"))
        or int(state23.get("new_raw_count", -1)) != 0
    ):
        raise ValueError("independent R8R31 R8R23 outcome changed")

    stage14 = _source_stage(args.r8r14_run, cfg["source_r8r14"])
    paths14 = {
        "final_report": stage14 / "analysis/final_report.json",
        "stage_manifest": stage14 / "stage_manifest.json",
        "stage_state": stage14 / "stage_state.json",
        "all_specs": stage14 / "specs/all_specs.json",
    }
    hashes14 = {name: _sha(path) for name, path in paths14.items()}
    if any(
        digest != str(cfg["source_r8r14"][f"{name}_sha256"])
        for name, digest in hashes14.items()
    ):
        raise ValueError("independent R8R31 R8R14 hash authentication failed")
    inventory14 = {
        phase: ind28._inventory(stage14 / "raw" / phase)
        for phase in ("safety", "qualification")
    }
    if any(
        inventory14[phase][key]
        != cfg["source_r8r14"][f"{phase}_raw_{'digest' if key == 'digest' else key}"]
        for phase in inventory14
        for key in ("count", "bytes", "digest")
    ):
        raise ValueError("independent R8R31 R8R14 raw authentication failed")

    stage28 = _source_stage(args.r8r28_run, cfg["source_r8r28"])
    paths28 = {
        "final_report": stage28 / "analysis/final_report.json",
        "final_independent": stage28 / "analysis/final_independent.json",
        "stage_manifest": stage28 / "stage_manifest.json",
        "stage_state": stage28 / "stage_state.json",
        "all_specs": stage28 / "specs/all_specs.json",
    }
    hashes28 = {name: _sha(path) for name, path in paths28.items()}
    if any(
        digest != str(cfg["source_r8r28"][f"{name}_sha256"])
        for name, digest in hashes28.items()
    ):
        raise ValueError("independent R8R31 R8R28 hash authentication failed")
    inventory28 = {
        phase: ind28._inventory(stage28 / "raw" / phase)
        for phase in ("safety", "qualification")
    }
    if any(
        inventory28[phase][key]
        != cfg["source_r8r28"][f"{phase}_raw_{'digest' if key == 'digest' else key}"]
        for phase in inventory28
        for key in ("count", "bytes", "digest")
    ):
        raise ValueError("independent R8R31 R8R28 raw authentication failed")
    final28, state28 = _read(paths28["final_report"]), _read(paths28["stage_state"])
    if (
        args.r8r28_run.name != str(cfg["source_r8r28"]["run_name"])
        or final28.get("route") != str(cfg["source_r8r28"]["required_route"])
        or final28.get("integrity_gate_passed") is not True
        or final28.get("scientific_gate_passed") is not False
        or state28.get("finished") is not True
        or state28.get("real_tsc_executed") is not True
        or int(state28.get("new_raw_count", -1)) != 64
    ):
        raise ValueError("independent R8R31 R8R28 outcome changed")
    return {
        "r8r23": {"hashes": hashes23, "transitive": transitive23},
        "r8r14": {"hashes": hashes14, "inventories": inventory14},
        "r8r28": {"hashes": hashes28, "inventories": inventory28},
        "passed": True,
    }


def _states(result: Mapping[str, Any], target: Sequence[float]) -> np.ndarray:
    target_value = np.asarray(target, dtype=float).reshape(3)
    rows = []
    for index, current in enumerate(result["trajectory"]):
        previous = result["trajectory"][index - 1] if index else current
        rows.append(
            [
                (float(current["R"]) - target_value[0]) / 0.03,
                (float(current["Z"]) - target_value[1]) / 0.03,
                (float(current["Ip"]) - target_value[2]) / 10000.0,
                (float(current["R"]) - float(previous["R"])) / 0.01,
                (float(current["Z"]) - float(previous["Z"])) / 0.01,
            ]
        )
    value = np.asarray(rows, dtype=float)
    if value.ndim != 2 or value.shape[1] != 5 or not np.all(np.isfinite(value)):
        raise ValueError("independent R8R31 state matrix invalid")
    return value


def _q4(q2: Sequence[float]) -> np.ndarray:
    u, v = map(float, np.asarray(q2, dtype=float).reshape(2))
    return np.asarray([0.0, -v, u, 0.0], dtype=float)


def _feature(
    states: np.ndarray,
    trajectory: Sequence[Mapping[str, Any]],
    decision: int,
    previous_decision: int,
    previous_q: Sequence[float],
    limits: Sequence[float],
) -> np.ndarray:
    current = np.asarray(trajectory[decision]["currents_a_tsc"], dtype=float)
    previous = np.asarray(trajectory[previous_decision]["currents_a_tsc"], dtype=float)
    value = np.r_[
        states[decision - 3 : decision + 1, :3].ravel(),
        current / np.asarray(limits, dtype=float),
        (current - previous) / np.asarray(limits, dtype=float),
        np.asarray(previous_q, dtype=float) / 1.5,
    ]
    if value.shape != (44,) or not np.all(np.isfinite(value)):
        raise ValueError("independent R8R31 causal feature invalid")
    return value


def _expand(feature: Sequence[float], q: Sequence[float], previous_q: Sequence[float]) -> np.ndarray:
    base = np.asarray(feature, dtype=float).reshape(44)
    value_q = np.asarray(q, dtype=float).reshape(4)
    old_q = np.asarray(previous_q, dtype=float).reshape(4)
    a, b, c, d = map(float, value_q)
    action = np.asarray(
        [
            a, b, c, d, a * a, a * b, a * c, a * d, b * b,
            b * c, b * d, c * c, c * d, d * d, *(value_q - old_q),
        ],
        dtype=float,
    )
    expanded = np.r_[base, action, base * a, base * b, base * c, base * d]
    if expanded.shape != (238,) or not np.all(np.isfinite(expanded)):
        raise ValueError("independent R8R31 expanded feature invalid")
    return expanded


def _source_entries(
    args: argparse.Namespace, cfg: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], dict[tuple[str, str], dict[str, Any]]]:
    config23 = _read((_root() / str(cfg["source_r8r23_config"])).resolve())
    source_args, source_cfg = ind23._source_args(args, config23)
    ind22 = ind23.ind22
    source_ctx = ind22._source_context(source_args, source_cfg)
    baseline_specs, baseline_results = ind22._source_baselines(source_args, source_cfg, source_ctx)
    u_specs, u_results = ind22._source_r8r12_candidates(source_args, source_cfg)
    v_specs, v_results = ind22._source_r8r14_candidates(source_args, source_cfg)
    r15_specs, r15_results = ind22._source_r8r15_candidates(source_args, source_cfg)
    r20_specs, r20_results = ind22._source_r8r20_candidates(source_args, source_cfg)
    r22_specs = ind22._expected_specs(source_args, source_cfg, source_ctx)
    evaluators, _ = ind22.r8r7.r8.d1r11._formal_callback(
        source_ctx.r8_ctx.d1r11_ctx, baseline_specs
    )
    evaluator_by_context = {
        (str(spec["pair_id"]), str(spec["history_member"])): evaluators[str(spec["experiment_id"])]
        for spec in baseline_specs
    }
    entries: list[dict[str, Any]] = []

    def add(
        spec: Mapping[str, Any], result: Mapping[str, Any], schedule: str,
        sequence: Sequence[Sequence[float]], source: str,
    ) -> None:
        q_by_step = {10: _q4(sequence[0]), 12: np.zeros(4), 14: _q4(sequence[1]),
                     16: np.zeros(4), 18: _q4(sequence[2]), 22: _q4(sequence[3])}
        entries.append({"spec": spec, "result": result, "schedule": schedule,
                        "q_by_step": q_by_step, "source": source})

    for spec in baseline_specs:
        add(spec, baseline_results[str(spec["experiment_id"])], "q0", [[0.0, 0.0]] * 4, "R8R7")
    for spec in u_specs:
        add(spec, u_results[str(spec["experiment_id"])], "UUUU", [[1.0, 0.0]] * 4, "R8R12")
    for spec in v_specs:
        add(spec, v_results[str(spec["experiment_id"])], "VVVV", [[0.0, 1.0]] * 4, "R8R14")
    for spec in r15_specs:
        code = str(spec["r8r15_sequence_code"])
        add(spec, r15_results[str(spec["experiment_id"])], code,
            [[1.0, 0.0] if symbol == "U" else [0.0, 1.0] for symbol in code], "R8R15")
    for spec in r20_specs:
        code = str(spec["r8r20_sequence_code"])
        add(spec, r20_results[str(spec["experiment_id"])], code,
            [[1.0, 0.0] if symbol == "U" else [0.0, 1.0] for symbol in code], "R8R20")
    stage22 = ind22._stage(source_args)
    for spec in r22_specs:
        result = ind22._gzip(stage22 / "raw" / str(spec["partition"]) / f"{spec['experiment_id']}.json.gz")
        amplitude, weight = float(spec["r8r22_amplitude"]), float(spec["r8r22_mixing_weight"])
        q = [amplitude * weight, amplitude * (1.0 - weight)]
        add(spec, result, str(spec["r8r22_candidate_id"]), [q] * 4, "R8R22")

    r22_by_context: dict[tuple[str, str], Mapping[str, Any]] = {}
    for spec in r22_specs:
        r22_by_context.setdefault((str(spec["pair_id"]), str(spec["history_member"])), spec)
    baseline_by_context = {
        (str(spec["pair_id"]), str(spec["history_member"])):
        (spec, baseline_results[str(spec["experiment_id"])])
        for spec in baseline_specs
    }
    execution = ind22._execution_context(source_ctx, stage22)
    lattice = execution.d1r11_ctx.base_ctx.base_ctx.cfg["lattice_probe"]
    metadata = {}
    for key, spec in r22_by_context.items():
        payload = _read(stage22 / "variants" / f"payload_{spec['experiment_id']}.json")
        actuator = ind22.mpc.actuator_from_payload(payload, lattice)
        limits = np.maximum(
            np.abs(np.asarray(actuator.minimum_current_a_tsc, dtype=float)),
            np.abs(np.asarray(actuator.maximum_current_a_tsc, dtype=float)),
        )
        base_spec, base_result = baseline_by_context[key]
        metadata[key] = {
            "target": np.asarray(evaluator_by_context[key].target, dtype=float),
            "limits": limits,
            "horizon": int(base_spec["horizon_steps"]),
            "baseline_result": base_result,
        }
    return entries, metadata


def _build_bank(args: argparse.Namespace, cfg: Mapping[str, Any]) -> list[dict[str, Any]]:
    entries, metadata = _source_entries(args, cfg)
    stage14 = _source_stage(args.r8r14_run, cfg["source_r8r14"])
    for spec in _read(stage14 / "specs/all_specs.json"):
        direction, sign = int(spec["r8r14_direction_index"]), int(spec["r8r14_sign"])
        if (direction, sign) in ((2, 1), (1, -1)):
            continue
        q = np.zeros(4, dtype=float)
        q[direction] = sign * float(spec["r8r14_canonical_scale"])
        entries.append(
            {
                "spec": spec,
                "result": ind28._gzip(stage14 / "raw" / str(spec["partition"]) / f"{spec['experiment_id']}.json.gz"),
                "schedule": f"R8R14_d{direction}_{'p' if sign > 0 else 'm'}",
                "q_by_step": {step: q for step in (10, 14, 18, 22)},
                "source": "R8R14",
            }
        )
    stage28 = _source_stage(args.r8r28_run, cfg["source_r8r28"])
    for spec in _read(stage28 / "specs/all_specs.json"):
        if str(spec["r8r28_grid_id"]) != "g2":
            continue
        direction, sign = int(spec["r8r28_direction_index"]), int(spec["r8r28_sign"])
        q = np.zeros(4, dtype=float)
        q[direction] = float(sign)
        entries.append(
            {
                "spec": spec,
                "result": ind28._gzip(stage28 / "raw" / str(spec["partition"]) / f"{spec['experiment_id']}.json.gz"),
                "schedule": f"R8R28_g2_{spec['r8r28_sequence_id']}",
                "q_by_step": {step: q for step in (10, 12, 14, 16)},
                "source": "R8R28",
            }
        )

    output = []
    for entry in entries:
        spec, result = entry["spec"], entry["result"]
        key = (str(spec["pair_id"]), str(spec["history_member"]))
        meta = metadata[key]
        horizon = int(spec["horizon_steps"])
        if result.get("success") is not True or len(result["trajectory"]) != horizon + 1:
            raise ValueError("independent R8R31 source trajectory incomplete")
        states = _states(result, meta["target"])
        previous_q = np.zeros(4, dtype=float)
        intervals = []
        for interval, decision in enumerate(DECISIONS):
            previous_decision = decision if interval == 0 else DECISIONS[interval - 1]
            end = DECISIONS[interval + 1] if interval < 5 else horizon
            q = np.asarray(entry["q_by_step"].get(decision, np.zeros(4)), dtype=float)
            feature = _feature(states, result["trajectory"], decision, previous_decision,
                               previous_q, meta["limits"])
            targets = states[decision + 1 : end + 1]
            row = {
                "row_id": f"{entry['source']}|{spec['experiment_id']}|i{interval}",
                "interval": interval,
                "decision": decision,
                "feature": feature,
                "q": q,
                "previous_q": previous_q.copy(),
                "targets": targets,
            }
            row["expanded"] = _expand(feature, q, previous_q)
            intervals.append(row)
            previous_q = q
        output.append(
            {
                "trajectory_id": f"{entry['source']}|{spec['experiment_id']}",
                "pair_id": key[0],
                "history_member": key[1],
                "schedule_id": str(entry["schedule"]),
                "source": str(entry["source"]),
                "intervals": intervals,
            }
        )
    schedules = {}
    for trajectory in output:
        key = (trajectory["pair_id"], trajectory["history_member"])
        schedules.setdefault(key, set()).add(trajectory["schedule_id"])
    if (
        len(output) != 560
        or len(schedules) != 16
        or any(len(value) != 35 for value in schedules.values())
        or sum(len(row["intervals"]) for row in output) != 3360
    ):
        raise ValueError("independent R8R31 bank coverage changed")
    return sorted(output, key=lambda row: row["trajectory_id"])


def _bank_evidence(bank: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    serial = []
    for trajectory in bank:
        serial.append(
            {
                "trajectory_id": trajectory["trajectory_id"],
                "pair_id": trajectory["pair_id"],
                "history_member": trajectory["history_member"],
                "schedule_id": trajectory["schedule_id"],
                "rows": [
                    {
                        "row_id": row["row_id"],
                        "decision": row["decision"],
                        "feature": np.asarray(row["feature"]).tolist(),
                        "q": np.asarray(row["q"]).tolist(),
                        "previous_q": np.asarray(row["previous_q"]).tolist(),
                        "targets": np.asarray(row["targets"]).tolist(),
                    }
                    for row in trajectory["intervals"]
                ],
            }
        )
    schedules = sorted({str(row["schedule_id"]) for row in bank})
    sources = sorted({str(row["source"]) for row in bank})
    return {
        "trajectory_count": len(bank),
        "context_count": len({(row["pair_id"], row["history_member"]) for row in bank}),
        "schedule_count": len(schedules),
        "interval_record_count": 3360,
        "source_counts": {source: sum(row["source"] == source for row in bank) for source in sources},
        "schedule_ids": schedules,
        "bank_digest": _digest(serial),
        "feature_digest": _digest([row["feature"] for item in serial for row in item["rows"]]),
        "target_digest": _digest([row["targets"] for item in serial for row in item["rows"]]),
    }


def _fit(
    bank: Sequence[Mapping[str, Any]], selected: Callable[[Mapping[str, Any]], bool], ridge: float
) -> dict[str, Any]:
    groups = []
    for interval in range(6):
        rows = [trajectory["intervals"][interval] for trajectory in bank if selected(trajectory)]
        offsets = []
        for offset in range(max(len(row["targets"]) for row in rows)):
            current = [row for row in rows if len(row["targets"]) > offset]
            x = np.asarray([row["expanded"] for row in current], dtype=float)
            y = np.asarray([row["targets"][offset] for row in current], dtype=float)
            mean_x, mean_y = np.mean(x, axis=0), np.mean(y, axis=0)
            dx, dy = x - mean_x, y - mean_y
            coefficient = np.linalg.solve(dx.T @ dx + ridge * np.eye(238), dx.T @ dy)
            intercept = mean_y - mean_x @ coefficient
            if not np.all(np.isfinite(coefficient)) or not np.all(np.isfinite(intercept)):
                raise ValueError("independent R8R31 ridge fit invalid")
            offsets.append(
                {"sample_offset": offset, "training_row_count": len(current),
                 "intercept": intercept, "coefficients": coefficient}
            )
        groups.append({"interval": interval, "offsets": offsets})
    return {"intervals": groups}


def _model_json(model: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "intervals": [
            {
                "interval": int(group["interval"]),
                "offsets": [
                    {
                        "sample_offset": int(offset["sample_offset"]),
                        "training_row_count": int(offset["training_row_count"]),
                        "intercept": np.asarray(offset["intercept"]).tolist(),
                        "coefficients": np.asarray(offset["coefficients"]).tolist(),
                    }
                    for offset in group["offsets"]
                ],
            }
            for group in model["intervals"]
        ]
    }


def _predict(model: Mapping[str, Any], row: Mapping[str, Any]) -> np.ndarray:
    feature = np.asarray(row["expanded"], dtype=float)
    return np.asarray(
        [
            np.asarray(offset["intercept"]) + feature @ np.asarray(offset["coefficients"])
            for offset in model["intervals"][int(row["interval"])]["offsets"][: len(row["targets"])]
        ],
        dtype=float,
    )


def _residual_groups(
    model: Mapping[str, Any], rows: Sequence[Mapping[str, Any]]
) -> tuple[list[list[list[np.ndarray]]], str]:
    groups: list[list[list[np.ndarray]]] = [[[] for _ in range(count)] for count in MAX_COUNTS]
    serial = []
    for trajectory in rows:
        current_serial = []
        for interval, row in enumerate(trajectory["intervals"]):
            residual = np.abs(np.asarray(row["targets"]) - _predict(model, row))
            current_serial.append(residual.tolist())
            for offset, value in enumerate(residual):
                groups[interval][offset].append(value)
        serial.append({"trajectory_id": trajectory["trajectory_id"], "absolute_residuals": current_serial})
    return groups, _digest(serial)


def _tube(
    folds: Sequence[Mapping[str, Any]], selected: Callable[[Mapping[str, Any]], bool], cfg: Mapping[str, Any]
) -> tuple[list[np.ndarray], dict[str, Any]]:
    chosen = [fold for fold in folds if selected(fold)]
    floor = np.asarray(cfg["model_contract"]["physical_point_error_floors"], dtype=float) / FACTORS
    reserve = float(cfg["model_contract"]["reserve_multiplier"])
    output, counts = [], []
    for interval, count in enumerate(MAX_COUNTS):
        values = []
        for offset in range(count):
            residual = np.asarray(
                [value for fold in chosen for value in fold["residual_groups"][interval][offset]],
                dtype=float,
            ).reshape((-1, 5))
            values.append(np.maximum(reserve * np.max(residual, axis=0), floor))
            counts.append(len(residual))
        output.append(np.asarray(values))
    return output, {
        "selected_fold_count": len(chosen),
        "minimum_group_count": min(counts),
        "maximum_group_count": max(counts),
        "tube_digest": _digest([value.tolist() for value in output]),
    }


def _support(
    bank: Sequence[Mapping[str, Any]], training: Sequence[str], held: str, multiplier: float
) -> dict[str, Any]:
    rows = []
    for interval in range(6):
        by_pair = {
            pair: np.asarray(
                [row["intervals"][interval]["feature"] for row in bank if row["pair_id"] == pair],
                dtype=float,
            )
            for pair in training
        }
        nested = []
        for pair, values in by_pair.items():
            other = np.concatenate([item for other_pair, item in by_pair.items() if other_pair != pair])
            nested.extend(np.min(np.linalg.norm(values[:, None] - other[None, :], axis=2), axis=1))
        threshold = multiplier * max(map(float, nested))
        trained = np.concatenate(list(by_pair.values()))
        held_values = np.asarray(
            [row["intervals"][interval]["feature"] for row in bank if row["pair_id"] == held],
            dtype=float,
        )
        distance = np.min(np.linalg.norm(held_values[:, None] - trained[None, :], axis=2), axis=1)
        rows.append(
            {"interval": interval, "threshold": threshold,
             "maximum_held_distance": float(np.max(distance)),
             "pass_count": int(np.count_nonzero(distance <= threshold + 1e-15)),
             "row_count": len(distance)}
        )
    return {"rows": rows, "passed": all(row["pass_count"] == row["row_count"] for row in rows)}


def _outer(
    bank: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    pairs = sorted({str(row["pair_id"]) for row in bank})
    ridge = float(cfg["model_contract"]["ridge_penalty"])
    folds = []
    for held in pairs:
        training = [pair for pair in pairs if pair != held]
        model = _fit(bank, lambda row, allowed=set(training): row["pair_id"] in allowed, ridge)
        held_rows = [row for row in bank if row["pair_id"] == held]
        residual_groups, residual_digest = _residual_groups(model, held_rows)
        folds.append(
            {"held_pair": held, "training_pairs": training, "model": model,
             "model_digest": _digest(_model_json(model)), "held": held_rows,
             "residual_groups": residual_groups, "residual_digest": residual_digest,
             "support": _support(bank, training, held,
                                  float(cfg["model_contract"]["support_threshold_multiplier"]))}
        )
    contained = component_count = 0
    maximum_error = np.zeros(5)
    maximum_tube = np.zeros(5)
    rows = []
    for fold in folds:
        tube, evidence = _tube(folds, lambda row, held=fold["held_pair"]: row["held_pair"] != held, cfg)
        fold_contained = fold_count = 0
        fold_error = np.zeros(5)
        for interval, offsets in enumerate(fold["residual_groups"]):
            for offset, values in enumerate(offsets):
                residual = np.asarray(values, dtype=float).reshape((-1, 5))
                fold_contained += int(np.count_nonzero(residual <= tube[interval][offset] + 1e-15))
                fold_count += residual.size
                fold_error = np.maximum(fold_error, np.max(residual, axis=0))
        maximum_error = np.maximum(maximum_error, fold_error * FACTORS)
        maximum_tube = np.maximum(maximum_tube, np.max(np.concatenate(tube), axis=0) * FACTORS)
        contained += fold_contained
        component_count += fold_count
        fold["tube"] = tube
        rows.append(
            {"held_pair": fold["held_pair"], "model_digest": fold["model_digest"],
             "residual_digest": fold["residual_digest"],
             "maximum_physical_error": (fold_error * FACTORS).tolist(),
             "contained_count": fold_contained, "component_count": fold_count,
             "support": fold["support"], "tube_evidence": evidence}
        )
    gates = cfg["model_gates"]
    rate = contained / component_count
    passed = bool(
        np.all(maximum_error <= np.asarray(gates["maximum_point_error"]) + 1e-15)
        and np.all(maximum_tube <= np.asarray(gates["maximum_tube_half_width"]) + 1e-15)
        and rate >= float(gates["required_reserved_tube_containment_rate"]) - 1e-15
        and all(fold["support"]["passed"] for fold in folds)
    )
    return folds, {
        "maximum_absolute_physical_error": maximum_error.tolist(),
        "maximum_reserved_physical_tube_half_width": maximum_tube.tolist(),
        "reserved_contained_count": contained,
        "reserved_component_count": component_count,
        "reserved_containment_rate": rate,
        "state_support_pass_count": sum(fold["support"]["passed"] for fold in folds),
        "fold_rows": rows,
        "passed": passed,
    }


def _maximum_difference(left: Any, right: Any) -> float:
    if isinstance(left, Mapping) and isinstance(right, Mapping):
        if set(left) != set(right):
            return math.inf
        return max((_maximum_difference(left[key], right[key]) for key in left), default=0.0)
    if isinstance(left, list) and isinstance(right, list):
        if len(left) != len(right):
            return math.inf
        return max((_maximum_difference(a, b) for a, b in zip(left, right)), default=0.0)
    if isinstance(left, bool) or isinstance(right, bool) or isinstance(left, str) or isinstance(right, str):
        return 0.0 if left == right else math.inf
    if left is None or right is None:
        return 0.0 if left is right else math.inf
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return abs(float(left) - float(right))
    return 0.0 if left == right else math.inf


def audit(args: argparse.Namespace, cfg: Mapping[str, Any]) -> dict[str, Any]:
    if cfg.get("stage") != STAGE or cfg.get("identity") != IDENTITY:
        raise ValueError("independent R8R31 configuration identity changed")
    authentication = _authenticate(args, cfg)
    stage = _stage(args)
    primary_path = stage / "analysis/primary_detailed.json"
    summary_path = stage / "analysis/primary_summary.json"
    model_path = stage / "model/preflight_model.json"
    primary, summary, primary_model = _read(primary_path), _read(summary_path), _read(model_path)
    bank = _build_bank(args, cfg)
    bank_evidence = _bank_evidence(bank)
    folds, outer = _outer(bank, cfg)
    tolerance = float(cfg["offline_gate"]["primary_independent_absolute_tolerance"])
    independent_models = [
        {"held_pair": fold["held_pair"], "model": _model_json(fold["model"]),
         "model_digest": fold["model_digest"]}
        for fold in folds
    ]
    bank_difference = _maximum_difference(primary["bank_evidence"], bank_evidence)
    fit_difference = _maximum_difference(primary_model["outer_folds"], independent_models)
    outer_difference = _maximum_difference(primary["outer_model_evaluation"], outer)
    if outer["passed"]:
        raise ValueError(
            "independent R8R31 schedule/support/action-tree implementation required before controller authorization"
        )
    route = str(cfg["routes"]["preflight_fail"])
    early_agreement = bool(
        primary["schedule_jackknife"] == {"ran": False, "passed": False}
        and primary["planning_evaluation"] == {"ran": False, "passed": False}
        and primary["fault_injection"] == {"ran": False, "passed": False}
    )
    result = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "audit_kind": "aligned_explicit_four_coordinate_feedback_preflight_independent",
        "source_authentication": authentication,
        "bank_evidence": bank_evidence,
        "outer_model_evaluation": outer,
        "maximum_bank_absolute_difference": bank_difference,
        "maximum_fit_absolute_difference": fit_difference,
        "maximum_outer_absolute_difference": outer_difference,
        "primary_bank_agreement": bank_difference <= tolerance,
        "primary_fit_agreement": fit_difference <= tolerance,
        "primary_outer_agreement": outer_difference <= tolerance,
        "primary_early_stop_agreement": early_agreement,
        "primary_route_agreement": primary.get("route") == route and summary.get("route") == route,
        "primary_outcome_agreement": (
            primary.get("integrity_gate_passed") is True
            and primary.get("scientific_gate_passed") is False
            and summary.get("scientific_gate_passed") is False
        ),
        "route": route,
        "primary_detailed_sha256": _sha(primary_path),
        "primary_summary_sha256": _sha(summary_path),
        "primary_model_sha256": _sha(model_path),
        "real_tsc_executed": False,
        "plant_step_count": 0,
        "new_raw_count": 0,
    }
    result["passed"] = bool(
        result["primary_bank_agreement"]
        and result["primary_fit_agreement"]
        and result["primary_outer_agreement"]
        and result["primary_early_stop_agreement"]
        and result["primary_route_agreement"]
        and result["primary_outcome_agreement"]
    )
    if not result["passed"]:
        raise ValueError("independent R8R31 preflight disagrees with primary")
    _write(stage / "analysis/independent.json", result)
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    for name in (
        "r8r23-run", "r8r28-run", "r8r22-run", "r8r7-run", "r8r12-run",
        "r8r14-run", "r8r15-run", "r8r19-run", "r8r20-run", "r8r27-run",
        "r8-run", "r8r1-output", "r8r6-run", "source-d1r11-run",
        "source-r2-run", "source-r4-run", "source-r6-run", "source-s21-run",
        "source-s23r1-output", "source-s24-run", "source-d1r9-v1",
        "source-d1r9-v2", "source-d1r10-run", "source-d1r10-audit",
        "source-stage42r3b-run", "source-stage42r3c3-run",
        "source-stage42r3c3-bank-dir", "source-stage42r3c3t1-run",
        "source-stage42r3c3t1-audit-dir", "source-stage42r3c3t3-controller-bank",
        "q1-run", "q2-run", "q1-audit", "q2-audit", "r3b-server-audit",
        "r3b-snapshot-checks",
    ):
        parser.add_argument(f"--{name}", dest=name.replace("-", "_"), type=Path, required=True)
    return parser


def main() -> None:
    args = _parser().parse_args()
    cfg = _read(args.config.expanduser().resolve())
    result = audit(args, cfg)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
