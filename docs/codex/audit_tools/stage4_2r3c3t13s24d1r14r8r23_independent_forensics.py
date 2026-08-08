#!/usr/bin/env python3
"""Structurally independent zero-TSC audit for frozen R8R23."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r8r22_independent_forensics as ind22,
)


STAGE = "Stage4.2R3c3T13S24D1R14R8R23"
RUN_NAME = "stage4_2r3c3t13s24d1r14r8r23_causal_online_innovation_receding_horizon_preflight"
DECISIONS = (10, 14, 18, 22)
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
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _source_args(args: argparse.Namespace, cfg: Mapping[str, Any]) -> tuple[argparse.Namespace, Mapping[str, Any]]:
    source = copy.copy(args)
    source.run_dir = args.r8r22_run
    source_cfg = _read((_root() / str(cfg["source_r8r22_config"])).resolve())
    return source, source_cfg


def _authenticate(args: argparse.Namespace, cfg: Mapping[str, Any]) -> dict[str, Any]:
    source_args, source_cfg = _source_args(args, cfg)
    stage = ind22._stage(source_args)
    expected = cfg["source_r8r22"]
    paths = {
        "primary_detailed": stage / "analysis/primary_detailed.json",
        "primary_summary": stage / "analysis/primary_summary.json",
        "final_independent": stage / "analysis/final_independent.json",
        "final_report": stage / "analysis/final_report.json",
        "offline_primary": stage / "analysis/offline_primary.json",
        "offline_independent": stage / "analysis/offline_independent.json",
        "safety_raw_primary": stage / "analysis/safety_raw_primary.json",
        "safety_raw_independent": stage / "analysis/safety_raw_independent.json",
        "qualification_raw_primary": stage / "analysis/qualification_raw_primary.json",
        "qualification_raw_independent": stage / "analysis/qualification_raw_independent.json",
        "stage_manifest": stage / "stage_manifest.json",
        "stage_state": stage / "stage_state.json",
    }
    hashes = {name: _sha(path) for name, path in paths.items()}
    if any(value != str(expected[f"{name}_sha256"]) for name, value in hashes.items()):
        raise ValueError("independent R8R23 R8R22 hash authentication failed")
    final, independent, state = (
        _read(paths["final_report"]),
        _read(paths["final_independent"]),
        _read(paths["stage_state"]),
    )
    specs = _read(stage / "specs/all_specs.json")
    inventories = {
        phase: ind22._inventory(stage / "raw" / phase)
        for phase in ("safety", "qualification")
    }
    for phase, inventory in inventories.items():
        if (
            int(inventory["count"]) != int(expected[f"{phase}_raw_count"])
            or int(inventory["bytes"]) != int(expected[f"{phase}_raw_bytes"])
            or inventory["digest"] != str(expected[f"{phase}_raw_digest"])
        ):
            raise ValueError("independent R8R23 raw inventory changed")
    route = str(expected["actual_route"])
    if (
        args.r8r22_run.name != str(expected["run_name"])
        or _digest(specs) != str(expected["spec_digest"])
        or final.get("route") != route
        or final.get("integrity_gate_passed") is not True
        or independent.get("passed") is not True
        or state.get("finished") is not True
        or int(state.get("new_raw_count", -1)) != 160
    ):
        raise ValueError("independent R8R23 R8R22 outcome changed")
    # These are the source-authentication implementations independent of the
    # primary R8R22 module used by R8R23.
    transitive = {
        "r8r12": ind22._authenticate_r8r12(source_args, source_cfg),
        "r8r14": ind22._authenticate_r8r14(source_args, source_cfg),
        "r8r15": ind22._authenticate_r8r15(source_args, source_cfg),
        "r8r19": ind22._authenticate_r8r19(source_args, source_cfg),
        "r8r20": ind22._authenticate_r8r20(source_args, source_cfg),
    }
    return {
        "hashes": hashes,
        "raw_inventories": inventories,
        "spec_digest": _digest(specs),
        "route": route,
        "transitive_source_authentication": transitive,
        "passed": True,
    }


def _states(result: Mapping[str, Any], target: Sequence[float]) -> np.ndarray:
    target = np.asarray(target, dtype=float)
    output = []
    for index, row in enumerate(result["trajectory"]):
        previous = result["trajectory"][index - 1] if index else row
        output.append(
            [
                (float(row["R"]) - target[0]) / 0.03,
                (float(row["Z"]) - target[1]) / 0.03,
                (float(row["Ip"]) - target[2]) / 10000.0,
                (float(row["R"]) - float(previous["R"])) / 0.01,
                (float(row["Z"]) - float(previous["Z"])) / 0.01,
            ]
        )
    value = np.asarray(output, dtype=float)
    if value.shape[1] != 5 or not np.all(np.isfinite(value)):
        raise ValueError("independent R8R23 state matrix invalid")
    return value


def _feature(
    states: np.ndarray,
    trajectory: Sequence[Mapping[str, Any]],
    decision: int,
    previous_decision: int,
    previous_q: Sequence[float],
    limits: np.ndarray,
) -> np.ndarray:
    current = np.asarray(trajectory[decision]["currents_a_tsc"], dtype=float)
    previous = np.asarray(trajectory[previous_decision]["currents_a_tsc"], dtype=float)
    value = np.r_[
        states[decision - 3 : decision + 1, :3].ravel(),
        current / limits,
        (current - previous) / limits,
        np.asarray(previous_q, dtype=float) / 1.5,
    ]
    if value.shape != (42,) or not np.all(np.isfinite(value)):
        raise ValueError("independent R8R23 feature invalid")
    return value


def _expand(feature: np.ndarray, q: Sequence[float], previous_q: Sequence[float]) -> np.ndarray:
    u, v = map(float, q)
    pu, pv = map(float, previous_q)
    action = np.asarray([u, v, u * u, u * v, v * v, u - pu, v - pv])
    value = np.r_[feature, action, feature * u, feature * v]
    if value.shape != (133,) or not np.all(np.isfinite(value)):
        raise ValueError("independent R8R23 expanded feature invalid")
    return value


def _build_bank(args: argparse.Namespace, cfg: Mapping[str, Any]) -> list[dict[str, Any]]:
    source_args, source_cfg = _source_args(args, cfg)
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
        (str(spec["pair_id"]), str(spec["history_member"])):
        evaluators[str(spec["experiment_id"])] for spec in baseline_specs
    }
    entries: list[dict[str, Any]] = []

    def add(spec: Mapping[str, Any], result: Mapping[str, Any], schedule: str,
            q_sequence: Sequence[Sequence[float]], source: str) -> None:
        entries.append({"spec": spec, "result": result, "schedule": schedule,
                        "q_sequence": [list(map(float, q)) for q in q_sequence],
                        "source": source})

    for spec in baseline_specs:
        add(spec, baseline_results[str(spec["experiment_id"])], "q0", [[0.0, 0.0]] * 4, "R8R7")
    for spec in u_specs:
        add(spec, u_results[str(spec["experiment_id"])], "UUUU", [[1.0, 0.0]] * 4, "R8R12")
    for spec in v_specs:
        add(spec, v_results[str(spec["experiment_id"])], "VVVV", [[0.0, 1.0]] * 4, "R8R14")
    for spec in r15_specs:
        code = str(spec["r8r15_sequence_code"])
        add(spec, r15_results[str(spec["experiment_id"])], code,
            [[1.0, 0.0] if value == "U" else [0.0, 1.0] for value in code], "R8R15")
    for spec in r20_specs:
        code = str(spec["r8r20_sequence_code"])
        add(spec, r20_results[str(spec["experiment_id"])], code,
            [[1.0, 0.0] if value == "U" else [0.0, 1.0] for value in code], "R8R20")
    source_stage = ind22._stage(source_args)
    for spec in r22_specs:
        result = ind22._gzip(source_stage / "raw" / str(spec["partition"]) /
                             f"{spec['experiment_id']}.json.gz")
        amplitude, weight = float(spec["r8r22_amplitude"]), float(spec["r8r22_mixing_weight"])
        q = [amplitude * weight, amplitude * (1.0 - weight)]
        add(spec, result, str(spec["r8r22_candidate_id"]), [q] * 4, "R8R22")

    r22_by_context = {}
    for spec in r22_specs:
        r22_by_context.setdefault((str(spec["pair_id"]), str(spec["history_member"])), spec)
    baseline_by_context = {
        (str(spec["pair_id"]), str(spec["history_member"])):
        (spec, baseline_results[str(spec["experiment_id"])]) for spec in baseline_specs
    }
    execution = ind22._execution_context(source_ctx, source_stage)
    lattice = execution.d1r11_ctx.base_ctx.base_ctx.cfg["lattice_probe"]
    metadata = {}
    for key, spec in r22_by_context.items():
        payload = _read(source_stage / "variants" / f"payload_{spec['experiment_id']}.json")
        actuator = ind22.mpc.actuator_from_payload(payload, lattice)
        limits = np.maximum(np.abs(np.asarray(actuator.minimum_current_a_tsc)),
                            np.abs(np.asarray(actuator.maximum_current_a_tsc)))
        base_spec, base_result = baseline_by_context[key]
        metadata[key] = {
            "target": np.asarray(evaluator_by_context[key].target, dtype=float),
            "limits": limits,
            "horizon": int(base_spec["horizon_steps"]),
        }
    output = []
    for entry in entries:
        spec, result = entry["spec"], entry["result"]
        key = (str(spec["pair_id"]), str(spec["history_member"]))
        meta = metadata[key]
        horizon = int(spec["horizon_steps"])
        if result.get("success") is not True or len(result["trajectory"]) != horizon + 1:
            raise ValueError("independent R8R23 incomplete source")
        states = _states(result, meta["target"])
        interval_rows = []
        for interval, decision in enumerate(DECISIONS):
            previous_decision = decision if interval == 0 else DECISIONS[interval - 1]
            previous_q = [0.0, 0.0] if interval == 0 else entry["q_sequence"][interval - 1]
            end = DECISIONS[interval + 1] if interval < 3 else horizon
            feature = _feature(states, result["trajectory"], decision,
                               previous_decision, previous_q, meta["limits"])
            q = entry["q_sequence"][interval]
            interval_rows.append({
                "row_id": f"{entry['source']}|{spec['experiment_id']}|i{interval}",
                "interval": interval, "feature": feature,
                "q": np.asarray(q, dtype=float),
                "previous_q": np.asarray(previous_q, dtype=float),
                "expanded": _expand(feature, q, previous_q),
                "targets": states[decision + 1 : end + 1],
            })
        output.append({
            "trajectory_id": f"{entry['source']}|{spec['experiment_id']}",
            "pair_id": key[0], "history_member": key[1],
            "schedule_id": entry["schedule"], "intervals": interval_rows,
        })
    contexts = {(row["pair_id"], row["history_member"]) for row in output}
    if len(output) != 432 or len(contexts) != 16 or sum(len(x["intervals"]) for x in output) != 1728:
        raise ValueError("independent R8R23 bank coverage changed")
    return sorted(output, key=lambda row: row["trajectory_id"])


def _serial(model: Mapping[str, Any]) -> dict[str, Any]:
    return {"intervals": [{"interval": int(group["interval"]), "offsets": [
        {"sample_offset": int(item["sample_offset"]),
         "training_row_count": int(item["training_row_count"]),
         "intercept": np.asarray(item["intercept"]).tolist(),
         "coefficients": np.asarray(item["coefficients"]).tolist()}
        for item in group["offsets"]]} for group in model["intervals"]]}


def _fit(bank: Sequence[Mapping[str, Any]], pairs: Sequence[str], ridge: float) -> dict[str, Any]:
    allowed = set(map(str, pairs))
    groups = []
    for interval in range(4):
        rows = [trajectory["intervals"][interval] for trajectory in bank
                if str(trajectory["pair_id"]) in allowed]
        offsets = []
        for offset in range(max(len(row["targets"]) for row in rows)):
            selected = [row for row in rows if len(row["targets"]) > offset]
            x = np.asarray([row["expanded"] for row in selected], dtype=float)
            y = np.asarray([row["targets"][offset] for row in selected], dtype=float)
            xm, ym = np.mean(x, axis=0), np.mean(y, axis=0)
            dx, dy = x - xm, y - ym
            coefficient = np.linalg.solve(
                dx.T @ dx + ridge * np.eye(x.shape[1]), dx.T @ dy
            )
            intercept = ym - xm @ coefficient
            if not np.all(np.isfinite(coefficient)) or not np.all(np.isfinite(intercept)):
                raise ValueError("independent R8R23 ridge fit invalid")
            offsets.append({"sample_offset": offset, "training_row_count": len(selected),
                            "intercept": intercept, "coefficients": coefficient})
        groups.append({"interval": interval, "offsets": offsets})
    return {"intervals": groups}


def _predict(model: Mapping[str, Any], row: Mapping[str, Any]) -> np.ndarray:
    values = []
    for item in model["intervals"][int(row["interval"])]["offsets"][:len(row["targets"])]:
        values.append(np.asarray(item["intercept"]) +
                      np.asarray(row["expanded"]) @ np.asarray(item["coefficients"]))
    result = np.asarray(values, dtype=float)
    if result.shape != np.asarray(row["targets"]).shape or not np.all(np.isfinite(result)):
        raise ValueError("independent R8R23 prediction invalid")
    return result


def _predictions(model: Mapping[str, Any], bank: Sequence[Mapping[str, Any]]) -> dict[str, list[np.ndarray]]:
    return {str(trajectory["trajectory_id"]): [_predict(model, row)
            for row in trajectory["intervals"]] for trajectory in bank}


def _tube(bank: Sequence[Mapping[str, Any]], training: Sequence[str], ridge: float) -> tuple[list[np.ndarray], list[dict[str, Any]]]:
    pairs = tuple(sorted(map(str, training)))
    bounds = [np.zeros((count, 5)) for count in (4, 4, 4, 15)]
    evidence = []
    for held in pairs:
        fit_pairs = tuple(pair for pair in pairs if pair != held)
        model = _fit(bank, fit_pairs, ridge)
        rows = [row for row in bank if str(row["pair_id"]) == held]
        predicted = _predictions(model, rows)
        for trajectory in rows:
            for interval, row in enumerate(trajectory["intervals"]):
                residual = np.abs(np.asarray(row["targets"]) -
                                  predicted[str(trajectory["trajectory_id"])][interval])
                bounds[interval][:len(residual)] = np.maximum(
                    bounds[interval][:len(residual)], residual)
        evidence.append({"held_pair": held, "training_pairs": list(fit_pairs),
                         "model_digest": _digest(_serial(model))})
    return bounds, evidence


def _support(bank: Sequence[Mapping[str, Any]], training: Sequence[str], held: str,
             multiplier: float) -> dict[str, Any]:
    thresholds, maxima, passed_counts, counts = [], [], [], []
    for interval in range(4):
        by_pair = {pair: np.asarray([row["intervals"][interval]["feature"] for row in bank
                                    if str(row["pair_id"]) == pair])
                   for pair in sorted(map(str, training))}
        nested = []
        for pair, values in by_pair.items():
            other = np.concatenate([v for name, v in by_pair.items() if name != pair])
            nested.extend(np.min(np.linalg.norm(values[:, None] - other[None, :], axis=2), axis=1))
        threshold = multiplier * max(map(float, nested), default=0.0)
        train = np.concatenate(list(by_pair.values()))
        test = np.asarray([row["intervals"][interval]["feature"] for row in bank
                           if str(row["pair_id"]) == held])
        distances = np.min(np.linalg.norm(test[:, None] - train[None, :], axis=2), axis=1)
        thresholds.append(float(threshold)); maxima.append(float(np.max(distances)))
        passed_counts.append(int(np.count_nonzero(distances <= threshold + 1e-15)))
        counts.append(len(distances))
    return {"thresholds": thresholds, "maximum_held_distances": maxima,
            "pass_counts": passed_counts, "row_counts": counts,
            "passed": sum(passed_counts) == sum(counts)}


def _adapt(rows: Sequence[Mapping[str, Any]], cold: Mapping[str, Sequence[np.ndarray]],
           tube: Sequence[np.ndarray]) -> tuple[dict[str, list[np.ndarray]], int]:
    result, clipping = {}, 0
    for trajectory in rows:
        identifier = str(trajectory["trajectory_id"])
        bias = np.zeros(5)
        values = []
        for interval, row in enumerate(trajectory["intervals"]):
            forecast = np.asarray(cold[identifier][interval]) + bias[None]
            values.append(forecast)
            residual = np.asarray(row["targets"][-1]) - forecast[-1]
            candidate = 0.5 * bias + 0.5 * residual
            bound = np.asarray(tube[interval][len(row["targets"]) - 1])
            clipping += int(np.any(np.abs(candidate) > bound + 1e-15))
            bias = np.clip(candidate, -bound, bound)
        result[identifier] = values
    return result, clipping


def _sse(rows: Sequence[Mapping[str, Any]], prediction: Mapping[str, Sequence[np.ndarray]]) -> float:
    total = 0.0
    for trajectory in rows:
        identifier = str(trajectory["trajectory_id"])
        for interval, row in enumerate(trajectory["intervals"]):
            residual = np.asarray(row["targets"]) - prediction[identifier][interval]
            total += float(np.sum(residual * residual))
    return total


def _outer(bank: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]) -> list[dict[str, Any]]:
    pairs = tuple(sorted({str(row["pair_id"]) for row in bank}))
    ridge = float(cfg["model_contract"]["ridge_penalty"])
    output = []
    for held in pairs:
        training = tuple(pair for pair in pairs if pair != held)
        model = _fit(bank, training, ridge)
        base, nested = _tube(bank, training, ridge)
        reserved = [value * float(cfg["model_contract"]["tube_reserve_multiplier"])
                    for value in base]
        rows = [row for row in bank if str(row["pair_id"]) == held]
        cold = _predictions(model, rows)
        adapted, clipping = _adapt(rows, cold, base)
        output.append({
            "held_pair": held, "training_pairs": list(training), "model": model,
            "model_digest": _digest(_serial(model)), "nested_fit_evidence": nested,
            "base_tube": base, "reserved_tube": reserved, "held": rows,
            "cold": cold, "adapted": adapted, "cold_squared_error": _sse(rows, cold),
            "adapted_squared_error": _sse(rows, adapted),
            "innovation_clipping_row_count": clipping,
            "support": _support(bank, training, held,
                                float(cfg["model_contract"]["support_threshold_multiplier"])),
        })
    return output


def _usefulness(folds: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]) -> dict[str, Any]:
    cold = sum(float(row["cold_squared_error"]) for row in folds)
    adapted = sum(float(row["adapted_squared_error"]) for row in folds)
    rows = []
    for fold in folds:
        ratio = float(fold["adapted_squared_error"]) / float(fold["cold_squared_error"])
        rows.append({"pair_id": fold["held_pair"],
                     "cold_squared_error": fold["cold_squared_error"],
                     "adapted_squared_error": fold["adapted_squared_error"],
                     "adapted_to_cold_ratio": ratio,
                     "strictly_improved": fold["adapted_squared_error"] < fold["cold_squared_error"]})
    ratio = adapted / cold
    clipping = sum(int(row["innovation_clipping_row_count"]) for row in folds)
    improved = sum(bool(row["strictly_improved"]) for row in rows)
    gate = cfg["adaptation_gates"]
    passed = bool(ratio <= float(gate["maximum_aggregate_squared_error_ratio"]) + 1e-15
                  and improved >= int(gate["minimum_strictly_improved_outer_pair_count"])
                  and all(float(row["adapted_to_cold_ratio"]) <=
                          float(gate["maximum_outer_pair_squared_error_ratio"]) + 1e-15
                          for row in rows)
                  and clipping <= int(gate["maximum_innovation_clipping_row_count"]))
    return {"cold_squared_error": cold, "adapted_squared_error": adapted,
            "adapted_to_cold_ratio": ratio, "strictly_improved_outer_pair_count": improved,
            "innovation_clipping_row_count": clipping, "rows": rows, "passed": passed}


def _evaluate(folds: Sequence[Mapping[str, Any]], adapted: bool,
              cfg: Mapping[str, Any]) -> dict[str, Any]:
    maxima, tube_max = np.zeros(5), np.zeros(5)
    contained = total = support_pass = support_total = finite = 0
    fold_rows = []
    for fold in folds:
        predictions = fold["adapted" if adapted else "cold"]
        fold_max = np.zeros(5); fold_contained = fold_total = 0
        for trajectory in fold["held"]:
            identifier = str(trajectory["trajectory_id"])
            for interval, row in enumerate(trajectory["intervals"]):
                actual = np.asarray(row["targets"]); predicted = predictions[identifier][interval]
                residual = np.abs(actual - predicted); physical = residual * FACTORS
                fold_max = np.maximum(fold_max, np.max(physical, axis=0))
                maxima = np.maximum(maxima, np.max(physical, axis=0))
                tube = np.asarray(fold["reserved_tube"][interval][:len(actual)])
                inside = residual <= tube + 1e-15
                fold_contained += int(np.count_nonzero(inside)); fold_total += inside.size
                finite += int(not np.all(np.isfinite(actual)) or not np.all(np.isfinite(predicted)))
        current_tube = np.max(np.concatenate(fold["reserved_tube"]) * FACTORS, axis=0)
        tube_max = np.maximum(tube_max, current_tube)
        contained += fold_contained; total += fold_total
        support_pass += sum(map(int, fold["support"]["pass_counts"]))
        support_total += sum(map(int, fold["support"]["row_counts"]))
        fold_rows.append({"pair_id": fold["held_pair"],
                          "maximum_absolute_physical_error": fold_max.tolist(),
                          "reserved_tube_contained_component_count": fold_contained,
                          "reserved_tube_component_count": fold_total,
                          "reserved_tube_containment_rate": fold_contained / fold_total,
                          "maximum_reserved_physical_tube_half_width": current_tube.tolist(),
                          "support": fold["support"]})
    gate = cfg["model_gates"]
    point = bool(maxima[0] <= float(gate["maximum_R_point_error_m"]) + 1e-15
                 and maxima[1] <= float(gate["maximum_Z_point_error_m"]) + 1e-15
                 and maxima[2] <= float(gate["maximum_Ip_point_error_A"]) + 1e-12
                 and maxima[3] <= float(gate["maximum_vR_point_error_m_per_s"]) + 1e-15
                 and maxima[4] <= float(gate["maximum_vZ_point_error_m_per_s"]) + 1e-15)
    tube_cap = bool(tube_max[0] <= float(gate["maximum_reserved_R_tube_half_width_m"]) + 1e-15
                    and tube_max[1] <= float(gate["maximum_reserved_Z_tube_half_width_m"]) + 1e-15
                    and tube_max[2] <= float(gate["maximum_reserved_Ip_tube_half_width_A"]) + 1e-12
                    and tube_max[3] <= float(gate["maximum_reserved_vR_tube_half_width_m_per_s"]) + 1e-15
                    and tube_max[4] <= float(gate["maximum_reserved_vZ_tube_half_width_m_per_s"]) + 1e-15)
    containment_rate, support_rate = contained / total, support_pass / support_total
    passed = bool(point and tube_cap and containment_rate >= 1.0 - 1e-15
                  and support_rate >= 1.0 - 1e-15 and finite == 0)
    return {"selected_predictor": "adapted" if adapted else "cold",
            "maximum_absolute_physical_error": maxima.tolist(),
            "maximum_reserved_physical_tube_half_width": tube_max.tolist(),
            "reserved_tube_contained_component_count": contained,
            "reserved_tube_component_count": total,
            "reserved_tube_containment_rate": containment_rate,
            "support_pass_count": support_pass, "support_row_count": support_total,
            "support_rate": support_rate, "finite_exclusion_count": finite,
            "forbidden_input_count": 0, "point_error_gate_passed": point,
            "tube_cap_gate_passed": tube_cap, "fold_rows": fold_rows, "passed": passed}


def _bank_evidence(bank: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    features, targets = [], []
    for trajectory in bank:
        for row in trajectory["intervals"]:
            features.append({"row_id": row["row_id"],
                             "feature": np.asarray(row["feature"]).tolist(),
                             "q": np.asarray(row["q"]).tolist(),
                             "previous_q": np.asarray(row["previous_q"]).tolist(),
                             "expanded": np.asarray(row["expanded"]).tolist()})
            targets.append({"row_id": row["row_id"],
                            "targets": np.asarray(row["targets"]).tolist()})
    return {"trajectory_count": len(bank), "origin_row_count": len(features),
            "forecast_point_count": sum(len(row["targets"]) for trajectory in bank
                                        for row in trajectory["intervals"]),
            "feature_digest": _digest(features), "target_digest": _digest(targets),
            "feature_dimension": 42, "expanded_feature_dimension": 133,
            "forbidden_input_count": 0, "allowed_in_expert_dataset": False}


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
    authentication = _authenticate(args, cfg)
    stage = args.run_dir.expanduser().resolve() / RUN_NAME
    primary_path = stage / "analysis/primary_detailed.json"
    summary_path = stage / "analysis/primary_summary.json"
    model_path = stage / "model/outer_fold_models.json"
    primary, summary, primary_models = _read(primary_path), _read(summary_path), _read(model_path)
    bank = _build_bank(args, cfg)
    bank_evidence = _bank_evidence(bank)
    folds = _outer(bank, cfg)
    usefulness = _usefulness(folds, cfg)
    adaptation_enabled = bool(usefulness["passed"])
    evaluation = _evaluate(folds, adaptation_enabled, cfg)
    if evaluation["passed"]:
        # A passing model requires an independently implemented full action
        # tree.  Fail closed rather than borrowing primary plans.
        raise ValueError("independent R8R23 safe action-tree implementation required")
    planning = {
        "safe_complete_plan_count": 0,
        "predicted_repaired_failed_baseline_count": 0,
        "predicted_regressed_baseline_pass_count": 0,
        "predicted_baseline_plus_policy_oracle_count": 6,
        "plans": [],
        "skipped_reason": "frozen_model_tube_or_support_gate_failed",
        "passed": False,
    }
    route = str(cfg["routes"]["model_fail"])
    independent_models = {
        "schema_version": 1,
        "stage": STAGE,
        "feature_digest": bank_evidence["feature_digest"],
        "target_digest": bank_evidence["target_digest"],
        "folds": [{"held_pair": fold["held_pair"], "model": _serial(fold["model"]),
                   "nested_fit_evidence": fold["nested_fit_evidence"]} for fold in folds],
    }
    tolerance = float(cfg["planning_gate"]["primary_independent_absolute_tolerance"])
    fit_difference = _maximum_difference(primary_models, independent_models)
    primary_tubes = [{"held_pair": fold["held_pair"], "base_tube": fold["base_tube"],
                      "reserved_tube": fold["reserved_tube"]} for fold in primary["folds"]]
    independent_tubes = [{"held_pair": fold["held_pair"],
                          "base_tube": [value.tolist() for value in fold["base_tube"]],
                          "reserved_tube": [value.tolist() for value in fold["reserved_tube"]]}
                         for fold in folds]
    tube_difference = _maximum_difference(primary_tubes, independent_tubes)
    feature_agreement = bool(primary["bank_evidence"]["feature_digest"] ==
                             bank_evidence["feature_digest"] and
                             primary["bank_evidence"]["target_digest"] ==
                             bank_evidence["target_digest"])
    fit_agreement = bool(fit_difference <= tolerance)
    tube_agreement = bool(tube_difference <= tolerance and
                          _maximum_difference(primary["model_evaluation"], evaluation) <= tolerance)
    plan_agreement = bool(_maximum_difference(primary["planning_evaluation"], planning) <= tolerance)
    route_agreement = bool(primary.get("route") == route and summary.get("route") == route)
    outcome_agreement = bool(primary.get("adaptation_enabled") is adaptation_enabled and
                             primary.get("model_gate_passed") is False and
                             summary.get("model_gate_passed") is False)
    result = {
        "schema_version": 1,
        "stage": STAGE,
        "audit_kind": "causal_online_innovation_receding_horizon_preflight_independent",
        "source_authentication": authentication,
        "bank_evidence": bank_evidence,
        "adaptation_usefulness": usefulness,
        "adaptation_enabled": adaptation_enabled,
        "model_evaluation": evaluation,
        "planning_evaluation": planning,
        "route": route,
        "maximum_fit_absolute_difference": fit_difference,
        "maximum_tube_absolute_difference": tube_difference,
        "primary_feature_agreement": feature_agreement,
        "primary_fit_agreement": fit_agreement,
        "primary_tube_agreement": tube_agreement,
        "primary_plan_agreement": plan_agreement,
        "primary_route_agreement": route_agreement,
        "primary_outcome_agreement": outcome_agreement,
        "primary_detailed_sha256": _sha(primary_path),
        "primary_summary_sha256": _sha(summary_path),
        "primary_model_evidence_sha256": _sha(model_path),
        "real_tsc_executed": False,
        "plant_step_count": 0,
        "new_raw_count": 0,
    }
    result["passed"] = bool(feature_agreement and fit_agreement and tube_agreement
                            and plan_agreement and route_agreement and outcome_agreement)
    if not result["passed"]:
        raise ValueError("independent R8R23 audit disagrees with primary")
    _write(stage / "analysis/independent.json", result)
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    for name in (
        "r8r22-run", "r8r7-run", "r8r12-run", "r8r14-run", "r8r15-run",
        "r8r19-run", "r8r20-run", "r8-run", "r8r1-output", "r8r6-run",
        "source-d1r11-run", "source-r2-run", "source-r4-run", "source-r6-run",
        "source-s21-run", "source-s23r1-output", "source-s24-run",
        "source-d1r9-v1", "source-d1r9-v2", "source-d1r10-run",
        "source-d1r10-audit", "source-stage42r3b-run",
        "source-stage42r3c3-run", "source-stage42r3c3-bank-dir",
        "source-stage42r3c3t1-run", "source-stage42r3c3t1-audit-dir",
        "source-stage42r3c3t3-controller-bank", "q1-run", "q2-run",
        "q1-audit", "q2-audit", "r3b-server-audit", "r3b-snapshot-checks",
    ):
        parser.add_argument(f"--{name}", type=Path, required=True)
    return parser


def main() -> None:
    args = _parser().parse_args()
    cfg = _read(args.config.expanduser().resolve())
    result = audit(args, cfg)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
