#!/usr/bin/env python3
"""Independent continuous-lag numerical replay for D1R14R7R1."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from docs.codex.audit_tools import stage4_2r3c3t13s24d1r14r7_independent_forensics as frozen


STAGE = "Stage4.2R3c3T13S24D1R14R7R1"


def _validate(cfg: Mapping[str, Any]) -> None:
    bank = cfg["bank_contract"]
    model = cfg["model_contract"]
    gates = cfg["gates"]
    execution = cfg["execution_contract"]
    timing = cfg["formal_timing_contract"]
    scope = cfg["scientific_scope"]
    invalid = (
        cfg.get("stage") != STAGE
        or cfg.get("identity") != "continuous_lag_causal_response_model_development_v1"
        or cfg.get("package_revision") != "r42r3c3t13s24d1r14r7r1_continuous_lag_response_model_v1"
        or cfg.get("design_document_sha256") != "959decfbdebda3e41d793cb85ddbee1a2d0919a8b88a126dad422536054d9e4b"
        or tuple(map(int, bank["issue_task_steps"])) != (10, 14, 18, 22)
        or tuple(map(float, bank["response_scales"])) != (0.03, 0.03, 0.1, 0.1, 10000.0)
        or tuple(map(float, bank["target_scales"])) != (0.03, 0.03, 10000.0)
        or tuple(map(int, bank["descriptor_state_offsets"])) != (0, 1, 2, 4, 8)
        or float(bank["dt_s"]) != 0.01
        or int(bank["maximum_relative_lag"]) != 27
        or tuple(int(bank[key]) for key in ("context_count", "pair_count", "histories_per_pair", "direction_count", "response_count")) != (8, 4, 2, 4, 256)
        or tuple(map(int, model["pca_ranks"])) != (2, 4, 6)
        or tuple(map(int, model["temporal_legendre_degrees"])) != (2, 3, 5)
        or tuple(map(float, model["ridges"])) != (1e-6, 1e-3, 1e-1)
        or float(model["standard_deviation_floor"]) != 1e-12
        or tuple(map(int, model["output_indices"])) != (2, 3, 4)
        or model["outer_group_key"] != "pair_id"
        or not bool(model["heads_use_only_action_sign_and_direction"])
        or not bool(model["nested_whole_pair_selection"])
        or bool(model["final_all_data_fit_is_validation"])
        or tuple(float(gates[key]) for key in ("maximum_relative_l2_error", "minimum_response_cosine", "minimum_peak_ratio", "maximum_peak_ratio", "maximum_absolute_scaled_point_error", "minimum_predicted_peak", "maximum_condition_number")) != (0.75, 0.8, 0.5, 1.5, 0.1, 0.0025, 20.0)
        or tuple(map(float, gates["response_floor_physical"])) != (1e-9, 1e-9, 1e-7, 1e-7, 1e-4)
        or float(gates["tube_multiplier"]) != 2.0
        or tuple(map(float, gates["tube_caps_physical"])) != (0.003, 0.003, 0.01, 0.01, 1000.0)
        or float(gates["rank_relative_tolerance"]) != 1e-10
        or tuple(int(gates[key]) for key in ("required_rank", "required_response_pass_count", "required_branch_pass_count")) != (4, 256, 64)
        or tuple(cfg["forbidden_predictor_fields"]) != ("pair_id", "history_member", "prefix", "target_id", "regime_id", "source_result", "matched_future_baseline", "source_action", "source_coil_current", "source_wire_current", "hidden_wire_current", "future_measurement", "future_executed_action")
        or int(execution["new_raw_count"]) != 0
        or int(execution["plant_steps_executed"]) != 0
        or any(bool(execution[key]) for key in ("controller_executed", "ray_executed", "gotsc_executed", "tsc_executed"))
        or not bool(execution["source_raw_read_in_place"])
        or tuple(int(timing[key]) for key in ("normal_arrival_deadline_step", "normal_hold_through_step", "weak_arrival_deadline_step", "weak_hold_through_step")) != (25, 35, 27, 37)
        or bool(timing["arrival_deadline_expansion_allowed"])
        or bool(timing["evaluated_in_r7r1"])
        or not bool(scope["identification_development_only"])
        or any(bool(scope[key]) for key in ("probe_trajectories_allowed_in_expert_dataset", "transition_response_model_validated_fresh", "mpc_validated", "expert_data_allowed", "bc_dagger_or_rl_allowed"))
        or cfg["routes"] != {
            "source_fail": "CONTINUOUS_LAG_RESPONSE_MODEL_SOURCE_FAIL_NO_TSC",
            "model_fail": "CONTINUOUS_LAG_RESPONSE_MODEL_DEVELOPMENT_FAIL_BROADER_DECONFOUNDED_IDENTIFICATION_REQUIRED",
            "pass": "CONTINUOUS_LAG_RESPONSE_MODEL_DEVELOPMENT_PASS_FRESH_MULTIPULSE_VALIDATION_DESIGN_REQUIRED",
        }
    )
    if invalid:
        raise ValueError("R7R1 independent frozen contract changed")


def _grid(cfg: Mapping[str, Any]) -> list[tuple[int, int, float]]:
    model = cfg["model_contract"]
    return [(int(rank), int(degree), float(ridge)) for rank in model["pca_ranks"] for degree in model["temporal_legendre_degrees"] for ridge in model["ridges"]]


def _prep(items: Sequence[Mapping[str, Any]], rank: int, floor: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    x = np.asarray([row["descriptor"] for row in items])
    mean, scale = x.mean(axis=0), np.maximum(x.std(axis=0), floor)
    _, _, vt = np.linalg.svd((x - mean) / scale, full_matrices=False)
    if rank > len(vt):
        raise ValueError("R7R1 independent PCA unavailable")
    return mean, scale, vt[:rank]


def _context(row: Mapping[str, Any], prep: tuple[np.ndarray, np.ndarray, np.ndarray]) -> np.ndarray:
    mean, scale, components = prep
    return ((np.asarray(row["descriptor"]) - mean) / scale) @ components.T


def _legendre(lag: int, degree: int) -> np.ndarray:
    x = 2.0 * lag / 27.0 - 1.0
    values = [1.0, x]
    for order in range(2, degree + 1):
        values.append(((2 * order - 1) * x * values[-1] - (order - 1) * values[-2]) / order)
    return np.asarray(values[: degree + 1])


def _features(context: np.ndarray, lag: int, degree: int) -> np.ndarray:
    return np.kron(_legendre(lag, degree), np.r_[1.0, context])


def _fit(train: Sequence[Mapping[str, Any]], candidate: tuple[int, int, float], cfg: Mapping[str, Any]) -> dict[str, Any]:
    rank, degree, ridge = candidate
    floor = float(cfg["model_contract"]["standard_deviation_floor"])
    prep = _prep(train, rank, floor)
    heads = {}
    for sign in (-1, 1):
        for direction in range(4):
            x_rows, y_rows = [], []
            for row in train:
                if row["sign"] != sign or row["direction_index"] != direction:
                    continue
                context = _context(row, prep)
                for lag, response in enumerate(row["response"], start=1):
                    x_rows.append(_features(context, lag, degree)); y_rows.append(response[2:5])
            x, y = np.asarray(x_rows), np.asarray(y_rows)
            x_mean, x_scale = x.mean(axis=0), np.maximum(x.std(axis=0), floor)
            z = (x - x_mean) / x_scale
            y_mean = y.mean(axis=0)
            coef = np.linalg.lstsq(z.T @ z + ridge * np.eye(z.shape[1]), z.T @ (y - y_mean), rcond=None)[0]
            heads[(sign, direction)] = (x_mean, x_scale, y_mean, coef)
    return {"candidate": candidate, "prep": prep, "heads": heads}


def _predict(model: Mapping[str, Any], row: Mapping[str, Any], cfg: Mapping[str, Any]) -> np.ndarray:
    _, degree, _ = model["candidate"]
    context = _context(row, model["prep"])
    x_mean, x_scale, y_mean, coef = model["heads"][(row["sign"], row["direction_index"])]
    output = np.zeros_like(row["response"])
    for lag in range(1, len(output) + 1):
        output[lag - 1, 2:5] = y_mean + ((_features(context, lag, degree) - x_mean) / x_scale) @ coef
    scales = np.asarray(cfg["bank_contract"]["response_scales"])
    output[:, 0] = np.cumsum(output[:, 2]) * 0.01 * scales[2] / scales[0]
    output[:, 1] = np.cumsum(output[:, 3]) * 0.01 * scales[3] / scales[1]
    return output


def _cv(items: Sequence[Mapping[str, Any]], candidate: tuple[int, int, float], cfg: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for pair in sorted({row["pair_id"] for row in items}):
        train = [row for row in items if row["pair_id"] != pair]
        held = [row for row in items if row["pair_id"] == pair]
        fitted = _fit(train, candidate, cfg)
        rows.extend(frozen._metric(row, _predict(fitted, row, cfg), cfg) for row in held)
    return sorted(rows, key=lambda row: row["response_id"])


def _score(rows: Sequence[Mapping[str, Any]], candidate: tuple[int, int, float]) -> tuple[Any, ...]:
    relative = np.asarray([row["relative_l2_error"] for row in rows])
    return (sum(not row["passed"] for row in rows), max(row["maximum_absolute_scaled_point_error"] for row in rows), float(np.quantile(relative, 0.95, method="linear")), float(np.mean([row["mean_squared_scaled_error"] for row in rows])), *candidate)


def _select(items: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]) -> tuple[tuple[int, int, float], list[dict[str, Any]]]:
    scored = []
    for candidate in _grid(cfg):
        scored.append((candidate, _score(_cv(items, candidate, cfg), candidate)))
    selected = min(scored, key=lambda row: row[1])[0]
    return selected, [{"candidate": {"pca_rank": c[0], "temporal_degree": c[1], "ridge": c[2]}, "selection_score": list(score[:4])} for c, score in scored]


def _nested(items: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows, folds = [], []
    for pair in sorted({row["pair_id"] for row in items}):
        train = [row for row in items if row["pair_id"] != pair]
        held = [row for row in items if row["pair_id"] == pair]
        selected, scores = _select(train, cfg)
        fitted = _fit(train, selected, cfg)
        rows.extend(frozen._metric(row, _predict(fitted, row, cfg), cfg) for row in held)
        folds.append({"held_pair_id": pair, "training_pair_count": 3, "held_response_count": len(held), "selected_candidate": {"pca_rank": selected[0], "temporal_degree": selected[1], "ridge": selected[2]}, "inner_candidate_scores": scores})
    return sorted(rows, key=lambda row: row["response_id"]), folds


def audit(args: argparse.Namespace) -> dict[str, Any]:
    cfg = frozen._json(args.config.resolve()); _validate(cfg)
    if frozen._sha(args.design_document.resolve()) != cfg["design_document_sha256"]:
        raise ValueError("R7R1 independent design hash changed")
    sources = {"r2": frozen._read_source(args.source_r2_run.resolve(), cfg["source_contracts"]["r2"]), "r4": frozen._read_source(args.source_r4_run.resolve(), cfg["source_contracts"]["r4"]), "r6": frozen._read_source(args.source_r6_run.resolve(), cfg["source_contracts"]["r6"])}
    items, bank = frozen._items(sources, cfg)
    rows, folds = _nested(items, cfg)
    aggregate, geometry = frozen._aggregate(rows, cfg), frozen._geometry(rows, cfg)
    final_candidate, final_scores = _select(items, cfg)
    passed = bool(aggregate["passed"] and geometry["passed"])
    route = cfg["routes"]["pass" if passed else "model_fail"]
    primary = frozen._json(args.primary_output.resolve() / "stage4_2r3c3t13s24d1r14r7r1_detailed_v1.json")
    candidate_dict = {"pca_rank": final_candidate[0], "temporal_degree": final_candidate[1], "ridge": final_candidate[2]}
    agreement = bool(frozen._agrees(primary.get("bank"), bank) and frozen._agrees(primary.get("nested_outer_folds"), folds) and frozen._agrees(primary.get("outer_prediction_rows"), rows) and frozen._agrees(primary.get("aggregate"), aggregate) and frozen._agrees(primary.get("predicted_geometry"), geometry) and frozen._agrees(primary.get("final_candidate_development_only"), candidate_dict) and frozen._agrees(primary.get("final_candidate_scores"), final_scores) and primary.get("passed") == passed and primary.get("route") == route)
    result = {"schema_version": 1, "stage": STAGE, "passed": bool(passed and agreement), "route": route, "source_authentication_passed": True, "bank": bank, "nested_outer_folds": folds, "outer_prediction_rows": rows, "aggregate": aggregate, "predicted_geometry": geometry, "final_candidate_development_only": candidate_dict, "final_candidate_scores": final_scores, "primary_numerical_agreement": agreement, "classification": {"runtime_or_environment_error": False, "packaging_import_or_deployment_error": False, "raw_or_snapshot_corruption": False, "summary_or_reporting_error": not agreement, "model_design_failure": not passed}, "new_raw_count": 0, "tsc_executed": False}
    frozen._write(args.output.resolve(), result)
    print(json.dumps({key: result[key] for key in ("stage", "passed", "route", "primary_numerical_agreement", "aggregate")}, indent=2, sort_keys=True, allow_nan=False))
    if not agreement:
        raise ValueError("R7R1 independent result disagrees with primary")
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(); parser.add_argument("--config", type=Path, required=True); parser.add_argument("--design-document", type=Path, required=True); parser.add_argument("--source-r2-run", type=Path, required=True); parser.add_argument("--source-r4-run", type=Path, required=True); parser.add_argument("--source-r6-run", type=Path, required=True); parser.add_argument("--primary-output", type=Path, required=True); parser.add_argument("--output", type=Path, required=True); return parser


if __name__ == "__main__":
    audit(_parser().parse_args())
