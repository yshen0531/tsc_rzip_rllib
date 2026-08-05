"""Zero-TSC fixed-candidate short-horizon discriminator for R8R1."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from tsc_rzip_rllib.control import action_conditioned_history_response_model as model
from tsc_rzip_rllib.control import causal_response_model as metrics


STAGE = "Stage4.2R3c3T13S24D1R14R8R1"
RUN_NAME = "stage4_2r3c3t13s24d1r14r8r1_fixed_candidate_short_horizon_discriminator"
IDENTITY = "fixed_candidate_short_horizon_whole_pair_discriminator_v1"
PACKAGE_REVISION = "r42r3c3t13s24d1r14r8r1_fixed_candidate_short_horizon_v1"


def validate_config(cfg: Mapping[str, Any]) -> None:
    bank, candidate, horizon, gates, timing = (
        cfg["bank_contract"], cfg["fixed_candidate"], cfg["horizon_contract"],
        cfg["gates"], cfg["formal_timing_contract"],
    )
    invalid = (
        cfg.get("schema_version") != 1
        or cfg.get("stage") != STAGE
        or cfg.get("run_name") != RUN_NAME
        or cfg.get("campaign_identity") != IDENTITY
        or cfg.get("package_revision") != PACKAGE_REVISION
        or tuple(int(bank[key]) for key in (
            "response_count", "pair_count", "context_count", "descriptor_dimension",
        )) != (912, 12, 24, 142)
        or tuple(map(float, bank["response_scales"]))
        != (0.03, 0.03, 0.1, 0.1, 10000.0)
        or float(bank["dt_s"]) != 0.01
        or int(bank["direction_count"]) != 4
        or (int(candidate["pca_rank"]), float(candidate["bandwidth_multiplier"]), float(candidate["ridge"]))
        != (4, 2.0, 0.1)
        or tuple(map(int, horizon["evaluated_relative_lags"])) != (4, 6, 8, 10, 12)
        or tuple(map(int, horizon["diagnostic_only_relative_lags"])) != (4, 6)
        or tuple(map(int, horizon["controller_useful_relative_lags"])) != (8, 10, 12)
        or tuple(map(int, horizon["selection_order"])) != (12, 10, 8)
        or bool(horizon["origin_shift_allowed"])
        or int(horizon["minimum_response_length"]) != 12
        or tuple(float(gates[key]) for key in (
            "maximum_relative_l2_error", "minimum_response_cosine",
            "minimum_peak_ratio", "maximum_peak_ratio",
            "maximum_absolute_scaled_point_error", "tube_multiplier",
            "minimum_predicted_peak", "minimum_actual_peak",
            "maximum_condition_number",
        )) != (0.75, 0.8, 0.5, 1.5, 0.1, 2.0, 0.0025, 0.0025, 20.0)
        or tuple(map(float, gates["response_floor_physical"]))
        != (1e-9, 1e-9, 1e-7, 1e-7, 1e-4)
        or tuple(map(float, gates["tube_caps_physical"]))
        != (0.003, 0.003, 0.01, 0.01, 1000.0)
        or tuple(int(gates[key]) for key in (
            "required_response_pass_count", "required_signal_pass_count",
            "required_canonical_branch_count", "required_operational_branch_count",
        )) != (912, 912, 192, 192)
        or tuple(int(timing[key]) for key in (
            "normal_arrival_deadline_step", "normal_hold_through_step",
            "weak_arrival_deadline_step", "weak_hold_through_step",
        )) != (25, 35, 27, 37)
        or bool(timing["arrival_deadline_expansion_allowed"])
        or int(cfg["new_tsc_rollouts"]) != 0
        or not bool(cfg["identification_only"])
        or bool(cfg["probe_trajectories_allowed_in_expert_dataset"])
        or bool(cfg["mpc_validated"])
        or bool(cfg["bc_dagger_or_rl_allowed"])
    )
    if invalid:
        raise ValueError("R8R1 frozen contract changed")


def candidate_tuple(cfg: Mapping[str, Any]) -> tuple[int, float, float]:
    value = cfg["fixed_candidate"]
    return int(value["pca_rank"]), float(value["bandwidth_multiplier"]), float(value["ridge"])


def model_config(cfg: Mapping[str, Any], r8_cfg: Mapping[str, Any]) -> dict[str, Any]:
    output = copy.deepcopy(r8_cfg)
    output["gates"].update(copy.deepcopy(cfg["gates"]))
    output["model_contract"].update(copy.deepcopy(cfg["model_contract"]))
    output["bank_contract"]["response_scales"] = list(cfg["bank_contract"]["response_scales"])
    output["bank_contract"]["dt_s"] = float(cfg["bank_contract"]["dt_s"])
    output["bank_contract"]["direction_count"] = int(cfg["bank_contract"]["direction_count"])
    return output


def truncate_item(item: Mapping[str, Any], horizon: int) -> dict[str, Any]:
    response = np.asarray(item["response"], dtype=float)
    if response.ndim != 2 or response.shape[1] != 5 or len(response) < horizon:
        raise ValueError("R8R1 response shorter than frozen common horizon")
    output = dict(item)
    output["descriptor"] = np.asarray(item["descriptor"], dtype=float).tolist()
    output["response"] = response[:horizon].tolist()
    return output


def _candidate(cfg: Mapping[str, Any]) -> model.Candidate:
    rank, bandwidth, ridge = candidate_tuple(cfg)
    return model.Candidate(rank, bandwidth, ridge)


def outer_prediction_rows(
    items: Sequence[Mapping[str, Any]],
    cfg: Mapping[str, Any],
    r8_cfg: Mapping[str, Any],
) -> tuple[dict[int, list[dict[str, Any]]], list[dict[str, Any]]]:
    """Fit the fixed candidate once per outer pair and reuse common prefixes."""
    mcfg = model_config(cfg, r8_cfg)
    horizons = tuple(map(int, cfg["horizon_contract"]["evaluated_relative_lags"]))
    maximum = max(horizons)
    pairs = sorted({str(item["pair_id"]) for item in items})
    if len(items) != 912 or len(pairs) != 12:
        raise ValueError("R8R1 training bank coverage changed")
    rows = {horizon: [] for horizon in horizons}
    folds = []
    for pair in pairs:
        train = [truncate_item(item, maximum) for item in items if str(item["pair_id"]) != pair]
        held = [truncate_item(item, maximum) for item in items if str(item["pair_id"]) == pair]
        fitted = model.fit_model(train, _candidate(cfg), mcfg)
        for item in held:
            prediction = model.predict_item(fitted, item, mcfg)
            for horizon in horizons:
                current = truncate_item(item, horizon)
                rows[horizon].append(model.prediction_row(current, prediction[:horizon], mcfg))
        folds.append(
            {
                "held_pair_id": pair,
                "training_pair_count": 11,
                "held_response_count": len(held),
                "fixed_candidate": dict(cfg["fixed_candidate"]),
            }
        )
    for horizon in horizons:
        rows[horizon].sort(key=lambda row: str(row["response_id"]))
        if len(rows[horizon]) != 912:
            raise ValueError("R8R1 outer response coverage changed")
    return rows, folds


def actual_geometry_rows(
    items: Sequence[Mapping[str, Any]], horizon: int
) -> list[dict[str, Any]]:
    output = []
    for source in items:
        item = truncate_item(source, horizon)
        output.append(
            {
                "response_id": item["response_id"],
                "context_id": item["context_id"],
                "pair_id": item["pair_id"],
                "history_member": item["history_member"],
                "issue_task_step": item["issue_task_step"],
                "sign": item["sign"],
                "direction_index": item["direction_index"],
                "source_stage": item["source_stage"],
                "action_scale": item["action_scale"],
                "geometry_roles": list(item["geometry_roles"]),
                "predicted_response": item["response"],
            }
        )
    return sorted(output, key=lambda row: str(row["response_id"]))


def evaluate_horizon(
    items: Sequence[Mapping[str, Any]],
    prediction_rows: Sequence[Mapping[str, Any]],
    horizon: int,
    cfg: Mapping[str, Any],
    r8_cfg: Mapping[str, Any],
) -> dict[str, Any]:
    mcfg = model_config(cfg, r8_cfg)
    aggregate = metrics.aggregate(prediction_rows, mcfg)
    predicted = model.geometry(prediction_rows, mcfg)
    actual = model.geometry(actual_geometry_rows(items, horizon), mcfg)
    actual["interpretation"] = "actual_truncated_response_geometry"
    return {
        "relative_lag_horizon": horizon,
        "elapsed_horizon_ms": 10 * horizon,
        "diagnostic_only": horizon in set(map(int, cfg["horizon_contract"]["diagnostic_only_relative_lags"])),
        "aggregate": aggregate,
        "predicted_geometry": predicted,
        "actual_geometry": actual,
        "passed": bool(aggregate["passed"] and predicted["passed"] and actual["passed"]),
    }


def select_horizon(results: Mapping[int, Mapping[str, Any]], cfg: Mapping[str, Any]) -> int | None:
    for horizon in map(int, cfg["horizon_contract"]["selection_order"]):
        if bool(results[horizon]["passed"]):
            return horizon
    return None


def fit_all_data_artifact(
    items: Sequence[Mapping[str, Any]],
    selected_horizon: int,
    cfg: Mapping[str, Any],
    r8_cfg: Mapping[str, Any],
) -> dict[str, Any]:
    mcfg = model_config(cfg, r8_cfg)
    truncated = [truncate_item(item, selected_horizon) for item in items]
    fitted = model.fit_model(truncated, _candidate(cfg), mcfg)
    return {
        "schema_version": 1,
        "stage": STAGE,
        "campaign_identity": IDENTITY,
        "selected_relative_lag_horizon": selected_horizon,
        "elapsed_horizon_ms": 10 * selected_horizon,
        "fixed_candidate": dict(cfg["fixed_candidate"]),
        "validation_claim": False,
        "model": model.serializable_model(fitted),
    }


def route_for(selected_horizon: int | None, cfg: Mapping[str, Any]) -> str:
    return str(cfg["routes"]["pass" if selected_horizon is not None else "fail"])


def summary_geometry(value: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "response_count": value["response_count"],
        "signal_pass_count": value["signal_pass_count"],
        "minimum_predicted_peak": value["minimum_predicted_peak"],
        "canonical": {key: row for key, row in value["canonical"].items() if key != "rows"},
        "operational": {key: row for key, row in value["operational"].items() if key != "rows"},
        "passed": value["passed"],
    }


def compact_horizon(value: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "relative_lag_horizon": value["relative_lag_horizon"],
        "elapsed_horizon_ms": value["elapsed_horizon_ms"],
        "diagnostic_only": value["diagnostic_only"],
        "aggregate": value["aggregate"],
        "predicted_geometry": summary_geometry(value["predicted_geometry"]),
        "actual_geometry": summary_geometry(value["actual_geometry"]),
        "passed": value["passed"],
    }


def self_test(config_path: Path) -> dict[str, Any]:
    import json

    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    validate_config(cfg)
    fake = {horizon: {"passed": horizon == 10} for horizon in (4, 6, 8, 10, 12)}
    if select_horizon(fake, cfg) != 10:
        raise AssertionError("R8R1 frozen horizon selection changed")
    fake[12]["passed"] = True
    if select_horizon(fake, cfg) != 12:
        raise AssertionError("R8R1 largest passing horizon rule changed")
    return {"stage": STAGE, "passed": True, "new_tsc_rollouts": 0}
