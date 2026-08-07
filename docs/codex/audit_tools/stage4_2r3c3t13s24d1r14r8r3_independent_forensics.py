#!/usr/bin/env python3
"""Structurally independent R8R3 causal observer recomputation."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r7_independent_forensics as frozen,
    stage4_2r3c3t13s24d1r14r8_independent_forensics as r8_independent,
    stage4_2r3c3t13s24d1r14r8r1_independent_forensics as r8r1_independent,
    stage4_2r3c3t13s24d1r14r8r2_independent_forensics as r8r2_independent,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r3_causal_history_no_action_observer as contract,
)


def _json(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
    )


def _write(path: Path, value: Any) -> None:
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


def _check(path: Path, size: int, sha: str) -> None:
    if not path.is_file() or path.stat().st_size != size or _sha(path) != sha:
        raise ValueError("R8R3 independent source artifact changed")


def _r8r2_source(output: Path, cfg: Mapping[str, Any]) -> dict[str, Any]:
    source = cfg["source_r8r2_contract"]
    paths = {
        "primary_detailed": output / "primary_detailed.json",
        "primary_summary": output / "primary_summary.json",
        "independent": output / "independent.json",
        "stage_state": output / "stage_state.json",
    }
    for key, path in paths.items():
        _check(path, int(source[f"{key}_bytes"]), str(source[f"{key}_sha256"]))
    primary = _json(paths["primary_detailed"])
    independent = _json(paths["independent"])
    state = _json(paths["stage_state"])
    route = str(source["required_route"])
    if (
        primary.get("route") != route
        or primary.get("scientific_gate_passed") is not False
        or independent.get("route") != route
        or independent.get("scientific_gate_passed") is not False
        or independent.get("primary_numerical_agreement") is not True
        or independent.get("primary_outcome_agreement") is not True
        or state.get("route") != route
        or state.get("finished") is not True
        or state.get("independent_completed") is not True
        or int(state.get("new_raw_count", -1)) != 0
        or bool(state.get("heldout_outcomes_opened"))
        or str(state.get("development_artifact_sha256") or "")
    ):
        raise ValueError("R8R3 independent R8R2 outcome changed")
    return {key + "_sha256": _sha(path) for key, path in paths.items()}


def _actions(result: Mapping[str, Any]) -> np.ndarray:
    value = np.asarray(
        [row.get("action_norm_tsc", []) for row in result.get("controller_trace") or []],
        dtype=float,
    )
    if value.ndim != 2 or value.shape[1] != 14 or not np.all(np.isfinite(value)):
        raise ValueError("R8R3 independent action history invalid")
    return value


def _currents(result: Mapping[str, Any]) -> np.ndarray:
    value = np.asarray(
        [row.get("currents_a_tsc", []) for row in result.get("trajectory") or []],
        dtype=float,
    )
    if value.ndim != 2 or value.shape[1] != 14 or not np.all(np.isfinite(value)):
        raise ValueError("R8R3 independent current history invalid")
    return value


def _target(spec: Mapping[str, Any]) -> np.ndarray:
    return np.asarray(
        [
            spec["target_R_offset_m"],
            spec["target_Z_offset_m"],
            spec["target_Ip_offset_A"],
        ],
        dtype=float,
    )


def _feature(
    visible: np.ndarray,
    actions: np.ndarray,
    currents: np.ndarray,
    target: np.ndarray,
    origin: int,
    cfg: Mapping[str, Any],
) -> np.ndarray:
    state_index = origin + np.arange(-10, 1)
    action_index = origin + np.arange(-10, 0)
    current_index = origin + np.arange(-10, 1)
    value = np.r_[
        visible[state_index].reshape(-1),
        actions[action_index].reshape(-1),
        currents[current_index].reshape(-1),
        target / np.asarray(cfg["bank_contract"]["target_scales"], dtype=float),
        (origin - 10.0) / 15.0,
    ]
    if value.shape != (353,) or not np.all(np.isfinite(value)):
        raise ValueError("R8R3 independent causal feature invalid")
    return value


def _source_rows(
    cfg: Mapping[str, Any],
    r8r2_cfg: Mapping[str, Any],
    r8_cfg: Mapping[str, Any],
    paths: Mapping[str, Path],
    args: argparse.Namespace,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    records, windows, r8r2_signature = r8r2_independent._source_records(
        r8r2_cfg, r8_cfg, paths, args
    )
    sources = {
        "r2": frozen._read_source(
            args.source_r2_run.resolve(), r8_cfg["source_response_contracts"]["r2"]
        ),
        "r4": frozen._read_source(
            args.source_r4_run.resolve(), r8_cfg["source_response_contracts"]["r4"]
        ),
        "r6": frozen._read_source(
            args.source_r6_run.resolve(), r8_cfg["source_response_contracts"]["r6"]
        ),
    }
    indexes = {
        "r2": frozen._index(sources["r2"], "d1r14r2", 10),
        "r4": frozen._index(sources["r4"], "d1r14r4", -1),
    }
    existing_by_id = {}
    for source in sources.values():
        specs = {str(row["experiment_id"]): row for row in source["specs"]}
        existing_by_id.update(
            {
                experiment_id: (specs[experiment_id], result)
                for experiment_id, result in source["results"].items()
            }
        )
    specs = r8_independent._specs(paths, "training")
    results = {
        str(spec["experiment_id"]): r8_independent._gzip(
            paths["raw_training"] / f"{spec['experiment_id']}.json.gz"
        )
        for spec in specs
    }
    new_by_id = {
        str(spec["experiment_id"]): (spec, results[str(spec["experiment_id"])])
        for spec in specs
    }
    new_baselines = {}
    for spec in specs:
        if str(spec["d1r14r8_role"]) == "baseline":
            context = f"{spec['pair_id']}|{spec['history_member']}"
            new_baselines[context] = (spec, results[str(spec["experiment_id"])])
    r2_baselines = {
        context: members[("baseline", -1, -1, 0)]
        for context, members in indexes["r2"].items()
    }
    r4_baselines = {
        context: members[("baseline", -1, -1, 0)]
        for context, members in indexes["r4"].items()
    }
    meta = {
        str(row["context_id"]): (str(row["pair_id"]), str(row["history_member"]))
        for row in records
    }
    r8r2_windows = {
        (str(row["context_id"]), int(row["issue_task_step"])): np.asarray(
            row["baseline_visible"], dtype=float
        )
        for row in windows
    }
    scales = np.asarray(cfg["bank_contract"]["visible_scales"], dtype=float)
    issues = set(map(int, cfg["bank_contract"]["prescribed_issue_task_steps"]))
    rows = []
    selected_results = {}
    exact = 0
    for context in sorted(meta):
        pair, history = meta[context]
        if context in new_baselines:
            at_ten = later = new_baselines[context]
        else:
            at_ten, later = r2_baselines[context], r4_baselines[context]
        later_visible = frozen._visible(later[1]["trajectory"], scales)
        maximum = len(later_visible) - 13
        for origin in range(10, maximum + 1):
            spec, result = at_ten if origin == 10 else later
            visible = frozen._visible(result["trajectory"], scales)
            action = _actions(result)
            current = _currents(result)
            feature = _feature(
                visible[: origin + 1],
                action[:origin],
                current[: origin + 1],
                _target(spec),
                origin,
                cfg,
            )
            future = visible[origin + 1 : origin + 13]
            delta = future[:, 2:5] - visible[origin, 2:5]
            if origin in issues:
                if not np.array_equal(visible, r8r2_windows[(context, origin)]):
                    raise ValueError("R8R3 independent prescribed baseline changed")
                exact += 1
            selected_results[str(result["experiment_id"])] = result
            rows.append(
                {
                    "row_id": f"{context}|origin{origin:02d}",
                    "context_id": context,
                    "pair_id": pair,
                    "history_member": history,
                    "origin_task_step": origin,
                    "prescribed_issue": origin in issues,
                    "feature": feature,
                    "origin_visible": visible[origin],
                    "target_delta": delta,
                    "future_visible": future,
                }
            )
    zero = constant = 0
    for result in selected_results.values():
        action, current = _actions(result), _currents(result)
        zero += int(np.array_equal(action[10:], np.zeros_like(action[10:])))
        difference = np.diff(current[10:], axis=0)
        constant += int(np.array_equal(difference, np.zeros_like(difference)))
    row_index = {
        (str(row["context_id"]), int(row["origin_task_step"])): row for row in rows
    }
    probe_equal = 0
    for record in records:
        experiment_id = str(record["response_id"])
        spec, result = (
            new_by_id[experiment_id]
            if str(record["source_stage"]) == "R8"
            else existing_by_id[experiment_id]
        )
        issue = int(record["issue_task_step"])
        visible = frozen._visible(result["trajectory"][: issue + 1], scales)
        feature = _feature(
            visible,
            _actions(result)[:issue],
            _currents(result)[: issue + 1],
            _target(spec),
            issue,
            cfg,
        )
        baseline = row_index[(str(record["context_id"]), issue)]["feature"]
        probe_equal += int(np.array_equal(feature, baseline))
    signature = {
        "pair_count": len({row["pair_id"] for row in rows}),
        "context_count": len({row["context_id"] for row in rows}),
        "origin_row_count": len(rows),
        "prescribed_issue_row_count": sum(row["prescribed_issue"] for row in rows),
        "prescribed_baseline_exact_count": exact,
        "selected_baseline_raw_count": len(selected_results),
        "zero_future_action_baseline_count": zero,
        "constant_future_current_baseline_count": constant,
        "probe_feature_count": len(records),
        "probe_feature_equal_count": probe_equal,
        "feature_dimension": len(rows[0]["feature"]),
        "forbidden_predictor_input_count": 0,
        "matched_baseline_future_predictor_input_count": 0,
        "future_probe_state_predictor_input_count": 0,
        "r8r2_record_signature": r8r2_signature,
    }
    expected = cfg["bank_contract"]
    if (
        signature["pair_count"] != int(expected["pair_count"])
        or signature["context_count"] != int(expected["context_count"])
        or signature["origin_row_count"] != int(expected["origin_row_count"])
        or signature["prescribed_issue_row_count"]
        != int(expected["prescribed_issue_row_count"])
        or exact != 96
        or len(selected_results) != 32
        or zero != 32
        or constant != 32
        or probe_equal != int(expected["probe_feature_count"])
    ):
        raise ValueError("R8R3 independent row coverage changed")
    return sorted(rows, key=lambda row: row["row_id"]), signature


def _candidates(cfg: Mapping[str, Any]) -> list[tuple[str, int, float, float]]:
    model = cfg["model_contract"]
    output = []
    for rank in map(int, model["pca_ranks"]):
        output.extend(("linear", rank, 0.0, ridge) for ridge in map(float, model["kernel_ridges"]))
        output.extend(
            ("rbf", rank, multiplier, ridge)
            for multiplier in map(float, model["rbf_median_distance_multipliers"])
            for ridge in map(float, model["kernel_ridges"])
        )
    if len(output) != 48:
        raise ValueError("R8R3 independent candidate count changed")
    return output


def _candidate_dict(candidate: tuple[str, int, float, float]) -> dict[str, Any]:
    return {
        "family": candidate[0],
        "pca_rank": candidate[1],
        "bandwidth_multiplier": candidate[2],
        "ridge": candidate[3],
    }


def _key(candidate: tuple[str, int, float, float]) -> str:
    return f"{candidate[0]}:r{candidate[1]}:b{candidate[2]:.17g}:k{candidate[3]:.17g}"


def _pre(items: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]) -> dict[str, np.ndarray]:
    values = np.asarray([row["feature"] for row in items], dtype=float)
    mean = values.mean(axis=0)
    scale = np.maximum(
        values.std(axis=0), float(cfg["model_contract"]["standard_deviation_floor"])
    )
    _, _, components = np.linalg.svd((values - mean) / scale, full_matrices=False)
    components = components.copy()
    for row in components:
        index = int(np.argmax(np.abs(row)))
        if row[index] < 0.0:
            row *= -1.0
    return {"mean": mean, "scale": scale, "components": components}


def _project(pre: Mapping[str, np.ndarray], items: Sequence[Mapping[str, Any]], rank: int) -> np.ndarray:
    values = np.asarray([row["feature"] for row in items], dtype=float)
    return ((values - pre["mean"]) / pre["scale"]) @ pre["components"][:rank].T


def _targets(items: Sequence[Mapping[str, Any]]) -> np.ndarray:
    return np.asarray([row["target_delta"] for row in items], dtype=float).reshape(len(items), 36)


def _median(values: np.ndarray, floor: float) -> float:
    difference = values[:, None] - values[None, :]
    distance = np.sqrt(np.sum(difference * difference, axis=2))
    upper = distance[np.triu_indices(len(values), 1)]
    positive = upper[upper > floor]
    return max(float(np.median(positive)) if len(positive) else floor, floor)


def _rbf(left: np.ndarray, right: np.ndarray, bandwidth: float) -> np.ndarray:
    difference = left[:, None] - right[None, :]
    return np.exp(-0.5 * np.sum(difference * difference, axis=2) / bandwidth**2)


def _forecast(item: Mapping[str, Any], flat: np.ndarray, cfg: Mapping[str, Any]) -> np.ndarray:
    delta = np.asarray(flat, dtype=float).reshape(12, 3)
    origin = np.asarray(item["origin_visible"], dtype=float)
    output = np.zeros((12, 5), dtype=float)
    output[:, 2:5] = origin[2:5] + delta
    scales = np.asarray(cfg["bank_contract"]["visible_scales"], dtype=float)
    dt = float(cfg["bank_contract"]["dt_s"])
    output[:, 0] = origin[0] + np.cumsum(output[:, 2]) * dt * scales[2] / scales[0]
    output[:, 1] = origin[1] + np.cumsum(output[:, 3]) * dt * scales[3] / scales[1]
    return output


def _all_predictions(
    training: Sequence[Mapping[str, Any]], held: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]
) -> dict[str, list[np.ndarray]]:
    pre = _pre(training, cfg)
    target = _targets(training)
    mean = target.mean(axis=0)
    centered = target - mean
    output = {}
    floor = float(cfg["model_contract"]["bandwidth_floor"])
    ridges = tuple(map(float, cfg["model_contract"]["kernel_ridges"]))
    for rank in map(int, cfg["model_contract"]["pca_ranks"]):
        x = _project(pre, training, rank)
        held_x = _project(pre, held, rank)
        left, right = x.T @ x / rank, x.T @ centered / rank
        for ridge in ridges:
            beta = np.linalg.lstsq(left + ridge * np.eye(rank), right, rcond=None)[0]
            predicted = mean + held_x @ beta
            candidate = ("linear", rank, 0.0, ridge)
            output[_key(candidate)] = [
                _forecast(item, value, cfg) for item, value in zip(held, predicted)
            ]
        median = _median(x, floor)
        for multiplier in map(float, cfg["model_contract"]["rbf_median_distance_multipliers"]):
            bandwidth = max(multiplier * median, floor)
            gram = _rbf(x, x, bandwidth)
            eigenvalues, eigenvectors = np.linalg.eigh(0.5 * (gram + gram.T))
            projected = eigenvectors.T @ centered
            held_kernel = _rbf(held_x, x, bandwidth)
            for ridge in ridges:
                alpha = eigenvectors @ (projected / (eigenvalues + ridge)[:, None])
                predicted = mean + held_kernel @ alpha
                candidate = ("rbf", rank, multiplier, ridge)
                output[_key(candidate)] = [
                    _forecast(item, value, cfg) for item, value in zip(held, predicted)
                ]
    return output


def _fit(
    items: Sequence[Mapping[str, Any]], candidate: tuple[str, int, float, float], cfg: Mapping[str, Any]
) -> dict[str, Any]:
    family, rank, multiplier, ridge = candidate
    pre = _pre(items, cfg)
    x = _project(pre, items, rank)
    target = _targets(items)
    mean = target.mean(axis=0)
    centered = target - mean
    model = {"candidate": candidate, "pre": pre, "x": x, "mean": mean}
    if family == "linear":
        model["weights"] = np.linalg.lstsq(
            x.T @ x / rank + ridge * np.eye(rank), x.T @ centered / rank, rcond=None
        )[0]
    else:
        bandwidth = max(
            multiplier * _median(x, float(cfg["model_contract"]["bandwidth_floor"])),
            float(cfg["model_contract"]["bandwidth_floor"]),
        )
        gram = _rbf(x, x, bandwidth)
        eigenvalues, eigenvectors = np.linalg.eigh(0.5 * (gram + gram.T))
        model["weights"] = eigenvectors @ (
            (eigenvectors.T @ centered) / (eigenvalues + ridge)[:, None]
        )
        model["bandwidth"] = bandwidth
    return model


def _predict(model: Mapping[str, Any], items: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]) -> list[np.ndarray]:
    family, rank, _, _ = model["candidate"]
    x = _project(model["pre"], items, rank)
    if family == "linear":
        values = model["mean"] + x @ model["weights"]
    else:
        values = model["mean"] + _rbf(x, model["x"], model["bandwidth"]) @ model["weights"]
    return [_forecast(item, value, cfg) for item, value in zip(items, values)]


def _metric(item: Mapping[str, Any], prediction: np.ndarray, cfg: Mapping[str, Any]) -> dict[str, Any]:
    target = np.asarray(item["future_visible"], dtype=float)
    scales = np.asarray(cfg["bank_contract"]["visible_scales"], dtype=float)
    caps = np.asarray(cfg["gates"]["component_caps_physical"], dtype=float)
    residual = prediction - target
    absolute = np.abs(residual * scales)
    violation = absolute > caps[None, :] + 1e-15
    return {
        "row_id": str(item["row_id"]),
        "pair_id": str(item["pair_id"]),
        "history_member": str(item["history_member"]),
        "origin_task_step": int(item["origin_task_step"]),
        "prescribed_issue": bool(item["prescribed_issue"]),
        "predicted_visible": prediction.tolist(),
        "target_visible": target.tolist(),
        "absolute_residual_physical": absolute.tolist(),
        "component_future_violation_count": int(np.sum(violation)),
        "component_violation_counts": np.sum(violation, axis=0).astype(int).tolist(),
        "maximum_absolute_scaled_point_error": float(np.max(np.abs(residual))),
        "mean_squared_scaled_error": float(np.mean(residual * residual)),
        "passed": bool(not np.any(violation) and np.all(np.isfinite(prediction))),
    }


def _score(rows: Sequence[Mapping[str, Any]], candidate: tuple[str, int, float, float]) -> tuple[Any, ...]:
    maxima = np.asarray([row["maximum_absolute_scaled_point_error"] for row in rows])
    return (
        sum(not row["passed"] for row in rows),
        sum(row["component_future_violation_count"] for row in rows),
        float(np.max(maxima)),
        float(np.quantile(maxima, 0.95, method="linear")),
        float(np.mean([row["mean_squared_scaled_error"] for row in rows])),
        0 if candidate[0] == "linear" else 1,
        candidate[1],
        candidate[2],
        candidate[3],
    )


def _select(
    items: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]
) -> tuple[tuple[str, int, float, float], list[dict[str, Any]], list[dict[str, Any]]]:
    stored = {_key(candidate): [] for candidate in _candidates(cfg)}
    for pair in sorted({str(row["pair_id"]) for row in items}):
        training = [row for row in items if str(row["pair_id"]) != pair]
        held = [row for row in items if str(row["pair_id"]) == pair]
        predicted = _all_predictions(training, held, cfg)
        for candidate in _candidates(cfg):
            stored[_key(candidate)].extend(
                _metric(item, value, cfg)
                for item, value in zip(held, predicted[_key(candidate)])
            )
    scored = []
    for candidate in _candidates(cfg):
        rows = sorted(stored[_key(candidate)], key=lambda row: row["row_id"])
        scored.append((candidate, _score(rows, candidate), rows))
    selected, _, rows = min(scored, key=lambda value: value[1])
    report = [
        {"candidate": _candidate_dict(candidate), "selection_score": list(score[:5])}
        for candidate, score, _ in scored
    ]
    return selected, report, rows


def _tube(rows: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]) -> np.ndarray:
    residual = np.asarray([row["absolute_residual_physical"] for row in rows])
    floor = np.asarray(cfg["tube_contract"]["component_floor_physical"], dtype=float)
    return 1.25 * np.max(residual, axis=0) + floor[None, :]


def _outer(items: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]):
    rows, folds = [], []
    caps = np.asarray(cfg["gates"]["component_caps_physical"], dtype=float)
    pairs = sorted({str(row["pair_id"]) for row in items})
    for pair in pairs:
        training = [row for row in items if str(row["pair_id"]) != pair]
        held = [row for row in items if str(row["pair_id"]) == pair]
        selected, scores, inner = _select(training, cfg)
        tube = _tube(inner, cfg)
        tube_cap = bool(np.all(tube <= caps[None, :] + 1e-15))
        model = _fit(training, selected, cfg)
        held_rows = [
            _metric(item, value, cfg) for item, value in zip(held, _predict(model, held, cfg))
        ]
        contained = 0
        for row in held_rows:
            row["tube_contained"] = bool(
                np.all(np.asarray(row["absolute_residual_physical"]) <= tube + 1e-15)
            )
            contained += int(row["tube_contained"])
        rows.extend(held_rows)
        folds.append(
            {
                "held_pair_id": pair,
                "training_pair_count": 11,
                "training_origin_row_count": len(training),
                "held_origin_row_count": len(held),
                "selected_candidate": _candidate_dict(selected),
                "inner_candidate_scores": scores,
                "tube_physical": tube.tolist(),
                "tube_cap_passed": tube_cap,
                "held_tube_contained_count": contained,
                "passed": bool(
                    tube_cap
                    and contained == len(held_rows)
                    and all(row["passed"] for row in held_rows)
                ),
            }
        )
    return sorted(rows, key=lambda row: row["row_id"]), folds


def _evaluate(rows: Sequence[Mapping[str, Any]], folds: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]) -> dict[str, Any]:
    issues = [row for row in rows if row["prescribed_issue"]]
    result = {
        "outer_fold_count": len(folds),
        "origin_row_count": len(rows),
        "origin_pass_count": sum(row["passed"] for row in rows),
        "prescribed_issue_row_count": len(issues),
        "prescribed_issue_pass_count": sum(row["passed"] for row in issues),
        "tube_cap_fold_count": sum(fold["tube_cap_passed"] for fold in folds),
        "tube_contained_origin_count": sum(row["tube_contained"] for row in rows),
        "component_violation_counts": np.sum(
            np.asarray([row["component_violation_counts"] for row in rows]), axis=0
        ).astype(int).tolist(),
        "maximum_absolute_scaled_point_error": max(
            row["maximum_absolute_scaled_point_error"] for row in rows
        ),
        "maximum_absolute_physical_error": np.max(
            np.asarray([row["absolute_residual_physical"] for row in rows]), axis=(0, 1)
        ).tolist(),
        "pair_pass_counts": {
            pair: {
                "passed": sum(row["passed"] for row in rows if row["pair_id"] == pair),
                "total": sum(row["pair_id"] == pair for row in rows),
            }
            for pair in sorted({row["pair_id"] for row in rows})
        },
        "history_pass_counts": {
            history: {
                "passed": sum(row["passed"] for row in rows if row["history_member"] == history),
                "total": sum(row["history_member"] == history for row in rows),
            }
            for history in sorted({row["history_member"] for row in rows})
        },
    }
    gates = cfg["gates"]
    result["passed"] = bool(
        result["outer_fold_count"] == gates["required_outer_fold_count"]
        and result["origin_row_count"] == gates["required_outer_origin_row_count"]
        and result["origin_pass_count"] == gates["required_origin_pass_count"]
        and result["prescribed_issue_row_count"] == gates["required_prescribed_issue_row_count"]
        and result["prescribed_issue_pass_count"] == gates["required_prescribed_issue_pass_count"]
        and result["tube_cap_fold_count"] == gates["required_tube_cap_fold_count"]
        and result["tube_contained_origin_count"] == gates["required_tube_contained_origin_count"]
        and all(fold["passed"] for fold in folds)
    )
    return result


def _agrees(left: Any, right: Any, cfg: Mapping[str, Any]) -> bool:
    if (
        isinstance(left, (int, float))
        and not isinstance(left, bool)
        and isinstance(right, (int, float))
        and not isinstance(right, bool)
    ):
        return bool(
            np.isclose(
                float(left),
                float(right),
                rtol=float(cfg["gates"]["independent_relative_tolerance"]),
                atol=float(cfg["gates"]["independent_absolute_tolerance"]),
            )
        )
    if isinstance(left, Mapping) and isinstance(right, Mapping):
        return set(left) == set(right) and all(_agrees(left[key], right[key], cfg) for key in left)
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(_agrees(a, b, cfg) for a, b in zip(left, right))
    return type(left) is type(right) and left == right


def run(args: argparse.Namespace) -> dict[str, Any]:
    cfg = _json(args.config.resolve())
    contract.validate_config(cfg)
    output = args.output_dir.resolve()
    primary = _json(output / "primary_detailed.json")
    summary = _json(output / "primary_summary.json")
    state_path = output / "stage_state.json"
    state = _json(state_path)
    if state.get("primary_completed") is not True or state.get("independent_completed") is not False:
        raise ValueError("R8R3 independent state boundary changed")
    root = Path(__file__).resolve().parents[3]
    design = (root / str(cfg["design_document"])).resolve()
    source_r8r2_config = (root / str(cfg["source_r8r2_config"])).resolve()
    if _sha(design) != cfg["design_document_sha256"] or _sha(source_r8r2_config) != cfg["source_r8r2_config_sha256"]:
        raise ValueError("R8R3 independent design or source config changed")
    r8r2_source = _r8r2_source(args.r8r2_output.resolve(), cfg)
    r8r2_cfg = _json(source_r8r2_config)
    r8r1_config = (root / str(r8r2_cfg["source_r8r1_config"])).resolve()
    r8r1_cfg = _json(r8r1_config)
    authenticated_items, r8_cfg = r8r1_independent._authenticate(args, r8r1_cfg)
    if len(authenticated_items) != 912:
        raise ValueError("R8R3 independent R8 authentication changed")
    paths = r8_independent._paths(args.r8_run.resolve())
    rows, signature = _source_rows(cfg, r8r2_cfg, r8_cfg, paths, args)
    outer_rows, folds = _outer(rows, cfg)
    evaluation = _evaluate(outer_rows, folds, cfg)
    scientific = bool(evaluation["passed"])
    route = str(cfg["routes"]["pass" if scientific else "fail"])
    numerical = bool(
        _agrees(primary["record_signature"], signature, cfg)
        and _agrees(primary["outer_evaluation"], evaluation, cfg)
        and _agrees(primary["outer_rows"], outer_rows, cfg)
        and _agrees(primary["outer_folds"], folds, cfg)
    )
    outcome = bool(
        primary.get("route") == route
        and summary.get("route") == route
        and bool(primary.get("scientific_gate_passed")) is scientific
        and bool(summary.get("scientific_gate_passed")) is scientific
    )
    artifact = output / "observer_model.json"
    artifact_presence = bool(artifact.is_file() is scientific)
    artifact_hash = _sha(artifact) if artifact.is_file() else ""
    artifact_contract = bool(artifact_hash == str(primary.get("development_artifact_sha256") or ""))
    result = {
        "schema_version": 1,
        "stage": contract.STAGE,
        "audit_kind": "independent",
        "source_r8r2_authentication": r8r2_source,
        "record_signature": signature,
        "outer_evaluation": evaluation,
        "outer_fold_selections": [
            {
                "held_pair_id": fold["held_pair_id"],
                "selected_candidate": fold["selected_candidate"],
                "tube_cap_passed": fold["tube_cap_passed"],
                "held_tube_contained_count": fold["held_tube_contained_count"],
                "held_origin_row_count": fold["held_origin_row_count"],
                "passed": fold["passed"],
            }
            for fold in folds
        ],
        "route": route,
        "scientific_gate_passed": scientific,
        "primary_numerical_agreement": numerical,
        "primary_outcome_agreement": outcome,
        "development_artifact_presence_agreement": artifact_presence,
        "development_artifact_hash_agreement": artifact_contract,
        "new_raw_count": 0,
        "ray_executed": False,
        "gotsc_executed": False,
        "tsc_executed": False,
        "controller_executed": False,
        "plant_advance_count": 0,
        "heldout_outcomes_opened": False,
        "passed": bool(numerical and outcome and artifact_presence and artifact_contract),
    }
    if not result["passed"]:
        raise ValueError("R8R3 independent recomputation disagrees with primary")
    independent_path = output / "independent.json"
    _write(independent_path, result)
    state.update(
        {
            "independent_completed": True,
            "independent_passed": True,
            "independent_sha256": _sha(independent_path),
        }
    )
    _write(state_path, state)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--r8r2-output", type=Path, required=True)
    parser.add_argument("--r8-run", type=Path, required=True)
    parser.add_argument("--source-r2-run", type=Path, required=True)
    parser.add_argument("--source-r4-run", type=Path, required=True)
    parser.add_argument("--source-r6-run", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser


if __name__ == "__main__":
    run(_parser().parse_args())
