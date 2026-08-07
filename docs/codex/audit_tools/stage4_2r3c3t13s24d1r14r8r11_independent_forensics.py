#!/usr/bin/env python3
"""Structurally independent R8R11 source, raw, and formal forensics."""

from __future__ import annotations

import argparse
import copy
from decimal import Decimal
import gzip
import hashlib
import json
import math
from pathlib import Path
import statistics
from typing import Any, Mapping, Sequence

import numpy as np

from tsc_rzip_rllib.control.quantized_actuator import QuantizedActuatorModel
from tsc_rzip_rllib.core.coil_order import display_to_tsc
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r7_fresh_multipulse_static_observer_interaction_campaign as r8r7,
    stage4_2r3c3t13s24d1r14r8r9_measured_multipulse_authority_audit as r8r9,
)


STAGE = "Stage4.2R3c3T13S24D1R14R8R11"
IDENTITY = "sustained_exact_target_refresh_authority_sentinel_v1"
RUN_NAME = "stage4_2r3c3t13s24d1r14r8r11_sustained_exact_target_refresh_authority_sentinel"
CONTROLLER_REVISION = "sustained_exact_target_refresh_v42r3c3t13s24d1r14r8r11_v1"
PREFIX_END = 10
N_COILS = 14


def _root() -> Path:
    return Path(__file__).resolve().parents[3]


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
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


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


def _stage(args: argparse.Namespace) -> Path:
    return args.run_dir.expanduser().resolve() / RUN_NAME


def _source_stage(args: argparse.Namespace, cfg: Mapping[str, Any]) -> Path:
    return args.r8r7_run.expanduser().resolve() / str(cfg["source_r8r7"]["stage_directory"])


def _source_context(args: argparse.Namespace, cfg: Mapping[str, Any]) -> r8r7.Context:
    source_args = argparse.Namespace(**vars(args))
    source_args.config = (_root() / str(cfg["source_r8r7_config"])).resolve()
    source_args.run_dir = args.r8r7_run.expanduser().resolve()
    return r8r7.load_context(source_args)


def _source_baselines(
    args: argparse.Namespace, cfg: Mapping[str, Any], source_ctx: r8r7.Context
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    specs = [copy.deepcopy(row) for row in r8r7._phase_specs(source_ctx, "baseline")]
    ordered = tuple(map(str, cfg["context_contract"]["ordered_pairs"]))
    histories = tuple(map(str, cfg["context_contract"]["histories"]))
    order = {
        (pair, history): (pair_index, history_index)
        for pair_index, pair in enumerate(ordered)
        for history_index, history in enumerate(histories)
    }
    specs.sort(key=lambda row: order[(str(row["pair_id"]), str(row["history_member"]))])
    if len(specs) != 16 or {
        (str(row["pair_id"]), str(row["history_member"])) for row in specs
    } != set(order):
        raise ValueError("independent R8R11 source context coverage changed")
    source_stage = _source_stage(args, cfg)
    results = {
        str(row["experiment_id"]): _gzip(
            source_stage / "raw" / "baseline" / f"{row['experiment_id']}.json.gz"
        )
        for row in specs
    }
    return specs, results


def _expected_specs(
    args: argparse.Namespace, cfg: Mapping[str, Any], source_ctx: r8r7.Context
) -> list[dict[str, Any]]:
    baselines, _ = _source_baselines(args, cfg, source_ctx)
    matrix = np.asarray(cfg["schedule_contract"]["replacement_matrix_columns"], dtype=float)
    safety = set(map(str, cfg["context_contract"]["safety_pairs"]))
    output = []
    for context_index, source in enumerate(baselines):
        partition = "safety" if str(source["pair_id"]) in safety else "qualification"
        for issue in map(int, cfg["schedule_contract"]["issue_task_steps"]):
            for sign in map(int, cfg["schedule_contract"]["signs"]):
                row = copy.deepcopy(source)
                experiment_id = (
                    f"r8r11_{partition}_{context_index:02d}_s{issue}_"
                    f"{'p' if sign > 0 else 'm'}"
                )
                row.update(
                    {
                        "kind": "stage4_2r3c3t13s24d1r14r8r11_sustained_exact_target_refresh",
                        "stage": STAGE,
                        "campaign_identity": IDENTITY,
                        "controller_revision": CONTROLLER_REVISION,
                        "partition": partition,
                        "experiment_id": experiment_id,
                        "source_r8r7_baseline_experiment_id": str(source["experiment_id"]),
                        "r8r11_role": "sustained_exact_target_refresh",
                        "r8r11_direction_index": 0,
                        "r8r11_sign": sign,
                        "r8r11_requested_coordinate": (matrix[:, 0] * sign).tolist(),
                        "r8r11_matrix_digest": str(
                            cfg["schedule_contract"]["replacement_matrix_float64_le_c_sha256"]
                        ),
                        "r8r11_issue_task_step": issue,
                        "r8r11_refresh_task_step": issue + 1,
                        "r8r11_cancel_task_step": issue + 2,
                        "r8r11_zero_after_task_step": issue + 3,
                        "r8r11_allowed_in_expert_dataset": False,
                        "pair_or_history_label_available_to_controller": False,
                        "source_result_available_to_controller": False,
                        "future_measurement_count": 0,
                        "future_action_count": 0,
                        "formal_timing_unchanged": True,
                    }
                )
                output.append(row)
    return output


def _fixed_basis(result: Mapping[str, Any]) -> np.ndarray:
    values = [
        row.get("r3c3t13s16_fixed_basis_delta_field_kAt_tsc")
        for row in result["controller_trace"][:11]
        if row.get("r3c3t13s16_fixed_basis_delta_field_kAt_tsc")
    ]
    if not values or any(value != values[0] for value in values[1:]):
        raise ValueError("independent R8R11 fixed basis is not unique")
    matrix = np.asarray(values[0], dtype=float).T
    if matrix.shape != (N_COILS, 4) or not np.all(np.isfinite(matrix)):
        raise ValueError("independent R8R11 fixed basis is invalid")
    return matrix


def _offline_constructions(
    args: argparse.Namespace,
    cfg: Mapping[str, Any],
    source_ctx: r8r7.Context,
    specs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    _, source_results = _source_baselines(args, cfg, source_ctx)
    lattice = source_ctx.r8_ctx.d1r11_ctx.base_ctx.base_ctx.cfg["lattice_probe"]
    schedule = source_ctx.r8_ctx.d1r11_ctx.cfg["schedule_contract"]
    contract = cfg["controller_contract"]
    rows = []
    for spec in specs:
        source = source_results[str(spec["source_r8r7_baseline_experiment_id"])]
        issue = int(spec["r8r11_issue_task_step"])
        currents = np.asarray(source["trajectory"][issue]["currents_a_tsc"], dtype=float)
        payload = _read(_stage(args) / "variants" / f"payload_{spec['experiment_id']}.json")
        turns = np.asarray(display_to_tsc(payload["env_cfg"]["turns_display_order"]), dtype=float)
        minimum = np.asarray(payload["min_current_tsc"], dtype=float)
        maximum = np.asarray(payload["max_current_tsc"], dtype=float)
        actuator = QuantizedActuatorModel(
            minimum_current_a_tsc=tuple(minimum),
            maximum_current_a_tsc=tuple(maximum),
            max_slew_step_a=float(payload["max_delta_a"]),
            turns_tsc=tuple(turns),
        )
        field_basis = _fixed_basis(source)
        current_basis = field_basis * 1000.0 / turns[:, None]
        requested = np.asarray(spec["r8r11_requested_coordinate"], dtype=float)
        center = actuator.apply(currents, np.zeros(N_COILS))
        target_fields, actual_decimal, _ = r8r7.r8.d1r11.s21._dynamic_exact_target(
            center.card15_fields,
            tuple(Decimal(str(value)) for value in field_basis @ requested),
            search_radius=int(schedule["dynamic_exact_search_radius"]),
        )
        chosen = r8r7.r8.d1r11.s21.s16.s9.exact_stored_center_action(
            stored_fields=target_fields,
            measured_current_a_tsc=currents,
            baseline_action_norm_tsc=np.zeros(N_COILS),
            turns_tsc=turns,
            max_slew_step_a=float(payload["max_delta_a"]),
            minimum_current_a_tsc=minimum,
            maximum_current_a_tsc=maximum,
            cfg=lattice,
        )
        issued = actuator.apply(currents, chosen["action_norm_tsc"])
        actual_current = np.asarray([float(value) for value in actual_decimal]) * 1000.0 / turns
        desired_current = current_basis @ requested
        coordinate = np.linalg.lstsq(current_basis, actual_current, rcond=None)[0]
        reconstructed = current_basis @ coordinate
        cosine = float(
            np.dot(desired_current, actual_current)
            / max(np.linalg.norm(desired_current) * np.linalg.norm(actual_current), 1e-300)
        )
        residual = float(
            np.linalg.norm(actual_current - reconstructed)
            / max(np.linalg.norm(actual_current), 1e-300)
        )
        criteria = {
            "finite": bool(np.all(np.isfinite(coordinate)) and math.isfinite(cosine) and math.isfinite(residual)),
            "requested_exact": bool(
                np.array_equal(
                    requested,
                    np.asarray(cfg["schedule_contract"]["replacement_matrix_columns"], dtype=float)[:, 0]
                    * int(spec["r8r11_sign"]),
                )
            ),
            "target_reproduction": list(issued.card15_fields) == list(target_fields),
            "no_saturation": not any(issued.action_saturated),
            "no_current_clip": not any(issued.current_limit_clipped),
            "incremental_action": float(chosen["incremental_normalized_action_linf"])
            <= float(contract["maximum_incremental_normalized_action_linf"]) + 1e-12,
            "total_action": float(chosen["total_normalized_action_abs"])
            <= float(contract["maximum_total_normalized_action_abs"]) + 1e-12,
            "current_utilization": float(chosen["predicted_maximum_current_utilization"])
            <= float(contract["maximum_current_utilization"]) + 1e-12,
            "cosine": cosine >= float(contract["minimum_desired_applied_current_cosine"]) - 1e-12,
            "off_basis": residual <= float(contract["maximum_relative_off_basis_residual"]) + 1e-12,
            "actuator_gate": bool(chosen["passed"]),
        }
        rows.append(
            {
                "experiment_id": spec["experiment_id"],
                "incremental_normalized_action_linf": float(
                    chosen["incremental_normalized_action_linf"]
                ),
                "predicted_current_utilization": float(
                    chosen["predicted_maximum_current_utilization"]
                ),
                "desired_applied_current_cosine": cosine,
                "relative_off_basis_residual": residual,
                "criteria": criteria,
                "passed": bool(all(criteria.values())),
            }
        )
    return {
        "construction_count": len(rows),
        "construction_pass_count": sum(bool(row["passed"]) for row in rows),
        "maximum_incremental_normalized_action_linf": max(
            float(row["incremental_normalized_action_linf"]) for row in rows
        ),
        "maximum_predicted_current_utilization": max(
            float(row["predicted_current_utilization"]) for row in rows
        ),
        "rows": rows,
        "passed": len(rows) == 96 and all(bool(row["passed"]) for row in rows),
    }


def offline_audit(args: argparse.Namespace, cfg: Mapping[str, Any]) -> dict[str, Any]:
    stage = _stage(args)
    source_ctx = _source_context(args, cfg)
    source = r8r9._authenticate_r8r7(_source_stage(args, cfg), cfg)
    saved = _read(stage / "specs" / "all_specs.json")
    expected = _expected_specs(args, cfg, source_ctx)
    manifest = _read(stage / "stage_manifest.json")
    primary_path = stage / "analysis" / "offline_issue_preflight.json"
    primary = _read(primary_path)
    primary_summary = _read(stage / "analysis" / "offline_primary.json")
    construction = _offline_constructions(args, cfg, source_ctx, saved)
    maximum_difference = max(
        abs(
            float(construction[key])
            - float(primary[key])
        )
        for key in (
            "maximum_incremental_normalized_action_linf",
            "maximum_predicted_current_utilization",
        )
    )
    specs_exact = saved == expected
    digest_exact = _digest(saved) == str(manifest["spec_digest"])
    numerical = bool(
        construction["construction_count"] == primary["construction_count"]
        and construction["construction_pass_count"]
        == primary["construction_pass_count"]
        and maximum_difference <= 1e-12
    )
    passed = bool(
        source["passed"] and specs_exact and digest_exact and construction["passed"]
        and primary.get("passed") is True and primary_summary.get("passed") is True
        and numerical
    )
    result = {
        "schema_version": 1,
        "stage": STAGE,
        "audit_kind": "offline_independent",
        "source_authenticated": bool(source["passed"]),
        "specs_exact": specs_exact,
        "spec_digest_exact": digest_exact,
        "spec_count": len(saved),
        "construction_count": construction["construction_count"],
        "construction_pass_count": construction["construction_pass_count"],
        "maximum_incremental_normalized_action_linf": construction[
            "maximum_incremental_normalized_action_linf"
        ],
        "maximum_predicted_current_utilization": construction[
            "maximum_predicted_current_utilization"
        ],
        "maximum_primary_abs_difference": maximum_difference,
        "primary_sha256": _sha(primary_path),
        "primary_agreement": numerical,
        "passed": passed,
    }
    _write(stage / "analysis" / "offline_independent.json", result)
    return result


def _raw_rows(
    args: argparse.Namespace,
    cfg: Mapping[str, Any],
    source_ctx: r8r7.Context,
    phase: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    stage = _stage(args)
    specs = [row for row in _read(stage / "specs" / "all_specs.json") if row["partition"] == phase]
    _, source_results = _source_baselines(args, cfg, source_ctx)
    contract = cfg["controller_contract"]
    rows = []
    for spec in specs:
        result = _gzip(stage / "raw" / phase / f"{spec['experiment_id']}.json.gz")
        trajectory = result.get("trajectory") or []
        trace = result.get("controller_trace") or []
        horizon = int(spec["horizon_steps"])
        full = len(trajectory) == horizon + 1 and len(trace) == horizon
        source = source_results[str(spec["source_r8r7_baseline_experiment_id"])]
        prefix_state = bool(
            full
            and all(
                r8r7.r8.r4._semantic_state(current) == r8r7.r8.r4._semantic_state(reference)
                for current, reference in zip(
                    trajectory[: PREFIX_END + 1], source["trajectory"][: PREFIX_END + 1]
                )
            )
        )
        prefix_trace = bool(
            full
            and all(
                r8r7.r8.r4._source_trace_projection(reference, current)
                for current, reference in zip(
                    trace[:PREFIX_END], source["controller_trace"][:PREFIX_END]
                )
            )
        )
        calibration = bool(full and r8r7.r8.r4._calibration_exact(trace))
        actions = np.asarray([row.get("action_norm_tsc", []) for row in trace], dtype=float)
        currents = np.asarray([row.get("currents_a_tsc", []) for row in trajectory], dtype=float)
        event_steps = [
            int(spec[key])
            for key in (
                "r8r11_issue_task_step",
                "r8r11_refresh_task_step",
                "r8r11_cancel_task_step",
            )
        ]
        names = ["sustained_issue", "sustained_refresh", "stored_center_cancel"]
        events = [
            (trace[step].get("r3c3t13s24d1r14r8r11_event_detail") or {})
            if full else {}
            for step in event_steps
        ]
        event_exact = bool(
            full
            and all(
                trace[step].get("r3c3t13s24d1r14r8r11_event") == name
                and event.get("passed") is True
                and all(bool(value) for value in (event.get("criteria") or {}).values())
                for step, name, event in zip(event_steps, names, events)
            )
        )
        center_target_exact = bool(
            event_exact
            and events[1].get("stored_target_card15_fields")
            == events[0].get("target_card15_fields")
            and events[2].get("stored_center_card15_fields")
            == events[0].get("center_card15_fields")
            and events[2].get("issue_target_card15_fields")
            == events[0].get("target_card15_fields")
        )
        zero_steps = [
            step for step in range(PREFIX_END, horizon) if step not in set(event_steps)
        ]
        zero_exact = bool(
            full
            and actions.shape == (horizon, N_COILS)
            and currents.shape == (horizon + 1, N_COILS)
            and np.array_equal(actions[zero_steps], np.zeros((len(zero_steps), N_COILS)))
            and np.array_equal(
                currents[np.asarray(zero_steps) + 1] - currents[zero_steps],
                np.zeros((len(zero_steps), N_COILS)),
            )
        )
        finite = bool(
            full and np.all(np.isfinite(actions)) and np.all(np.isfinite(currents))
            and all(math.isfinite(float(row[key])) for row in trajectory for key in ("R", "Z", "Ip"))
            and all(
                np.all(np.isfinite(np.asarray(row.get("wire_currents_a", []), dtype=float)))
                for row in trajectory
            )
            and not any(bool(row.get("abnormal")) for row in trajectory)
        )
        forbidden = sum(
            any(
                bool(row.get(key))
                for key in (
                    "r3c3t13s24d1r14r8r11_forbidden_input_used",
                    "r3c3t13s24d1r14r8r11_pair_or_history_label_used",
                    "r3c3t13s24d1r14r8r11_future_measurement_used",
                    "r3c3t13s24d1r14r8r11_future_action_used",
                    "r3c3t13s24d1r14r8r11_source_result_used",
                    "r3c3t13s24d1r14r8r11_hidden_wire_used",
                )
            )
            for row in trace
        )
        payload = _read(stage / "variants" / f"payload_{spec['experiment_id']}.json")
        minimum, maximum = r8r7.r8.d1r11.s21.s13._current_limits_tsc(payload)
        center, half = 0.5 * (minimum + maximum), 0.5 * (maximum - minimum)
        utilization = (
            float(np.max(np.abs((currents - center) / half)))
            if currents.shape == (horizon + 1, N_COILS) else None
        )
        increments = [event.get("incremental_normalized_action_linf") for event in events]
        passed = bool(
            result.get("success") and full and prefix_state and prefix_trace and calibration
            and event_exact and center_target_exact and zero_exact and finite and forbidden == 0
            and all(value is not None and math.isfinite(float(value)) for value in increments)
            and float(increments[0])
            <= float(contract["maximum_incremental_normalized_action_linf"]) + 1e-12
            and float(increments[1])
            <= float(contract["maximum_incremental_normalized_action_linf"]) + 1e-12
            and float(increments[2])
            <= float(contract["maximum_online_cancel_incremental_linf"]) + 1e-12
            and utilization is not None
            and utilization <= float(contract["maximum_current_utilization"]) + 1e-12
        )
        rows.append(
            {
                "experiment_id": spec["experiment_id"],
                "pair_id": spec["pair_id"],
                "history_member": spec["history_member"],
                "issue_task_step": int(spec["r8r11_issue_task_step"]),
                "sign": int(spec["r8r11_sign"]),
                "runtime_success": bool(result.get("success")),
                "full_horizon": full,
                "source_prefix_state_exact": prefix_state,
                "source_prefix_trace_exact": prefix_trace,
                "calibration_exact": calibration,
                "event_exact": event_exact,
                "center_target_exact": center_target_exact,
                "zero_non_event_exact": zero_exact,
                "finite": finite,
                "forbidden_trace_count": forbidden,
                "issue_increment": increments[0],
                "refresh_increment": increments[1],
                "cancel_increment": increments[2],
                "maximum_current_utilization": utilization,
                "failure_reason": str(result.get("failure_reason") or ""),
                "passed": passed,
            }
        )
    return rows, _inventory(stage / "raw" / phase)


def raw_audit(
    args: argparse.Namespace, cfg: Mapping[str, Any], phase: str
) -> dict[str, Any]:
    stage = _stage(args)
    source_ctx = _source_context(args, cfg)
    r8r9._authenticate_r8r7(_source_stage(args, cfg), cfg)
    rows, inventory = _raw_rows(args, cfg, source_ctx, phase)
    expected = {"safety": 24, "qualification": 72}[phase]

    def maximum(key: str) -> float | None:
        values = [row.get(key) for row in rows]
        return (
            max(map(float, values))
            if values and all(value is not None and math.isfinite(float(value)) for value in values)
            else None
        )

    aggregate = {
        "runtime_success_count": sum(bool(row["runtime_success"]) for row in rows),
        "full_horizon_count": sum(bool(row["full_horizon"]) for row in rows),
        "source_prefix_state_exact_count": sum(bool(row["source_prefix_state_exact"]) for row in rows),
        "source_prefix_trace_exact_count": sum(bool(row["source_prefix_trace_exact"]) for row in rows),
        "calibration_exact_count": sum(bool(row["calibration_exact"]) for row in rows),
        "event_exact_count": sum(bool(row["event_exact"]) for row in rows),
        "center_target_exact_count": sum(bool(row["center_target_exact"]) for row in rows),
        "zero_non_event_exact_count": sum(bool(row["zero_non_event_exact"]) for row in rows),
        "finite_count": sum(bool(row["finite"]) for row in rows),
        "forbidden_trace_count": sum(int(row["forbidden_trace_count"]) for row in rows),
        "maximum_issue_increment": maximum("issue_increment"),
        "maximum_refresh_increment": maximum("refresh_increment"),
        "maximum_cancel_increment": maximum("cancel_increment"),
        "maximum_current_utilization": maximum("maximum_current_utilization"),
        "passed_count": sum(bool(row["passed"]) for row in rows),
    }
    primary_path = stage / "analysis" / f"{phase}_raw_primary.json"
    primary = _read(primary_path)
    primary_agreement = bool(
        primary.get("raw_inventory") == inventory
        and primary.get("rows") == rows
        and all(primary.get(key) == value for key, value in aggregate.items())
    )
    passed = bool(
        inventory["count"] == expected and len(rows) == expected
        and aggregate["passed_count"] == expected and primary_agreement
    )
    result = {
        "schema_version": 1,
        "stage": STAGE,
        "audit_kind": f"{phase}_raw_independent",
        "phase": phase,
        "expected_raw_count": expected,
        "raw_inventory": inventory,
        **aggregate,
        "rows": rows,
        "primary_sha256": _sha(primary_path),
        "primary_agreement": primary_agreement,
        "passed": passed,
    }
    _write(stage / "analysis" / f"{phase}_raw_independent.json", result)
    return result


def _formal_row(evaluator: Any, result: Mapping[str, Any], meta: Mapping[str, Any]) -> dict[str, Any]:
    values = np.asarray([[row["R"], row["Z"], row["Ip"]] for row in result["trajectory"]], dtype=float)
    compact = evaluator.evaluate(values)
    existing = evaluator.exact_existing_metric(result, values)
    difference = max(
        abs(float(compact[key]) - float(existing[key]))
        for key in ("formal_minimum_signed_margin", "formal_mean_signed_margin")
    )
    return {
        **dict(meta),
        "formal_contract_pass": bool(compact["formal_contract_pass"]),
        "formal_best_arrival_ms": int(compact["formal_best_arrival_ms"]),
        "formal_minimum_signed_margin": float(compact["formal_minimum_signed_margin"]),
        "formal_mean_signed_margin": float(compact["formal_mean_signed_margin"]),
        "existing_pass": bool(existing["formal_contract_pass"]),
        "existing_arrival_ms": int(existing["formal_best_arrival_ms"]),
        "maximum_margin_abs_difference": difference,
    }


def final_audit(args: argparse.Namespace, cfg: Mapping[str, Any]) -> dict[str, Any]:
    stage = _stage(args)
    source_ctx = _source_context(args, cfg)
    baseline_specs, baseline_results = _source_baselines(args, cfg, source_ctx)
    candidate_specs = _read(stage / "specs" / "all_specs.json")
    evaluators, _ = r8r7.r8.d1r11._formal_callback(
        source_ctx.r8_ctx.d1r11_ctx, [*baseline_specs, *candidate_specs]
    )
    rows = []
    for spec in baseline_specs:
        experiment_id = str(spec["experiment_id"])
        rows.append(
            _formal_row(
                evaluators[experiment_id],
                baseline_results[experiment_id],
                {
                    "kind": "baseline",
                    "experiment_id": experiment_id,
                    "pair_id": spec["pair_id"],
                    "history_member": spec["history_member"],
                    "issue_task_step": -1,
                    "sign": 0,
                },
            )
        )
    for spec in candidate_specs:
        experiment_id = str(spec["experiment_id"])
        rows.append(
            _formal_row(
                evaluators[experiment_id],
                _gzip(stage / "raw" / str(spec["partition"]) / f"{experiment_id}.json.gz"),
                {
                    "kind": "candidate",
                    "experiment_id": experiment_id,
                    "pair_id": spec["pair_id"],
                    "history_member": spec["history_member"],
                    "issue_task_step": int(spec["r8r11_issue_task_step"]),
                    "sign": int(spec["r8r11_sign"]),
                },
            )
        )
    tolerance = float(cfg["formal_contract"]["metric_equivalence_absolute_tolerance"])
    equivalence = bool(
        all(
            row["formal_contract_pass"] == row["existing_pass"]
            and row["formal_best_arrival_ms"] == row["existing_arrival_ms"]
            and float(row["maximum_margin_abs_difference"]) <= tolerance
            for row in rows
        )
    )
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault((str(row["pair_id"]), str(row["history_member"])), []).append(row)
    contexts = []
    for key, group in sorted(groups.items()):
        baseline = [row for row in group if row["kind"] == "baseline"]
        candidates = [row for row in group if row["kind"] == "candidate"]
        if len(baseline) != 1 or len(candidates) != 6:
            raise ValueError("independent R8R11 formal context coverage changed")
        base = baseline[0]
        best = max(
            candidates,
            key=lambda row: (
                float(row["formal_minimum_signed_margin"]),
                float(row["formal_mean_signed_margin"]),
                -int(row["issue_task_step"]),
                -int(row["sign"]),
            ),
        )
        oracle = max(
            [base, *candidates],
            key=lambda row: (
                float(row["formal_minimum_signed_margin"]),
                float(row["formal_mean_signed_margin"]),
                row["kind"] == "baseline",
                -int(row["issue_task_step"]),
                -int(row["sign"]),
            ),
        )
        contexts.append(
            {
                "pair_id": key[0],
                "history_member": key[1],
                "baseline": base,
                "candidates": candidates,
                "best_candidate_experiment_id": best["experiment_id"],
                "best_candidate_minimum_margin_gain": float(best["formal_minimum_signed_margin"])
                - float(base["formal_minimum_signed_margin"]),
                "failed_baseline_repaired": bool(
                    not base["formal_contract_pass"]
                    and any(row["formal_contract_pass"] for row in candidates)
                ),
                "held_oracle_formal_pass": bool(oracle["formal_contract_pass"]),
                "held_oracle_experiment_id": oracle["experiment_id"],
            }
        )
    baseline_pass = sum(bool(row["baseline"]["formal_contract_pass"]) for row in contexts)
    repairs = sum(bool(row["failed_baseline_repaired"]) for row in contexts)
    oracle_pass = sum(bool(row["held_oracle_formal_pass"]) for row in contexts)
    gains = [
        float(row["best_candidate_minimum_margin_gain"])
        for row in contexts if not row["baseline"]["formal_contract_pass"]
    ]
    candidate_pass = sum(
        bool(row["formal_contract_pass"]) for row in rows if row["kind"] == "candidate"
    )
    scientific = bool(
        baseline_pass == int(cfg["scientific_gate"]["required_baseline_formal_pass_count"])
        and len(contexts) - baseline_pass == int(cfg["scientific_gate"]["required_failed_baseline_count"])
        and repairs >= int(cfg["scientific_gate"]["minimum_repaired_failed_baseline_count"])
        and oracle_pass >= int(cfg["scientific_gate"]["minimum_held_oracle_formal_pass_count"])
        and oracle_pass > baseline_pass
    )
    route = cfg["routes"]["pass" if equivalence and scientific else "authority_fail"]
    primary_path = stage / "analysis" / "primary_summary.json"
    primary = _read(primary_path)
    numerical = bool(
        float(primary["maximum_margin_abs_difference"])
        == max(float(row["maximum_margin_abs_difference"]) for row in rows)
        and primary["failed_baseline_best_margin_gain"]
        == {"minimum": min(gains), "median": statistics.median(gains), "maximum": max(gains)}
    )
    outcome = bool(
        int(primary["baseline_formal_pass_count"]) == baseline_pass
        and int(primary["failed_baseline_count"]) == len(contexts) - baseline_pass
        and int(primary["candidate_formal_pass_trajectory_count"]) == candidate_pass
        and int(primary["repaired_failed_baseline_count"]) == repairs
        and int(primary["held_oracle_formal_pass_count"]) == oracle_pass
        and bool(primary["scientific_gate_passed"]) == scientific
        and bool(primary["formal_metric_equivalence_passed"]) == equivalence
    )
    result = {
        "schema_version": 1,
        "stage": STAGE,
        "audit_kind": "final_independent",
        "formal_metric_equivalence_passed": equivalence,
        "maximum_margin_abs_difference": max(
            float(row["maximum_margin_abs_difference"]) for row in rows
        ),
        "context_count": len(contexts),
        "baseline_formal_pass_count": baseline_pass,
        "failed_baseline_count": len(contexts) - baseline_pass,
        "candidate_formal_pass_trajectory_count": candidate_pass,
        "repaired_failed_baseline_count": repairs,
        "held_oracle_formal_pass_count": oracle_pass,
        "failed_baseline_best_margin_gain": {
            "minimum": min(gains),
            "median": statistics.median(gains),
            "maximum": max(gains),
        },
        "scientific_gate_passed": scientific,
        "route": route,
        "primary_sha256": _sha(primary_path),
        "primary_route_agreement": primary.get("route") == route,
        "primary_outcome_agreement": outcome,
        "primary_numerical_agreement": numerical,
        "passed": bool(
            equivalence and primary.get("route") == route and outcome and numerical
        ),
    }
    _write(stage / "analysis" / "final_independent.json", result)
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--r8r7-run", type=Path, required=True)
    parser.add_argument("--r8-run", type=Path, required=True)
    parser.add_argument("--r8r1-output", type=Path, required=True)
    parser.add_argument("--r8r6-run", type=Path, required=True)
    for name in (
        "source-d1r11-run", "source-r2-run", "source-r4-run", "source-r6-run",
        "source-s21-run", "source-s23r1-output", "source-s24-run", "source-d1r9-v1",
        "source-d1r9-v2", "source-d1r10-run", "source-d1r10-audit", "source-stage42r3b-run",
        "source-stage42r3c3-run", "source-stage42r3c3-bank-dir", "source-stage42r3c3t1-run",
        "source-stage42r3c3t1-audit-dir", "source-stage42r3c3t3-controller-bank",
        "q1-run", "q2-run", "q1-audit", "q2-audit", "r3b-server-audit", "r3b-snapshot-checks",
    ):
        parser.add_argument(f"--{name}", dest=name.replace("-", "_"), type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument(
        "--audit-kind",
        choices=("offline", "safety_raw", "qualification_raw", "final"),
        required=True,
    )
    return parser


def main() -> None:
    args = _parser().parse_args()
    cfg = _read(args.config.expanduser().resolve())
    if cfg.get("stage") != STAGE or cfg.get("identity") != IDENTITY:
        raise ValueError("independent R8R11 configuration identity changed")
    if args.audit_kind == "offline":
        result = offline_audit(args, cfg)
    elif args.audit_kind in {"safety_raw", "qualification_raw"}:
        result = raw_audit(args, cfg, args.audit_kind.removesuffix("_raw"))
    else:
        result = final_audit(args, cfg)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
