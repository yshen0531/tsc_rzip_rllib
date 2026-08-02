#!/usr/bin/env python3
"""Read-only immediate-effect audit of immutable T13S5 trajectories."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s5_lattice_native_split_holdout as s5,
)


STAGE = "Stage4.2R3c3T13S6"
AUDIT_REVISION = "immediate_post_queue_effect_reinterpretation_v1"
PASS_ROUTE = "IMMEDIATE_EFFECT_MODEL_CANDIDATE_NEW_HISTORY_HOLDOUT_REQUIRED"
FAIL_ROUTE = "IMMEDIATE_EFFECT_LOCAL_MAP_INSUFFICIENT_REDESIGN"


def corrected_effect_states(spec: Mapping[str, Any]) -> tuple[int, int]:
    """The wrapper modifies the post-queue action applied at the next state."""
    first = int(spec["r3c3_probe_issue_step"]) + 1
    cancel = int(spec["r3c3_probe_cancel_step"]) + 1
    if cancel != first + 1:
        raise ValueError("T13S6 corrected effect states must be adjacent")
    return first, cancel


def _effect_response(
    result: Mapping[str, Any],
    baseline: Mapping[str, Any],
    *,
    dt_s: float,
    radius_a: np.ndarray,
) -> dict[str, Any]:
    spec = result["spec"]
    first, cancel = corrected_effect_states(spec)
    feature = s5._feature_arrays(result, dt_s)
    base_feature = s5._feature_arrays(baseline, dt_s)
    current = np.asarray(
        [row["currents_a_tsc"] for row in result["trajectory"]], dtype=float
    )
    base_current = np.asarray(
        [row["currents_a_tsc"] for row in baseline["trajectory"]], dtype=float
    )
    if cancel >= len(feature) or cancel >= len(current):
        raise ValueError("T13S6 corrected effect state exceeds trajectory")
    displacement = current[[first, cancel]] - base_current[[first, cancel]]
    pre_feature = feature[:first] - base_feature[:first]
    pre_current = current[:first] - base_current[:first]
    return {
        "first_effect_state": first,
        "cancel_effect_state": cancel,
        "response_unscaled": np.concatenate(
            (
                feature[first] - base_feature[first],
                feature[cancel] - base_feature[cancel],
            )
        ),
        "input_measured_current_A": displacement.reshape(-1),
        "first_effect_current_displacement_A": displacement[0],
        "maximum_pre_effect_position_m": (
            float(np.max(np.abs(pre_feature[:, :2]))) if len(pre_feature) else 0.0
        ),
        "maximum_pre_effect_velocity_m_per_s": (
            float(np.max(np.abs(pre_feature[:, 2:4]))) if len(pre_feature) else 0.0
        ),
        "maximum_pre_effect_ip_A": (
            float(np.max(np.abs(pre_feature[:, 4]))) if len(pre_feature) else 0.0
        ),
        "maximum_pre_effect_coil_radius_units": (
            float(np.max(np.abs(pre_current) / radius_a[None, :]))
            if len(pre_current)
            else 0.0
        ),
    }


def matrix_diagnostics(
    matrix: np.ndarray,
    *,
    required_rank: int,
    maximum_condition: float,
) -> dict[str, Any]:
    rank, condition, finite, passed = s5._development_matrix_diagnostics(
        matrix,
        required_rank=required_rank,
        maximum_condition=maximum_condition,
    )
    return {
        "rank": rank,
        "condition_number": condition,
        "condition_number_finite": finite,
        "rank_condition_pass": passed,
    }


def fit_cell(
    rows: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]
) -> dict[str, Any]:
    ordered = sorted(
        rows, key=lambda row: s5.DIRECTIONS.index(str(row["probe_direction"]))
    )
    if len(ordered) != s5.N_DIRECTIONS:
        raise ValueError("T13S6 development cell direction coverage mismatch")
    x = np.asarray([row["odd_input_measured_current_A"] for row in ordered])
    y = np.asarray([row["odd_response_unscaled"] for row in ordered])
    diagnostics = matrix_diagnostics(
        x,
        required_rank=int(cfg["required_development_rank"]),
        maximum_condition=float(cfg["maximum_development_condition_number"]),
    )
    jacobian = np.linalg.lstsq(x, y, rcond=None)[0]
    residuals = []
    for row in ordered:
        for sign in s5.SIGNS:
            xi = np.asarray(row["signed_inputs_measured_current_A"][str(sign)])
            yi = np.asarray(row["signed_responses_unscaled"][str(sign)])
            residuals.append(yi - xi @ jacobian)
    floor = np.tile(np.asarray([1e-9, 1e-9, 1e-7, 1e-7, 1e-4]), 2)
    caps = np.asarray(cfg["tube_caps_unscaled"], dtype=float)
    radius = floor + float(cfg["tube_residual_multiplier"]) * np.max(
        np.abs(np.asarray(residuals)), axis=0
    )
    tube_pass = bool(np.all(radius <= caps))
    signal_pass = all(bool(row["development_signal_pass"]) for row in ordered)
    return {
        **diagnostics,
        "jacobian": jacobian.tolist(),
        "tube_radius_unscaled": radius.tolist(),
        "tube_caps_unscaled": caps.tolist(),
        "maximum_tube_to_cap_ratio": float(np.max(radius / caps)),
        "development_signal_pass": signal_pass,
        "tube_non_vacuous_pass": tube_pass,
        "passed": bool(
            diagnostics["rank_condition_pass"] and signal_pass and tube_pass
        ),
    }


def _signed_groups(
    ctx: s5.Stage42R3C3T13S5Context,
    results: Sequence[Mapping[str, Any]],
    *,
    dt_s: float,
    radius_a: np.ndarray,
) -> list[dict[str, Any]]:
    cfg = ctx.cfg["lattice_probe"]
    scales = np.asarray(cfg["response_scales"], dtype=float)
    floor_one = np.asarray([1e-9, 1e-9, 1e-7, 1e-7, 1e-4])
    floor_scaled = float(np.linalg.norm(np.tile(floor_one / scales, 2)))
    grouped = s5._group_results(results)
    rows = []
    for context_key, members in sorted(grouped.items()):
        baseline = members.get(s5.BASELINE_PROBE_ID)
        if baseline is None:
            raise ValueError("T13S6 context baseline missing")
        for window in s5.WINDOWS:
            for direction in s5.DIRECTIONS:
                signed = {
                    sign: members.get(f"{window}:{direction}:{sign}")
                    for sign in s5.SIGNS
                }
                if not all(value is not None for value in signed.values()):
                    raise ValueError("T13S6 signed member missing")
                response = {
                    sign: _effect_response(
                        value, baseline, dt_s=dt_s, radius_a=radius_a
                    )
                    for sign, value in signed.items()
                }
                plus_issue = s5._issue_trace(signed[1])
                minus_issue = s5._issue_trace(signed[-1])
                plus_fields = plus_issue["r3c3t13s5_actuator_prediction"][
                    "card15_fields"
                ]
                minus_fields = minus_issue["r3c3t13s5_actuator_prediction"][
                    "card15_fields"
                ]
                plus_center = plus_issue["r3c3t13s5_center_card15_fields"]
                minus_center = minus_issue["r3c3t13s5_center_card15_fields"]
                target_symmetry = bool(
                    plus_center == minus_center
                    and all(
                        s5._decimal_field(plus) - s5._decimal_field(center)
                        == s5._decimal_field(center) - s5._decimal_field(minus)
                        for plus, center, minus in zip(
                            plus_fields, plus_center, minus_fields
                        )
                    )
                )
                plus_first = response[1]["first_effect_current_displacement_A"]
                minus_first = response[-1]["first_effect_current_displacement_A"]
                odd_current = (plus_first - minus_first) / 2.0
                even_current = (plus_first + minus_first) / 2.0
                odd_norm = float(np.linalg.norm(odd_current))
                even_norm = float(np.linalg.norm(even_current))
                signal = bool(
                    odd_norm
                    >= float(cfg["required_observed_odd_signal_radius_l2"])
                    * float(np.linalg.norm(radius_a))
                )
                ratio = even_norm / max(odd_norm, 1e-300)
                symmetry = bool(
                    target_symmetry
                    and signal
                    and ratio <= float(cfg["maximum_observed_even_to_odd_l2"])
                )
                pre_position = max(
                    response[sign]["maximum_pre_effect_position_m"]
                    for sign in s5.SIGNS
                )
                pre_velocity = max(
                    response[sign]["maximum_pre_effect_velocity_m_per_s"]
                    for sign in s5.SIGNS
                )
                pre_ip = max(
                    response[sign]["maximum_pre_effect_ip_A"]
                    for sign in s5.SIGNS
                )
                pre_coil = max(
                    response[sign]["maximum_pre_effect_coil_radius_units"]
                    for sign in s5.SIGNS
                )
                pre_pass = bool(
                    pre_position <= float(cfg["pre_effect_position_max_m"])
                    and pre_velocity
                    <= float(cfg["pre_effect_velocity_max_m_per_s"])
                    and pre_ip <= float(cfg["pre_effect_ip_max_A"])
                    and pre_coil <= 1.0 + 1e-12
                )
                odd_input = (
                    response[1]["input_measured_current_A"]
                    - response[-1]["input_measured_current_A"]
                ) / 2.0
                odd_output = (
                    response[1]["response_unscaled"]
                    - response[-1]["response_unscaled"]
                ) / 2.0
                development_signal = bool(
                    np.linalg.norm(odd_output / np.tile(scales, 2))
                    >= float(cfg["signal_floor_multiplier"]) * floor_scaled
                )
                baseline_spec = baseline["spec"]
                rows.append(
                    {
                        "offline_role": baseline_spec["r3c3t13s5_offline_role"],
                        "stratum": baseline_spec["r3c3t13s5_stratum"],
                        "probe_window": window,
                        "probe_direction": direction,
                        "corrected_first_effect_state": response[1][
                            "first_effect_state"
                        ],
                        "corrected_cancel_effect_state": response[1][
                            "cancel_effect_state"
                        ],
                        "target_field_central_symmetry_exact": target_symmetry,
                        "observed_current_odd_l2_A": odd_norm,
                        "observed_current_even_l2_A": even_norm,
                        "observed_current_even_to_odd_l2": ratio,
                        "observed_current_signal_pass": signal,
                        "observed_current_symmetry_pass": symmetry,
                        "maximum_pre_effect_position_m": pre_position,
                        "maximum_pre_effect_velocity_m_per_s": pre_velocity,
                        "maximum_pre_effect_ip_A": pre_ip,
                        "maximum_pre_effect_coil_radius_units": pre_coil,
                        "pre_effect_causality_pass": pre_pass,
                        "development_signal_pass": development_signal,
                        "odd_input_measured_current_A": odd_input.tolist(),
                        "odd_response_unscaled": odd_output.tolist(),
                        "signed_inputs_measured_current_A": {
                            str(sign): response[sign][
                                "input_measured_current_A"
                            ].tolist()
                            for sign in s5.SIGNS
                        },
                        "signed_responses_unscaled": {
                            str(sign): response[sign]["response_unscaled"].tolist()
                            for sign in s5.SIGNS
                        },
                    }
                )
    return rows


def _validation_rows(
    rows: Sequence[Mapping[str, Any]],
    models: Mapping[tuple[str, str], Mapping[str, Any]],
    cfg: Mapping[str, Any],
) -> list[dict[str, Any]]:
    scales = np.tile(np.asarray(cfg["response_scales"], dtype=float), 2)
    floor = float(
        np.linalg.norm(
            np.tile(
                np.asarray([1e-9, 1e-9, 1e-7, 1e-7, 1e-4])
                / np.asarray(cfg["response_scales"]),
                2,
            )
        )
    )
    output = []
    for group in rows:
        key = (str(group["stratum"]), str(group["probe_window"]))
        model = models[key]
        jacobian = np.asarray(model["jacobian"], dtype=float)
        radius = np.asarray(model["tube_radius_unscaled"], dtype=float)
        for sign in s5.SIGNS:
            actual = np.asarray(
                group["signed_responses_unscaled"][str(sign)], dtype=float
            )
            model_input = np.asarray(
                group["signed_inputs_measured_current_A"][str(sign)], dtype=float
            )
            residual = actual - model_input @ jacobian
            contained = bool(np.all(np.abs(residual) <= radius + 1e-15))
            relative = float(
                np.linalg.norm(residual / scales)
                / max(np.linalg.norm(actual / scales), floor)
            )
            relative_pass = bool(
                relative
                <= float(cfg["maximum_holdout_scaled_center_relative_error"])
            )
            output.append(
                {
                    "stratum": key[0],
                    "probe_window": key[1],
                    "probe_direction": group["probe_direction"],
                    "probe_sign": sign,
                    "componentwise_contained": contained,
                    "scaled_center_relative_error": relative,
                    "scaled_center_relative_error_pass": relative_pass,
                    "pre_effect_causality_pass": bool(
                        group["pre_effect_causality_pass"]
                    ),
                    "passed": bool(
                        contained
                        and relative_pass
                        and group["pre_effect_causality_pass"]
                    ),
                }
            )
    return output


def run_audit(args: argparse.Namespace) -> dict[str, Any]:
    ctx = s5.load_stage42r3c3t13s5_config(
        args.config,
        source_stage42r3b_run=args.source_stage4_2r3b_run,
        source_stage42r3c3_run=args.source_stage4_2r3c3_run,
        source_stage42r3c3_bank_dir=args.source_stage4_2r3c3_bank_dir,
        source_stage42r3c3t1_run=args.source_stage4_2r3c3t1_run,
        source_stage42r3c3t1_audit_dir=args.source_stage4_2r3c3t1_audit_dir,
        source_stage42r3c3t3_controller_bank=(
            args.source_stage4_2r3c3t3_controller_bank
        ),
        run_dir_override=args.run_dir,
    )
    selected_pairs = s5._selected_pairs(ctx)
    specs = s5.build_control_specs(ctx, selected_pairs)
    raw_paths = [
        ctx.paths.raw / f"{spec['experiment_id']}.json.gz" for spec in specs
    ]
    if len(raw_paths) != 68 or len(list(ctx.paths.raw.glob("*.json.gz"))) != 68:
        raise ValueError("T13S6 exact raw inventory count mismatch")
    results = []
    raw_rows = []
    for path, spec in zip(raw_paths, specs):
        if not s5._result_complete(path, spec):
            raise ValueError(f"T13S6 raw identity mismatch: {path}")
        result = s5.t11.t1.r3c3.read_json_gz(path)
        results.append(result)
        raw_rows.append(
            {
                "path": path.name,
                "size_bytes": path.stat().st_size,
                "sha256": s5._sha256(path),
            }
        )
    raw_rows.sort(key=lambda row: row["path"])
    raw_digest = s5._canonical_digest(raw_rows)
    source_audit = s5.t11.t1.r3c3.read_json(args.source_audit)
    source_certified = bool(
        source_audit.get("certified_scientific_result")
        and source_audit.get("control_raw_identity_exact")
        and source_audit.get("raw_inventory", {}).get("digest") == raw_digest
    )
    if not source_certified:
        raise ValueError("T13S6 source T13S5 audit authentication failed")

    payload = s5.t11.t1.r3c3.read_json(
        ctx.paths.variants / f"payload_{results[0]['experiment_id']}.json"
    )
    from tsc_rzip_rllib.core.coil_order import display_to_tsc

    turns = np.asarray(
        display_to_tsc(payload["env_cfg"]["turns_display_order"]), dtype=float
    )
    radius_a = s5.OUTPUT_GRID_KAT * 1000.0 / turns
    _, _, dt_s = s5.s1._stage34_identity(ctx)
    signed = _signed_groups(ctx, results, dt_s=dt_s, radius_a=radius_a)
    development = [row for row in signed if row["offline_role"] == "development"]
    validation = [row for row in signed if row["offline_role"] == "blind_holdout"]
    if len(development) != 16 or len(validation) != 16:
        raise ValueError("T13S6 signed role split mismatch")

    models = {}
    model_rows = []
    for stratum in ("easy", "hard"):
        for window in s5.WINDOWS:
            cell = [
                row
                for row in development
                if row["stratum"] == stratum and row["probe_window"] == window
            ]
            model = fit_cell(cell, ctx.cfg["lattice_probe"])
            model = {"stratum": stratum, "probe_window": window, **model}
            models[(stratum, window)] = model
            model_rows.append(model)
    validation_rows = _validation_rows(
        validation, models, ctx.cfg["lattice_probe"]
    )

    def count(rows: Sequence[Mapping[str, Any]], key: str) -> int:
        return sum(bool(row.get(key)) for row in rows)

    trace_identity_count = 0
    forbidden_count = 0
    for result in results:
        baseline = result["spec"]["r3c3_probe_id"] == s5.BASELINE_PROBE_ID
        events = [
            row.get("r3c3t13s5_lattice_event")
            for row in result["controller_trace"]
            if row.get("r3c3t13s5_lattice_event") != "none"
        ]
        trace_identity_count += int(
            events == ([] if baseline else ["issue", "cancel"])
        )
        forbidden_count += sum(
            any(
                bool(row.get(key))
                for key in (
                    "pair_or_history_label_used",
                    "source_result_used",
                    "source_action_used",
                    "source_coil_current_used",
                    "source_wire_current_used",
                    "current_run_future_used",
                    "future_measurement_used",
                    "hidden_wire_used",
                )
            )
            for row in result["controller_trace"]
        )
    summary = {
        "raw_identity_pass_count": len(results),
        "raw_expected": 68,
        "raw_total_bytes": sum(row["size_bytes"] for row in raw_rows),
        "raw_inventory_digest": raw_digest,
        "source_t13s5_audit_certified": source_certified,
        "trace_identity_pass_count": trace_identity_count,
        "trace_identity_expected": 68,
        "signed_group_count": len(signed),
        "target_field_symmetry_pass_count": count(
            signed, "target_field_central_symmetry_exact"
        ),
        "corrected_pre_effect_causality_pass_count": count(
            signed, "pre_effect_causality_pass"
        ),
        "observed_current_signal_pass_count": count(
            signed, "observed_current_signal_pass"
        ),
        "observed_current_symmetry_pass_count": count(
            signed, "observed_current_symmetry_pass"
        ),
        "development_group_count": len(development),
        "development_signal_pass_count": count(
            development, "development_signal_pass"
        ),
        "model_cell_count": len(model_rows),
        "model_rank_condition_pass_count": count(
            model_rows, "rank_condition_pass"
        ),
        "model_tube_pass_count": count(model_rows, "tube_non_vacuous_pass"),
        "maximum_finite_condition_number": max(
            (
                float(row["condition_number"])
                for row in model_rows
                if row["condition_number"] is not None
            ),
            default=None,
        ),
        "nonfinite_condition_count": sum(
            not bool(row["condition_number_finite"]) for row in model_rows
        ),
        "maximum_tube_to_cap_ratio": max(
            float(row["maximum_tube_to_cap_ratio"]) for row in model_rows
        ),
        "consumed_validation_row_count": len(validation_rows),
        "validation_containment_pass_count": count(
            validation_rows, "componentwise_contained"
        ),
        "validation_relative_error_pass_count": count(
            validation_rows, "scaled_center_relative_error_pass"
        ),
        "validation_pre_effect_causality_pass_count": count(
            validation_rows, "pre_effect_causality_pass"
        ),
        "maximum_validation_scaled_relative_error": max(
            float(row["scaled_center_relative_error"])
            for row in validation_rows
        ),
        "forbidden_model_or_trace_input_count": forbidden_count,
    }
    passed = bool(
        summary["raw_identity_pass_count"] == summary["raw_expected"] == 68
        and summary["trace_identity_pass_count"]
        == summary["trace_identity_expected"]
        == 68
        and summary["signed_group_count"]
        == summary["target_field_symmetry_pass_count"]
        == summary["corrected_pre_effect_causality_pass_count"]
        == summary["observed_current_signal_pass_count"]
        == summary["observed_current_symmetry_pass_count"]
        == 32
        and summary["development_group_count"]
        == summary["development_signal_pass_count"]
        == 16
        and summary["model_cell_count"]
        == summary["model_rank_condition_pass_count"]
        == summary["model_tube_pass_count"]
        == 4
        and summary["consumed_validation_row_count"]
        == summary["validation_containment_pass_count"]
        == summary["validation_relative_error_pass_count"]
        == summary["validation_pre_effect_causality_pass_count"]
        == 32
        and summary["forbidden_model_or_trace_input_count"] == 0
    )
    return {
        "schema_version": 1,
        "stage": STAGE,
        "audit_revision": AUDIT_REVISION,
        "source_stage": s5.STAGE,
        "source_run": str(args.run_dir),
        "source_audit": str(args.source_audit),
        "source_audit_sha256": s5._sha256(args.source_audit),
        "formal_timing_unchanged": True,
        "corrected_effect_contract": "post_queue_probe_effects_at_issue_plus_one",
        "former_holdout_is_blind": False,
        "consumed_validation_only": True,
        "real_tsc_executed": False,
        "controller_or_plant_step_executed": False,
        "probe_trajectories_allowed_in_expert_dataset": False,
        "real_mpc_authorized": False,
        "bc_dagger_or_rl_allowed": False,
        "summary": summary,
        "model_cells": model_rows,
        "signed_group_results": signed,
        "consumed_validation_results": validation_rows,
        "raw_inventory": raw_rows,
        "passed": passed,
        "route": PASS_ROUTE if passed else FAIL_ROUTE,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--source-stage4-2r3b-run", required=True, type=Path)
    parser.add_argument("--source-stage4-2r3c3-run", required=True, type=Path)
    parser.add_argument("--source-stage4-2r3c3-bank-dir", required=True, type=Path)
    parser.add_argument("--source-stage4-2r3c3t1-run", required=True, type=Path)
    parser.add_argument("--source-stage4-2r3c3t1-audit-dir", required=True, type=Path)
    parser.add_argument(
        "--source-stage4-2r3c3t3-controller-bank", required=True, type=Path
    )
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--source-audit", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = run_audit(args)
    s5.t11.t1.r3c3.atomic_write_json(args.output, output)
    print(
        json.dumps(
            {
                "output": str(args.output),
                "sha256": s5._sha256(args.output),
                "passed": output["passed"],
                "route": output["route"],
                "summary": output["summary"],
            },
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
    )


if __name__ == "__main__":
    main()
