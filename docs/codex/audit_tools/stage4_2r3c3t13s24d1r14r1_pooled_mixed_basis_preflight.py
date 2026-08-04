#!/usr/bin/env python3
"""Zero-TSC pooled mixed-basis preflight for Stage4.2R3c3T13S24D1R14R1."""

from __future__ import annotations

import argparse
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping, Sequence

import numpy as np

from tsc_rzip_rllib.control.quantized_actuator import QuantizedActuatorModel
from tsc_rzip_rllib.core.coil_order import display_to_tsc
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14_zero_baseline_signed_excitation_sentinel as d1r14,
)


STAGE = "Stage4.2R3c3T13S24D1R14R1"
IDENTITY = "pooled_whitened_amplified_mixed_basis_preflight_v1"
N_CONTEXTS = 8
N_DIRECTIONS = 4
N_COILS = 14


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _digest(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        + "\n",
        encoding="utf-8",
    )


def _matrix_digest(matrix: Sequence[Sequence[float]]) -> str:
    value = np.asarray(matrix, dtype="<f8")
    if value.shape != (N_DIRECTIONS, N_DIRECTIONS):
        raise ValueError("D1R14R1 selected matrix shape changed")
    return hashlib.sha256(value.tobytes(order="C")).hexdigest()


def _validate_design(cfg: Mapping[str, Any]) -> None:
    source = cfg["source_contract"]
    response = cfg["response_contract"]
    search = cfg["search_contract"]
    issue = cfg["static_issue_contract"]
    formal = cfg["formal_timing_contract"]
    execution = cfg["execution_contract"]
    scope = cfg["scientific_scope"]
    matrix = np.asarray(cfg["selected_requested_coordinate_matrix_columns"], dtype=float)
    if (
        int(cfg.get("schema_version", -1)) != 1
        or cfg.get("stage") != STAGE
        or cfg.get("identity") != IDENTITY
        or cfg.get("package_revision")
        != "r42r3c3t13s24d1r14r1_pooled_mixed_basis_preflight_v1"
        or cfg.get("selection_status")
        != "frozen_after_d1r14_v2_before_r1_implementation_or_formal_execution"
        or source["run_name"]
        != "stage4_2r3c3t13s24d1r14_zero_baseline_signed_excitation_sentinel_20260804_d32761c_v1"
        or source["package_checkpoint"] != "d32761c"
        or source["controller_revision"]
        != "zero_baseline_signed_excitation_v42r3c3t13s24d1r14_v2"
        or tuple(int(source[key]) for key in (
            "expected_raw_count", "expected_raw_total_bytes",
            "required_safety_pass_count", "required_issue_exact_count",
            "required_cancel_exact_count", "required_baseline_reproduction_count",
        )) != (72, 2239479, 72, 64, 64, 8)
        or source["required_final_route"]
        != "ZERO_BASELINE_EXCITATION_GEOMETRY_FAIL_REDESIGN_REQUIRED"
        or not bool(source["required_official_geometry_exact"])
        or tuple(map(float, response["visible_output_scales"]))
        != (0.03, 0.03, 0.1, 0.1, 10000.0)
        or tuple(int(response[key]) for key in (
            "center_state", "first_response_state", "context_count",
            "original_direction_count", "signed_pair_count",
        )) != (10, 11, 8, 4, 32)
        or float(response["original_requested_coordinate_amplitude"]) != 0.25
        or search["generator"] != "numpy_default_rng"
        or int(search["seed"]) != 140042
        or int(search["candidate_count"]) != 60000
        or tuple(map(int, search["normal_draw_shape"])) != (4, 4)
        or search["candidate_transform"]
        != "pooled_gram_inverse_sqrt_times_qr"
        or search["column_normalization"]
        != "maximum_absolute_coefficient_one"
        or float(search["objective_signal_floor"]) != 0.005
        or float(search["objective_signal_penalty"]) != 10000.0
        or tuple(search["tie_order"])
        != ("objective", "maximum_condition", "negative_minimum_peak", "candidate_index")
        or int(search["expected_selected_candidate_index_zero_based"]) != 35377
        or float(search["target_minimum_predicted_odd_peak"]) != 0.006
        or float(search["maximum_predicted_unit_column_condition"]) != 4.0
        or float(search["recomputed_matrix_atol"]) != 5e-10
        or any(bool(search[key]) for key in (
            "adaptive_refinement_allowed", "alternate_seed_allowed",
            "continuous_optimization_allowed",
        ))
        or matrix.shape != (4, 4)
        or not np.all(np.isfinite(matrix))
        or _matrix_digest(matrix) != cfg["selected_matrix_float64_le_c_sha256"]
        or tuple(int(issue[key]) for key in (
            "expected_context_count", "expected_signed_construction_count",
            "dynamic_exact_search_radius",
        )) != (8, 64, 16)
        or not bool(issue["baseline_action_exact_zero"])
        or float(issue["maximum_incremental_normalized_action_linf"]) != 0.25
        or float(issue["maximum_online_cancel_incremental_linf_diagnostic_only"])
        != 0.24
        or float(issue["maximum_total_normalized_action_abs"]) != 1.0
        or float(issue["maximum_current_utilization"]) != 0.55
        or float(issue["minimum_desired_applied_current_cosine"]) != 0.98
        or float(issue["maximum_relative_off_basis_residual"]) != 0.10
        or not all(bool(issue[key]) for key in (
            "require_exact_card15_center_and_target", "require_target_reproduction",
            "require_no_saturation_or_current_clip",
        ))
        or bool(issue["cancellation_proved_by_static_preflight"])
        or tuple(int(formal[key]) for key in (
            "normal_arrival_deadline_step", "normal_hold_through_step",
            "weak_arrival_deadline_step", "weak_hold_through_step",
            "arrival_streak_steps",
        )) != (25, 35, 27, 37, 3)
        or float(formal["position_tolerance_m"]) != 0.03
        or float(formal["speed_tolerance_m_per_s"]) != 0.1
        or float(formal["ip_tolerance_A"]) != 10000.0
        or bool(formal["arrival_deadline_expansion_allowed"])
        or bool(formal["evaluated_in_r1"])
        or not bool(execution["server_side_only_for_large_raw"])
        or not bool(execution["read_raw_in_place"])
        or int(execution["new_raw_count"]) != 0
        or int(execution["plant_steps_executed"]) != 0
        or any(bool(execution[key]) for key in (
            "controller_executed", "ray_executed", "gotsc_executed",
            "tsc_executed", "snapshot_creation_allowed",
        ))
        or not bool(scope["development_data_consumed"])
        or not bool(scope["linear_superposition_only"])
        or any(bool(scope[key]) for key in (
            "symmetry_validated", "online_cancellation_validated",
            "plant_response_validated", "transition_model_validated",
            "mpc_validated", "expert_data_allowed", "bc_dagger_or_rl_allowed",
        ))
        or not bool(scope["pass_authorizes_r2_design_only"])
    ):
        raise ValueError("D1R14R1 frozen design changed")


def _source_paths(run: Path, cfg: Mapping[str, Any]) -> dict[str, Path]:
    stage = run / cfg["source_contract"]["stage_subdir"]
    return {
        "stage": stage,
        "raw": stage / "raw",
        "variants": stage / "variants",
        "specs": stage / "specs" / "sentinel_specs.json",
        "final": stage / "analysis" / "final_result.json",
        "audit": stage / "analysis" / "independent_forensics_v2.json",
        "manifest": stage / "stage_manifest.json",
        "state": stage / "stage_state.json",
    }


def _authenticate_source(
    run: Path, project: Path, cfg: Mapping[str, Any]
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, dict[str, Any]], dict[str, Path]]:
    source = cfg["source_contract"]
    paths = _source_paths(run, cfg)
    required = [paths[key] for key in ("raw", "variants", "specs", "final", "audit", "manifest", "state")]
    if run.name != source["run_name"] or any(not path.exists() for path in required):
        raise ValueError("D1R14R1 immutable source path changed or is incomplete")
    local_hashes = {
        "config": _sha256(project / source["config"]),
        "implementation": _sha256(project / source["implementation"]),
        "lattice_config": _sha256(project / source["lattice_config"]),
    }
    expected_local = {
        "config": source["config_sha256"],
        "implementation": source["implementation_sha256"],
        "lattice_config": source["lattice_config_sha256"],
    }
    evidence_hashes = {
        "final": _sha256(paths["final"]),
        "audit": _sha256(paths["audit"]),
        "specs": _sha256(paths["specs"]),
        "manifest": _sha256(paths["manifest"]),
        "state": _sha256(paths["state"]),
    }
    expected_evidence = {
        "final": source["final_result_sha256"],
        "audit": source["independent_audit_sha256"],
        "specs": source["sentinel_specs_sha256"],
        "manifest": source["stage_manifest_sha256"],
        "state": source["stage_state_sha256"],
    }
    if local_hashes != expected_local or evidence_hashes != expected_evidence:
        raise ValueError("D1R14R1 immutable source hash changed")
    final = _read_json(paths["final"])
    audit = _read_json(paths["audit"])
    specs_value = _read_json(paths["specs"])
    specs = specs_value if isinstance(specs_value, list) else specs_value.get("specs", specs_value.get("rows"))
    if not isinstance(specs, list) or len(specs) != 72:
        raise ValueError("D1R14R1 source specification inventory changed")
    inventory = d1r14._raw_inventory(paths["raw"])
    if (
        inventory["count"] != int(source["expected_raw_count"])
        or inventory["bytes"] != int(source["expected_raw_total_bytes"])
        or inventory["digest"] != source["expected_raw_inventory_digest"]
        or final.get("route") != source["required_final_route"]
        or int(final.get("strict_raw_count", -1)) != 72
        or int(final.get("safety_pass_count", -1)) != int(source["required_safety_pass_count"])
        or int(final.get("issue_exact_count", -1)) != int(source["required_issue_exact_count"])
        or int(final.get("cancel_exact_count", -1)) != int(source["required_cancel_exact_count"])
        or int(final.get("baseline_reproduction_count", -1))
        != int(source["required_baseline_reproduction_count"])
        or not bool(audit.get("audit_completed"))
        or not bool(audit.get("official_route_reproduced"))
        or not bool(audit.get("official_geometry_exact"))
        or audit.get("independent_route") != source["required_final_route"]
        or int(audit.get("strict_raw_parse_count", -1)) != 72
    ):
        raise ValueError("D1R14R1 source result contract changed")
    result_rows = {}
    expected_inventory = {row["name"]: row for row in final["raw_inventory"]["rows"]}
    for spec in specs:
        experiment_id = str(spec["experiment_id"])
        raw_path = paths["raw"] / f"{experiment_id}.json.gz"
        inv = expected_inventory.get(raw_path.name)
        if (
            inv is None
            or raw_path.stat().st_size != int(inv["size"])
            or _sha256(raw_path) != inv["sha256"]
        ):
            raise ValueError(f"D1R14R1 raw authentication failed: {experiment_id}")
        result = d1r14._read_gz(raw_path)
        if (
            str(result.get("experiment_id")) != experiment_id
            or not bool(result.get("success"))
            or not bool(result.get("completed"))
        ):
            raise ValueError(f"D1R14R1 strict raw result failed: {experiment_id}")
        result_rows[experiment_id] = result
    source_cfg = _read_json(project / source["config"])
    reproduced = d1r14._response_geometry(
        SimpleNamespace(cfg=source_cfg), specs, result_rows
    )
    if reproduced != final["response_geometry"]:
        raise ValueError("D1R14R1 official geometry did not reproduce exactly")
    authentication = {
        "run": str(run),
        "local_source_hashes": local_hashes,
        "evidence_hashes": evidence_hashes,
        "raw_inventory": inventory,
        "strict_raw_count": len(result_rows),
        "official_geometry_digest": _digest(reproduced),
        "passed": True,
    }
    return authentication, specs, result_rows, paths


def _group_results(
    specs: Sequence[Mapping[str, Any]], results: Mapping[str, Mapping[str, Any]]
) -> dict[str, dict[tuple[str, int, int], tuple[Mapping[str, Any], Mapping[str, Any]]]]:
    grouped: dict[str, dict[tuple[str, int, int], tuple[Mapping[str, Any], Mapping[str, Any]]]] = {}
    for spec in specs:
        key = (
            str(spec["d1r14_role"]),
            int(spec["d1r14_direction_index"]),
            int(spec["d1r14_sign"]),
        )
        grouped.setdefault(str(spec["source_d1r13_experiment_id"]), {})[key] = (
            spec,
            results[str(spec["experiment_id"])],
        )
    return grouped


def _response_matrices(
    source_cfg: Mapping[str, Any],
    specs: Sequence[Mapping[str, Any]],
    results: Mapping[str, Mapping[str, Any]],
) -> tuple[list[str], list[np.ndarray]]:
    grouped = _group_results(specs, results)
    scales = np.asarray(source_cfg["response_geometry"]["visible_output_scales"], dtype=float)
    first = int(source_cfg["response_geometry"]["first_response_state"])
    context_ids = list(map(str, source_cfg["selected_source_d1r13_experiment_ids"]))
    matrices = []
    for context_id in context_ids:
        columns = []
        group = grouped[context_id]
        for direction in range(N_DIRECTIONS):
            positive = group[("signed_probe", direction, 1)][1]
            negative = group[("signed_probe", direction, -1)][1]
            p = d1r14._visible_outputs5(positive["trajectory"], scales)[first:]
            n = d1r14._visible_outputs5(negative["trajectory"], scales)[first:]
            columns.append((0.5 * (p - n)).reshape(-1))
        matrix = np.column_stack(columns)
        if matrix.shape[1] != 4 or not np.all(np.isfinite(matrix)):
            raise ValueError("D1R14R1 response matrix is invalid")
        matrices.append(matrix)
    if len(matrices) != N_CONTEXTS:
        raise ValueError("D1R14R1 response context coverage changed")
    return context_ids, matrices


def _candidate_metrics(matrices: Sequence[np.ndarray], weights: np.ndarray) -> tuple[float, float, list[dict[str, float]]]:
    minimum_peak = math.inf
    maximum_condition = 0.0
    rows = []
    for matrix in matrices:
        response = matrix @ weights
        peaks = np.max(np.abs(response), axis=0)
        norms = np.linalg.norm(response, axis=0)
        if np.any(norms <= 0.0) or not np.all(np.isfinite(norms)):
            condition = math.inf
        else:
            condition = float(np.linalg.cond(response / norms[None, :]))
        minimum_peak = min(minimum_peak, float(np.min(peaks)))
        maximum_condition = max(maximum_condition, condition)
        rows.append({
            "minimum_odd_peak": float(np.min(peaks)),
            "maximum_odd_peak": float(np.max(peaks)),
            "unit_column_condition": condition,
        })
    return minimum_peak, maximum_condition, rows


def _search(matrices: Sequence[np.ndarray], cfg: Mapping[str, Any]) -> dict[str, Any]:
    search = cfg["search_contract"]
    gram = sum(matrix.T @ matrix for matrix in matrices) / float(len(matrices))
    eigenvalues, eigenvectors = np.linalg.eigh(gram)
    if np.any(eigenvalues <= 0.0) or not np.all(np.isfinite(eigenvalues)):
        raise ValueError("D1R14R1 pooled Gram matrix is not positive definite")
    whitener = eigenvectors @ np.diag(1.0 / np.sqrt(eigenvalues)) @ eigenvectors.T
    rng = np.random.default_rng(int(search["seed"]))
    best_key = None
    best_weights = None
    best_metrics = None
    signal_floor = float(search["objective_signal_floor"])
    penalty = float(search["objective_signal_penalty"])
    for index in range(int(search["candidate_count"])):
        orthogonal, _ = np.linalg.qr(rng.standard_normal((4, 4)))
        weights = whitener @ orthogonal
        weights = weights / np.max(np.abs(weights), axis=0)[None, :]
        minimum_peak, maximum_condition, _ = _candidate_metrics(matrices, weights)
        objective = maximum_condition + penalty * max(0.0, signal_floor - minimum_peak)
        key = (objective, maximum_condition, -minimum_peak, index)
        if best_key is None or key < best_key:
            best_key = key
            best_weights = weights.copy()
            best_metrics = (minimum_peak, maximum_condition)
    assert best_key is not None and best_weights is not None and best_metrics is not None
    column_minima = np.asarray([
        min(float(np.max(np.abs(matrix @ best_weights[:, column]))) for matrix in matrices)
        for column in range(4)
    ])
    scales = float(search["target_minimum_predicted_odd_peak"]) / column_minima
    original_amplitude = float(cfg["response_contract"]["original_requested_coordinate_amplitude"])
    recomputed = original_amplitude * best_weights * scales[None, :]
    selected = np.asarray(cfg["selected_requested_coordinate_matrix_columns"], dtype=float)
    agreement = float(np.max(np.abs(recomputed - selected)))
    selected_weights = selected / original_amplitude
    minimum_peak, maximum_condition, context_rows = _candidate_metrics(matrices, selected_weights)
    passed = bool(
        int(best_key[3]) == int(search["expected_selected_candidate_index_zero_based"])
        and agreement <= float(search["recomputed_matrix_atol"])
        and minimum_peak >= float(search["target_minimum_predicted_odd_peak"]) - 5e-12
        and maximum_condition
        <= float(search["maximum_predicted_unit_column_condition"]) + 1e-12
    )
    return {
        "pooled_gram": gram.tolist(),
        "pooled_whitener": whitener.tolist(),
        "selected_candidate_index_zero_based": int(best_key[3]),
        "unscaled_objective": float(best_key[0]),
        "unscaled_minimum_odd_peak": float(best_metrics[0]),
        "unscaled_maximum_condition": float(best_metrics[1]),
        "column_scale_factors": scales.tolist(),
        "recomputed_requested_coordinate_matrix": recomputed.tolist(),
        "configured_requested_coordinate_matrix": selected.tolist(),
        "configured_matrix_float64_le_c_sha256": _matrix_digest(selected),
        "maximum_recomputed_matrix_absolute_difference": agreement,
        "predicted_minimum_odd_peak": minimum_peak,
        "predicted_maximum_unit_column_condition": maximum_condition,
        "context_rows": context_rows,
        "passed": passed,
    }


def _unique(values: Sequence[Any], name: str) -> Any:
    if not values or any(value != values[0] for value in values[1:]):
        raise ValueError(f"D1R14R1 context {name} is not unique")
    return values[0]


def _fixed_field_basis(result: Mapping[str, Any]) -> np.ndarray:
    rows = [
        row.get("r3c3t13s16_fixed_basis_delta_field_kAt_tsc")
        for row in result["controller_trace"][:11]
        if row.get("r3c3t13s16_fixed_basis_delta_field_kAt_tsc")
    ]
    value = _unique(rows, "fixed field basis")
    matrix = np.asarray(value, dtype=float).T
    if matrix.shape != (N_COILS, N_DIRECTIONS) or not np.all(np.isfinite(matrix)):
        raise ValueError("D1R14R1 fixed field basis is invalid")
    return matrix


def _static_issue_preflight(
    project: Path,
    paths: Mapping[str, Path],
    cfg: Mapping[str, Any],
    source_cfg: Mapping[str, Any],
    specs: Sequence[Mapping[str, Any]],
    results: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    grouped = _group_results(specs, results)
    issue_cfg = cfg["static_issue_contract"]
    lattice = _read_json(project / cfg["source_contract"]["lattice_config"])["lattice_probe"]
    selected = np.asarray(cfg["selected_requested_coordinate_matrix_columns"], dtype=float)
    context_rows = []
    construction_rows = []
    maximum_issue = 0.0
    maximum_cancel_diagnostic = 0.0
    for context_id in map(str, source_cfg["selected_source_d1r13_experiment_ids"]):
        group = grouped[context_id]
        members = list(group.values())
        currents_values = [tuple(map(float, result["trajectory"][10]["currents_a_tsc"])) for _, result in members]
        currents = np.asarray(_unique(currents_values, "state-10 current"), dtype=float)
        signed = [(spec, result) for (role, _, _), (spec, result) in group.items() if role == "signed_probe"]
        centers = [tuple(result["controller_trace"][10]["r3c3t13s24d1r14_event_detail"]["center_card15_fields"]) for _, result in signed]
        center_fields = tuple(_unique(centers, "Card15 center"))
        bases = [_fixed_field_basis(result).tolist() for _, result in signed]
        field_basis = np.asarray(_unique(bases, "fixed field basis across probes"), dtype=float)
        payloads = [
            _read_json(paths["variants"] / f"payload_{spec['experiment_id']}.json")
            for spec, _ in signed
        ]
        payload = payloads[0]
        for other in payloads[1:]:
            for key in ("min_current_tsc", "max_current_tsc", "max_delta_a"):
                if other[key] != payload[key]:
                    raise ValueError(f"D1R14R1 payload {key} changed within context")
            if other["env_cfg"]["turns_display_order"] != payload["env_cfg"]["turns_display_order"]:
                raise ValueError("D1R14R1 payload turns changed within context")
        turns = np.asarray(display_to_tsc(payload["env_cfg"]["turns_display_order"]), dtype=float)
        minimum = np.asarray(payload["min_current_tsc"], dtype=float)
        maximum = np.asarray(payload["max_current_tsc"], dtype=float)
        max_delta = float(payload["max_delta_a"])
        actuator = QuantizedActuatorModel(
            minimum_current_a_tsc=tuple(minimum),
            maximum_current_a_tsc=tuple(maximum),
            max_slew_step_a=max_delta,
            turns_tsc=tuple(turns),
            bias_grid_units_tsc=tuple(lattice["readback_bias_grid_units_tsc"]),
            uncertainty_radius_grid_units_tsc=tuple(lattice["readback_radius_grid_units_tsc"]),
        )
        current_basis = field_basis * 1000.0 / turns[:, None]
        context_pass_count = 0
        for direction in range(4):
            for sign in (-1, 1):
                requested = selected[:, direction] * sign
                desired_field = field_basis @ requested
                targets, actual_decimal, counts = d1r14.d1r11.s21._dynamic_exact_target(
                    center_fields,
                    tuple(Decimal(str(value)) for value in desired_field),
                    search_radius=int(issue_cfg["dynamic_exact_search_radius"]),
                )
                chosen = d1r14.d1r11.s21.s16.s9.exact_stored_center_action(
                    stored_fields=targets,
                    measured_current_a_tsc=currents,
                    baseline_action_norm_tsc=np.zeros(N_COILS),
                    turns_tsc=turns,
                    max_slew_step_a=max_delta,
                    minimum_current_a_tsc=minimum,
                    maximum_current_a_tsc=maximum,
                    cfg=issue_cfg,
                )
                issued = actuator.apply(currents, chosen["action_norm_tsc"])
                actual_field = np.asarray([float(value) for value in actual_decimal], dtype=float)
                actual_current = actual_field * 1000.0 / turns
                desired_current = current_basis @ requested
                coordinate = np.linalg.lstsq(current_basis, actual_current, rcond=None)[0]
                reconstructed = current_basis @ coordinate
                cosine = float(np.dot(desired_current, actual_current) / max(np.linalg.norm(desired_current) * np.linalg.norm(actual_current), 1e-300))
                residual = float(np.linalg.norm(actual_current - reconstructed) / max(np.linalg.norm(actual_current), 1e-300))
                criteria = {
                    "finite": bool(np.all(np.isfinite(actual_field)) and np.all(np.isfinite(coordinate)) and math.isfinite(cosine) and math.isfinite(residual)),
                    "center_exact": all(len(field) == 10 for field in center_fields),
                    "target_exact": all(len(field) == 10 for field in targets),
                    "target_reproduction": list(issued.card15_fields) == list(targets),
                    "no_saturation": not any(issued.action_saturated),
                    "no_current_clip": not any(issued.current_limit_clipped),
                    "incremental_action": float(chosen["incremental_normalized_action_linf"]) <= float(issue_cfg["maximum_incremental_normalized_action_linf"]) + 1e-12,
                    "total_action": float(chosen["total_normalized_action_abs"]) <= float(issue_cfg["maximum_total_normalized_action_abs"]) + 1e-12,
                    "current_utilization": float(chosen["predicted_maximum_current_utilization"]) <= float(issue_cfg["maximum_current_utilization"]) + 1e-12,
                    "cosine": cosine >= float(issue_cfg["minimum_desired_applied_current_cosine"]) - 1e-12,
                    "off_basis": residual <= float(issue_cfg["maximum_relative_off_basis_residual"]) + 1e-12,
                    "actuator_gate": bool(chosen["passed"]),
                }
                target_current = np.asarray(issued.card15_target_current_a_tsc, dtype=float)
                cancel = d1r14.d1r11.s21.s16.s9.exact_stored_center_action(
                    stored_fields=center_fields,
                    measured_current_a_tsc=target_current,
                    baseline_action_norm_tsc=np.zeros(N_COILS),
                    turns_tsc=turns,
                    max_slew_step_a=max_delta,
                    minimum_current_a_tsc=minimum,
                    maximum_current_a_tsc=maximum,
                    cfg=issue_cfg,
                )
                row_pass = bool(all(criteria.values()))
                context_pass_count += int(row_pass)
                maximum_issue = max(maximum_issue, float(chosen["incremental_normalized_action_linf"]))
                maximum_cancel_diagnostic = max(maximum_cancel_diagnostic, float(cancel["incremental_normalized_action_linf"]))
                construction_rows.append({
                    "source_d1r13_experiment_id": context_id,
                    "direction_index": direction,
                    "sign": sign,
                    "requested_coordinate": requested.tolist(),
                    "actual_coordinate": coordinate.tolist(),
                    "integer_grid_steps_tsc": list(map(int, counts)),
                    "incremental_normalized_action_linf": float(chosen["incremental_normalized_action_linf"]),
                    "total_normalized_action_abs": float(chosen["total_normalized_action_abs"]),
                    "predicted_current_utilization": float(chosen["predicted_maximum_current_utilization"]),
                    "desired_applied_current_cosine": cosine,
                    "relative_off_basis_residual": residual,
                    "linearized_cancel_incremental_linf_diagnostic_only": float(cancel["incremental_normalized_action_linf"]),
                    "criteria": criteria,
                    "passed": row_pass,
                })
        context_rows.append({
            "source_d1r13_experiment_id": context_id,
            "construction_pass_count": context_pass_count,
            "passed": context_pass_count == 8,
        })
    passed_count = sum(bool(row["passed"]) for row in construction_rows)
    passed = bool(
        len(context_rows) == int(issue_cfg["expected_context_count"])
        and len(construction_rows) == int(issue_cfg["expected_signed_construction_count"])
        and passed_count == int(issue_cfg["expected_signed_construction_count"])
    )
    return {
        "context_count": len(context_rows),
        "construction_count": len(construction_rows),
        "construction_pass_count": passed_count,
        "maximum_issue_incremental_normalized_action_linf": maximum_issue,
        "maximum_linearized_cancel_incremental_linf_diagnostic_only": maximum_cancel_diagnostic,
        "online_cancellation_proved": False,
        "context_rows": context_rows,
        "construction_rows": construction_rows,
        "passed": passed,
    }


def run_audit(args: argparse.Namespace) -> dict[str, Any]:
    project = args.project.expanduser().resolve()
    config_path = args.config.expanduser().resolve()
    design_path = args.design_document.expanduser().resolve()
    source_run = args.source_run.expanduser().resolve()
    output = args.output.expanduser().resolve()
    cfg = _read_json(config_path)
    _validate_design(cfg)
    if _sha256(design_path) != cfg["design_document_sha256"]:
        raise ValueError("D1R14R1 design-document hash mismatch")
    if output.exists():
        raise ValueError("D1R14R1 output directory must be new")
    authentication, specs, results, paths = _authenticate_source(source_run, project, cfg)
    source_cfg = _read_json(project / cfg["source_contract"]["config"])
    context_ids, matrices = _response_matrices(source_cfg, specs, results)
    search = _search(matrices, cfg)
    issue = _static_issue_preflight(project, paths, cfg, source_cfg, specs, results)
    passed = bool(authentication["passed"] and search["passed"] and issue["passed"])
    route = cfg["routes"]["pass"] if passed else cfg["routes"]["preflight_fail"]
    detailed = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "source_authentication": authentication,
        "context_ids": context_ids,
        "search": search,
        "static_issue_preflight": issue,
        "execution": {
            "new_raw_count": 0,
            "plant_steps_executed": 0,
            "controller_executed": False,
            "ray_executed": False,
            "gotsc_executed": False,
            "tsc_executed": False,
        },
        "scientific_boundary": cfg["scientific_scope"],
        "passed": passed,
        "route": route,
    }
    summary = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "source_raw_count": authentication["strict_raw_count"],
        "selected_candidate_index_zero_based": search["selected_candidate_index_zero_based"],
        "predicted_minimum_odd_peak": search["predicted_minimum_odd_peak"],
        "predicted_maximum_unit_column_condition": search["predicted_maximum_unit_column_condition"],
        "static_issue_construction_pass_count": issue["construction_pass_count"],
        "static_issue_construction_count": issue["construction_count"],
        "maximum_issue_incremental_normalized_action_linf": issue["maximum_issue_incremental_normalized_action_linf"],
        "maximum_linearized_cancel_incremental_linf_diagnostic_only": issue["maximum_linearized_cancel_incremental_linf_diagnostic_only"],
        "online_cancellation_proved": False,
        "new_raw_count": 0,
        "tsc_executed": False,
        "passed": passed,
        "route": route,
    }
    output.mkdir(parents=True)
    detailed_path = output / "stage4_2r3c3t13s24d1r14r1_detailed_v1.json"
    summary_path = output / "stage4_2r3c3t13s24d1r14r1_summary_v1.json"
    _write_json(detailed_path, detailed)
    _write_json(summary_path, summary)
    manifest = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "config": str(config_path),
        "config_sha256": _sha256(config_path),
        "design_document": str(design_path),
        "design_document_sha256": _sha256(design_path),
        "source_run": str(source_run),
        "source_raw_read_in_place": True,
        "new_raw_files_created": 0,
        "ray_gotsc_tsc_plant_or_controller_executed": False,
        "outputs": {
            detailed_path.name: _sha256(detailed_path),
            summary_path.name: _sha256(summary_path),
        },
        "route": route,
    }
    _write_json(output / "stage4_2r3c3t13s24d1r14r1_manifest_v1.json", manifest)
    return summary


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--design-document", type=Path, required=True)
    parser.add_argument("--source-run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main() -> None:
    summary = run_audit(_parser().parse_args())
    print(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
