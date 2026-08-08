#!/usr/bin/env python3
"""Structurally independent zero-TSC audit for frozen R8R24."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
from scipy.spatial import cKDTree

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r8r22_independent_forensics as ind22,
    stage4_2r3c3t13s24d1r14r8r23_independent_forensics as ind23,
)


STAGE = "Stage4.2R3c3T13S24D1R14R8R24"
IDENTITY = "causal_local_residual_tube_receding_horizon_preflight_v1"
RUN_NAME = "stage4_2r3c3t13s24d1r14r8r24_causal_local_residual_tube_receding_horizon_preflight"
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
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _source_config(cfg: Mapping[str, Any]) -> Mapping[str, Any]:
    return _read((_root() / str(cfg["source_r8r23_config"])).resolve())


def _validate_config(cfg: Mapping[str, Any]) -> None:
    root = _root().resolve()
    design = (root / str(cfg["design_document"])).resolve()
    source = (root / str(cfg["source_r8r23_config"])).resolve()
    bank, model = cfg["bank_contract"], cfg["model_contract"]
    local, action = cfg["local_tube_contract"], cfg["action_contract"]
    gates, formal, planning = (
        cfg["model_gates"], cfg["formal_contract"], cfg["planning_gate"]
    )
    if (
        int(cfg.get("schema_version", -1)) != 1
        or cfg.get("stage") != STAGE
        or cfg.get("identity") != IDENTITY
        or cfg.get("run_name") != RUN_NAME
        or not design.is_relative_to(root)
        or not source.is_relative_to(root)
        or _sha(design) != str(cfg["design_document_sha256"])
        or _sha(source) != str(cfg["source_r8r23_config_sha256"])
        or tuple(map(int, bank["decision_task_steps"])) != DECISIONS
        or tuple(map(int, bank["maximum_forecast_samples_by_interval"])) != (4, 4, 4, 15)
        or tuple(map(int, (bank["physical_pair_count"], bank["history_context_count"],
                           bank["trajectory_count_per_context"], bank["total_trajectory_count"],
                           bank["causal_feature_dimension"], bank["expanded_feature_dimension"])))
        != (8, 16, 27, 432, 42, 133)
        or tuple(map(float, bank["visible_scales"])) != (0.03, 0.03, 10000.0)
        or float(model["ridge_penalty"]) != 1e-4
        or tuple(map(int, (model["outer_fold_count"], model["nested_fold_count_per_outer"]))) != (8, 7)
        or float(model["support_threshold_multiplier"]) != 1.5
        or model.get("whole_pair_exclusion") is not True
        or model.get("masked_final_horizon_outputs") is not True
        or model.get("feature_selection_allowed") is not False
        or model.get("hyperparameter_search_allowed") is not False
        or model.get("innovation_enabled") is not False
        or int(local["distance_feature_dimension"]) != 133
        or local.get("distance_metric") != "ordinary_euclidean"
        or local.get("same_interval_required") is not True
        or local.get("same_lead_sample_required") is not True
        or int(local["neighbor_count"]) != 32
        or local.get("include_all_kth_distance_ties") is not True
        or float(local["reserve_multiplier"]) != 1.25
        or tuple(map(float, local["physical_point_error_floors"])) != (0.015, 0.015, 3000.0, 0.05, 0.05)
        or local.get("tube_clipping_allowed") is not False
        or tuple(map(float, (action["maximum_incremental_normalized_action_linf"],
                             action["maximum_total_normalized_action_abs"],
                             action["maximum_current_utilization"],
                             action["minimum_desired_applied_current_cosine"],
                             action["maximum_relative_off_basis_residual"]))) != (0.25, 1.0, 0.55, 0.98, 0.10)
        or int(action["alphabet_size"]) != 11
        or int(action["maximum_unfiltered_sequence_count"]) != 14641
        or action.get("require_exact_card15_issue") is not True
        or action.get("require_exact_card15_refresh") is not True
        or action.get("safe_stop_before_failed_advance") is not True
        or tuple(map(float, (gates["maximum_R_point_error_m"], gates["maximum_Z_point_error_m"],
                             gates["maximum_Ip_point_error_A"], gates["maximum_vR_point_error_m_per_s"],
                             gates["maximum_vZ_point_error_m_per_s"]))) != (0.015, 0.015, 3000.0, 0.05, 0.05)
        or tuple(map(float, (gates["maximum_reserved_R_tube_half_width_m"],
                             gates["maximum_reserved_Z_tube_half_width_m"],
                             gates["maximum_reserved_Ip_tube_half_width_A"],
                             gates["maximum_reserved_vR_tube_half_width_m_per_s"],
                             gates["maximum_reserved_vZ_tube_half_width_m_per_s"]))) != (0.025, 0.025, 5000.0, 0.08, 0.08)
        or tuple(map(float, (gates["required_reserved_tube_containment_rate"],
                             gates["required_support_rate"]))) != (1.0, 1.0)
        or tuple(map(int, (gates["maximum_finite_exclusion_count"],
                           gates["maximum_forbidden_input_count"]))) != (0, 0)
        or tuple(map(int, (formal["normal_arrival_deadline_step"], formal["normal_hold_through_step"],
                           formal["weak_arrival_deadline_step"], formal["weak_hold_through_step"],
                           formal["arrival_streak_steps"]))) != (25, 35, 27, 37, 3)
        or tuple(map(float, (formal["position_tolerance_m"], formal["speed_tolerance_m_per_s"],
                             formal["ip_tolerance_A"]))) != (0.03, 0.1, 10000.0)
        or formal.get("arrival_deadline_expansion_allowed") is not False
        or tuple(map(int, (planning["required_safe_complete_plan_count"],
                           planning["minimum_predicted_repaired_failed_baseline_count"],
                           planning["maximum_predicted_regressed_baseline_pass_count"],
                           planning["minimum_predicted_oracle_count"]))) != (16, 1, 0, 7)
        or float(planning["primary_independent_absolute_tolerance"]) != 1e-12
        or cfg.get("routes") != {
            "evidence_fail": "R8R24_INTEGRITY_FAIL_STOP",
            "model_fail": "CAUSAL_LOCAL_RESIDUAL_TUBE_PREFLIGHT_INSUFFICIENT_REDESIGN_REQUIRED",
            "planning_fail": "CAUSAL_LOCAL_RESIDUAL_TUBE_AUTHORITY_INSUFFICIENT_CONTROLLER_SENTINEL_NOT_AUTHORIZED",
            "pass": "CAUSAL_LOCAL_RESIDUAL_TUBE_PREFLIGHT_PASS_FRESH_CONTROLLER_SENTINEL_DESIGN_REQUIRED",
        }
        or cfg.get("zero_new_tsc") is not True
        or cfg.get("expert_data_allowed") is not False
        or cfg.get("gate_a_qualified") is not False
    ):
        raise ValueError("independent R8R24 frozen contract changed")


def _source_stage(args: argparse.Namespace, cfg: Mapping[str, Any]) -> Path:
    return args.r8r23_run.expanduser().resolve() / str(
        cfg["source_r8r23"]["stage_directory"]
    )


def _authenticate(
    args: argparse.Namespace, cfg: Mapping[str, Any]
) -> dict[str, Any]:
    stage = _source_stage(args, cfg)
    expected = cfg["source_r8r23"]
    paths = {
        "primary_detailed": stage / "analysis/primary_detailed.json",
        "primary_summary": stage / "analysis/primary_summary.json",
        "independent": stage / "analysis/independent.json",
        "final_report": stage / "analysis/final_report.json",
        "model_evidence": stage / "model/outer_fold_models.json",
        "stage_manifest": stage / "stage_manifest.json",
        "stage_state": stage / "stage_state.json",
    }
    hashes = {name: _sha(path) for name, path in paths.items()}
    if any(hashes[name] != str(expected[f"{name}_sha256"]) for name in paths):
        raise ValueError("independent R8R24 R8R23 hash changed")
    primary = _read(paths["primary_detailed"])
    summary = _read(paths["primary_summary"])
    independent = _read(paths["independent"])
    final = _read(paths["final_report"])
    state = _read(paths["stage_state"])
    manifest = _read(paths["stage_manifest"])
    if (
        stage.parent.name != str(expected["run_name"])
        or final.get("route") != str(expected["required_route"])
        or final.get("primary_independent_agreement") is not True
        or independent.get("passed") is not True
        or state.get("finished") is not True
        or state.get("real_tsc_executed") is not False
        or int(state.get("plant_step_count", -1)) != 0
        or int(state.get("new_raw_count", -1)) != 0
        or manifest.get("zero_new_tsc") is not True
        or primary["bank_evidence"]["feature_digest"] != str(expected["feature_digest"])
        or primary["bank_evidence"]["target_digest"] != str(expected["target_digest"])
        or int(summary["trajectory_count"]) != int(expected["trajectory_count"])
    ):
        raise ValueError("independent R8R24 R8R23 outcome changed")
    transitive = ind23._authenticate(args, _source_config(cfg))
    if transitive.get("passed") is not True:
        raise ValueError("independent R8R24 transitive authentication failed")
    return {"hashes": hashes, "transitive": transitive, "passed": True}


def _calibration(
    bank: Sequence[Mapping[str, Any]], training: Sequence[str], ridge: float
) -> tuple[list[list[dict[str, Any]]], list[dict[str, Any]]]:
    pairs = tuple(sorted(map(str, training)))
    grouped: list[list[list[tuple[np.ndarray, np.ndarray]]]] = [
        [[] for _ in range(count)] for count in (4, 4, 4, 15)
    ]
    evidence = []
    for held_pair in pairs:
        fit_pairs = tuple(pair for pair in pairs if pair != held_pair)
        model = ind23._fit(bank, fit_pairs, ridge)
        held = [row for row in bank if str(row["pair_id"]) == held_pair]
        predictions = ind23._predictions(model, held)
        for trajectory in held:
            identifier = str(trajectory["trajectory_id"])
            for interval, row in enumerate(trajectory["intervals"]):
                residual = np.abs(
                    np.asarray(row["targets"], dtype=float)
                    - np.asarray(predictions[identifier][interval], dtype=float)
                )
                for offset, value in enumerate(residual):
                    grouped[interval][offset].append(
                        (np.asarray(row["expanded"], dtype=float), value)
                    )
        evidence.append(
            {
                "held_pair": held_pair,
                "training_pairs": list(fit_pairs),
                "model_digest": _digest(ind23._serial(model)),
            }
        )
    output = []
    for interval in grouped:
        offsets = []
        for values in interval:
            features = np.asarray([row[0] for row in values], dtype=float)
            residuals = np.asarray([row[1] for row in values], dtype=float)
            if len(features) < 32 or residuals.shape != (len(features), 5):
                raise ValueError("independent R8R24 calibration invalid")
            offsets.append(
                {"features": features, "residuals": residuals, "tree": cKDTree(features)}
            )
        output.append(offsets)
    return output, evidence


def _neighbors(record: Mapping[str, Any], query: np.ndarray, k: int) -> np.ndarray:
    features = np.asarray(record["features"], dtype=float)
    distance, _ = record["tree"].query(query, k=k, eps=0.0, workers=1)
    kth = float(np.asarray(distance).reshape(-1)[-1])
    candidates = set(
        map(
            int,
            record["tree"].query_ball_point(
                query, r=kth + max(1e-15, abs(kth) * 1e-14)
            ),
        )
    )
    exact = np.linalg.norm(features - query[None, :], axis=1)
    exact_kth = float(np.partition(exact, k - 1)[k - 1])
    selected = np.flatnonzero(
        exact <= exact_kth + max(1e-15, abs(exact_kth) * 1e-14)
    )
    if len(selected) < k or not set(map(int, selected)).issubset(candidates):
        raise ValueError("independent R8R24 neighbor tie invalid")
    return selected


def _tube_query(
    calibration: Sequence[Sequence[Mapping[str, Any]]],
    row: Mapping[str, Any],
    cfg: Mapping[str, Any],
) -> tuple[np.ndarray, list[int]]:
    interval, count = int(row["interval"]), len(row["targets"])
    query = np.asarray(row["expanded"], dtype=float).reshape(133)
    contract = cfg["local_tube_contract"]
    k, reserve = int(contract["neighbor_count"]), float(contract["reserve_multiplier"])
    floor = np.asarray(contract["physical_point_error_floors"], dtype=float) / FACTORS
    output, counts = [], []
    for offset in range(count):
        record = calibration[interval][offset]
        selected = _neighbors(record, query, k)
        residual = np.max(np.asarray(record["residuals"])[selected], axis=0)
        output.append(np.maximum(reserve * residual, floor))
        counts.append(len(selected))
    value = np.asarray(output, dtype=float)
    if value.shape != (count, 5) or not np.all(np.isfinite(value)):
        raise ValueError("independent R8R24 tube invalid")
    return value, counts


def _tubes(
    calibration: Sequence[Sequence[Mapping[str, Any]]],
    rows: Sequence[Mapping[str, Any]],
    cfg: Mapping[str, Any],
) -> tuple[dict[str, list[np.ndarray]], dict[str, Any]]:
    output, serial, counts = {}, [], []
    for trajectory in rows:
        identifier = str(trajectory["trajectory_id"])
        current = []
        for row in trajectory["intervals"]:
            tube, used = _tube_query(calibration, row, cfg)
            current.append(tube)
            counts.extend(used)
        output[identifier] = current
        serial.append(
            {"trajectory_id": identifier, "tubes": [value.tolist() for value in current]}
        )
    return output, {
        "tube_digest": _digest(serial),
        "minimum_neighbor_count_after_ties": min(counts),
        "maximum_neighbor_count_after_ties": max(counts),
        "query_count": len(counts),
    }


def _outer(bank: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]) -> list[dict[str, Any]]:
    pairs = tuple(sorted({str(row["pair_id"]) for row in bank}))
    ridge = float(cfg["model_contract"]["ridge_penalty"])
    folds = []
    for held_pair in pairs:
        training = tuple(pair for pair in pairs if pair != held_pair)
        model = ind23._fit(bank, training, ridge)
        calibration, nested = _calibration(bank, training, ridge)
        held = [row for row in bank if str(row["pair_id"]) == held_pair]
        tubes, tube_evidence = _tubes(calibration, held, cfg)
        support = ind23._support(
            bank,
            training,
            held_pair,
            float(cfg["model_contract"]["support_threshold_multiplier"]),
        )
        allowed = set(training)
        training_features = [
            np.asarray(
                [row["intervals"][interval]["feature"] for row in bank
                 if str(row["pair_id"]) in allowed],
                dtype=float,
            )
            for interval in range(4)
        ]
        folds.append(
            {
                "held_pair": held_pair,
                "training_pairs": list(training),
                "model": model,
                "model_digest": _digest(ind23._serial(model)),
                "calibration": calibration,
                "nested_fit_evidence": nested,
                "local_tube_evidence": tube_evidence,
                "held": held,
                "predictions": ind23._predictions(model, held),
                "tubes": tubes,
                "support": support,
                "training_features": training_features,
            }
        )
    return folds


def _evaluate(folds: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]) -> dict[str, Any]:
    maxima, tube_maxima = np.zeros(5), np.zeros(5)
    contained = total = finite = support_pass = support_total = 0
    fold_rows = []
    for fold in folds:
        fold_max, fold_tube = np.zeros(5), np.zeros(5)
        fold_contained = fold_total = 0
        for trajectory in fold["held"]:
            identifier = str(trajectory["trajectory_id"])
            for interval, row in enumerate(trajectory["intervals"]):
                actual = np.asarray(row["targets"], dtype=float)
                prediction = np.asarray(fold["predictions"][identifier][interval])
                tube = np.asarray(fold["tubes"][identifier][interval])
                residual = np.abs(actual - prediction)
                fold_max = np.maximum(
                    fold_max, np.max(residual * FACTORS[None, :], axis=0)
                )
                fold_tube = np.maximum(
                    fold_tube, np.max(tube * FACTORS[None, :], axis=0)
                )
                inside = residual <= tube + 1e-15
                fold_contained += int(np.count_nonzero(inside))
                fold_total += int(inside.size)
                finite += int(
                    not np.all(np.isfinite(actual))
                    or not np.all(np.isfinite(prediction))
                    or not np.all(np.isfinite(tube))
                )
        maxima, tube_maxima = np.maximum(maxima, fold_max), np.maximum(tube_maxima, fold_tube)
        contained, total = contained + fold_contained, total + fold_total
        support_pass += sum(map(int, fold["support"]["pass_counts"]))
        support_total += sum(map(int, fold["support"]["row_counts"]))
        fold_rows.append(
            {
                "pair_id": fold["held_pair"],
                "maximum_absolute_physical_error": fold_max.tolist(),
                "maximum_reserved_physical_tube_half_width": fold_tube.tolist(),
                "reserved_tube_contained_component_count": fold_contained,
                "reserved_tube_component_count": fold_total,
                "reserved_tube_containment_rate": fold_contained / fold_total,
                "support": fold["support"],
                "local_tube_evidence": fold["local_tube_evidence"],
            }
        )
    gate = cfg["model_gates"]
    point = bool(
        maxima[0] <= float(gate["maximum_R_point_error_m"]) + 1e-15
        and maxima[1] <= float(gate["maximum_Z_point_error_m"]) + 1e-15
        and maxima[2] <= float(gate["maximum_Ip_point_error_A"]) + 1e-12
        and maxima[3] <= float(gate["maximum_vR_point_error_m_per_s"]) + 1e-15
        and maxima[4] <= float(gate["maximum_vZ_point_error_m_per_s"]) + 1e-15
    )
    cap = bool(
        tube_maxima[0] <= float(gate["maximum_reserved_R_tube_half_width_m"]) + 1e-15
        and tube_maxima[1] <= float(gate["maximum_reserved_Z_tube_half_width_m"]) + 1e-15
        and tube_maxima[2] <= float(gate["maximum_reserved_Ip_tube_half_width_A"]) + 1e-12
        and tube_maxima[3] <= float(gate["maximum_reserved_vR_tube_half_width_m_per_s"]) + 1e-15
        and tube_maxima[4] <= float(gate["maximum_reserved_vZ_tube_half_width_m_per_s"]) + 1e-15
    )
    containment, support_rate = contained / total, support_pass / support_total
    containment_passed = bool(
        containment
        >= float(gate["required_reserved_tube_containment_rate"]) - 1e-15
    )
    support_passed = bool(
        support_rate >= float(gate["required_support_rate"]) - 1e-15
    )
    passed = bool(
        point
        and cap
        and containment_passed
        and support_passed
        and finite <= int(gate["maximum_finite_exclusion_count"])
    )
    return {
        "selected_predictor": "cold",
        "maximum_absolute_physical_error": maxima.tolist(),
        "maximum_reserved_physical_tube_half_width": tube_maxima.tolist(),
        "reserved_tube_contained_component_count": contained,
        "reserved_tube_component_count": total,
        "reserved_tube_containment_rate": containment,
        "support_pass_count": support_pass,
        "support_row_count": support_total,
        "support_rate": support_rate,
        "finite_exclusion_count": finite,
        "forbidden_input_count": 0,
        "point_error_gate_passed": point,
        "tube_cap_gate_passed": cap,
        "reserved_tube_containment_gate_passed": containment_passed,
        "support_gate_passed": support_passed,
        "fold_rows": fold_rows,
        "passed": passed,
    }


def _planning_metadata(
    args: argparse.Namespace, source_cfg: Mapping[str, Any]
) -> tuple[dict[tuple[str, str], dict[str, Any]], Mapping[str, Any], Path]:
    source_args, r22_cfg = ind23._source_args(args, source_cfg)
    source_ctx = ind22._source_context(source_args, r22_cfg)
    baseline_specs, baseline_results = ind22._source_baselines(
        source_args, r22_cfg, source_ctx
    )
    r22_specs = ind22._expected_specs(source_args, r22_cfg, source_ctx)
    evaluators, _ = ind22.r8r7.r8.d1r11._formal_callback(
        source_ctx.r8_ctx.d1r11_ctx, baseline_specs
    )
    source_stage = ind22._stage(source_args)
    execution = ind22._execution_context(source_ctx, source_stage)
    lattice = execution.d1r11_ctx.base_ctx.base_ctx.cfg["lattice_probe"]
    baseline_by_context = {
        (str(spec["pair_id"]), str(spec["history_member"])):
        (spec, baseline_results[str(spec["experiment_id"])])
        for spec in baseline_specs
    }
    first_spec = {}
    for spec in r22_specs:
        first_spec.setdefault((str(spec["pair_id"]), str(spec["history_member"])), spec)
    metadata = {}
    for key, spec in first_spec.items():
        payload = _read(source_stage / "variants" / f"payload_{spec['experiment_id']}.json")
        actuator = ind22.mpc.actuator_from_payload(payload, lattice)
        limits = np.maximum(
            np.abs(np.asarray(actuator.minimum_current_a_tsc, dtype=float)),
            np.abs(np.asarray(actuator.maximum_current_a_tsc, dtype=float)),
        )
        base_spec, base_result = baseline_by_context[key]
        metadata[key] = {
            "pair_id": key[0],
            "history_member": key[1],
            "target": np.asarray(evaluators[str(base_spec["experiment_id"])].target),
            "limits": limits,
            "actuator": actuator,
            "lattice": lattice,
            "basis": ind22._fixed_basis(base_result),
            "baseline_result": base_result,
            "horizon": int(base_spec["horizon_steps"]),
            "slew_scale": float(base_spec["slew_scale"]),
        }
    return metadata, r22_cfg, source_stage


def _levels(r22_cfg: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = [{"index": 0, "level_id": "q0", "q": [0.0, 0.0], "coordinate": [0.0] * 4}]
    for index, candidate in enumerate(ind22._candidate_definitions(r22_cfg), start=1):
        amplitude, weight = float(candidate["amplitude"]), float(candidate["mixing_weight"])
        rows.append({"index": index, "level_id": candidate["candidate_id"],
                     "q": [amplitude * weight, amplitude * (1.0 - weight)],
                     "coordinate": candidate["requested_coordinate"]})
    if len(rows) != 11:
        raise ValueError("independent R8R24 action alphabet changed")
    return rows


def _safe_issue(cfg: Mapping[str, Any], r22_cfg: Mapping[str, Any], meta: Mapping[str, Any],
                current: np.ndarray, level: Mapping[str, Any], task_step: int) -> dict[str, Any]:
    actuator = meta["actuator"]
    if int(level["index"]) == 0:
        applied = actuator.apply(current, np.zeros(14, dtype=float))
        minimum, maximum = np.asarray(actuator.minimum_current_a_tsc), np.asarray(actuator.maximum_current_a_tsc)
        center, half = 0.5 * (minimum + maximum), 0.5 * (maximum - minimum)
        utilization = float(np.max(np.abs((np.asarray(applied.nominal_readback_current_a_tsc) - center) / half)))
        return {"passed": bool(not any(applied.action_saturated)
                                and not any(applied.current_limit_clipped)
                                and utilization <= float(cfg["action_contract"]["maximum_current_utilization"]) + 1e-12),
                "nominal_issue_readback_current_a_tsc": list(applied.nominal_readback_current_a_tsc),
                "predicted_current_utilization": utilization}
    contract = copy.deepcopy(cfg["action_contract"])
    contract["dynamic_exact_search_radius"] = int(r22_cfg["schedule_contract"]["dynamic_exact_search_radius"])
    return ind22._coordinate_issue(task_step=task_step, currents=current,
                                   basis=np.asarray(meta["basis"]), coordinate=level["coordinate"],
                                   candidate_id=str(level["level_id"]), actuator=actuator,
                                   lattice=meta["lattice"], contract=contract)


def _feature(states: np.ndarray, current: np.ndarray, previous: np.ndarray,
             previous_q: np.ndarray, limits: np.ndarray) -> np.ndarray:
    value = np.r_[states[-4:, :3].ravel(), current / limits,
                  (current - previous) / limits, previous_q / 1.5]
    if value.shape != (42,) or not np.all(np.isfinite(value)):
        raise ValueError("independent R8R24 planning feature invalid")
    return value


def _supported(fold: Mapping[str, Any], feature: np.ndarray, interval: int) -> bool:
    distance = float(np.min(np.linalg.norm(np.asarray(fold["training_features"][interval]) - feature[None], axis=1)))
    return distance <= float(fold["support"]["thresholds"][interval]) + 1e-15


def _formal(states: np.ndarray, tubes: np.ndarray, deadline: int, endpoint: int,
            cfg: Mapping[str, Any]) -> tuple[bool, float, float]:
    formal = cfg["formal_contract"]
    robust = np.abs(states) * FACTORS[None] + tubes * FACTORS[None]
    violation = np.c_[robust[:, 0] / float(formal["position_tolerance_m"]),
                      robust[:, 1] / float(formal["position_tolerance_m"]),
                      robust[:, 2] / float(formal["ip_tolerance_A"]),
                      robust[:, 3] / float(formal["speed_tolerance_m_per_s"]),
                      robust[:, 4] / float(formal["speed_tolerance_m_per_s"])] - 1.0
    per_step = np.max(violation, axis=1)
    streak = int(formal["arrival_streak_steps"])
    worst = min((float(np.max(per_step[start:endpoint + 1]))
                 for start in range(0, max(0, deadline - streak + 2))), default=math.inf)
    return worst <= 1e-15, max(0.0, worst), float(np.sum(states[10:endpoint + 1, :3] ** 2))


def _plan_one(cfg: Mapping[str, Any], r22_cfg: Mapping[str, Any], meta: Mapping[str, Any],
              fold: Mapping[str, Any]) -> dict[str, Any]:
    levels, model = _levels(r22_cfg), fold["model"]
    states = ind23._states(meta["baseline_result"], meta["target"])
    prefix_states, prefix_tubes = states[:11], np.zeros_like(states[:11])
    current0 = np.asarray(meta["baseline_result"]["trajectory"][10]["currents_a_tsc"], dtype=float)
    weak = math.isclose(float(meta["slew_scale"]), 0.9, abs_tol=1e-15)
    deadline = int(cfg["formal_contract"]["weak_arrival_deadline_step" if weak else "normal_arrival_deadline_step"])
    endpoint = int(cfg["formal_contract"]["weak_hold_through_step" if weak else "normal_hold_through_step"])
    best_key, best = None, None
    complete = safe_nodes = unsupported = 0

    def visit(interval: int, current_states: np.ndarray, current_tubes: np.ndarray,
              current: np.ndarray, previous: np.ndarray, previous_q: np.ndarray,
              indices: tuple[int, ...], movement: float, maximum_current: float) -> None:
        nonlocal best_key, best, complete, safe_nodes, unsupported
        if interval == 4:
            complete += 1
            passed, violation, integrated = _formal(current_states, current_tubes, deadline, endpoint, cfg)
            key = (not passed, violation, integrated, movement, maximum_current, indices)
            if best_key is None or key < best_key:
                best_key = key
                best = {"alphabet_indices": list(indices),
                        "level_ids": [levels[index]["level_id"] for index in indices],
                        "robust_formal_pass": passed,
                        "worst_formal_margin_violation": violation,
                        "integrated_normalized_error": integrated,
                        "cumulative_normalized_action_movement": movement,
                        "maximum_predicted_current_utilization": maximum_current}
            return
        feature = _feature(current_states, current, previous, previous_q, np.asarray(meta["limits"]))
        if not _supported(fold, feature, interval):
            unsupported += 1
            return
        count = 4 if interval < 3 else endpoint - 22
        for level in levels:
            issue = _safe_issue(cfg, r22_cfg, meta, current, level, DECISIONS[interval])
            if not bool(issue["passed"]):
                continue
            safe_nodes += 1
            q = np.asarray(level["q"], dtype=float)
            row = {"interval": interval, "feature": feature, "q": q,
                   "previous_q": previous_q, "targets": np.zeros((count, 5))}
            row["expanded"] = ind23._expand(feature, q, previous_q)
            prediction = ind23._predict(model, row)
            tube, _ = _tube_query(fold["calibration"], row, cfg)
            next_current = np.asarray(issue["nominal_issue_readback_current_a_tsc"], dtype=float)
            visit(interval + 1, np.concatenate((current_states, prediction)),
                  np.concatenate((current_tubes, tube)), next_current, current, q,
                  indices + (int(level["index"]),), movement + float(np.sum(np.abs(q - previous_q))),
                  max(maximum_current, float(issue["predicted_current_utilization"])))

    visit(0, prefix_states, prefix_tubes, current0, current0, np.zeros(2), (), 0.0, 0.0)
    return {"pair_id": meta["pair_id"], "history_member": meta["history_member"],
            "unfiltered_sequence_count": 14641, "safe_issue_node_count": safe_nodes,
            "unsupported_node_count": unsupported, "safe_complete_sequence_count": complete,
            "selected_plan": best, "safe_complete_plan": best is not None,
            "predicted_formal_pass": bool(best and best["robust_formal_pass"])}


def _planning(args: argparse.Namespace, cfg: Mapping[str, Any], source_cfg: Mapping[str, Any],
              folds: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    metadata, r22_cfg, source_stage = _planning_metadata(args, source_cfg)
    by_pair = {str(fold["held_pair"]): fold for fold in folds}
    plans = [_plan_one(cfg, r22_cfg, metadata[key], by_pair[key[0]]) for key in sorted(metadata)]
    source = _read(source_stage / "analysis/primary_detailed.json")
    baseline = {(str(row["pair_id"]), str(row["history_member"])):
                bool(row["baseline"]["formal_contract_pass"])
                for row in source["formal_authority"]["context_rows"]}
    repairs = regressions = oracle = 0
    for plan in plans:
        key = (str(plan["pair_id"]), str(plan["history_member"]))
        predicted = bool(plan["predicted_formal_pass"])
        repairs += int(not baseline[key] and predicted)
        regressions += int(baseline[key] and not predicted)
        oracle += int(baseline[key] or predicted)
    complete = sum(bool(plan["safe_complete_plan"]) for plan in plans)
    gate = cfg["planning_gate"]
    passed = bool(complete == int(gate["required_safe_complete_plan_count"])
                  and repairs >= int(gate["minimum_predicted_repaired_failed_baseline_count"])
                  and regressions <= int(gate["maximum_predicted_regressed_baseline_pass_count"])
                  and oracle >= int(gate["minimum_predicted_oracle_count"]))
    return {"safe_complete_plan_count": complete,
            "predicted_repaired_failed_baseline_count": repairs,
            "predicted_regressed_baseline_pass_count": regressions,
            "predicted_baseline_plus_policy_oracle_count": oracle,
            "plans": plans, "passed": passed}


def audit(args: argparse.Namespace, cfg: Mapping[str, Any]) -> dict[str, Any]:
    _validate_config(cfg)
    authentication = _authenticate(args, cfg)
    source_cfg = _source_config(cfg)
    stage = args.run_dir.expanduser().resolve() / RUN_NAME
    primary_path, summary_path = stage / "analysis/primary_detailed.json", stage / "analysis/primary_summary.json"
    model_path = stage / "model/outer_fold_models.json"
    primary, summary, primary_models = _read(primary_path), _read(summary_path), _read(model_path)
    bank = ind23._build_bank(args, source_cfg)
    bank_evidence = ind23._bank_evidence(bank)
    folds = _outer(bank, cfg)
    evaluation = _evaluate(folds, cfg)
    source_primary = _read(_source_stage(args, cfg) / "analysis/primary_detailed.json")
    source_models = _read(_source_stage(args, cfg) / "model/outer_fold_models.json")
    source_by_pair = {
        str(row["held_pair"]): row["model"] for row in source_models["folds"]
    }
    current_by_pair = {
        str(fold["held_pair"]): ind23._serial(fold["model"]) for fold in folds
    }
    source_evaluation = source_primary["model_evaluation"]
    source_support = {
        str(row["pair_id"]): row["support"]
        for row in source_evaluation["fold_rows"]
    }
    current_support = {
        str(row["pair_id"]): row["support"] for row in evaluation["fold_rows"]
    }
    source_point_reproduction = {
        "source_selected_predictor": source_evaluation["selected_predictor"],
        "source_innovation_enabled": bool(source_primary["adaptation_enabled"]),
        "maximum_outer_model_absolute_difference": ind23._maximum_difference(
            source_by_pair, current_by_pair
        ),
        "maximum_point_metric_absolute_difference": ind23._maximum_difference(
            source_evaluation["maximum_absolute_physical_error"],
            evaluation["maximum_absolute_physical_error"],
        ),
        "maximum_support_absolute_difference": ind23._maximum_difference(
            source_support, current_support
        ),
    }
    source_point_reproduction["passed"] = bool(
        source_point_reproduction["source_selected_predictor"] == "cold"
        and source_point_reproduction["source_innovation_enabled"] is False
        and max(
            source_point_reproduction["maximum_outer_model_absolute_difference"],
            source_point_reproduction["maximum_point_metric_absolute_difference"],
            source_point_reproduction["maximum_support_absolute_difference"],
        )
        <= 1e-12
    )
    if not source_point_reproduction["passed"]:
        raise ValueError("independent R8R24 did not reproduce the R8R23 cold point model")
    planning = (_planning(args, cfg, source_cfg, folds) if evaluation["passed"] else
                {"safe_complete_plan_count": 0, "predicted_repaired_failed_baseline_count": 0,
                 "predicted_regressed_baseline_pass_count": 0,
                 "predicted_baseline_plus_policy_oracle_count": 6, "plans": [],
                 "skipped_reason": "frozen_point_support_or_local_tube_gate_failed", "passed": False})
    scientific = bool(evaluation["passed"] and planning["passed"])
    route = str(cfg["routes"]["pass" if scientific else
                               ("planning_fail" if evaluation["passed"] else "model_fail")])
    independent_models = {"schema_version": 1, "stage": STAGE,
                          "feature_digest": bank_evidence["feature_digest"],
                          "target_digest": bank_evidence["target_digest"],
                          "folds": [{"held_pair": fold["held_pair"],
                                     "model": ind23._serial(fold["model"]),
                                     "nested_fit_evidence": fold["nested_fit_evidence"],
                                     "local_tube_evidence": fold["local_tube_evidence"]}
                                    for fold in folds]}
    tolerance = float(cfg["planning_gate"]["primary_independent_absolute_tolerance"])
    fit_difference = ind23._maximum_difference(primary_models, independent_models)
    tube_difference = ind23._maximum_difference(primary["model_evaluation"], evaluation)
    plan_difference = ind23._maximum_difference(primary["planning_evaluation"], planning)
    reproduction_difference = ind23._maximum_difference(
        primary["source_point_reproduction"], source_point_reproduction
    )
    feature_agreement = bool(primary["bank_evidence"]["feature_digest"] == bank_evidence["feature_digest"]
                             and primary["bank_evidence"]["target_digest"] == bank_evidence["target_digest"])
    fit_agreement, tube_agreement = fit_difference <= tolerance, tube_difference <= tolerance
    plan_agreement = plan_difference <= tolerance
    source_reproduction_agreement = reproduction_difference <= tolerance
    route_agreement = primary.get("route") == route and summary.get("route") == route
    outcome_agreement = bool(primary.get("model_gate_passed") is evaluation["passed"]
                             and primary.get("predicted_feasibility_gate_passed") is planning["passed"])
    result = {"schema_version": 1, "stage": STAGE,
              "audit_kind": "causal_local_residual_tube_receding_horizon_preflight_independent",
              "source_authentication": authentication, "bank_evidence": bank_evidence,
              "innovation_enabled": False,
              "source_point_reproduction": source_point_reproduction,
              "model_evaluation": evaluation,
              "planning_evaluation": planning, "route": route,
              "maximum_fit_absolute_difference": fit_difference,
              "maximum_tube_absolute_difference": tube_difference,
              "maximum_plan_absolute_difference": plan_difference,
              "maximum_source_reproduction_absolute_difference": reproduction_difference,
              "primary_feature_agreement": feature_agreement,
              "primary_fit_agreement": fit_agreement,
              "primary_tube_agreement": tube_agreement,
              "primary_plan_agreement": plan_agreement,
              "primary_source_reproduction_agreement": source_reproduction_agreement,
              "primary_route_agreement": route_agreement,
              "primary_outcome_agreement": outcome_agreement,
              "primary_detailed_sha256": _sha(primary_path),
              "primary_summary_sha256": _sha(summary_path),
              "primary_model_evidence_sha256": _sha(model_path),
              "real_tsc_executed": False, "plant_step_count": 0, "new_raw_count": 0}
    result["passed"] = bool(feature_agreement and fit_agreement and tube_agreement
                            and plan_agreement and source_reproduction_agreement
                            and route_agreement and outcome_agreement)
    if not result["passed"]:
        raise ValueError("independent R8R24 audit disagrees with primary")
    _write(stage / "analysis/independent.json", result)
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--r8r23-run", type=Path, required=True)
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
    _validate_config(cfg)
    result = audit(args, cfg)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
