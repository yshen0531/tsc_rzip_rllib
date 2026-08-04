#!/usr/bin/env python3
"""Independent strict-source and numerical replay for D1R14R7."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np


STAGE = "Stage4.2R3c3T13S24D1R14R7"
IDENTITY = "causal_deconfounded_response_model_development_v1"


def _pairs_guard(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    output = {}
    for key, value in pairs:
        if key in output:
            raise ValueError(f"duplicate JSON key: {key}")
        output[key] = value
    return output


def _constant_guard(value: str) -> None:
    raise ValueError(f"nonstandard JSON constant: {value}")


def _loads(text: str) -> Any:
    return json.loads(text, object_pairs_hook=_pairs_guard, parse_constant=_constant_guard)


def _json(path: Path) -> Any:
    return _loads(path.read_text(encoding="utf-8", errors="strict"))


def _gzip(path: Path) -> dict[str, Any]:
    with gzip.open(path, "rt", encoding="utf-8", errors="strict") as handle:
        value = _loads(handle.read())
    if not isinstance(value, dict):
        raise ValueError("R7 independent raw root changed")
    return value


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def _agrees(left: Any, right: Any) -> bool:
    """Exact structural agreement with a tight independent-numerics tolerance."""

    if isinstance(left, bool) or isinstance(right, bool):
        return type(left) is type(right) and left == right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return math.isclose(float(left), float(right), rel_tol=1e-10, abs_tol=1e-12)
    if isinstance(left, Mapping) and isinstance(right, Mapping):
        return set(left) == set(right) and all(_agrees(left[key], right[key]) for key in left)
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(_agrees(a, b) for a, b in zip(left, right))
    return type(left) is type(right) and left == right


def _write(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def _validate_frozen_contract(cfg: Mapping[str, Any]) -> None:
    bank = cfg["bank_contract"]
    model = cfg["model_contract"]
    gates = cfg["gates"]
    execution = cfg["execution_contract"]
    invalid = (
        cfg.get("stage") != STAGE
        or cfg.get("identity") != IDENTITY
        or cfg.get("design_document_sha256") != "567a02c6ce4f8e52c2d517f2eca1ceef52314796b051f5ab43a5b92144337897"
        or tuple(map(int, bank["issue_task_steps"])) != (10, 14, 18, 22)
        or tuple(map(int, bank["descriptor_state_offsets"])) != (0, 1, 2, 4, 8)
        or tuple(map(float, bank["response_scales"])) != (0.03, 0.03, 0.1, 0.1, 10000.0)
        or tuple(map(int, model["pca_ranks"])) != (2, 4, 6)
        or tuple(map(float, model["rbf_median_distance_multipliers"])) != (0.5, 1.0, 2.0)
        or tuple(map(float, model["kernel_ridges"])) != (1e-6, 1e-3, 1e-1)
        or not bool(model["nested_whole_pair_selection"])
        or tuple(float(gates[key]) for key in ("maximum_relative_l2_error", "minimum_response_cosine", "minimum_peak_ratio", "maximum_peak_ratio", "maximum_absolute_scaled_point_error", "minimum_predicted_peak", "maximum_condition_number")) != (0.75, 0.8, 0.5, 1.5, 0.1, 0.0025, 20.0)
        or int(execution["new_raw_count"]) != 0
        or int(execution["plant_steps_executed"]) != 0
        or any(bool(execution[key]) for key in ("controller_executed", "ray_executed", "gotsc_executed", "tsc_executed"))
        or bool(cfg["scientific_scope"]["bc_dagger_or_rl_allowed"])
    )
    if invalid:
        raise ValueError("R7 independent frozen contract changed")


def _inventory(directory: Path) -> dict[str, Any]:
    digest = hashlib.sha256()
    rows = []
    for path in sorted(directory.glob("*.json.gz")):
        size = path.stat().st_size
        sha = _sha(path)
        digest.update(f"{path.name}\0{size}\0{sha}\n".encode())
        rows.append({"name": path.name, "size": size, "sha256": sha})
    return {"count": len(rows), "bytes": sum(row["size"] for row in rows), "digest": digest.hexdigest(), "rows": rows}


def _source_independent_route(value: Mapping[str, Any]) -> str:
    route = value.get("independent_route")
    if not isinstance(route, str) or value.get("official_route_reproduced") is not True:
        raise ValueError("R7 independent source-route schema changed")
    return route


def _read_source(run: Path, contract: Mapping[str, Any]) -> dict[str, Any]:
    if run.name != contract["run_name"]:
        raise ValueError("R7 independent source run changed")
    stage = run / contract["stage_directory"]
    raw = stage / "raw"
    specs_path = stage / "specs/sentinel_specs.json"
    final_path = stage / "analysis/final_result.json"
    independent_path = run / "server_independent_forensics_v1.json"
    inventory = _inventory(raw)
    if (
        inventory["count"] != int(contract["raw_count"])
        or inventory["bytes"] != int(contract["raw_bytes"])
        or inventory["digest"] != contract["raw_digest"]
        or _sha(final_path) != contract["final_sha256"]
        or _sha(independent_path) != contract["independent_sha256"]
    ):
        raise ValueError("R7 independent source hash changed")
    final = _json(final_path)
    frozen = _json(independent_path)
    if final.get("route") != contract["required_route"] or _source_independent_route(frozen) != contract["required_route"]:
        raise ValueError("R7 independent source route changed")
    specs = _json(specs_path)
    if len(specs) != int(contract["raw_count"]):
        raise ValueError("R7 independent spec count changed")
    expected = {row["name"]: row for row in inventory["rows"]}
    results = {}
    for spec in specs:
        experiment_id = str(spec["experiment_id"])
        path = raw / f"{experiment_id}.json.gz"
        row = expected.get(path.name)
        if row is None or path.stat().st_size != row["size"] or _sha(path) != row["sha256"]:
            raise ValueError("R7 independent raw inventory row changed")
        result = _gzip(path)
        if result.get("experiment_id") != experiment_id or result.get("spec") != spec or result.get("completed") is not True or result.get("success") is not True:
            raise ValueError("R7 independent raw identity changed")
        results[experiment_id] = result
    return {"specs": specs, "results": results, "inventory": inventory}


def _visible(trajectory: Sequence[Mapping[str, Any]], scales: np.ndarray) -> np.ndarray:
    output = []
    for index, state in enumerate(trajectory):
        previous = trajectory[index - 1] if index else trajectory[1]
        direction = 1.0 if index else -1.0
        v_r = direction * (float(state["R"]) - float(previous["R"])) / 0.01
        v_z = direction * (float(state["Z"]) - float(previous["Z"])) / 0.01
        output.append([float(state["R"]), float(state["Z"]), v_r, v_z, float(state["Ip"])])
    values = np.asarray(output, dtype=float) / scales
    if not np.all(np.isfinite(values)):
        raise ValueError("R7 independent visible values invalid")
    return values


def _index(source: Mapping[str, Any], prefix: str, default_issue: int) -> dict[str, dict[tuple[str, int, int, int], tuple[Mapping[str, Any], Mapping[str, Any]]]]:
    output = {}
    for spec in source["specs"]:
        role = str(spec[f"{prefix}_role"])
        issue = int(spec.get(f"{prefix}_issue_task_step", default_issue)) if role == "signed_probe" else -1
        key = (role, issue, int(spec[f"{prefix}_direction_index"]), int(spec[f"{prefix}_sign"]))
        context = str(spec["source_d1r13_experiment_id"])
        if key in output.setdefault(context, {}):
            raise ValueError("R7 independent duplicate bank key")
        output[context][key] = (spec, source["results"][str(spec["experiment_id"])])
    return output


def _items(sources: Mapping[str, Mapping[str, Any]], cfg: Mapping[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    scales = np.asarray(cfg["bank_contract"]["response_scales"], dtype=float)
    target_scales = np.asarray(cfg["bank_contract"]["target_scales"], dtype=float)
    offsets = tuple(map(int, cfg["bank_contract"]["descriptor_state_offsets"]))
    r2 = _index(sources["r2"], "d1r14r2", 10)
    r4 = _index(sources["r4"], "d1r14r4", -1)
    r6 = _index(sources["r6"], "d1r14r6", -1)
    if sorted(r2) != sorted(r4) or sorted(r2) != sorted(r6) or len(r2) != 8:
        raise ValueError("R7 independent context closure changed")
    items = []
    for context in sorted(r2):
        for issue in (10, 14, 18, 22):
            baseline_spec, baseline_result = (r2 if issue == 10 else r4)[context][("baseline", -1, -1, 0)]
            base = _visible(baseline_result["trajectory"], scales)
            descriptor = np.concatenate((
                base[[max(0, issue - offset) for offset in offsets]].reshape(-1),
                np.asarray([baseline_spec["target_R_offset_m"], baseline_spec["target_Z_offset_m"], baseline_spec["target_Ip_offset_A"]], dtype=float) / target_scales,
                [(issue - 10.0) / 12.0],
            ))
            for sign in (-1, 1):
                for direction in range(4):
                    if issue == 10:
                        spec, result = r2[context][("signed_probe", issue, direction, sign)]
                        source_stage = "R2"
                    elif direction == 0:
                        spec, result = r6[context][("signed_probe", issue, direction, sign)]
                        source_stage = "R6"
                    else:
                        spec, result = r4[context][("signed_probe", issue, direction, sign)]
                        source_stage = "R4"
                    response = _visible(result["trajectory"], scales)[issue + 1 :] - base[issue + 1 :]
                    items.append({
                        "response_id": str(spec["experiment_id"]), "source_stage": source_stage,
                        "context_id": context, "pair_id": str(spec["pair_id"]),
                        "history_member": str(spec["history_member"]), "issue_task_step": issue,
                        "sign": sign, "direction_index": direction,
                        "descriptor": descriptor, "response": response,
                    })
    items.sort(key=lambda row: row["response_id"])
    pairs = sorted({row["pair_id"] for row in items})
    histories = {pair: sorted({row["history_member"] for row in items if row["pair_id"] == pair}) for pair in pairs}
    serial = [{key: (value.tolist() if isinstance(value, np.ndarray) else value) for key, value in row.items()} for row in items]
    bank = {
        "response_count": len(items), "context_count": len({row["context_id"] for row in items}),
        "pair_count": len(pairs), "pairs": pairs, "histories_by_pair": histories,
        "source_counts": {name: sum(row["source_stage"] == name for row in items) for name in ("R2", "R4", "R6")},
        "bank_digest": _digest(serial),
    }
    if len(items) != 256 or len(pairs) != 4 or any(v != ["minus_first", "plus_first"] for v in histories.values()) or bank["source_counts"] != {"R2": 64, "R4": 144, "R6": 48}:
        raise ValueError("R7 independent bank contract changed")
    return items, bank


def _candidate_grid(cfg: Mapping[str, Any]) -> list[tuple[int, float, float]]:
    model = cfg["model_contract"]
    return [(int(rank), float(mult), float(ridge)) for rank in model["pca_ranks"] for mult in model["rbf_median_distance_multipliers"] for ridge in model["kernel_ridges"]]


def _projection(train: Sequence[Mapping[str, Any]], rank: int, floor: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    x = np.asarray([row["descriptor"] for row in train])
    mean = x.mean(axis=0)
    scale = np.maximum(x.std(axis=0), floor)
    _, _, right = np.linalg.svd((x - mean) / scale, full_matrices=False)
    if rank > len(right):
        raise ValueError("R7 independent PCA rank unavailable")
    return mean, scale, right[:rank]


def _project(rows: Sequence[Mapping[str, Any]], projection: tuple[np.ndarray, np.ndarray, np.ndarray]) -> np.ndarray:
    mean, scale, components = projection
    return ((np.asarray([row["descriptor"] for row in rows]) - mean) / scale) @ components.T


def _rbf(left: np.ndarray, right: np.ndarray, bandwidth: float) -> np.ndarray:
    difference = left[:, None, :] - right[None, :, :]
    return np.exp(-np.sum(difference * difference, axis=2) / (2.0 * bandwidth * bandwidth))


def _bandwidth(x: np.ndarray, multiplier: float, floor: float) -> float:
    difference = x[:, None, :] - x[None, :, :]
    distance = np.sqrt(np.sum(difference * difference, axis=2))[np.triu_indices(len(x), 1)]
    positive = distance[distance > floor]
    median = float(np.median(positive)) if len(positive) else floor
    return max(multiplier * median, floor)


def _predict(train: Sequence[Mapping[str, Any]], test: Sequence[Mapping[str, Any]], candidate: tuple[int, float, float], cfg: Mapping[str, Any]) -> list[np.ndarray]:
    rank, multiplier, ridge = candidate
    projection = _projection(train, rank, float(cfg["model_contract"]["standard_deviation_floor"]))
    train_x = _project(train, projection)
    test_x = _project(test, projection)
    lookup = {id(row): train_x[index] for index, row in enumerate(train)}
    outputs = []
    for test_index, item in enumerate(test):
        head = [row for row in train if row["sign"] == item["sign"] and row["direction_index"] == item["direction_index"]]
        prediction = np.zeros_like(item["response"])
        for lag in range(1, len(prediction) + 1):
            available = [row for row in head if len(row["response"]) >= lag]
            x = np.asarray([lookup[id(row)] for row in available])
            y = np.asarray([row["response"][lag - 1, 2:5] for row in available])
            width = _bandwidth(x, multiplier, float(cfg["model_contract"]["bandwidth_floor"]))
            gram = _rbf(x, x, width)
            center = y.mean(axis=0)
            coefficient = np.linalg.lstsq(gram + ridge * np.eye(len(gram)), y - center, rcond=None)[0]
            prediction[lag - 1, 2:5] = center + _rbf(test_x[test_index:test_index + 1], x, width)[0] @ coefficient
        scales = np.asarray(cfg["bank_contract"]["response_scales"], dtype=float)
        prediction[:, 0] = np.cumsum(prediction[:, 2]) * 0.01 * scales[2] / scales[0]
        prediction[:, 1] = np.cumsum(prediction[:, 3]) * 0.01 * scales[3] / scales[1]
        outputs.append(prediction)
    return outputs


def _metric(item: Mapping[str, Any], prediction: np.ndarray, cfg: Mapping[str, Any]) -> dict[str, Any]:
    actual = item["response"]
    error = prediction - actual
    a = actual.reshape(-1)
    p = prediction.reshape(-1)
    an = float(np.linalg.norm(a))
    pn = float(np.linalg.norm(p))
    relative = float(np.linalg.norm(error) / max(an, 1e-300))
    cosine = float(np.dot(a, p) / max(an * pn, 1e-300))
    actual_peak = float(np.max(np.abs(actual)))
    predicted_peak = float(np.max(np.abs(prediction)))
    ratio = predicted_peak / max(actual_peak, 1e-300)
    gates = cfg["gates"]
    criteria = {
        "finite": bool(np.all(np.isfinite(prediction))),
        "relative_l2": relative <= float(gates["maximum_relative_l2_error"]) + 1e-15,
        "cosine": cosine >= float(gates["minimum_response_cosine"]) - 1e-15,
        "peak_ratio": float(gates["minimum_peak_ratio"]) - 1e-15 <= ratio <= float(gates["maximum_peak_ratio"]) + 1e-15,
        "point_error": float(np.max(np.abs(error))) <= float(gates["maximum_absolute_scaled_point_error"]) + 1e-15,
    }
    return {
        "response_id": item["response_id"], "context_id": item["context_id"], "pair_id": item["pair_id"],
        "history_member": item["history_member"], "issue_task_step": item["issue_task_step"],
        "sign": item["sign"], "direction_index": item["direction_index"],
        "relative_l2_error": relative, "response_cosine": cosine,
        "actual_peak": actual_peak, "predicted_peak": predicted_peak, "peak_ratio": ratio,
        "maximum_absolute_scaled_point_error": float(np.max(np.abs(error))),
        "componentwise_maximum_absolute_scaled_error": np.max(np.abs(error), axis=0).tolist(),
        "mean_squared_scaled_error": float(np.mean(error * error)),
        "criteria": criteria, "passed": bool(all(criteria.values())),
        "predicted_response": prediction.tolist(),
    }


def _cv(items: Sequence[Mapping[str, Any]], candidate: tuple[int, float, float], cfg: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for pair in sorted({row["pair_id"] for row in items}):
        train = [row for row in items if row["pair_id"] != pair]
        held = [row for row in items if row["pair_id"] == pair]
        rows.extend(_metric(item, prediction, cfg) for item, prediction in zip(held, _predict(train, held, candidate, cfg)))
    return sorted(rows, key=lambda row: row["response_id"])


def _score(rows: Sequence[Mapping[str, Any]], candidate: tuple[int, float, float]) -> tuple[Any, ...]:
    relative = np.asarray([row["relative_l2_error"] for row in rows])
    return (
        sum(not row["passed"] for row in rows), max(row["maximum_absolute_scaled_point_error"] for row in rows),
        float(np.quantile(relative, 0.95, method="linear")), float(np.mean([row["mean_squared_scaled_error"] for row in rows])),
        candidate[0], candidate[1], candidate[2],
    )


def _select(items: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]) -> tuple[tuple[int, float, float], list[dict[str, Any]]]:
    scored = []
    for candidate in _candidate_grid(cfg):
        rows = _cv(items, candidate, cfg)
        scored.append((candidate, _score(rows, candidate)))
    selected = min(scored, key=lambda row: row[1])[0]
    reports = [{"candidate": {"pca_rank": c[0], "bandwidth_multiplier": c[1], "ridge": c[2]}, "selection_score": list(score[:4])} for c, score in scored]
    return selected, reports


def _nested(items: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows = []
    folds = []
    for pair in sorted({row["pair_id"] for row in items}):
        train = [row for row in items if row["pair_id"] != pair]
        held = [row for row in items if row["pair_id"] == pair]
        selected, scores = _select(train, cfg)
        predictions = _predict(train, held, selected, cfg)
        rows.extend(_metric(item, prediction, cfg) for item, prediction in zip(held, predictions))
        folds.append({
            "held_pair_id": pair, "training_pair_count": 3, "held_response_count": len(held),
            "selected_candidate": {"pca_rank": selected[0], "bandwidth_multiplier": selected[1], "ridge": selected[2]},
            "inner_candidate_scores": scores,
        })
    return sorted(rows, key=lambda row: row["response_id"]), folds


def _aggregate(rows: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]) -> dict[str, Any]:
    component = np.max(np.asarray([row["componentwise_maximum_absolute_scaled_error"] for row in rows]), axis=0)
    scales = np.asarray(cfg["bank_contract"]["response_scales"])
    gates = cfg["gates"]
    precursor = np.asarray(gates["response_floor_physical"]) / scales + float(gates["tube_multiplier"]) * component
    caps = np.asarray(gates["tube_caps_physical"]) / scales
    return {
        "response_count": len(rows), "response_pass_count": sum(row["passed"] for row in rows),
        "maximum_relative_l2_error": max(row["relative_l2_error"] for row in rows),
        "minimum_response_cosine": min(row["response_cosine"] for row in rows),
        "minimum_peak_ratio": min(row["peak_ratio"] for row in rows), "maximum_peak_ratio": max(row["peak_ratio"] for row in rows),
        "maximum_absolute_scaled_point_error": max(row["maximum_absolute_scaled_point_error"] for row in rows),
        "componentwise_maximum_absolute_scaled_error": component.tolist(),
        "tube_precursor_scaled": precursor.tolist(), "tube_precursor_physical": (precursor * scales).tolist(),
        "tube_cap_pass": bool(np.all(precursor <= caps + 1e-15)),
        "passed": bool(len(rows) == 256 and all(row["passed"] for row in rows) and np.all(precursor <= caps + 1e-15)),
    }


def _geometry(rows: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]) -> dict[str, Any]:
    grouped = {}
    for row in rows:
        grouped.setdefault((row["context_id"], row["issue_task_step"], row["sign"]), []).append(row)
    branches = []
    directions = ranks = conditions = 0
    gates = cfg["gates"]
    for key, members in sorted(grouped.items()):
        members.sort(key=lambda row: row["direction_index"])
        columns = []
        peaks = []
        for row in members:
            value = np.asarray(row["predicted_response"]).reshape(-1)
            peak = float(np.max(np.abs(value)))
            norm = float(np.linalg.norm(value))
            directions += int(np.all(np.isfinite(value)) and norm > 0 and peak >= float(gates["minimum_predicted_peak"]) - 1e-15)
            peaks.append(peak)
            columns.append(value / max(norm, 1e-300))
        singular = np.linalg.svd(np.column_stack(columns), compute_uv=False)
        rank = int(np.sum(singular > singular[0] * float(gates["rank_relative_tolerance"])))
        condition = float(singular[0] / singular[-1]) if rank == 4 and singular[-1] > 0 else float("inf")
        rank_ok = rank == 4
        condition_ok = condition <= 20.0 + 1e-12
        ranks += int(rank_ok)
        conditions += int(condition_ok)
        branches.append({"context_id": key[0], "issue_task_step": key[1], "sign": key[2], "direction_peaks": peaks, "rank": rank, "condition_number": condition, "passed": bool(min(peaks) >= 0.0025 - 1e-15 and rank_ok and condition_ok)})
    return {
        "branch_count": len(branches), "direction_pass_count": directions, "rank_pass_count": ranks,
        "condition_pass_count": conditions, "maximum_condition_number": max(row["condition_number"] for row in branches),
        "minimum_predicted_peak": min(min(row["direction_peaks"]) for row in branches), "rows": branches,
        "passed": bool(len(branches) == 64 and directions == 256 and ranks == 64 and conditions == 64),
    }


def audit(args: argparse.Namespace) -> dict[str, Any]:
    cfg = _json(args.config.resolve())
    _validate_frozen_contract(cfg)
    if _sha(args.design_document.resolve()) != cfg["design_document_sha256"]:
        raise ValueError("R7 independent design hash changed")
    sources = {
        "r2": _read_source(args.source_r2_run.resolve(), cfg["source_contracts"]["r2"]),
        "r4": _read_source(args.source_r4_run.resolve(), cfg["source_contracts"]["r4"]),
        "r6": _read_source(args.source_r6_run.resolve(), cfg["source_contracts"]["r6"]),
    }
    items, bank = _items(sources, cfg)
    rows, folds = _nested(items, cfg)
    aggregate = _aggregate(rows, cfg)
    geometry = _geometry(rows, cfg)
    final_candidate, final_scores = _select(items, cfg)
    passed = bool(aggregate["passed"] and geometry["passed"])
    route = cfg["routes"]["pass" if passed else "model_fail"]
    primary = _json(args.primary_output.resolve() / "stage4_2r3c3t13s24d1r14r7_detailed_v1.json")
    candidate_dict = {"pca_rank": final_candidate[0], "bandwidth_multiplier": final_candidate[1], "ridge": final_candidate[2]}
    agreement = bool(
        _agrees(primary.get("bank"), bank)
        and _agrees(primary.get("nested_outer_folds"), folds)
        and _agrees(primary.get("outer_prediction_rows"), rows)
        and _agrees(primary.get("aggregate"), aggregate)
        and _agrees(primary.get("predicted_geometry"), geometry)
        and _agrees(primary.get("final_candidate_development_only"), candidate_dict)
        and _agrees(primary.get("final_candidate_scores"), final_scores)
        and primary.get("passed") == passed
        and primary.get("route") == route
    )
    result = {
        "schema_version": 1, "stage": STAGE, "passed": bool(passed and agreement), "route": route,
        "source_authentication_passed": True, "bank": bank, "nested_outer_folds": folds,
        "outer_prediction_rows": rows, "aggregate": aggregate, "predicted_geometry": geometry,
        "final_candidate_development_only": candidate_dict, "final_candidate_scores": final_scores,
        "primary_numerical_agreement": agreement,
        "classification": {
            "runtime_or_environment_error": False, "packaging_import_or_deployment_error": False,
            "raw_or_snapshot_corruption": False, "summary_or_reporting_error": not agreement,
            "model_design_failure": not passed,
        },
        "new_raw_count": 0, "tsc_executed": False,
    }
    _write(args.output.resolve(), result)
    print(json.dumps({key: result[key] for key in ("stage", "passed", "route", "primary_numerical_agreement", "aggregate")}, indent=2, sort_keys=True, allow_nan=False))
    if not agreement:
        raise ValueError("R7 independent result does not agree with primary")
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--design-document", type=Path, required=True)
    parser.add_argument("--source-r2-run", type=Path, required=True)
    parser.add_argument("--source-r4-run", type=Path, required=True)
    parser.add_argument("--source-r6-run", type=Path, required=True)
    parser.add_argument("--primary-output", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


if __name__ == "__main__":
    audit(_parser().parse_args())
