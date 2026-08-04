#!/usr/bin/env python3
"""Independent raw-to-route reconstruction for D1R14R7R2."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from docs.codex.audit_tools import stage4_2r3c3t13s24d1r14r7_independent_forensics as frozen


STAGE = "Stage4.2R3c3T13S24D1R14R7R2"
DESIGN_SHA256 = "32d0a5d123b70f9565cd27534e576eb63a6688bb0f6021755746b2f1e98dfdc5"


def _validate(cfg: Mapping[str, Any]) -> None:
    bank, request = cfg["bank_contract"], cfg["request_contract"]
    model, gates = cfg["model_contract"], cfg["gates"]
    execution, timing, scope = (
        cfg["execution_contract"],
        cfg["formal_timing_contract"],
        cfg["scientific_scope"],
    )
    invalid = (
        cfg.get("stage") != STAGE
        or cfg.get("identity") != "action_conditioned_full_history_kernel_development_v1"
        or cfg.get("package_revision")
        != "r42r3c3t13s24d1r14r7r2_action_conditioned_full_history_kernel_v1"
        or cfg.get("design_document_sha256") != DESIGN_SHA256
        or tuple(map(int, bank["issue_task_steps"])) != (10, 14, 18, 22)
        or tuple(map(int, bank["history_offsets"])) != tuple(range(23))
        or tuple(map(float, bank["response_scales"]))
        != (0.03, 0.03, 0.1, 0.1, 10000.0)
        or tuple(map(float, bank["target_scales"])) != (0.03, 0.03, 10000.0)
        or float(bank["dt_s"]) != 0.01
        or int(bank["maximum_relative_lag"]) != 27
        or tuple(
            int(bank[key])
            for key in (
                "context_count",
                "pair_count",
                "histories_per_pair",
                "direction_count",
                "response_count",
            )
        )
        != (8, 4, 2, 4, 304)
        or bank["source_response_counts"] != {"R2": 64, "R4": 192, "R6": 48}
        or request["canonical_matrix_digest"]
        != "c8cd62c00c1f60b46312927789659657dc8cc35717533193433b0e398c1ec94c"
        or request["replacement_matrix_digest"]
        != "69528f0e204b51847c1d2a7df428555a557454e9fa6bc76768d39e7cc5a90da8"
        or np.asarray(request["canonical_matrix_columns"]).shape != (4, 4)
        or np.asarray(request["replacement_matrix_columns"]).shape != (4, 4)
        or tuple(map(float, (request["canonical_scale"], request["replacement_scale"])))
        != (1.0, 1.5)
        or int(request["replacement_direction_index"]) != 0
        or float(request["coordinate_absolute_tolerance"]) != 1e-15
        or tuple(map(int, model["pca_ranks"])) != (4, 8, 12)
        or tuple(map(float, model["rbf_median_distance_multipliers"]))
        != (0.5, 1.0, 2.0)
        or tuple(map(float, model["kernel_ridges"])) != (1e-6, 1e-3, 1e-1)
        or tuple(map(float, (model["standard_deviation_floor"], model["bandwidth_floor"])))
        != (1e-12, 1e-12)
        or tuple(map(int, (model["tail_polynomial_degree"], model["tail_fit_point_count"])))
        != (2, 8)
        or tuple(map(int, model["output_indices"])) != (2, 3, 4)
        or model["outer_group_key"] != "pair_id"
        or not bool(model["heads_use_only_action_sign_and_direction"])
        or not bool(model["nested_whole_pair_selection"])
        or bool(model["final_all_data_fit_is_validation"])
        or tuple(
            float(gates[key])
            for key in (
                "maximum_relative_l2_error",
                "minimum_response_cosine",
                "minimum_peak_ratio",
                "maximum_peak_ratio",
                "maximum_absolute_scaled_point_error",
                "minimum_predicted_peak",
                "maximum_condition_number",
            )
        )
        != (0.75, 0.8, 0.5, 1.5, 0.1, 0.0025, 20.0)
        or tuple(map(float, gates["response_floor_physical"]))
        != (1e-9, 1e-9, 1e-7, 1e-7, 1e-4)
        or float(gates["tube_multiplier"]) != 2.0
        or tuple(map(float, gates["tube_caps_physical"]))
        != (0.003, 0.003, 0.01, 0.01, 1000.0)
        or float(gates["rank_relative_tolerance"]) != 1e-10
        or tuple(
            int(gates[key])
            for key in (
                "required_rank",
                "required_response_pass_count",
                "required_signal_pass_count",
                "required_canonical_branch_count",
                "required_operational_branch_count",
            )
        )
        != (4, 304, 304, 64, 64)
        or tuple(cfg["forbidden_predictor_fields"])
        != (
            "pair_id",
            "history_member",
            "prefix",
            "target_id",
            "regime_id",
            "delay_label",
            "slew_label",
            "source_result",
            "source_action",
            "source_coil_current",
            "source_wire_current",
            "current_coil_current",
            "current_wire_current",
            "hidden_wire_current",
            "future_measurement",
            "future_executed_action",
        )
        or int(execution["new_raw_count"]) != 0
        or int(execution["plant_steps_executed"]) != 0
        or any(
            bool(execution[key])
            for key in ("controller_executed", "ray_executed", "gotsc_executed", "tsc_executed")
        )
        or not bool(execution["source_raw_read_in_place"])
        or tuple(
            int(timing[key])
            for key in (
                "normal_arrival_deadline_step",
                "normal_hold_through_step",
                "weak_arrival_deadline_step",
                "weak_hold_through_step",
            )
        )
        != (25, 35, 27, 37)
        or bool(timing["arrival_deadline_expansion_allowed"])
        or bool(timing["evaluated_in_r7r2"])
        or not bool(scope["identification_development_only"])
        or any(
            bool(scope[key])
            for key in (
                "probe_trajectories_allowed_in_expert_dataset",
                "transition_response_model_validated_fresh",
                "mpc_validated",
                "expert_data_allowed",
                "bc_dagger_or_rl_allowed",
            )
        )
        or cfg["routes"]
        != {
            "source_fail": "ACTION_CONDITIONED_FULL_HISTORY_SOURCE_FAIL_NO_TSC",
            "model_fail": "ACTION_CONDITIONED_FULL_HISTORY_MODEL_FAIL_NEW_IDENTIFICATION_REQUIRED",
            "pass": "ACTION_CONDITIONED_FULL_HISTORY_MODEL_PASS_FRESH_MULTIPULSE_DESIGN_REQUIRED",
        }
    )
    if invalid:
        raise ValueError("R7R2 independent frozen contract changed")


def _request(
    spec: Mapping[str, Any], prefix: str, direction: int, sign: int, cfg: Mapping[str, Any]
) -> float:
    contract = cfg["request_contract"]
    replacement = prefix == "d1r14r6"
    matrix = np.asarray(
        contract["replacement_matrix_columns" if replacement else "canonical_matrix_columns"],
        dtype=float,
    )
    digest = contract["replacement_matrix_digest" if replacement else "canonical_matrix_digest"]
    actual = np.asarray(spec[f"{prefix}_requested_coordinate"], dtype=float)
    if (
        int(spec[f"{prefix}_direction_index"]) != direction
        or int(spec[f"{prefix}_sign"]) != sign
        or spec[f"{prefix}_requested_matrix_digest"] != digest
        or actual.shape != (4,)
        or np.max(np.abs(actual - sign * matrix[:, direction]))
        > float(contract["coordinate_absolute_tolerance"])
    ):
        raise ValueError("R7R2 independent request changed")
    canonical = np.asarray(contract["canonical_matrix_columns"], dtype=float)[:, direction]
    scale = float(np.linalg.norm(matrix[:, direction]) / np.linalg.norm(canonical))
    expected = float(contract["replacement_scale"] if replacement else contract["canonical_scale"])
    if replacement and direction != int(contract["replacement_direction_index"]):
        raise ValueError("R7R2 independent replacement direction changed")
    if abs(scale - expected) > 1e-12:
        raise ValueError("R7R2 independent request scale changed")
    return expected


def _items(
    sources: Mapping[str, Mapping[str, Any]], cfg: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    scales = np.asarray(cfg["bank_contract"]["response_scales"], dtype=float)
    target_scales = np.asarray(cfg["bank_contract"]["target_scales"], dtype=float)
    offsets = tuple(map(int, cfg["bank_contract"]["history_offsets"]))
    indices = {
        "r2": frozen._index(sources["r2"], "d1r14r2", 10),
        "r4": frozen._index(sources["r4"], "d1r14r4", -1),
        "r6": frozen._index(sources["r6"], "d1r14r6", -1),
    }
    contexts = sorted(indices["r2"])
    if contexts != sorted(indices["r4"]) or contexts != sorted(indices["r6"]):
        raise ValueError("R7R2 independent context closure changed")
    rows: list[dict[str, Any]] = []
    for context in contexts:
        for issue in (10, 14, 18, 22):
            baseline_index = indices["r2"] if issue == 10 else indices["r4"]
            baseline_spec, baseline_result = baseline_index[context][("baseline", -1, -1, 0)]
            visible = frozen._visible(baseline_result["trajectory"], scales)
            descriptor = np.concatenate(
                (
                    visible[[max(0, issue - offset) for offset in offsets]].reshape(-1),
                    [float(offset <= issue) for offset in offsets],
                    np.asarray(
                        [
                            baseline_spec["target_R_offset_m"],
                            baseline_spec["target_Z_offset_m"],
                            baseline_spec["target_Ip_offset_A"],
                        ],
                        dtype=float,
                    )
                    / target_scales,
                    [(issue - 10.0) / 12.0],
                )
            )
            if descriptor.shape != (142,):
                raise ValueError("R7R2 independent descriptor changed")
            baseline = visible[issue + 1 :]
            for sign in (-1, 1):
                for direction in range(4):
                    source_name, prefix = ("r2", "d1r14r2") if issue == 10 else ("r4", "d1r14r4")
                    spec, result = indices[source_name][context][
                        ("signed_probe", issue, direction, sign)
                    ]
                    response = frozen._visible(result["trajectory"], scales)[issue + 1 :] - baseline
                    roles = ["canonical"] + (["operational"] if issue == 10 or direction else [])
                    rows.append(
                        {
                            "response_id": str(spec["experiment_id"]),
                            "source_stage": source_name.upper(),
                            "context_id": context,
                            "pair_id": str(spec["pair_id"]),
                            "history_member": str(spec["history_member"]),
                            "issue_task_step": issue,
                            "sign": sign,
                            "direction_index": direction,
                            "action_scale": _request(spec, prefix, direction, sign, cfg),
                            "geometry_roles": roles,
                            "descriptor": descriptor,
                            "response": response,
                        }
                    )
                    if issue > 10 and direction == 0:
                        spec, result = indices["r6"][context][
                            ("signed_probe", issue, direction, sign)
                        ]
                        response = (
                            frozen._visible(result["trajectory"], scales)[issue + 1 :] - baseline
                        )
                        rows.append(
                            {
                                "response_id": str(spec["experiment_id"]),
                                "source_stage": "R6",
                                "context_id": context,
                                "pair_id": str(spec["pair_id"]),
                                "history_member": str(spec["history_member"]),
                                "issue_task_step": issue,
                                "sign": sign,
                                "direction_index": direction,
                                "action_scale": _request(
                                    spec, "d1r14r6", direction, sign, cfg
                                ),
                                "geometry_roles": ["operational"],
                                "descriptor": descriptor,
                                "response": response,
                            }
                        )
    rows.sort(key=lambda row: row["response_id"])
    pairs = sorted({row["pair_id"] for row in rows})
    histories = {
        pair: sorted({row["history_member"] for row in rows if row["pair_id"] == pair})
        for pair in pairs
    }
    counts = {name: sum(row["source_stage"] == name for row in rows) for name in ("R2", "R4", "R6")}
    serial = []
    for row in rows:
        serial.append(
            {
                key: value.tolist() if isinstance(value, np.ndarray) else value
                for key, value in row.items()
            }
        )
    bank = {
        "response_count": len(rows),
        "context_count": len(contexts),
        "pair_count": len(pairs),
        "pairs": pairs,
        "histories_by_pair": histories,
        "source_counts": counts,
        "descriptor_dimension": 142,
        "canonical_geometry_item_count": sum("canonical" in row["geometry_roles"] for row in rows),
        "operational_geometry_item_count": sum(
            "operational" in row["geometry_roles"] for row in rows
        ),
        "bank_digest": frozen._digest(serial),
    }
    if (
        len(rows) != 304
        or len(pairs) != 4
        or any(value != ["minus_first", "plus_first"] for value in histories.values())
        or counts != {"R2": 64, "R4": 192, "R6": 48}
        or bank["canonical_geometry_item_count"] != 256
        or bank["operational_geometry_item_count"] != 256
    ):
        raise ValueError("R7R2 independent bank contract changed")
    return rows, bank


def _grid(cfg: Mapping[str, Any]) -> list[tuple[int, float, float]]:
    contract = cfg["model_contract"]
    return [
        (int(rank), float(multiplier), float(ridge))
        for rank in contract["pca_ranks"]
        for multiplier in contract["rbf_median_distance_multipliers"]
        for ridge in contract["kernel_ridges"]
    ]


def _prepare(
    items: Sequence[Mapping[str, Any]], rank: int, floor: float
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    x = np.asarray([row["descriptor"] for row in items], dtype=float)
    mean, scale = x.mean(axis=0), np.maximum(x.std(axis=0), floor)
    _, _, vt = np.linalg.svd((x - mean) / scale, full_matrices=False)
    if rank <= 0 or rank > len(vt):
        raise ValueError("R7R2 independent PCA rank unavailable")
    return mean, scale, vt[:rank]


def _project(row: Mapping[str, Any], prep: tuple[np.ndarray, np.ndarray, np.ndarray]) -> np.ndarray:
    mean, scale, components = prep
    return ((np.asarray(row["descriptor"]) - mean) / scale) @ components.T


def _rbf(left: np.ndarray, right: np.ndarray, bandwidth: float) -> np.ndarray:
    squared = np.sum((left[:, None, :] - right[None, :, :]) ** 2, axis=2)
    return np.exp(-squared / (2.0 * bandwidth**2))


def _fit(
    train: Sequence[Mapping[str, Any]], candidate: tuple[int, float, float], cfg: Mapping[str, Any]
) -> dict[str, Any]:
    rank, multiplier, ridge = candidate
    floor = float(cfg["model_contract"]["standard_deviation_floor"])
    bandwidth_floor = float(cfg["model_contract"]["bandwidth_floor"])
    prep = _prepare(train, rank, floor)
    projected = {row["response_id"]: _project(row, prep) for row in train}
    heads = {}
    for sign in (-1, 1):
        for direction in range(4):
            members = [
                row
                for row in train
                if row["sign"] == sign and row["direction_index"] == direction
            ]
            amplitude = np.asarray([row["action_scale"] for row in members])
            amplitude_mean = float(amplitude.mean())
            amplitude_scale = max(float(amplitude.std()), floor)
            features = {
                row["response_id"]: np.r_[
                    projected[row["response_id"]],
                    (row["action_scale"] - amplitude_mean) / amplitude_scale,
                ]
                for row in members
            }
            lag_models = []
            for lag in range(1, max(len(row["response"]) for row in members) + 1):
                available = [row for row in members if len(row["response"]) >= lag]
                x = np.asarray([features[row["response_id"]] for row in available])
                y = np.asarray(
                    [np.asarray(row["response"], dtype=float)[lag - 1, 2:5] for row in available]
                )
                delta = x[:, None, :] - x[None, :, :]
                distances = np.sqrt(np.sum(delta * delta, axis=2))
                upper = distances[np.triu_indices(len(x), 1)]
                positive = upper[upper > bandwidth_floor]
                median = max(float(np.median(positive)) if len(positive) else bandwidth_floor, bandwidth_floor)
                bandwidth = max(multiplier * median, bandwidth_floor)
                gram = _rbf(x, x, bandwidth)
                y_mean = y.mean(axis=0)
                alpha = np.linalg.lstsq(
                    gram + ridge * np.eye(len(gram)), y - y_mean, rcond=None
                )[0]
                lag_models.append((x, bandwidth, y_mean, alpha))
            heads[(sign, direction)] = (amplitude_mean, amplitude_scale, lag_models)
    return {"candidate": candidate, "prep": prep, "heads": heads}


def _predict(model: Mapping[str, Any], row: Mapping[str, Any], cfg: Mapping[str, Any]) -> np.ndarray:
    amplitude_mean, amplitude_scale, lag_models = model["heads"][(row["sign"], row["direction_index"])]
    feature = np.r_[
        _project(row, model["prep"]),
        (row["action_scale"] - amplitude_mean) / amplitude_scale,
    ][None, :]
    count, observed = len(row["response"]), min(len(row["response"]), len(lag_models))
    output = np.zeros((count, 5))
    for index, (x, bandwidth, y_mean, alpha) in enumerate(lag_models[:observed]):
        output[index, 2:5] = y_mean + _rbf(feature, x, bandwidth)[0] @ alpha
    if count > observed:
        points = int(cfg["model_contract"]["tail_fit_point_count"])
        degree = int(cfg["model_contract"]["tail_polynomial_degree"])
        lag = np.arange(observed - points + 1, observed + 1, dtype=float)
        future = np.arange(observed + 1, count + 1, dtype=float)
        design = np.column_stack([lag**order for order in range(degree + 1)])
        future_design = np.column_stack([future**order for order in range(degree + 1)])
        for component in (2, 3, 4):
            coefficient = np.linalg.lstsq(
                design, output[observed - points : observed, component], rcond=None
            )[0]
            output[observed:, component] = future_design @ coefficient
    scales = np.asarray(cfg["bank_contract"]["response_scales"])
    dt = float(cfg["bank_contract"]["dt_s"])
    output[:, 0] = np.cumsum(output[:, 2]) * dt * scales[2] / scales[0]
    output[:, 1] = np.cumsum(output[:, 3]) * dt * scales[3] / scales[1]
    return output


def _metric(row: Mapping[str, Any], prediction: np.ndarray, cfg: Mapping[str, Any]) -> dict[str, Any]:
    result = frozen._metric(row, prediction, cfg)
    result.update(
        {
            "source_stage": row["source_stage"],
            "action_scale": float(row["action_scale"]),
            "geometry_roles": list(row["geometry_roles"]),
        }
    )
    return result


def _cv(
    items: Sequence[Mapping[str, Any]], candidate: tuple[int, float, float], cfg: Mapping[str, Any]
) -> list[dict[str, Any]]:
    rows = []
    for pair in sorted({row["pair_id"] for row in items}):
        train = [row for row in items if row["pair_id"] != pair]
        held = [row for row in items if row["pair_id"] == pair]
        fitted = _fit(train, candidate, cfg)
        rows.extend(_metric(row, _predict(fitted, row, cfg), cfg) for row in held)
    return sorted(rows, key=lambda row: row["response_id"])


def _score(rows: Sequence[Mapping[str, Any]], candidate: tuple[int, float, float]) -> tuple[Any, ...]:
    relative = np.asarray([row["relative_l2_error"] for row in rows])
    return (
        sum(not row["passed"] for row in rows),
        max(row["maximum_absolute_scaled_point_error"] for row in rows),
        float(np.quantile(relative, 0.95, method="linear")),
        float(np.mean([row["mean_squared_scaled_error"] for row in rows])),
        *candidate,
    )


def _select(
    items: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]
) -> tuple[tuple[int, float, float], list[dict[str, Any]]]:
    scored = [(candidate, _score(_cv(items, candidate, cfg), candidate)) for candidate in _grid(cfg)]
    selected = min(scored, key=lambda row: row[1])[0]
    reports = [
        {
            "candidate": {
                "pca_rank": candidate[0],
                "bandwidth_multiplier": candidate[1],
                "ridge": candidate[2],
            },
            "selection_score": list(score[:4]),
        }
        for candidate, score in scored
    ]
    return selected, reports


def _nested(
    items: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows, folds = [], []
    for pair in sorted({row["pair_id"] for row in items}):
        train = [row for row in items if row["pair_id"] != pair]
        held = [row for row in items if row["pair_id"] == pair]
        selected, scores = _select(train, cfg)
        fitted = _fit(train, selected, cfg)
        rows.extend(_metric(row, _predict(fitted, row, cfg), cfg) for row in held)
        folds.append(
            {
                "held_pair_id": pair,
                "training_pair_count": 3,
                "held_response_count": len(held),
                "selected_candidate": {
                    "pca_rank": selected[0],
                    "bandwidth_multiplier": selected[1],
                    "ridge": selected[2],
                },
                "inner_candidate_scores": scores,
            }
        )
    return sorted(rows, key=lambda row: row["response_id"]), folds


def _family(rows: Sequence[Mapping[str, Any]], role: str, cfg: Mapping[str, Any]) -> dict[str, Any]:
    gates = cfg["gates"]
    groups: dict[tuple[str, int, int], list[Mapping[str, Any]]] = {}
    for row in rows:
        if role in row["geometry_roles"]:
            groups.setdefault(
                (row["context_id"], row["issue_task_step"], row["sign"]), []
            ).append(row)
    branches = []
    for key, members in sorted(groups.items()):
        members.sort(key=lambda row: row["direction_index"])
        if [row["direction_index"] for row in members] != [0, 1, 2, 3]:
            raise ValueError("R7R2 independent geometry coverage changed")
        columns = []
        for row in members:
            value = np.asarray(row["predicted_response"]).reshape(-1)
            columns.append(value / max(float(np.linalg.norm(value)), 1e-300))
        singular = np.linalg.svd(np.column_stack(columns), compute_uv=False)
        rank = int(np.sum(singular > singular[0] * float(gates["rank_relative_tolerance"])))
        condition = (
            float(singular[0] / singular[-1])
            if rank == int(gates["required_rank"]) and singular[-1] > 0
            else float("inf")
        )
        passed = bool(
            rank == int(gates["required_rank"])
            and condition <= float(gates["maximum_condition_number"]) + 1e-12
        )
        branches.append(
            {
                "context_id": key[0],
                "issue_task_step": key[1],
                "sign": key[2],
                "rank": rank,
                "condition_number": condition,
                "passed": passed,
            }
        )
    required = int(
        gates[
            "required_canonical_branch_count"
            if role == "canonical"
            else "required_operational_branch_count"
        ]
    )
    return {
        "role": role,
        "branch_count": len(branches),
        "rank_pass_count": sum(row["rank"] == int(gates["required_rank"]) for row in branches),
        "condition_pass_count": sum(
            row["condition_number"] <= float(gates["maximum_condition_number"]) + 1e-12
            for row in branches
        ),
        "maximum_condition_number": max(row["condition_number"] for row in branches),
        "rows": branches,
        "passed": bool(len(branches) == required and all(row["passed"] for row in branches)),
    }


def _geometry(rows: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]) -> dict[str, Any]:
    gates = cfg["gates"]
    peaks = [float(np.max(np.abs(np.asarray(row["predicted_response"])))) for row in rows]
    signal = sum(peak >= float(gates["minimum_predicted_peak"]) - 1e-15 for peak in peaks)
    canonical, operational = _family(rows, "canonical", cfg), _family(rows, "operational", cfg)
    return {
        "response_count": len(rows),
        "signal_pass_count": signal,
        "minimum_predicted_peak": min(peaks),
        "canonical": canonical,
        "operational": operational,
        "passed": bool(
            len(rows) == int(gates["required_signal_pass_count"])
            and signal == int(gates["required_signal_pass_count"])
            and canonical["passed"]
            and operational["passed"]
        ),
    }


def audit(args: argparse.Namespace) -> dict[str, Any]:
    cfg = frozen._json(args.config.resolve())
    _validate(cfg)
    if frozen._sha(args.design_document.resolve()) != cfg["design_document_sha256"]:
        raise ValueError("R7R2 independent design hash changed")
    sources = {
        "r2": frozen._read_source(args.source_r2_run.resolve(), cfg["source_contracts"]["r2"]),
        "r4": frozen._read_source(args.source_r4_run.resolve(), cfg["source_contracts"]["r4"]),
        "r6": frozen._read_source(args.source_r6_run.resolve(), cfg["source_contracts"]["r6"]),
    }
    items, bank = _items(sources, cfg)
    rows, folds = _nested(items, cfg)
    aggregate, geometry = frozen._aggregate(rows, cfg), _geometry(rows, cfg)
    final_candidate, final_scores = _select(items, cfg)
    candidate_dict = {
        "pca_rank": final_candidate[0],
        "bandwidth_multiplier": final_candidate[1],
        "ridge": final_candidate[2],
    }
    passed = bool(aggregate["passed"] and geometry["passed"])
    route = cfg["routes"]["pass" if passed else "model_fail"]
    primary = frozen._json(
        args.primary_output.resolve() / "stage4_2r3c3t13s24d1r14r7r2_detailed_v1.json"
    )
    agreement = bool(
        frozen._agrees(primary.get("bank"), bank)
        and frozen._agrees(primary.get("nested_outer_folds"), folds)
        and frozen._agrees(primary.get("outer_prediction_rows"), rows)
        and frozen._agrees(primary.get("aggregate"), aggregate)
        and frozen._agrees(primary.get("predicted_geometry"), geometry)
        and frozen._agrees(primary.get("final_candidate_development_only"), candidate_dict)
        and frozen._agrees(primary.get("final_candidate_scores"), final_scores)
        and primary.get("passed") == passed
        and primary.get("route") == route
    )
    result = {
        "schema_version": 1,
        "stage": STAGE,
        "passed": bool(passed and agreement),
        "route": route,
        "source_authentication_passed": True,
        "bank": bank,
        "nested_outer_folds": folds,
        "outer_prediction_rows": rows,
        "aggregate": aggregate,
        "predicted_geometry": geometry,
        "final_candidate_development_only": candidate_dict,
        "final_candidate_scores": final_scores,
        "primary_numerical_agreement": agreement,
        "classification": {
            "runtime_or_environment_error": False,
            "packaging_import_or_deployment_error": False,
            "raw_or_snapshot_corruption": False,
            "summary_or_reporting_error": not agreement,
            "model_design_failure": not passed,
        },
        "new_raw_count": 0,
        "tsc_executed": False,
    }
    frozen._write(args.output.resolve(), result)
    print(
        json.dumps(
            {
                key: result[key]
                for key in ("stage", "passed", "route", "primary_numerical_agreement", "aggregate")
            },
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
    )
    if not agreement:
        raise ValueError("R7R2 independent result disagrees with primary")
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
