#!/usr/bin/env python3
"""Bounded zero-TSC development search for an S23 replacement schedule."""

from __future__ import annotations

import argparse
from collections import Counter
from decimal import Decimal
import hashlib
import itertools
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from docs.codex.audit_tools import (
    stage4_2r3c3t13s23_sequential_hadamard_lattice_preflight as s23,
)


STAGE = "Stage4.2R3c3T13S23D1"
IDENTITY = "bounded_ternary_exact_card15_schedule_redesign_search_v1"
N_COILS = 14
DIRECTIONS = s23.DIRECTIONS


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _digest(value: Any) -> str:
    text = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False,
    )
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(
            value, indent=2, sort_keys=True, ensure_ascii=False,
            allow_nan=False,
        ) + "\n",
        encoding="utf-8",
    )


def _validate_design(cfg: Mapping[str, Any]) -> None:
    source = cfg["source_contract"]
    search = cfg["search_contract"]
    formal = cfg["formal_contract"]
    execution = cfg["execution_contract"]
    scope = cfg["scientific_scope"]
    if (
        int(cfg.get("schema_version", -1)) != 1
        or cfg.get("stage") != STAGE
        or cfg.get("identity") != IDENTITY
        or cfg.get("package_revision")
        != "r42r3c3t13s23d1_bounded_schedule_redesign_search_v1"
        or cfg.get("selection_status")
        != "frozen_after_s23_failure_before_d1_implementation_or_candidate_computation"
        or cfg.get("design_document_sha256")
        != "379541be5807bb3023b70565f24803f26c92f32a80961cbb1be27c8ff0e2cb83"
        or str(source["s21_package_commit"]) != "98dc353"
        or int(source["s21_raw_count"]) != 360
        or int(source["s21_raw_total_bytes"]) != 21083271
        or int(source["expected_baseline_formal_pass_count"]) != 16
        or int(source["expected_probe_formal_pass_count"]) != 99
        or source["required_s22_route"]
        != "AFFINE_STATE10_AUTHORITY_FAIL_SEQUENTIAL_MODEL_REQUIRED"
        or int(source["required_s22_optimistic_affine_feasible"]) != 16
        or source["required_s23_route"]
        != "SEQUENTIAL_HADAMARD_LATTICE_PREFLIGHT_FAIL_SCHEDULE_REDESIGN"
        or int(source["required_s23_issue_pass"]) != 1920
        or int(source["required_s23_cancel_pass"]) != 3720
        or tuple(search["context_key_fields"]) != ("pair_id", "history_member")
        or int(search["expected_context_count"]) != 40
        or search["baseline_probe_id"] != "lattice_baseline"
        or tuple(search["ordered_directions"]) != DIRECTIONS
        or tuple(map(int, search["template_alphabet"])) != (-1, 0, 1)
        or tuple(map(float, search["amplitudes"])) != (0.25, 0.5, 0.75, 1.0)
        or int(search["signed_template_count"]) != 320
        or int(search["canonical_sign_pair_count"]) != 160
        or tuple(map(int, search["candidate_issue_steps"])) != tuple(range(10, 20))
        or int(search["adjacent_cancel_offset"]) != 1
        or int(search["minimum_issue_step_separation"]) != 2
        or int(search["selected_knot_count"]) != 4
        or int(search["dynamic_exact_search_radius"]) != 16
        or tuple(
            int(search[key]) for key in (
                "primary_sequence_rows", "central_sign_primary_rows",
                "central_sign_sentinel_rows", "total_sequence_rows",
            )
        ) != (16, 8, 8, 24)
        or int(search["random_seed"]) != 423231
        or int(search["maximum_candidate_schedules_per_knot_set"]) != 20000
        or float(search["maximum_absolute_coordinate_error"]) != 0.07
        or float(search["maximum_inactive_coordinate_abs"]) != 0.07
        or float(search["minimum_active_absolute_coordinate"]) != 0.18
        or float(search["minimum_desired_applied_current_cosine"]) != 0.98
        or float(search["maximum_relative_off_basis_residual"]) != 0.10
        or float(search["maximum_incremental_normalized_action_linf"]) != 0.25
        or float(search["maximum_total_normalized_action_abs"]) != 1.0
        or float(search["maximum_current_utilization"]) != 0.55
        or int(search["required_global_rank"]) != 16
        or float(search["maximum_global_normalized_condition"]) != 3.0
        or int(search["required_slot_rank"]) != 4
        or float(search["maximum_slot_normalized_condition"]) != 3.0
        or float(search["minimum_late_column_residual_outside_slot0_span"]) != 0.5
        or not bool(search["require_decimal_exact_central_target_symmetry"])
        or not bool(search["require_exact_stored_center_cancellation"])
        or not bool(search["require_exact_zero_target_jump_net"])
        or tuple(
            int(formal[key]) for key in (
                "normal_arrival_deadline_step", "normal_hold_through_step",
                "weak_arrival_deadline_step", "weak_hold_through_step",
                "arrival_streak_steps",
            )
        ) != (25, 35, 27, 37, 3)
        or float(formal["position_tolerance_m"]) != 0.03
        or float(formal["speed_tolerance_m_per_s"]) != 0.1
        or float(formal["ip_tolerance_A"]) != 10000.0
        or bool(formal["arrival_deadline_expansion_allowed"])
        or not bool(execution["server_side_only_for_large_raw"])
        or not bool(execution["read_raw_in_place"])
        or int(execution["new_raw_count"]) != 0
        or any(bool(execution[key]) for key in (
            "ray_executed", "gotsc_executed", "tsc_executed",
            "controller_executed", "snapshot_creation_allowed",
        ))
        or int(execution["plant_steps_executed"]) != 0
        or not bool(scope["adaptive_development_search"])
        or bool(scope["formal_outcomes_used_as_search_objective"])
        or bool(scope["plant_response_simulated"])
        or bool(scope["real_mpc_executed"])
        or bool(scope["global_plant_reachability_claimed"])
        or bool(scope["hidden_history_robustness_claimed"])
        or not bool(scope["candidate_authorizes_s23r1_only"])
        or bool(scope["candidate_authorizes_real_campaign"])
        or bool(scope["probe_trajectories_are_demonstrations"])
        or bool(scope["bc_dagger_or_rl_allowed"])
    ):
        raise ValueError("T13S23D1 frozen design changed")


def _template_id(amplitude: float, vector: Sequence[int]) -> str:
    labels = {-1: "m", 0: "z", 1: "p"}
    return "a%04d_%s" % (
        int(round(1000.0 * amplitude)),
        "".join(labels[int(value)] for value in vector),
    )


def _templates(cfg: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    search = cfg["search_contract"]
    signed = []
    canonical = []
    for amplitude in map(float, search["amplitudes"]):
        for vector in itertools.product((-1, 0, 1), repeat=4):
            if not any(vector):
                continue
            row = {
                "template_id": _template_id(amplitude, vector),
                "amplitude": amplitude,
                "integer_vector": list(map(int, vector)),
                "coordinate": [amplitude * int(value) for value in vector],
                "negative_template_id": _template_id(
                    amplitude, tuple(-int(value) for value in vector)
                ),
            }
            signed.append(row)
            first = next(value for value in vector if value)
            if first == 1:
                canonical.append(row)
    if (
        len(signed) != int(search["signed_template_count"])
        or len(canonical) != int(search["canonical_sign_pair_count"])
        or len({row["template_id"] for row in signed}) != len(signed)
    ):
        raise ValueError("T13S23D1 template catalog changed")
    return signed, canonical


def _candidate_knot_sets(
    steps: Sequence[int], cfg: Mapping[str, Any]
) -> list[tuple[int, ...]]:
    search = cfg["search_contract"]
    separation = int(search["minimum_issue_step_separation"])
    count = int(search["selected_knot_count"])
    return [
        tuple(map(int, values))
        for values in itertools.combinations(sorted(map(int, steps)), count)
        if all(b - a >= separation for a, b in zip(values, values[1:]))
    ]


def _authenticate_s23(
    output: Path, config_path: Path, implementation_path: Path,
    cfg: Mapping[str, Any],
) -> dict[str, Any]:
    source = cfg["source_contract"]
    if output.name != str(source["s23_output_name"]):
        raise ValueError("immutable S23 output name mismatch")
    paths = {
        "detailed": output / "stage4_2r3c3t13s23_sequential_lattice_preflight_v1.json",
        "summary": output / "stage4_2r3c3t13s23_summary_v1.json",
        "manifest": output / "stage4_2r3c3t13s23_manifest_v1.json",
    }
    expected = {
        "detailed": source["s23_detailed_sha256"],
        "summary": source["s23_summary_sha256"],
        "manifest": source["s23_manifest_sha256"],
    }
    hashes = {name: _sha256(path) for name, path in paths.items()}
    if (
        _sha256(config_path) != str(source["s23_config_sha256"])
        or _sha256(implementation_path)
        != str(source["s23_implementation_sha256"])
        or any(hashes[name] != str(expected[name]) for name in expected)
    ):
        raise ValueError("immutable S23 source hash mismatch")
    summary = _read_json(paths["summary"])
    manifest = _read_json(paths["manifest"])
    if (
        summary.get("route") != source["required_s23_route"]
        or bool(summary.get("primary_pass"))
        or int(summary.get("source_raw_authentication_count", -1)) != 360
        or int(summary.get("baseline_formal_reproduction_count", -1)) != 40
        or int(summary.get("measured_probe_formal_reproduction_count", -1)) != 320
        or int(summary.get("issue_gate_pass", -1))
        != int(source["required_s23_issue_pass"])
        or int(summary.get("cancellation_gate_pass", -1))
        != int(source["required_s23_cancel_pass"])
        or bool(manifest.get("ray_gotsc_tsc_plant_or_controller_executed"))
        or int(manifest.get("new_raw_files_created", -1)) != 0
    ):
        raise ValueError("immutable S23 scientific result changed")
    return {
        "paths": {name: str(path) for name, path in paths.items()},
        "hashes": hashes,
        "route": summary["route"],
        "issue_gate_pass": int(summary["issue_gate_pass"]),
        "cancellation_gate_pass": int(summary["cancellation_gate_pass"]),
    }


def _context_name(key: tuple[str, str]) -> str:
    return f"{key[0]}::{key[1]}"


def _issue_construction(
    *, ctx: Any, baseline: Mapping[str, Any], issue_step: int,
    desired_coordinate: np.ndarray, field_basis: np.ndarray,
    turns: np.ndarray, minimum: np.ndarray, maximum: np.ndarray,
    max_delta: float, actuator: Any, cfg: Mapping[str, Any],
) -> dict[str, Any]:
    s21 = s23.s22.s21
    search = cfg["search_contract"]
    trajectory = baseline["trajectory"]
    trace = baseline["controller_trace"]
    current = np.asarray(trajectory[issue_step]["currents_a_tsc"], dtype=float)
    baseline_action = np.asarray(
        trace[issue_step]["r3c3t13s9_baseline_action_norm_tsc"], dtype=float
    )
    center_fields = tuple(map(
        str, trace[issue_step]["r3c3t13s9_center_card15_fields"]
    ))
    center = actuator.apply(current, baseline_action)
    center_reproduction = list(center.card15_fields) == list(center_fields)
    desired_field = field_basis @ desired_coordinate
    target_fields, actual_decimal, integer_counts = s21._dynamic_exact_target(
        center_fields,
        s23._decimal_vector(desired_field),
        search_radius=int(search["dynamic_exact_search_radius"]),
    )
    chosen = s21.s16.s9.exact_stored_center_action(
        stored_fields=target_fields,
        measured_current_a_tsc=current,
        baseline_action_norm_tsc=baseline_action,
        turns_tsc=turns,
        max_slew_step_a=max_delta,
        minimum_current_a_tsc=minimum,
        maximum_current_a_tsc=maximum,
        cfg=ctx.base_ctx.cfg["lattice_probe"],
    )
    issued = actuator.apply(current, chosen["action_norm_tsc"])
    target_reproduction = list(issued.card15_fields) == list(target_fields)
    current_basis = field_basis * 1000.0 / turns[:, None]
    actual_field = np.asarray([float(value) for value in actual_decimal], dtype=float)
    actual_current = actual_field * 1000.0 / turns
    desired_current = current_basis @ desired_coordinate
    coordinate, _, _, _ = np.linalg.lstsq(current_basis, actual_current, rcond=None)
    reconstructed = current_basis @ coordinate
    desired_norm = float(np.linalg.norm(desired_current))
    actual_norm = float(np.linalg.norm(actual_current))
    cosine = float(
        np.dot(desired_current, actual_current)
        / max(desired_norm * actual_norm, 1e-300)
    )
    off_basis = float(
        np.linalg.norm(actual_current - reconstructed) / max(actual_norm, 1e-300)
    )
    error = np.abs(coordinate - desired_coordinate)
    active = np.abs(desired_coordinate) > 0.0
    inactive = ~active
    maximum_error = float(np.max(error))
    inactive_abs = float(np.max(np.abs(coordinate[inactive]))) if np.any(inactive) else 0.0
    active_sign = bool(np.all(
        np.sign(coordinate[active]) == np.sign(desired_coordinate[active])
    ))
    minimum_active = float(np.min(np.abs(coordinate[active])))
    criteria = {
        "finite": bool(
            np.all(np.isfinite(coordinate))
            and np.all(np.isfinite(actual_field))
            and math.isfinite(cosine) and math.isfinite(off_basis)
        ),
        "center_reproduction": center_reproduction,
        "target_reproduction": target_reproduction,
        "exact_fields": bool(
            len(target_fields) == N_COILS
            and all(len(field) == 10 for field in target_fields)
        ),
        "no_saturation": not any(issued.action_saturated),
        "no_current_clip": not any(issued.current_limit_clipped),
        "active_sign": active_sign,
        "minimum_active": minimum_active
        >= float(search["minimum_active_absolute_coordinate"]) - 1e-12,
        "coordinate_error": maximum_error
        <= float(search["maximum_absolute_coordinate_error"]) + 1e-12,
        "inactive_leakage": inactive_abs
        <= float(search["maximum_inactive_coordinate_abs"]) + 1e-12,
        "cosine": cosine
        >= float(search["minimum_desired_applied_current_cosine"]) - 1e-12,
        "off_basis": off_basis
        <= float(search["maximum_relative_off_basis_residual"]) + 1e-12,
        "incremental_action": float(chosen["incremental_normalized_action_linf"])
        <= float(search["maximum_incremental_normalized_action_linf"]) + 1e-12,
        "total_action": float(chosen["total_normalized_action_abs"])
        <= float(search["maximum_total_normalized_action_abs"]) + 1e-12,
        "current_utilization": float(chosen["predicted_maximum_current_utilization"])
        <= float(search["maximum_current_utilization"]) + 1e-12,
        "source_action_gate": bool(chosen["passed"]),
    }
    return {
        "passed": all(criteria.values()),
        "criteria": criteria,
        "coordinate": coordinate,
        "center_fields": center_fields,
        "target_fields": tuple(target_fields),
        "integer_counts": tuple(map(int, integer_counts)),
        "maximum_absolute_coordinate_error": maximum_error,
        "maximum_inactive_coordinate_abs": inactive_abs,
        "minimum_active_absolute_coordinate": minimum_active,
        "desired_applied_current_cosine": cosine,
        "relative_off_basis_residual": off_basis,
        "incremental_normalized_action_linf": float(
            chosen["incremental_normalized_action_linf"]
        ),
        "total_normalized_action_abs": float(chosen["total_normalized_action_abs"]),
        "predicted_current_utilization": float(
            chosen["predicted_maximum_current_utilization"]
        ),
    }


def _cancel_construction(
    *, ctx: Any, baseline: Mapping[str, Any], issue_step: int,
    turns: np.ndarray, minimum: np.ndarray, maximum: np.ndarray,
    max_delta: float, actuator: Any, cfg: Mapping[str, Any],
) -> dict[str, Any]:
    s21 = s23.s22.s21
    search = cfg["search_contract"]
    cancel_step = issue_step + int(search["adjacent_cancel_offset"])
    trajectory = baseline["trajectory"]
    trace = baseline["controller_trace"]
    issue_current = np.asarray(trajectory[issue_step]["currents_a_tsc"], dtype=float)
    issue_baseline = np.asarray(
        trace[issue_step]["r3c3t13s9_baseline_action_norm_tsc"], dtype=float
    )
    center_fields = tuple(map(
        str, trace[issue_step]["r3c3t13s9_center_card15_fields"]
    ))
    center = actuator.apply(issue_current, issue_baseline)
    cancel_current = np.asarray(trajectory[cancel_step]["currents_a_tsc"], dtype=float)
    cancel_baseline = np.asarray(
        trace[cancel_step]["r3c3t13s9_baseline_action_norm_tsc"], dtype=float
    )
    chosen = s21.s16.s9.exact_stored_center_action(
        stored_fields=center_fields,
        measured_current_a_tsc=cancel_current,
        baseline_action_norm_tsc=cancel_baseline,
        turns_tsc=turns,
        max_slew_step_a=max_delta,
        minimum_current_a_tsc=minimum,
        maximum_current_a_tsc=maximum,
        cfg=ctx.base_ctx.cfg["lattice_probe"],
    )
    cancelled = actuator.apply(cancel_current, chosen["action_norm_tsc"])
    criteria = {
        "center_reproduction": list(center.card15_fields) == list(center_fields),
        "target_exact": list(cancelled.card15_fields) == list(center_fields),
        "exact_fields": all(len(field) == 10 for field in center_fields),
        "no_saturation": not any(cancelled.action_saturated),
        "no_current_clip": not any(cancelled.current_limit_clipped),
        "incremental_action": float(chosen["incremental_normalized_action_linf"])
        <= float(search["maximum_incremental_normalized_action_linf"]) + 1e-12,
        "total_action": float(chosen["total_normalized_action_abs"])
        <= float(search["maximum_total_normalized_action_abs"]) + 1e-12,
        "current_utilization": float(chosen["predicted_maximum_current_utilization"])
        <= float(search["maximum_current_utilization"]) + 1e-12,
        "source_action_gate": bool(chosen["passed"]),
    }
    return {
        "passed": all(criteria.values()),
        "criteria": criteria,
        "incremental_normalized_action_linf": float(
            chosen["incremental_normalized_action_linf"]
        ),
        "total_normalized_action_abs": float(chosen["total_normalized_action_abs"]),
        "predicted_current_utilization": float(
            chosen["predicted_maximum_current_utilization"]
        ),
    }


def _update_extrema(extrema: dict[str, float], row: Mapping[str, Any]) -> None:
    extrema["maximum_absolute_coordinate_error"] = max(
        extrema["maximum_absolute_coordinate_error"],
        float(row["maximum_absolute_coordinate_error"]),
    )
    extrema["maximum_inactive_coordinate_abs"] = max(
        extrema["maximum_inactive_coordinate_abs"],
        float(row["maximum_inactive_coordinate_abs"]),
    )
    extrema["minimum_active_absolute_coordinate"] = min(
        extrema["minimum_active_absolute_coordinate"],
        float(row["minimum_active_absolute_coordinate"]),
    )
    extrema["minimum_desired_applied_current_cosine"] = min(
        extrema["minimum_desired_applied_current_cosine"],
        float(row["desired_applied_current_cosine"]),
    )
    extrema["maximum_relative_off_basis_residual"] = max(
        extrema["maximum_relative_off_basis_residual"],
        float(row["relative_off_basis_residual"]),
    )
    extrema["maximum_incremental_normalized_action_linf"] = max(
        extrema["maximum_incremental_normalized_action_linf"],
        float(row["incremental_normalized_action_linf"]),
    )
    extrema["maximum_total_normalized_action_abs"] = max(
        extrema["maximum_total_normalized_action_abs"],
        float(row["total_normalized_action_abs"]),
    )
    extrema["maximum_predicted_current_utilization"] = max(
        extrema["maximum_predicted_current_utilization"],
        float(row["predicted_current_utilization"]),
    )


def _new_extrema() -> dict[str, float]:
    return {
        "maximum_absolute_coordinate_error": 0.0,
        "maximum_inactive_coordinate_abs": 0.0,
        "minimum_active_absolute_coordinate": math.inf,
        "minimum_desired_applied_current_cosine": math.inf,
        "maximum_relative_off_basis_residual": 0.0,
        "maximum_incremental_normalized_action_linf": 0.0,
        "maximum_total_normalized_action_abs": 0.0,
        "maximum_predicted_current_utilization": 0.0,
    }


def _build_catalog(
    ctx: Any, contexts: Mapping[tuple[str, str], Mapping[str, Any]],
    basis: Mapping[tuple[str, str], tuple[Any, ...]], cfg: Mapping[str, Any],
) -> tuple[dict[int, list[dict[str, Any]]], list[dict[str, Any]]]:
    _, canonical = _templates(cfg)
    catalog: dict[int, list[dict[str, Any]]] = {}
    summaries = []
    for step in map(int, cfg["search_contract"]["candidate_issue_steps"]):
        feasible = []
        criterion_pass = Counter()
        signed_evaluations = 0
        for template in canonical:
            desired_plus = np.asarray(template["coordinate"], dtype=float)
            desired_minus = -desired_plus
            actual_by_context: dict[str, dict[str, list[float]]] = {}
            pair_pass = True
            symmetry_pass = True
            extrema = _new_extrema()
            for key in sorted(contexts):
                baseline = contexts[key]["baseline"]
                (
                    field_basis, turns, minimum, maximum, max_delta, actuator, _,
                ) = basis[key]
                plus = _issue_construction(
                    ctx=ctx, baseline=baseline, issue_step=step,
                    desired_coordinate=desired_plus, field_basis=field_basis,
                    turns=turns, minimum=minimum, maximum=maximum,
                    max_delta=max_delta, actuator=actuator, cfg=cfg,
                )
                minus = _issue_construction(
                    ctx=ctx, baseline=baseline, issue_step=step,
                    desired_coordinate=desired_minus, field_basis=field_basis,
                    turns=turns, minimum=minimum, maximum=maximum,
                    max_delta=max_delta, actuator=actuator, cfg=cfg,
                )
                signed_evaluations += 2
                for row in (plus, minus):
                    for name, passed in row["criteria"].items():
                        criterion_pass[name] += bool(passed)
                    _update_extrema(extrema, row)
                pair_pass = pair_pass and bool(plus["passed"]) and bool(minus["passed"])
                center = tuple(
                    s23.s22.s21.s16.s9._decimal_field(value)
                    for value in plus["center_fields"]
                )
                plus_target = tuple(
                    s23.s22.s21.s16.s9._decimal_field(value)
                    for value in plus["target_fields"]
                )
                minus_target = tuple(
                    s23.s22.s21.s16.s9._decimal_field(value)
                    for value in minus["target_fields"]
                )
                exact_symmetry = bool(
                    plus["center_fields"] == minus["center_fields"]
                    and all(p + m == 2 * c for p, m, c in zip(
                        plus_target, minus_target, center
                    ))
                )
                symmetry_pass = symmetry_pass and exact_symmetry
                actual_by_context[_context_name(key)] = {
                    "positive": plus["coordinate"].tolist(),
                    "negative": minus["coordinate"].tolist(),
                }
            if pair_pass and symmetry_pass:
                feasible.append({
                    "pair_id": template["template_id"],
                    "positive_template_id": template["template_id"],
                    "negative_template_id": template["negative_template_id"],
                    "amplitude": float(template["amplitude"]),
                    "canonical_integer_vector": template["integer_vector"],
                    "positive_coordinate": template["coordinate"],
                    "negative_coordinate": (-desired_plus).tolist(),
                    "actual_by_context": actual_by_context,
                    "extrema": extrema,
                    "exact_target_symmetry_contexts": len(contexts),
                })
        catalog[step] = feasible
        summaries.append({
            "issue_step": step,
            "cancel_step": step + 1,
            "signed_event_evaluations": signed_evaluations,
            "feasible_sign_pairs": len(feasible),
            "feasible_signed_templates": 2 * len(feasible),
            "criterion_pass_counts": dict(sorted(criterion_pass.items())),
            "feasible_pair_ids": [row["pair_id"] for row in feasible],
        })
    return catalog, summaries


def _cancellation_catalog(
    ctx: Any, contexts: Mapping[tuple[str, str], Mapping[str, Any]],
    basis: Mapping[tuple[str, str], tuple[Any, ...]], cfg: Mapping[str, Any],
) -> list[dict[str, Any]]:
    output = []
    for step in map(int, cfg["search_contract"]["candidate_issue_steps"]):
        passed = 0
        criteria = Counter()
        maximum_increment = 0.0
        maximum_total = 0.0
        maximum_current = 0.0
        for key in sorted(contexts):
            baseline = contexts[key]["baseline"]
            _, turns, minimum, maximum, max_delta, actuator, _ = basis[key]
            row = _cancel_construction(
                ctx=ctx, baseline=baseline, issue_step=step, turns=turns,
                minimum=minimum, maximum=maximum, max_delta=max_delta,
                actuator=actuator, cfg=cfg,
            )
            passed += bool(row["passed"])
            for name, value in row["criteria"].items():
                criteria[name] += bool(value)
            maximum_increment = max(
                maximum_increment, float(row["incremental_normalized_action_linf"])
            )
            maximum_total = max(
                maximum_total, float(row["total_normalized_action_abs"])
            )
            maximum_current = max(
                maximum_current, float(row["predicted_current_utilization"])
            )
        output.append({
            "issue_step": step,
            "cancel_step": step + 1,
            "passed_contexts": passed,
            "required_contexts": len(contexts),
            "all_contexts_pass": passed == len(contexts),
            "criterion_pass_counts": dict(sorted(criteria.items())),
            "maximum_incremental_normalized_action_linf": maximum_increment,
            "maximum_total_normalized_action_abs": maximum_total,
            "maximum_predicted_current_utilization": maximum_current,
        })
    return output


def _pair_orientation(row: Mapping[str, Any], orientation: int) -> dict[str, Any]:
    if orientation not in (-1, 1):
        raise ValueError("orientation must be signed")
    return {
        "pair_id": row["pair_id"],
        "orientation": orientation,
        "template_id": row[
            "positive_template_id" if orientation == 1 else "negative_template_id"
        ],
        "requested_coordinate": row[
            "positive_coordinate" if orientation == 1 else "negative_coordinate"
        ],
    }


def _actual_for(
    pair: Mapping[str, Any], orientation: int, context_name: str
) -> np.ndarray:
    label = "positive" if orientation == 1 else "negative"
    return np.asarray(pair["actual_by_context"][context_name][label], dtype=float)


def _schedule_matrix(
    selections: Sequence[Sequence[tuple[int, int]]],
    knot_steps: Sequence[int], catalog: Mapping[int, Sequence[Mapping[str, Any]]],
    context_name: str | None,
) -> np.ndarray:
    primary = np.zeros((16, 16), dtype=float)
    for row in range(16):
        for slot, step in enumerate(knot_steps):
            pair_index, orientation = selections[row][slot]
            pair = catalog[int(step)][pair_index]
            value = (
                np.asarray(pair[
                    "positive_coordinate" if orientation == 1 else "negative_coordinate"
                ], dtype=float)
                if context_name is None
                else _actual_for(pair, orientation, context_name)
            )
            primary[row, 4 * slot:4 * slot + 4] = value
    sentinel = np.zeros((8, 16), dtype=float)
    for row in range(8):
        for slot, step in enumerate(knot_steps):
            pair_index, orientation = selections[row][slot]
            pair = catalog[int(step)][pair_index]
            value = (
                np.asarray(pair[
                    "negative_coordinate" if orientation == 1 else "positive_coordinate"
                ], dtype=float)
                if context_name is None
                else _actual_for(pair, -orientation, context_name)
            )
            sentinel[row, 4 * slot:4 * slot + 4] = value
    return np.vstack((primary, sentinel))


def _search_schedule(
    catalog: Mapping[int, Sequence[Mapping[str, Any]]],
    cancellations: Sequence[Mapping[str, Any]],
    context_names: Sequence[str], cfg: Mapping[str, Any],
) -> dict[str, Any]:
    search = cfg["search_contract"]
    usable_steps = [
        int(row["issue_step"]) for row in cancellations
        if bool(row["all_contexts_pass"]) and len(catalog[int(row["issue_step"])]) >= 4
    ]
    knot_sets = _candidate_knot_sets(usable_steps, cfg)
    rng = np.random.default_rng(int(search["random_seed"]))
    matrix_cfg = {"schedule_contract": search}
    tested_by_knot: dict[str, int] = {}
    candidate = None
    for knot_steps in knot_sets:
        label = ",".join(map(str, knot_steps))
        tested_by_knot[label] = 0
        limit = int(search["maximum_candidate_schedules_per_knot_set"])
        batch_size = 256
        while tested_by_knot[label] < limit and candidate is None:
            count = min(batch_size, limit - tested_by_knot[label])
            indices = [
                rng.integers(0, len(catalog[step]), size=(count, 16))
                for step in knot_steps
            ]
            orientations = [
                2 * rng.integers(0, 2, size=(count, 16)) - 1
                for _step in knot_steps
            ]
            primary = np.zeros((count, 16, 16), dtype=float)
            for slot, step in enumerate(knot_steps):
                positive = np.asarray(
                    [row["positive_coordinate"] for row in catalog[step]],
                    dtype=float,
                )
                primary[:, :, 4 * slot:4 * slot + 4] = (
                    positive[indices[slot]] * orientations[slot][:, :, None]
                )
            desired_batch = np.concatenate((primary, -primary[:, :8, :]), axis=1)
            norms = np.linalg.norm(desired_batch, axis=1)
            finite_norms = np.all(np.isfinite(norms) & (norms > 0.0), axis=1)
            normalized = desired_batch / np.where(
                norms[:, None, :] > 0.0, norms[:, None, :], 1.0
            )
            global_rank = np.linalg.matrix_rank(normalized)
            global_condition = np.linalg.cond(normalized)
            eligible = (
                finite_norms
                & (global_rank == int(search["required_global_rank"]))
                & np.isfinite(global_condition)
                & (
                    global_condition
                    <= float(search["maximum_global_normalized_condition"]) + 1e-12
                )
            )
            for slot in range(4):
                block = normalized[:, :, 4 * slot:4 * slot + 4]
                eligible &= (
                    (np.linalg.matrix_rank(block) == int(search["required_slot_rank"]))
                    & np.isfinite(np.linalg.cond(block))
                    & (
                        np.linalg.cond(block)
                        <= float(search["maximum_slot_normalized_condition"]) + 1e-12
                    )
                )
            eligible_indices = np.flatnonzero(eligible)
            stop_offset = count
            for batch_index in eligible_indices:
                selections = [
                    [
                        (
                            int(indices[slot][batch_index, row]),
                            int(orientations[slot][batch_index, row]),
                        )
                        for slot in range(4)
                    ]
                    for row in range(16)
                ]
                desired = desired_batch[batch_index]
                desired_metrics = s23._matrix_metrics(desired, matrix_cfg)
                if not desired_metrics["late_novelty_pass"]:
                    continue
                context_metrics = []
                all_pass = True
                for name in context_names:
                    actual = _schedule_matrix(selections, knot_steps, catalog, name)
                    metrics = s23._matrix_metrics(actual, matrix_cfg)
                    context_metrics.append({"context": name, **metrics})
                    if (
                        not metrics["global_pass"]
                        or int(metrics["slot_pass_count"]) != 4
                        or not metrics["late_novelty_pass"]
                    ):
                        all_pass = False
                        break
                if not all_pass:
                    continue
                schedule_rows = []
                for row_index, row in enumerate(selections):
                    schedule_rows.append({
                        "sequence_index": row_index,
                        "sentinel_sequence_index": (
                            16 + row_index if row_index < 8 else None
                        ),
                        "slots": [
                            {
                                "slot": slot,
                                "issue_step": int(knot_steps[slot]),
                                "cancel_step": int(knot_steps[slot]) + 1,
                                **_pair_orientation(
                                    catalog[int(knot_steps[slot])][pair_index],
                                    orientation,
                                ),
                            }
                            for slot, (pair_index, orientation) in enumerate(row)
                        ],
                    })
                candidate = {
                    "knot_issue_steps": list(map(int, knot_steps)),
                    "knot_cancel_steps": [int(step) + 1 for step in knot_steps],
                    "primary_rows": schedule_rows,
                    "desired_matrix_metrics": desired_metrics,
                    "context_matrix_metrics": context_metrics,
                    "maximum_actual_global_normalized_condition": max(
                        float(row["global_normalized_condition"])
                        for row in context_metrics
                    ),
                    "maximum_actual_slot_normalized_condition": max(
                        float(slot["normalized_condition"])
                        for row in context_metrics for slot in row["slot_rows"]
                    ),
                    "minimum_actual_late_column_residual": min(
                        min(map(float, row["late_column_residuals"]))
                        for row in context_metrics
                    ),
                }
                stop_offset = int(batch_index) + 1
                break
            tested_by_knot[label] += stop_offset
        if candidate is not None:
            break
    return {
        "usable_issue_steps": usable_steps,
        "admissible_knot_sets": [list(row) for row in knot_sets],
        "tested_schedules_by_knot_set": tested_by_knot,
        "total_tested_schedules": sum(tested_by_knot.values()),
        "candidate": candidate,
    }


def run_search(args: argparse.Namespace) -> dict[str, Any]:
    config_path = args.config.expanduser().resolve()
    cfg = _read_json(config_path)
    _validate_design(cfg)
    design_path = args.design_document.expanduser().resolve()
    if _sha256(design_path) != str(cfg["design_document_sha256"]):
        raise ValueError("T13S23D1 design-document hash mismatch")
    source_run = args.source_s21_run.expanduser().resolve()
    source_s22 = args.source_s22_output.expanduser().resolve()
    source_s23_output = args.source_s23_output.expanduser().resolve()
    source_s23_config = args.source_s23_config.expanduser().resolve()
    source_s23_implementation = args.source_s23_implementation.expanduser().resolve()
    output = args.output.expanduser().resolve()
    if output.exists():
        raise ValueError("T13S23D1 output directory must be new")
    if any(
        output == source or source in output.parents
        for source in (source_run, source_s22, source_s23_output)
    ):
        raise ValueError("T13S23D1 output must remain outside immutable sources")

    s23.s22._load_s21_module()
    s21 = s23.s22.s21
    ctx = s21.load_config(
        args.source_s21_config.expanduser().resolve(),
        source_stage42r3b_run=args.source_stage42r3b_run,
        source_stage42r3c3_run=args.source_stage42r3c3_run,
        source_stage42r3c3_bank_dir=args.source_stage42r3c3_bank_dir,
        source_stage42r3c3t1_run=args.source_stage42r3c3t1_run,
        source_stage42r3c3t1_audit_dir=args.source_stage42r3c3t1_audit_dir,
        source_stage42r3c3t3_controller_bank=args.source_stage42r3c3t3_controller_bank,
        q1_run=args.q1_run, q2_run=args.q2_run,
        q1_audit=args.q1_audit, q2_audit=args.q2_audit,
        r3b_server_audit=args.r3b_server_audit,
        r3b_snapshot_checks=args.r3b_snapshot_checks,
        run_dir=source_run,
    )
    authenticated = s23.s22._authenticate_source(ctx, config_path, cfg)
    contexts, reproduction = s23.s22._load_and_authenticate_raw(
        ctx, authenticated["phase_formal_map"]
    )
    if (
        len(contexts) != int(cfg["search_contract"]["expected_context_count"])
        or reproduction["baseline_formal_pass_count"]
        != int(cfg["source_contract"]["expected_baseline_formal_pass_count"])
        or reproduction["measured_probe_formal_pass_count"]
        != int(cfg["source_contract"]["expected_probe_formal_pass_count"])
    ):
        raise ValueError("S21 frozen context or formal counts changed")
    s22_auth = s23._authenticate_s22(source_s22, cfg)
    s23_auth = _authenticate_s23(
        source_s23_output, source_s23_config, source_s23_implementation, cfg
    )
    basis = {
        key: s23._basis_and_actuator(ctx, contexts[key]["baseline"])
        for key in sorted(contexts)
    }
    if any(
        int(values[-1]["fixed_basis_rank"]) != 4
        or not bool(values[-1]["fixed_basis_constant_through_state20"])
        for values in basis.values()
    ):
        raise ValueError("S21 fixed basis changed")

    catalog, catalog_summaries = _build_catalog(ctx, contexts, basis, cfg)
    cancellation_summaries = _cancellation_catalog(ctx, contexts, basis, cfg)
    search_result = _search_schedule(
        catalog, cancellation_summaries,
        [_context_name(key) for key in sorted(contexts)], cfg,
    )
    candidate = search_result["candidate"]
    route = cfg["routes"]["pass" if candidate is not None else "fail"]
    provenance = {
        "stage": STAGE,
        "identity": IDENTITY,
        "design_config_sha256": _sha256(config_path),
        "design_document_sha256": _sha256(design_path),
        "source_s21_run": str(source_run),
        "source_s21_raw_inventory_digest": authenticated["raw_inventory"]["digest"],
        "source_s22_output": str(source_s22),
        "source_s22_hashes": s22_auth["hashes"],
        "source_s23_output": str(source_s23_output),
        "source_s23_hashes": s23_auth["hashes"],
        "template_catalog_digest": _digest(_templates(cfg)[0]),
        "formal_timing_changed": False,
    }
    provenance_digest = _digest(provenance)
    detailed = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "classification": "adaptive_zero_tsc_bounded_schedule_search",
        "provenance": provenance,
        "provenance_digest": provenance_digest,
        "source_authentication": {
            "s21_raw_count": int(authenticated["raw_inventory"]["count"]),
            "s21_reproduction": reproduction,
            "s22": s22_auth,
            "s23": s23_auth,
        },
        "catalog_summaries": catalog_summaries,
        "cancellation_summaries": cancellation_summaries,
        "search_result": search_result,
        "candidate_found": candidate is not None,
        "route": route,
        "scientific_guardrails": cfg["scientific_scope"],
        "execution": cfg["execution_contract"],
        "audit_complete": True,
    }
    summary = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "provenance_digest": provenance_digest,
        "source_raw_authentication_count": int(authenticated["raw_inventory"]["count"]),
        **reproduction,
        "context_count": len(contexts),
        "signed_template_evaluations": sum(
            int(row["signed_event_evaluations"]) for row in catalog_summaries
        ),
        "feasible_sign_pairs_by_issue_step": {
            str(row["issue_step"]): int(row["feasible_sign_pairs"])
            for row in catalog_summaries
        },
        "cancellation_pass_contexts_by_issue_step": {
            str(row["issue_step"]): int(row["passed_contexts"])
            for row in cancellation_summaries
        },
        "usable_issue_steps": search_result["usable_issue_steps"],
        "admissible_knot_set_count": len(search_result["admissible_knot_sets"]),
        "total_tested_schedules": int(search_result["total_tested_schedules"]),
        "candidate_found": candidate is not None,
        "candidate_knot_issue_steps": (
            candidate["knot_issue_steps"] if candidate is not None else None
        ),
        "candidate_maximum_global_normalized_condition": (
            float(candidate["maximum_actual_global_normalized_condition"])
            if candidate is not None else None
        ),
        "candidate_maximum_slot_normalized_condition": (
            float(candidate["maximum_actual_slot_normalized_condition"])
            if candidate is not None else None
        ),
        "candidate_minimum_late_column_residual": (
            float(candidate["minimum_actual_late_column_residual"])
            if candidate is not None else None
        ),
        "route": route,
        "scientific_classification": {
            "runtime_or_environment_error": False,
            "raw_or_snapshot_corruption": False,
            "statistics_or_reporting_error": False,
            "adaptive_schedule_search_result": "candidate_found" if candidate else "fail",
            "real_tsc_or_plant_executed": False,
            "real_controller_or_mpc_executed": False,
            "real_closed_loop_conclusion": "not_tested",
            "real_campaign_authorized": False,
        },
    }
    output.mkdir(parents=True, exist_ok=False)
    detailed_path = output / "stage4_2r3c3t13s23d1_bounded_schedule_search_v1.json"
    summary_path = output / "stage4_2r3c3t13s23d1_summary_v1.json"
    _write_json(detailed_path, detailed)
    _write_json(summary_path, summary)
    manifest = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "provenance_digest": provenance_digest,
        "output_files": [
            {"path": path.name, "size_bytes": path.stat().st_size, "sha256": _sha256(path)}
            for path in (detailed_path, summary_path)
        ],
        "source_raw_files_copied_or_modified": 0,
        "new_raw_files_created": 0,
        "ray_gotsc_tsc_plant_or_controller_executed": False,
        "candidate_authorizes_real_campaign": False,
    }
    manifest_path = output / "stage4_2r3c3t13s23d1_manifest_v1.json"
    _write_json(manifest_path, manifest)
    return {
        "output": str(output),
        "detailed_sha256": _sha256(detailed_path),
        "summary_sha256": _sha256(summary_path),
        "manifest_sha256": _sha256(manifest_path),
        **summary,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--design-document", type=Path, required=True)
    parser.add_argument("--source-s21-config", type=Path, required=True)
    parser.add_argument("--source-s21-run", type=Path, required=True)
    parser.add_argument("--source-s22-output", type=Path, required=True)
    parser.add_argument("--source-s23-config", type=Path, required=True)
    parser.add_argument("--source-s23-implementation", type=Path, required=True)
    parser.add_argument("--source-s23-output", type=Path, required=True)
    for name in (
        "source-stage42r3b-run", "source-stage42r3c3-run",
        "source-stage42r3c3-bank-dir", "source-stage42r3c3t1-run",
        "source-stage42r3c3t1-audit-dir", "source-stage42r3c3t3-controller-bank",
        "q1-run", "q2-run", "q1-audit", "q2-audit",
        "r3b-server-audit", "r3b-snapshot-checks",
    ):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main() -> None:
    result = run_search(_parser().parse_args())
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
