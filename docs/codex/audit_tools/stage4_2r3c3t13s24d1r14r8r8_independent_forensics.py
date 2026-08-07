#!/usr/bin/env python3
"""Structurally independent R8R8 offline and authentic-raw forensics."""

from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
import json
import math
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from tsc_rzip_rllib.control import action_conditioned_history_response_model as response_model
from tsc_rzip_rllib.control import causal_history_no_action_observer as observer
from tsc_rzip_rllib.control.quantized_actuator import QuantizedActuatorModel
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s13_recurrent_sequence_tube_identification as s13,
    stage4_2r3c3t13s21_cumulative_exact_card15_pooled_observer_campaign as s21,
    stage4_2r3c3t13s9_unified_postqueue_q1_identification as s9,
    stage4_2r3c3t13s24d1r14r8r7_fresh_multipulse_static_observer_interaction_campaign as r8r7,
    stage4_2r3c3t13s24d1r14r8r8_causal_discrete_pulse_mpc_core as contract,
)


N_COILS = 14
PREFIX_END = 10


def _read(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
    )


def _gzip(path: Path) -> dict[str, Any]:
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        return json.load(
            stream,
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
        )


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _inventory(path: Path) -> dict[str, Any]:
    files = sorted(path.glob("*.json.gz"), key=lambda value: value.name)
    digest = hashlib.sha256()
    rows = []
    for value in files:
        size = value.stat().st_size
        sha = _sha(value)
        digest.update(f"{value.name}\0{size}\0{sha}\n".encode())
        rows.append({"name": value.name, "size": size, "sha256": sha})
    return {
        "count": len(rows),
        "bytes": sum(int(row["size"]) for row in rows),
        "digest": digest.hexdigest(),
        "rows": rows,
    }


def _stage(run_dir: Path) -> Path:
    return run_dir.expanduser().resolve() / contract.RUN_NAME


def _source_context(args: argparse.Namespace, cfg: Mapping[str, Any]) -> r8r7.Context:
    source_args = argparse.Namespace(**vars(args))
    source_args.config = (Path(__file__).resolve().parents[3] / str(cfg["source_r8r7_config"])).resolve()
    source_args.run_dir = args.r8r7_run.expanduser().resolve()
    return r8r7.load_context(source_args)


def _source_stage(args: argparse.Namespace, cfg: Mapping[str, Any]) -> Path:
    source_cfg = _read(Path(__file__).resolve().parents[3] / str(cfg["source_r8r7_config"]))
    return args.r8r7_run.expanduser().resolve() / str(source_cfg["run_name"])


def _observer_model(value: Mapping[str, Any]) -> dict[str, Any]:
    source = value["model"]
    candidate = observer.Candidate(**source["candidate"])
    output: dict[str, Any] = {
        "candidate": candidate,
        "preprocessor": {key: np.asarray(item, dtype=float) for key, item in source["preprocessor"].items()},
        "training_x": np.asarray(source["training_x"], dtype=float),
        "target_mean": np.asarray(source["target_mean"], dtype=float),
        "bandwidth": float(source["bandwidth"]),
    }
    name = "beta" if candidate.family == "linear" else "alpha"
    output[name] = np.asarray(source[name], dtype=float)
    return output


def _response_model(value: Mapping[str, Any]) -> dict[str, Any]:
    source = value["model"]
    return {
        "candidate": response_model.Candidate(**source["candidate"]),
        "preprocessor": {key: np.asarray(item, dtype=float) for key, item in source["preprocessor"].items()},
        "heads": {
            key: {
                "amplitude_mean": float(head["amplitude_mean"]),
                "amplitude_scale": float(head["amplitude_scale"]),
                "lags": [
                    {
                        "lag": int(row["lag"]),
                        "x": np.asarray(row["x"], dtype=float),
                        "bandwidth": float(row["bandwidth"]),
                        "y_mean": np.asarray(row["y_mean"], dtype=float),
                        "alpha": np.asarray(row["alpha"], dtype=float),
                    }
                    for row in head["lags"]
                ],
            }
            for key, head in source["heads"].items()
        },
    }


def _visible(states: Sequence[Mapping[str, Any]], scales: np.ndarray) -> np.ndarray:
    rows = []
    for index, state in enumerate(states):
        other = states[1] if index == 0 else states[index - 1]
        sign = 1.0 if index == 0 else -1.0
        rows.append(
            [
                float(state["R"]),
                float(state["Z"]),
                sign * (float(other["R"]) - float(state["R"])) / 0.01,
                sign * (float(other["Z"]) - float(state["Z"])) / 0.01,
                float(state["Ip"]),
            ]
        )
    output = np.asarray(rows, dtype=float) / scales
    if not np.all(np.isfinite(output)):
        raise ValueError("R8R8 independent visible reconstruction non-finite")
    return output


def _descriptor(
    visible: np.ndarray, target_offsets: Sequence[float], origin: int, source_cfg: Mapping[str, Any]
) -> np.ndarray:
    offsets = tuple(map(int, source_cfg["bank_contract"]["history_offsets"]))
    history = visible[[max(0, origin - offset) for offset in offsets]].reshape(-1)
    available = np.asarray([float(offset <= origin) for offset in offsets])
    target = np.asarray(target_offsets, dtype=float) / np.asarray(
        source_cfg["bank_contract"]["target_scales"], dtype=float
    )
    output = np.concatenate((history, available, target, [(origin - 10.0) / 12.0]))
    if output.shape != (142,) or not np.all(np.isfinite(output)):
        raise ValueError("R8R8 independent response descriptor changed")
    return output


def _response_cfg(source_ctx: r8r7.Context) -> dict[str, Any]:
    output = copy.deepcopy(source_ctx.r8_cfg)
    output["gates"].update(copy.deepcopy(source_ctx.r8r1_cfg["gates"]))
    output["model_contract"].update(copy.deepcopy(source_ctx.r8r1_cfg["model_contract"]))
    output["bank_contract"]["response_scales"] = list(
        source_ctx.r8r1_cfg["bank_contract"]["response_scales"]
    )
    output["bank_contract"]["dt_s"] = float(source_ctx.r8r1_cfg["bank_contract"]["dt_s"])
    output["bank_contract"]["direction_count"] = int(
        source_ctx.r8r1_cfg["bank_contract"]["direction_count"]
    )
    return output


def _forecasts(
    *,
    states: Sequence[Mapping[str, Any]],
    actions: Sequence[Sequence[float]],
    target_offsets: Sequence[float],
    cfg: Mapping[str, Any],
    source_ctx: r8r7.Context,
    models: Mapping[str, Any],
) -> list[dict[str, Any]]:
    origin = len(states) - 1
    scales = np.asarray(source_ctx.cfg["bank_contract"]["visible_scales"], dtype=float)
    visible = _visible(states, scales)
    issued = np.asarray(actions, dtype=float)
    currents = np.asarray([row["currents_a_tsc"] for row in states], dtype=float)
    feature = observer.causal_feature(
        visible,
        issued,
        currents,
        target_offsets,
        origin,
        source_ctx.r8r6_cfg,
    )
    static = observer.predict_model(
        models["static"], [{"feature": feature, "origin_visible": visible[origin]}], source_ctx.r8r6_cfg
    )[0][:4]
    descriptor = _descriptor(visible, target_offsets, origin, source_ctx.cfg)
    base = np.asarray(cfg["objective_contract"]["base_target_physical"], dtype=float)
    offset = np.asarray(target_offsets, dtype=float)
    desired = np.asarray([base[0] + offset[0], base[1] + offset[1], 0.0, 0.0, base[2] + offset[2]])
    objective_scales = np.asarray(cfg["objective_contract"]["physical_scales"], dtype=float)
    component = np.asarray(cfg["objective_contract"]["component_weights"], dtype=float)
    lag = np.asarray(cfg["objective_contract"]["lag_weights"], dtype=float)
    rows = []
    for order, candidate in enumerate(cfg["candidate_contract"]["ordered_candidates"]):
        direction = int(candidate["direction_index"])
        sign = int(candidate["sign"])
        response = np.zeros((4, 5), dtype=float)
        tube = models["static_tube"][:4]
        if direction >= 0:
            response = response_model.predict_item(
                models["response"],
                {
                    "sign": sign,
                    "direction_index": direction,
                    "action_scale": 1.0,
                    "descriptor": descriptor,
                    "response": np.zeros((4, 5), dtype=float),
                },
                models["response_cfg"],
            )
            tube = models["combined_tube"]
        prediction = static + response
        upper = np.abs(prediction * objective_scales[None, :] - desired[None, :]) + tube
        normalized = upper / objective_scales[None, :]
        score = float(np.sum(lag[:, None] * component[None, :] * np.square(normalized)))
        if not math.isfinite(score):
            raise ValueError("R8R8 independent robust score non-finite")
        rows.append(
            {
                "order": order,
                "name": str(candidate["name"]),
                "direction_index": direction,
                "sign": sign,
                "score": score,
                "combined_prediction": prediction,
                "tube": np.asarray(tube, dtype=float),
                "feature_sha256": hashlib.sha256(np.asarray(feature, dtype="<f8").tobytes()).hexdigest(),
                "descriptor_sha256": hashlib.sha256(np.asarray(descriptor, dtype="<f8").tobytes()).hexdigest(),
            }
        )
    return rows


def _select(rows: Sequence[Mapping[str, Any]], eligible: Sequence[str], ratio: float) -> dict[str, Any]:
    allowed = set(map(str, eligible))
    zero = rows[0]
    choices = [row for row in rows[1:] if str(row["name"]) in allowed]
    best = min(choices, key=lambda row: (float(row["score"]), int(row["order"]))) if choices else None
    selected = best if best is not None and float(best["score"]) <= ratio * float(zero["score"]) else zero
    improvement = 0.0 if float(zero["score"]) <= 0 else (
        float(zero["score"]) - float(selected["score"])
    ) / float(zero["score"])
    return {
        "selected_name": str(selected["name"]),
        "selected_order": int(selected["order"]),
        "selected_direction_index": int(selected["direction_index"]),
        "selected_sign": int(selected["sign"]),
        "selected_score": float(selected["score"]),
        "zero_score": float(zero["score"]),
        "robust_improvement_fraction": improvement,
        "nonzero_selected": int(selected["direction_index"]) >= 0,
    }


def _actuator(payload: Mapping[str, Any], lattice: Mapping[str, Any]) -> QuantizedActuatorModel:
    minimum, maximum = s13._current_limits_tsc(payload)
    turns = s13._turns_tsc(payload)
    return QuantizedActuatorModel(
        minimum_current_a_tsc=tuple(map(float, minimum)),
        maximum_current_a_tsc=tuple(map(float, maximum)),
        max_slew_step_a=float(payload["max_delta_a"]),
        turns_tsc=tuple(map(float, turns)),
        bias_grid_units_tsc=tuple(map(float, lattice["readback_bias_grid_units_tsc"])),
        uncertainty_radius_grid_units_tsc=tuple(map(float, lattice["readback_radius_grid_units_tsc"])),
    )


def _issue(
    currents: Sequence[float],
    basis_rows: Sequence[Sequence[float]],
    candidate: Mapping[str, Any],
    cfg: Mapping[str, Any],
    actuator: QuantizedActuatorModel,
    lattice: Mapping[str, Any],
) -> dict[str, Any]:
    direction, sign = int(candidate["direction_index"]), int(candidate["sign"])
    current = np.asarray(currents, dtype=float)
    basis = np.asarray(basis_rows, dtype=float).reshape(4, N_COILS).T
    matrix = np.asarray(cfg["candidate_contract"]["canonical_matrix_columns"], dtype=float)
    requested = matrix[:, direction] * sign
    center = actuator.apply(current, np.zeros(N_COILS))
    target, actual_decimal, _ = s21._dynamic_exact_target(
        center.card15_fields,
        tuple(Decimal(str(value)) for value in basis @ requested),
        search_radius=int(cfg["controller_contract"]["dynamic_exact_search_radius"]),
    )
    chosen = s9.exact_stored_center_action(
        stored_fields=target,
        measured_current_a_tsc=current,
        baseline_action_norm_tsc=np.zeros(N_COILS),
        turns_tsc=actuator.turns_tsc,
        max_slew_step_a=actuator.max_slew_step_a,
        minimum_current_a_tsc=actuator.minimum_current_a_tsc,
        maximum_current_a_tsc=actuator.maximum_current_a_tsc,
        cfg=lattice,
    )
    issued = actuator.apply(current, chosen["action_norm_tsc"])
    actual_field = np.asarray([float(value) for value in actual_decimal])
    turns = np.asarray(actuator.turns_tsc)
    current_basis = basis * 1000.0 / turns[:, None]
    desired_current = current_basis @ requested
    actual_current = actual_field * 1000.0 / turns
    coordinate = np.linalg.lstsq(current_basis, actual_current, rcond=None)[0]
    reconstruction = current_basis @ coordinate
    cosine = float(
        np.dot(desired_current, actual_current)
        / max(float(np.linalg.norm(desired_current)) * float(np.linalg.norm(actual_current)), 1e-300)
    )
    off_basis = float(
        np.linalg.norm(actual_current - reconstruction) / max(float(np.linalg.norm(actual_current)), 1e-300)
    )
    hard = cfg["controller_contract"]
    passed = bool(
        np.all(np.isfinite(coordinate))
        and list(issued.card15_fields) == list(target)
        and not any(issued.action_saturated)
        and not any(issued.current_limit_clipped)
        and float(chosen["incremental_normalized_action_linf"]) <= float(hard["maximum_incremental_normalized_action_linf"]) + 1e-12
        and float(chosen["total_normalized_action_abs"]) <= float(hard["maximum_total_normalized_action_abs"]) + 1e-12
        and float(chosen["predicted_maximum_current_utilization"]) <= float(hard["maximum_current_utilization"]) + 1e-12
        and cosine >= float(hard["minimum_desired_applied_current_cosine"]) - 1e-12
        and off_basis <= float(hard["maximum_relative_off_basis_residual"]) + 1e-12
        and bool(chosen["passed"])
    )
    return {
        "name": str(candidate["name"]),
        "direction_index": direction,
        "sign": sign,
        "center_fields": list(center.card15_fields),
        "target_fields": list(target),
        "action": list(map(float, chosen["action_norm_tsc"])),
        "nominal_readback": list(issued.nominal_readback_current_a_tsc),
        "increment": float(chosen["incremental_normalized_action_linf"]),
        "utilization": float(chosen["predicted_maximum_current_utilization"]),
        "cosine": cosine,
        "off_basis": off_basis,
        "passed": passed,
    }


def _cancel(
    currents: Sequence[float],
    issue: Mapping[str, Any],
    cfg: Mapping[str, Any],
    actuator: QuantizedActuatorModel,
    lattice: Mapping[str, Any],
) -> dict[str, Any]:
    chosen = s9.exact_stored_center_action(
        stored_fields=issue["center_fields"],
        measured_current_a_tsc=currents,
        baseline_action_norm_tsc=np.zeros(N_COILS),
        turns_tsc=actuator.turns_tsc,
        max_slew_step_a=actuator.max_slew_step_a,
        minimum_current_a_tsc=actuator.minimum_current_a_tsc,
        maximum_current_a_tsc=actuator.maximum_current_a_tsc,
        cfg=lattice,
    )
    cancelled = actuator.apply(currents, chosen["action_norm_tsc"])
    hard = cfg["controller_contract"]
    passed = bool(
        list(cancelled.card15_fields) == list(issue["center_fields"])
        and not any(cancelled.action_saturated)
        and not any(cancelled.current_limit_clipped)
        and float(chosen["incremental_normalized_action_linf"]) <= float(hard["maximum_online_cancel_incremental_linf"]) + 1e-12
        and float(chosen["total_normalized_action_abs"]) <= float(hard["maximum_total_normalized_action_abs"]) + 1e-12
        and float(chosen["predicted_maximum_current_utilization"]) <= float(hard["maximum_current_utilization"]) + 1e-12
        and bool(chosen["passed"])
    )
    return {
        "action": list(map(float, chosen["action_norm_tsc"])),
        "increment": float(chosen["incremental_normalized_action_linf"]),
        "utilization": float(chosen["predicted_maximum_current_utilization"]),
        "passed": passed,
    }


def _models(stage: Path, source_ctx: r8r7.Context) -> dict[str, Any]:
    return {
        "static": _observer_model(_read(stage / "model/static_model.json")),
        "response": _response_model(_read(stage / "model/response_model.json")),
        "static_tube": np.asarray(_read(stage / "model/static_tube.json")["tube_physical"], dtype=float),
        "combined_tube": np.asarray(
            _read(stage / "model/combined_tube.json")["combined_tube_physical"], dtype=float
        ),
        "response_cfg": _response_cfg(source_ctx),
    }


def _source_baselines(source_stage: Path) -> dict[str, dict[str, Any]]:
    output = {}
    for path in sorted((source_stage / "raw/baseline").glob("*.json.gz")):
        value = _gzip(path)
        output[str(value["experiment_id"])] = value
    if len(output) != 16:
        raise ValueError("R8R8 independent source baseline coverage changed")
    return output


def offline_audit(args: argparse.Namespace, cfg: Mapping[str, Any]) -> dict[str, Any]:
    stage = _stage(args.run_dir)
    source_stage = _source_stage(args, cfg)
    source_ctx = _source_context(args, cfg)
    specs = _read(stage / "specs/core_specs.json")
    primary_path = stage / "analysis/offline_primary_summary.json"
    detailed = _read(stage / "analysis/offline_primary_detailed.json")
    source = _source_baselines(source_stage)
    models = _models(stage, source_ctx)
    lattice = source_ctx.r8_ctx.d1r11_ctx.base_ctx.base_ctx.cfg["lattice_probe"]
    primary_forecasts = {
        (str(row["row_id"]), str(row["name"])): row
        for row in detailed["forecast_rows"]
    }
    primary_selection = {str(row["row_id"]): row for row in detailed["selection_rows"]}
    maximum_prediction_difference = 0.0
    maximum_score_difference = 0.0
    forecast_count = selection_count = issue_count = cancel_count = nonzero_count = 0
    selected_match = True
    action_match = True
    for spec in specs:
        source_id = str(spec["source_r8r7_baseline_experiment_id"])
        result = source[source_id]
        payload = _read(source_stage / "variants" / f"payload_{source_id}.json")
        actuator = _actuator(payload, lattice)
        basis = result["controller_trace"][7]["r3c3t13s16_fixed_basis_delta_field_kAt_tsc"]
        actions = [row["action_norm_tsc"] for row in result["controller_trace"]]
        for origin in contract.DECISION_STEPS:
            forecasts = _forecasts(
                states=result["trajectory"][: origin + 1],
                actions=actions[:origin],
                target_offsets=spec["r8r8_numeric_target_offsets"],
                cfg=cfg,
                source_ctx=source_ctx,
                models=models,
            )
            eligible = []
            constructed = {}
            for candidate in cfg["candidate_contract"]["ordered_candidates"][1:]:
                issue = _issue(
                    result["trajectory"][origin]["currents_a_tsc"], basis, candidate, cfg, actuator, lattice
                )
                cancel = _cancel(issue["nominal_readback"], issue, cfg, actuator, lattice)
                issue_count += int(issue["passed"])
                cancel_count += int(cancel["passed"])
                if issue["passed"] and cancel["passed"]:
                    eligible.append(str(candidate["name"]))
                constructed[str(candidate["name"])] = (issue, cancel)
            selection = _select(
                forecasts, eligible, float(cfg["objective_contract"]["required_nonzero_score_ratio"])
            )
            row_id = f"{spec['experiment_id']}|origin{origin:02d}"
            for forecast in forecasts:
                primary = primary_forecasts[(row_id, str(forecast["name"]))]
                maximum_prediction_difference = max(
                    maximum_prediction_difference,
                    float(np.max(np.abs(forecast["combined_prediction"] - np.asarray(primary["combined_prediction"], dtype=float)))),
                )
                maximum_score_difference = max(
                    maximum_score_difference, abs(float(forecast["score"]) - float(primary["score"]))
                )
                forecast_count += 1
            primary_row = primary_selection[row_id]
            selected_match = selected_match and selection["selected_name"] == primary_row["selection"]["selected_name"]
            for name, (issue, cancel) in constructed.items():
                recorded = primary_row["constructions"][name]
                action_match = bool(
                    action_match
                    and np.array_equal(np.asarray(issue["action"]), np.asarray(recorded["issue"]["action_norm_tsc"]))
                    and np.array_equal(np.asarray(cancel["action"]), np.asarray(recorded["cancel"]["action_norm_tsc"]))
                )
            nonzero_count += int(selection["nonzero_selected"])
            selection_count += 1
    tolerance = float(cfg["offline_gates"]["independent_absolute_tolerance"])
    numerical = bool(
        maximum_prediction_difference <= tolerance
        and maximum_score_difference <= tolerance
        and selected_match
        and action_match
    )
    outcome = bool(
        forecast_count == 576
        and selection_count == 64
        and issue_count == 512
        and cancel_count == 512
        and nonzero_count == int(detailed["nonzero_selection_count"])
    )
    model_hashes = {
        "static_model": _sha(stage / "model/static_model.json"),
        "static_tube": _sha(stage / "model/static_tube.json"),
        "response_model": _sha(stage / "model/response_model.json"),
        "response_tube": _sha(stage / "model/response_tube.json"),
        "combined_tube": _sha(stage / "model/combined_tube.json"),
    }
    expected = cfg["source_model_contract"]
    artifacts = bool(
        model_hashes
        == {
            "static_model": expected["static_observer_model_sha256"],
            "static_tube": expected["static_observer_tube_sha256"],
            "response_model": expected["response_model_sha256"],
            "response_tube": expected["response_tube_sha256"],
            "combined_tube": expected["combined_tube_sha256"],
        }
    )
    output = {
        "schema_version": 1,
        "stage": contract.STAGE,
        "phase": "zero_tsc_structurally_independent_offline_acceptance",
        "forecast_count": forecast_count,
        "selection_count": selection_count,
        "issue_construction_pass_count": issue_count,
        "cancel_construction_pass_count": cancel_count,
        "nonzero_selection_count": nonzero_count,
        "maximum_prediction_abs_difference": maximum_prediction_difference,
        "maximum_score_abs_difference": maximum_score_difference,
        "selected_candidate_agreement": selected_match,
        "exact_action_agreement": action_match,
        "model_hashes": model_hashes,
        "primary_numerical_agreement": numerical,
        "primary_outcome_agreement": outcome,
        "artifact_hash_agreement": artifacts,
        "primary_sha256": _sha(primary_path),
        "real_tsc_executed": False,
        "new_raw_count": 0,
        "route": cfg["routes"]["pass" if numerical and outcome and artifacts else "offline_fail"],
        "passed": bool(numerical and outcome and artifacts),
    }
    _write(stage / "analysis/offline_independent.json", output)
    return output


FORBIDDEN = (
    "r3c3t13s24d1r14r8r8_pair_or_history_label_used",
    "r3c3t13s24d1r14r8r8_partition_label_used",
    "r3c3t13s24d1r14r8r8_source_result_used",
    "r3c3t13s24d1r14r8r8_source_formal_outcome_used",
    "r3c3t13s24d1r14r8r8_future_measurement_used",
    "r3c3t13s24d1r14r8r8_future_executed_action_used",
    "r3c3t13s24d1r14r8r8_hidden_wire_current_used",
)


def final_audit(args: argparse.Namespace, cfg: Mapping[str, Any]) -> dict[str, Any]:
    stage = _stage(args.run_dir)
    source_stage = _source_stage(args, cfg)
    source_ctx = _source_context(args, cfg)
    specs = _read(stage / "specs/core_specs.json")
    primary_path = stage / "analysis/primary_summary.json"
    primary = _read(primary_path)
    sources = _source_baselines(source_stage)
    models = _models(stage, source_ctx)
    lattice = source_ctx.r8_ctx.d1r11_ctx.base_ctx.base_ctx.cfg["lattice_probe"]
    evaluators, _ = r8r7.r8.d1r11._formal_callback(source_ctx.r8_ctx.d1r11_ctx, specs)
    execution_count = decision_count = nonzero_count = issue_count = cancel_count = formal_count = 0
    forbidden_count = 0
    maximum_prediction_difference = maximum_score_difference = maximum_action_difference = 0.0
    selection_agreement = True
    for spec in specs:
        experiment_id = str(spec["experiment_id"])
        result = _gzip(stage / "raw" / f"{experiment_id}.json.gz")
        source = sources[str(spec["source_r8r7_baseline_experiment_id"])]
        trace = result.get("controller_trace") or []
        trajectory = result.get("trajectory") or []
        horizon = int(spec["horizon_steps"])
        full = len(trace) == horizon and len(trajectory) == horizon + 1
        prefix = bool(
            full
            and all(
                r8r7.r8.r4._semantic_state(current) == r8r7.r8.r4._semantic_state(reference)
                for current, reference in zip(
                    trajectory[: PREFIX_END + 1], source["trajectory"][: PREFIX_END + 1]
                )
            )
            and all(
                r8r7.r8.r4._source_trace_projection(reference, current)
                for current, reference in zip(trace[:PREFIX_END], source["controller_trace"][:PREFIX_END])
            )
        )
        forbidden_count += sum(any(bool(row.get(key)) for key in FORBIDDEN) for row in trace)
        payload = _read(stage / "variants" / f"payload_{experiment_id}.json")
        actuator = _actuator(payload, lattice)
        basis = trace[7]["r3c3t13s16_fixed_basis_delta_field_kAt_tsc"] if full else []
        current_actions = [row.get("action_norm_tsc", []) for row in trace]
        row_ok = bool(result.get("success") and full and prefix)
        nonzero_action_steps: set[int] = set()
        for origin in contract.DECISION_STEPS:
            recorded = trace[origin].get("r3c3t13s24d1r14r8r8_decision") or {}
            forecasts = _forecasts(
                states=trajectory[: origin + 1],
                actions=current_actions[:origin],
                target_offsets=spec["r8r8_numeric_target_offsets"],
                cfg=cfg,
                source_ctx=source_ctx,
                models=models,
            )
            eligible, built = [], {}
            for candidate in cfg["candidate_contract"]["ordered_candidates"][1:]:
                issue = _issue(trajectory[origin]["currents_a_tsc"], basis, candidate, cfg, actuator, lattice)
                nominal_cancel = _cancel(
                    issue["nominal_readback"], issue, cfg, actuator, lattice
                )
                if issue["passed"] and nominal_cancel["passed"]:
                    eligible.append(str(candidate["name"]))
                built[str(candidate["name"])] = {
                    "issue": issue,
                    "nominal_cancel": nominal_cancel,
                }
            selection = _select(
                forecasts, eligible, float(cfg["objective_contract"]["required_nonzero_score_ratio"])
            )
            recorded_forecasts = recorded.get("candidate_forecasts") or []
            if len(recorded_forecasts) != 9:
                row_ok = False
            else:
                for current, expected in zip(forecasts, recorded_forecasts):
                    maximum_prediction_difference = max(
                        maximum_prediction_difference,
                        float(np.max(np.abs(current["combined_prediction"] - np.asarray(expected["combined_prediction"], dtype=float)))),
                    )
                    maximum_score_difference = max(
                        maximum_score_difference, abs(float(current["score"]) - float(expected["score"]))
                    )
            recorded_selection = recorded.get("selection") or {}
            selection_agreement = bool(
                selection_agreement and selection["selected_name"] == recorded_selection.get("selected_name")
            )
            recorded_constructions = recorded.get("candidate_constructions") or []
            row_ok = bool(
                row_ok
                and int(recorded.get("task_step", -1)) == origin
                and recorded.get("model_fault") is False
                and len(recorded_constructions) == 8
            )
            for candidate, expected in zip(
                cfg["candidate_contract"]["ordered_candidates"][1:],
                recorded_constructions,
            ):
                name = str(candidate["name"])
                current = built[name]
                row_ok = bool(
                    row_ok
                    and expected.get("candidate_name") == name
                    and bool(expected.get("passed"))
                    == bool(current["issue"]["passed"] and current["nominal_cancel"]["passed"])
                    and "construction_error" not in expected
                )
                if "issue" in expected and "nominal_cancel" in expected:
                    maximum_action_difference = max(
                        maximum_action_difference,
                        float(
                            np.max(
                                np.abs(
                                    np.asarray(current["issue"]["action"])
                                    - np.asarray(expected["issue"]["action_norm_tsc"])
                                )
                            )
                        ),
                        float(
                            np.max(
                                np.abs(
                                    np.asarray(current["nominal_cancel"]["action"])
                                    - np.asarray(expected["nominal_cancel"]["action_norm_tsc"])
                                )
                            )
                        ),
                    )
                else:
                    row_ok = False
            if selection["nonzero_selected"]:
                issue = built[selection["selected_name"]]["issue"]
                maximum_action_difference = max(
                    maximum_action_difference,
                    float(
                        np.max(
                            np.abs(
                                np.asarray(issue["action"])
                                - np.asarray(trace[origin]["action_norm_tsc"])
                            )
                        )
                    ),
                )
                cancel = _cancel(
                    trajectory[origin + 1]["currents_a_tsc"], issue, cfg, actuator, lattice
                )
                maximum_action_difference = max(
                    maximum_action_difference,
                    float(
                        np.max(
                            np.abs(
                                np.asarray(cancel["action"])
                                - np.asarray(trace[origin + 1]["action_norm_tsc"])
                            )
                        )
                    ),
                )
                row_ok = row_ok and issue["passed"] and cancel["passed"]
                nonzero_action_steps.update((origin, origin + 1))
                nonzero_count += 1
                issue_count += 1
                cancel_count += 1
            else:
                row_ok = row_ok and np.array_equal(
                    np.asarray(trace[origin]["action_norm_tsc"]), np.zeros(N_COILS)
                )
            decision_count += 1
        row_ok = bool(
            row_ok
            and all(
                step in nonzero_action_steps
                or np.array_equal(
                    np.asarray(trace[step]["action_norm_tsc"], dtype=float),
                    np.zeros(N_COILS),
                )
                for step in range(PREFIX_END, horizon)
            )
        )
        values = np.asarray([[row["R"], row["Z"], row["Ip"]] for row in trajectory], dtype=float)
        formal = bool(full and evaluators[experiment_id].evaluate(values)["formal_contract_pass"])
        formal_count += int(formal)
        execution_count += int(row_ok)
    inventory = _inventory(stage / "raw")
    atol = float(cfg["offline_gates"]["independent_absolute_tolerance"])
    numerical = bool(
        maximum_prediction_difference <= atol
        and maximum_score_difference <= atol
        and maximum_action_difference <= atol
        and selection_agreement
    )
    outcome = bool(
        inventory["count"] == 16
        and execution_count == 16
        and decision_count == 64
        and forbidden_count == 0
        and nonzero_count == int(primary["selected_nonzero_issue_count"])
        and issue_count == int(primary["exact_issue_count"])
        and cancel_count == int(primary["exact_cancel_count"])
        and formal_count == int(primary["formal_contract_pass_count"])
    )
    execution_gate = execution_count == 16 and decision_count == 64 and forbidden_count == 0 and nonzero_count >= 1
    scientific = execution_gate and formal_count == 16
    route = cfg["routes"]["pass" if scientific else ("formal_fail" if execution_gate else "execution_fail")]
    output = {
        "schema_version": 1,
        "stage": contract.STAGE,
        "phase": "structurally_independent_authentic_raw_mpc_forensics",
        "raw_inventory": inventory,
        "execution_pass_count": execution_count,
        "decision_record_count": decision_count,
        "selected_nonzero_issue_count": nonzero_count,
        "exact_issue_count": issue_count,
        "exact_cancel_count": cancel_count,
        "forbidden_trace_count": forbidden_count,
        "formal_contract_pass_count": formal_count,
        "maximum_prediction_abs_difference": maximum_prediction_difference,
        "maximum_score_abs_difference": maximum_score_difference,
        "maximum_action_abs_difference": maximum_action_difference,
        "selected_candidate_agreement": selection_agreement,
        "execution_gate_passed": execution_gate,
        "scientific_gate_passed": scientific,
        "primary_numerical_agreement": numerical,
        "primary_outcome_agreement": outcome,
        "primary_sha256": _sha(primary_path),
        "route": route,
        "passed": bool(numerical and outcome and route == primary.get("route")),
    }
    _write(stage / "analysis/final_independent.json", output)
    return output


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--r8r7-run", type=Path, required=True)
    parser.add_argument("--r8-run", type=Path, required=True)
    parser.add_argument("--r8r1-output", type=Path, required=True)
    parser.add_argument("--r8r6-run", type=Path, required=True)
    parser.add_argument("--source-d1r11-run", type=Path, required=True)
    parser.add_argument("--source-r2-run", type=Path, required=True)
    parser.add_argument("--source-r4-run", type=Path, required=True)
    parser.add_argument("--source-r6-run", type=Path, required=True)
    parser.add_argument("--source-s21-run", type=Path, required=True)
    parser.add_argument("--source-s23r1-output", type=Path, required=True)
    parser.add_argument("--source-s24-run", type=Path, required=True)
    parser.add_argument("--source-d1r9-v1", type=Path, required=True)
    parser.add_argument("--source-d1r9-v2", type=Path, required=True)
    parser.add_argument("--source-d1r10-run", type=Path, required=True)
    parser.add_argument("--source-d1r10-audit", type=Path, required=True)
    parser.add_argument("--source-stage42r3b-run", type=Path, required=True)
    parser.add_argument("--source-stage42r3c3-run", type=Path, required=True)
    parser.add_argument("--source-stage42r3c3-bank-dir", type=Path, required=True)
    parser.add_argument("--source-stage42r3c3t1-run", type=Path, required=True)
    parser.add_argument("--source-stage42r3c3t1-audit-dir", type=Path, required=True)
    parser.add_argument("--source-stage42r3c3t3-controller-bank", type=Path, required=True)
    parser.add_argument("--q1-run", type=Path, required=True)
    parser.add_argument("--q2-run", type=Path, required=True)
    parser.add_argument("--q1-audit", type=Path, required=True)
    parser.add_argument("--q2-audit", type=Path, required=True)
    parser.add_argument("--r3b-server-audit", type=Path, required=True)
    parser.add_argument("--r3b-snapshot-checks", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--audit-kind", choices=("offline", "final"), required=True)
    return parser


def main() -> None:
    args = _parser().parse_args()
    cfg = _read(args.config.expanduser().resolve())
    contract.validate_config(cfg, project_root=Path(__file__).resolve().parents[3])
    result = offline_audit(args, cfg) if args.audit_kind == "offline" else final_audit(args, cfg)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
