#!/usr/bin/env python3
"""Primary zero-TSC exact safety preflight for D1R14R5."""

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
    stage4_2r3c3t13s24d1r14r4_time_shifted_sign_split_sentinel as r4,
    stage4_2r3c3t13s24d1r14r2_mixed_basis_signed_excitation_sentinel as r2,
)


STAGE = "Stage4.2R3c3T13S24D1R14R5"
IDENTITY = "global_direction0_gain_exact_safety_preflight_v1"
N_COILS = 14


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        + "\n",
        encoding="utf-8",
    )


def _matrix_digest(value: Sequence[Sequence[float]]) -> str:
    matrix = np.asarray(value, dtype="<f8")
    if matrix.shape != (4, 4) or not np.all(np.isfinite(matrix)):
        raise ValueError("D1R14R5 candidate matrix is invalid")
    return hashlib.sha256(matrix.tobytes(order="C")).hexdigest()


def _validate_design(cfg: Mapping[str, Any]) -> None:
    source = cfg["source_r4_contract"]
    r2_source = cfg["source_r2_contract"]
    candidate = cfg["candidate_contract"]
    issue = cfg["static_issue_contract"]
    timing = cfg["formal_timing_contract"]
    execution = cfg["execution_contract"]
    scope = cfg["scientific_scope"]
    matrix = cfg["candidate_requested_coordinate_matrix_columns"]
    invalid = (
        int(cfg.get("schema_version", -1)) != 1
        or cfg.get("stage") != STAGE
        or cfg.get("identity") != IDENTITY
        or cfg.get("package_revision")
        != "r42r3c3t13s24d1r14r5_global_direction0_gain_preflight_v1"
        or cfg.get("selection_status")
        != "frozen_after_final_r4_forensics_before_r5_implementation_or_output"
        or source["package_checkpoint"] != "f5b8348"
        or source["required_route"]
        != "TIME_SHIFTED_SIGN_SPLIT_SENTINEL_GEOMETRY_FAIL_REDESIGN_REQUIRED"
        or tuple(
            int(source[k])
            for k in (
                "raw_count",
                "required_safety_pass_count",
                "required_signal_pass_count",
                "required_rank_pass_count",
                "required_condition_pass_count",
            )
        )
        != (200, 200, 254, 64, 64)
        or int(r2_source["raw_count"]) != 72
        or int(candidate["scaled_column_index"]) != 0
        or float(candidate["fixed_scale"]) != 1.5
        or tuple(map(int, candidate["issue_task_steps"])) != (14, 18, 22)
        or candidate["direction_name"] != "pooled_mixed_0"
        or any(
            bool(candidate[k])
            for k in (
                "context_dependent_selection_allowed",
                "history_or_pair_label_selection_allowed",
                "sign_dependent_magnitude_allowed",
                "alternate_scale_allowed",
                "alternate_column_allowed",
                "search_allowed",
            )
        )
        or _matrix_digest(matrix)
        != candidate["candidate_matrix_float64_le_c_sha256"]
        or tuple(
            int(issue[k])
            for k in (
                "expected_context_count",
                "expected_issue_time_count",
                "expected_signed_construction_count",
                "expected_antipodal_pair_count",
                "dynamic_exact_search_radius",
            )
        )
        != (8, 3, 48, 24, 16)
        or len(issue["readback_bias_grid_units_tsc"]) != N_COILS
        or len(issue["readback_radius_grid_units_tsc"]) != N_COILS
        or tuple(
            float(issue[k])
            for k in (
                "maximum_incremental_normalized_action_linf",
                "maximum_ideal_return_incremental_linf",
                "maximum_total_normalized_action_abs",
                "maximum_current_utilization",
                "minimum_desired_applied_current_cosine",
                "maximum_relative_off_basis_residual",
            )
        )
        != (0.25, 0.24, 1.0, 0.55, 0.98, 0.10)
        or not all(
            bool(issue[k])
            for k in (
                "require_exact_card15_center_and_target",
                "require_target_reproduction",
                "require_no_saturation_or_current_clip",
                "require_source_probe_center_reproduction",
            )
        )
        or bool(issue["online_cancellation_proved_by_static_preflight"])
        or tuple(
            int(timing[k])
            for k in (
                "normal_arrival_deadline_step",
                "normal_hold_through_step",
                "weak_arrival_deadline_step",
                "weak_hold_through_step",
            )
        )
        != (25, 35, 27, 37)
        or bool(timing["arrival_deadline_expansion_allowed"])
        or bool(timing["evaluated_in_r5"])
        or int(execution["new_raw_count"]) != 0
        or int(execution["plant_steps_executed"]) != 0
        or any(
            bool(execution[k])
            for k in (
                "controller_executed",
                "ray_executed",
                "gotsc_executed",
                "tsc_executed",
                "snapshot_creation_allowed",
            )
        )
        or not bool(execution["source_raw_read_in_place"])
        or not bool(scope["fixed_candidate_replay_only"])
        or any(
            bool(scope[k])
            for k in (
                "amplitude_linearity_validated",
                "online_cancellation_validated",
                "plant_response_validated",
                "transition_model_validated",
                "mpc_validated",
                "expert_data_allowed",
                "bc_dagger_or_rl_allowed",
            )
        )
        or not bool(scope["pass_authorizes_real_sentinel_design_only"])
    )
    if invalid:
        raise ValueError("D1R14R5 frozen design changed")


def _source_paths(run: Path, cfg: Mapping[str, Any]) -> dict[str, Path]:
    stage = run / cfg["source_r4_contract"]["stage_directory"]
    return {
        "stage": stage,
        "raw": stage / "raw",
        "variants": stage / "variants",
        "specs": stage / "specs" / "sentinel_specs.json",
        "manifest": stage / "stage_manifest.json",
        "state": stage / "stage_state.json",
        "final": stage / "analysis" / "final_result.json",
        "root_final": run / "final_result.json",
        "independent": run / "server_independent_forensics_v1.json",
    }


def _load_results(
    specs: Sequence[Mapping[str, Any]],
    raw_dir: Path,
    inventory_rows: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    expected = {str(row["name"]): row for row in inventory_rows}
    results: dict[str, dict[str, Any]] = {}
    for spec in specs:
        experiment_id = str(spec["experiment_id"])
        path = raw_dir / f"{experiment_id}.json.gz"
        row = expected.get(path.name)
        if (
            row is None
            or path.stat().st_size != int(row["size"])
            or _sha256(path) != str(row["sha256"])
        ):
            raise ValueError(f"D1R14R5 source raw hash mismatch: {experiment_id}")
        result = r4._read_gz(path)
        if (
            result.get("experiment_id") != experiment_id
            or result.get("spec") != spec
            or result.get("completed") is not True
            or result.get("success") is not True
        ):
            raise ValueError(f"D1R14R5 source raw identity mismatch: {experiment_id}")
        results[experiment_id] = result
    return results


def _load_r2(
    run: Path, cfg: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], dict[str, Any]]:
    contract = cfg["source_r2_contract"]
    if run.name != contract["run_name"]:
        raise ValueError("D1R14R5 source R2 run identity changed")
    stage = run / contract["stage_directory"]
    specs = _read_json(stage / "specs" / "sentinel_specs.json")
    inventory = r4._raw_inventory(stage / "raw")
    if (
        len(specs) != int(contract["raw_count"])
        or inventory["count"] != int(contract["raw_count"])
        or inventory["bytes"] != int(contract["raw_total_bytes"])
        or inventory["digest"] != contract["raw_inventory_digest"]
    ):
        raise ValueError("D1R14R5 source R2 inventory changed")
    results = {}
    for spec in specs:
        experiment_id = str(spec["experiment_id"])
        result = r4._read_gz(stage / "raw" / f"{experiment_id}.json.gz")
        if result.get("spec") != spec or result.get("success") is not True:
            raise ValueError(f"D1R14R5 source R2 raw invalid: {experiment_id}")
        results[experiment_id] = result
    return specs, results, inventory


def _failed_signal_rows(geometry: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for branch in geometry["branch_rows"]:
        for direction in branch["directions"]:
            if not bool(direction["signal_pass"]):
                rows.append(
                    {
                        "experiment_id": str(direction["experiment_id"]),
                        "peak": float(direction["peak_normalized_outputs5"]),
                        "issue_task_step": int(branch["issue_task_step"]),
                        "direction_index": int(direction["direction_index"]),
                        "sign": int(branch["sign"]),
                        "pair_id": str(branch["pair_id"]),
                        "history_member": str(branch["history_member"]),
                    }
                )
    return sorted(rows, key=lambda row: row["experiment_id"])


def _authenticate_source(
    project: Path,
    run: Path,
    r2_run: Path,
    real_log: Path,
    post_log: Path,
    cfg: Mapping[str, Any],
) -> tuple[
    dict[str, Any],
    list[dict[str, Any]],
    dict[str, dict[str, Any]],
    dict[str, Path],
    dict[str, Any],
]:
    contract = cfg["source_r4_contract"]
    paths = _source_paths(run, cfg)
    if run.name != contract["run_name"] or any(not path.exists() for path in paths.values()):
        raise ValueError("D1R14R5 immutable R4 source path changed")
    local_hashes = {
        "config": _sha256(project / contract["config"]),
        "implementation": _sha256(project / contract["implementation"]),
        "independent_implementation": _sha256(
            project / contract["independent_implementation"]
        ),
    }
    expected_local = {
        "config": contract["config_sha256"],
        "implementation": contract["implementation_sha256"],
        "independent_implementation": contract["independent_implementation_sha256"],
    }
    evidence_hashes = {
        "specs": _sha256(paths["specs"]),
        "manifest": _sha256(paths["manifest"]),
        "state": _sha256(paths["state"]),
        "final": _sha256(paths["final"]),
        "root_final": _sha256(paths["root_final"]),
        "independent": _sha256(paths["independent"]),
        "real_log": _sha256(real_log),
        "post_log": _sha256(post_log),
    }
    expected_evidence = {
        "specs": contract["sentinel_specs_sha256"],
        "manifest": contract["stage_manifest_sha256"],
        "state": contract["stage_state_sha256"],
        "final": contract["final_result_sha256"],
        "root_final": contract["final_result_sha256"],
        "independent": contract["independent_result_sha256"],
        "real_log": contract["real_log_sha256"],
        "post_log": contract["postprocess_log_sha256"],
    }
    if local_hashes != expected_local or evidence_hashes != expected_evidence:
        raise ValueError("D1R14R5 immutable R4 source hash changed")
    specs = _read_json(paths["specs"])
    final = _read_json(paths["final"])
    independent = _read_json(paths["independent"])
    manifest = _read_json(paths["manifest"])
    state = _read_json(paths["state"])
    inventory = r4._raw_inventory(paths["raw"])
    if (
        len(specs) != int(contract["raw_count"])
        or inventory["count"] != int(contract["raw_count"])
        or inventory["bytes"] != int(contract["raw_total_bytes"])
        or inventory["digest"] != contract["raw_inventory_digest"]
        or final.get("route") != contract["required_route"]
        or int(final.get("safety_pass_count", -1))
        != int(contract["required_safety_pass_count"])
        or state.get("phase_status") != "failed"
        or state.get("stop_reason") != contract["required_route"]
        or manifest.get("package_fingerprint", {}).get("digest")
        != contract["package_digest"]
        or manifest.get("spec_digest") != contract["spec_digest"]
        or independent.get("official_geometry_exact") is not True
        or independent.get("official_route_reproduced") is not True
        or independent.get("independent_route") != contract["required_route"]
    ):
        raise ValueError("D1R14R5 R4 result boundary changed")
    results = _load_results(specs, paths["raw"], final["raw_inventory"]["rows"])
    r2_specs, r2_results, r2_inventory = _load_r2(r2_run, cfg)
    r4_cfg = _read_json(project / contract["config"])
    reproduced = r4._response_geometry(
        SimpleNamespace(cfg=r4_cfg, source_r2_run=r2_run),
        specs,
        results,
        source_r2_specs=r2_specs,
        source_r2_results=r2_results,
    )
    failed = _failed_signal_rows(reproduced)
    expected_failed = sorted(map(str, contract["required_failed_experiment_ids"]))
    failed_map = {row["experiment_id"]: row["peak"] for row in failed}
    expected_map = dict(
        zip(map(str, contract["required_failed_experiment_ids"]), contract["required_failed_peaks"])
    )
    if (
        reproduced != final["response_geometry"]
        or independent["response_geometry"] != reproduced
        or int(reproduced["signal_pass_count"])
        != int(contract["required_signal_pass_count"])
        or int(reproduced["rank_pass_count"])
        != int(contract["required_rank_pass_count"])
        or int(reproduced["condition_pass_count"])
        != int(contract["required_condition_pass_count"])
        or [row["experiment_id"] for row in failed] != expected_failed
        or failed_map != expected_map
    ):
        raise ValueError("D1R14R5 R4 geometry did not reproduce exactly")
    return (
        {
            "run": str(run),
            "local_hashes": local_hashes,
            "evidence_hashes": evidence_hashes,
            "raw_inventory": inventory,
            "r2_raw_inventory": r2_inventory,
            "strict_raw_count": len(results),
            "reproduced_signal_pass_count": reproduced["signal_pass_count"],
            "reproduced_rank_pass_count": reproduced["rank_pass_count"],
            "reproduced_condition_pass_count": reproduced["condition_pass_count"],
            "failed_signal_rows": failed,
            "passed": True,
        },
        specs,
        results,
        paths,
        r4_cfg,
    )


def _fixed_matrix(cfg: Mapping[str, Any], r4_cfg: Mapping[str, Any]) -> dict[str, Any]:
    contract = cfg["candidate_contract"]
    source = np.asarray(
        r4_cfg["controller_contract"]["requested_coordinate_matrix_columns"], dtype=float
    )
    generated = source.copy()
    generated[:, int(contract["scaled_column_index"])] *= float(contract["fixed_scale"])
    configured = np.asarray(cfg["candidate_requested_coordinate_matrix_columns"], dtype=float)
    exact = bool(
        _matrix_digest(source) == contract["source_matrix_float64_le_c_sha256"]
        and np.array_equal(generated, configured)
        and _matrix_digest(generated)
        == contract["candidate_matrix_float64_le_c_sha256"]
        and np.array_equal(source[:, 1:], configured[:, 1:])
    )
    return {
        "scaled_column_index": 0,
        "fixed_scale": 1.5,
        "source_matrix": source.tolist(),
        "candidate_matrix": configured.tolist(),
        "matrix_digest": _matrix_digest(configured),
        "passed": exact,
    }


def _fixed_basis(result: Mapping[str, Any]) -> np.ndarray:
    values = [
        row.get("r3c3t13s16_fixed_basis_delta_field_kAt_tsc")
        for row in result["controller_trace"][:11]
        if row.get("r3c3t13s16_fixed_basis_delta_field_kAt_tsc")
    ]
    if not values or any(value != values[0] for value in values[1:]):
        raise ValueError("D1R14R5 fixed field basis is not unique")
    matrix = np.asarray(values[0], dtype=float).T
    if matrix.shape != (N_COILS, 4) or not np.all(np.isfinite(matrix)):
        raise ValueError("D1R14R5 fixed field basis is invalid")
    return matrix


def _static_preflight(
    cfg: Mapping[str, Any],
    specs: Sequence[Mapping[str, Any]],
    results: Mapping[str, Mapping[str, Any]],
    paths: Mapping[str, Path],
) -> dict[str, Any]:
    issue_cfg = cfg["static_issue_contract"]
    candidate = np.asarray(cfg["candidate_requested_coordinate_matrix_columns"], dtype=float)
    requested_base = candidate[:, 0]
    baseline_specs = {
        str(spec["source_d1r13_experiment_id"]): spec
        for spec in specs
        if spec["d1r14r4_role"] == "baseline"
    }
    probes: dict[tuple[str, int], list[tuple[Mapping[str, Any], Mapping[str, Any]]]] = {}
    for spec in specs:
        if spec["d1r14r4_role"] == "signed_probe":
            key = (
                str(spec["source_d1r13_experiment_id"]),
                int(spec["d1r14r4_issue_task_step"]),
            )
            probes.setdefault(key, []).append((spec, results[str(spec["experiment_id"])]))
    rows: list[dict[str, Any]] = []
    pair_rows: list[dict[str, Any]] = []
    maxima = {"issue": 0.0, "return": 0.0, "total": 0.0, "current": 0.0, "off_basis": 0.0}
    for context_id, spec in sorted(baseline_specs.items()):
        baseline = results[str(spec["experiment_id"])]
        payload = _read_json(paths["variants"] / f"payload_{spec['experiment_id']}.json")
        turns = np.asarray(display_to_tsc(payload["env_cfg"]["turns_display_order"]), dtype=float)
        minimum = np.asarray(payload["min_current_tsc"], dtype=float)
        maximum = np.asarray(payload["max_current_tsc"], dtype=float)
        max_delta = float(payload["max_delta_a"])
        actuator = QuantizedActuatorModel(
            minimum_current_a_tsc=tuple(minimum),
            maximum_current_a_tsc=tuple(maximum),
            max_slew_step_a=max_delta,
            turns_tsc=tuple(turns),
            bias_grid_units_tsc=tuple(issue_cfg["readback_bias_grid_units_tsc"]),
            uncertainty_radius_grid_units_tsc=tuple(
                issue_cfg["readback_radius_grid_units_tsc"]
            ),
        )
        field_basis = _fixed_basis(baseline)
        current_basis = field_basis * 1000.0 / turns[:, None]
        for issue_step in map(int, cfg["candidate_contract"]["issue_task_steps"]):
            currents = np.asarray(baseline["trajectory"][issue_step]["currents_a_tsc"], dtype=float)
            center = actuator.apply(currents, np.zeros(N_COILS, dtype=float))
            source_members = probes[(context_id, issue_step)]
            source_center_exact = len(source_members) == 8
            for _, member in source_members:
                event = member["controller_trace"][issue_step][
                    "r3c3t13s24d1r14r4_event_detail"
                ]
                source_center_exact = bool(
                    source_center_exact
                    and member["trajectory"][issue_step]["currents_a_tsc"]
                    == baseline["trajectory"][issue_step]["currents_a_tsc"]
                    and event["center_card15_fields"] == list(center.card15_fields)
                )
            signed_rows = []
            for sign in (-1, 1):
                requested = requested_base * sign
                desired_field = field_basis @ requested
                target_fields, actual_decimal, integer_counts = r4.d1r11.s21._dynamic_exact_target(
                    center.card15_fields,
                    tuple(Decimal(str(value)) for value in desired_field),
                    search_radius=int(issue_cfg["dynamic_exact_search_radius"]),
                )
                chosen = r4.d1r11.s21.s16.s9.exact_stored_center_action(
                    stored_fields=target_fields,
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
                cosine = float(
                    np.dot(desired_current, actual_current)
                    / max(np.linalg.norm(desired_current) * np.linalg.norm(actual_current), 1e-300)
                )
                residual = float(
                    np.linalg.norm(actual_current - reconstructed)
                    / max(np.linalg.norm(actual_current), 1e-300)
                )
                ideal_return = r4.d1r11.s21.s16.s9.exact_stored_center_action(
                    stored_fields=center.card15_fields,
                    measured_current_a_tsc=np.asarray(issued.card15_target_current_a_tsc, dtype=float),
                    baseline_action_norm_tsc=np.zeros(N_COILS),
                    turns_tsc=turns,
                    max_slew_step_a=max_delta,
                    minimum_current_a_tsc=minimum,
                    maximum_current_a_tsc=maximum,
                    cfg=issue_cfg,
                )
                criteria = {
                    "finite": bool(
                        np.all(np.isfinite(actual_field))
                        and np.all(np.isfinite(coordinate))
                        and math.isfinite(cosine)
                        and math.isfinite(residual)
                    ),
                    "requested_candidate_exact": bool(
                        np.array_equal(requested, candidate[:, 0] * sign)
                    ),
                    "source_probe_center_reproduction": source_center_exact,
                    "center_exact": all(len(value) == 10 for value in center.card15_fields),
                    "target_exact": all(len(value) == 10 for value in target_fields),
                    "target_reproduction": list(issued.card15_fields) == list(target_fields),
                    "no_saturation": not any(issued.action_saturated),
                    "no_current_clip": not any(issued.current_limit_clipped),
                    "incremental_action": float(chosen["incremental_normalized_action_linf"])
                    <= float(issue_cfg["maximum_incremental_normalized_action_linf"]) + 1e-12,
                    "ideal_return_increment": float(
                        ideal_return["incremental_normalized_action_linf"]
                    )
                    <= float(issue_cfg["maximum_ideal_return_incremental_linf"]) + 1e-12,
                    "total_action": float(chosen["total_normalized_action_abs"])
                    <= float(issue_cfg["maximum_total_normalized_action_abs"]) + 1e-12,
                    "current_utilization": float(chosen["predicted_maximum_current_utilization"])
                    <= float(issue_cfg["maximum_current_utilization"]) + 1e-12,
                    "cosine": cosine
                    >= float(issue_cfg["minimum_desired_applied_current_cosine"]) - 1e-12,
                    "off_basis": residual
                    <= float(issue_cfg["maximum_relative_off_basis_residual"]) + 1e-12,
                    "actuator_gate": bool(chosen["passed"] and ideal_return["passed"]),
                }
                row = {
                    "source_d1r13_experiment_id": context_id,
                    "pair_id": spec["pair_id"],
                    "history_member": spec["history_member"],
                    "issue_task_step": issue_step,
                    "direction_index": 0,
                    "sign": sign,
                    "requested_coordinate": requested.tolist(),
                    "actual_coordinate": coordinate.tolist(),
                    "actual_signed_delta_field_kAt_tsc": actual_field.tolist(),
                    "integer_grid_steps_tsc": list(map(int, integer_counts)),
                    "incremental_normalized_action_linf": float(
                        chosen["incremental_normalized_action_linf"]
                    ),
                    "ideal_return_incremental_linf": float(
                        ideal_return["incremental_normalized_action_linf"]
                    ),
                    "total_normalized_action_abs": float(chosen["total_normalized_action_abs"]),
                    "predicted_current_utilization": float(
                        chosen["predicted_maximum_current_utilization"]
                    ),
                    "desired_applied_current_cosine": cosine,
                    "relative_off_basis_residual": residual,
                    "criteria": criteria,
                    "passed": bool(all(criteria.values())),
                }
                rows.append(row)
                signed_rows.append(row)
                maxima["issue"] = max(maxima["issue"], row["incremental_normalized_action_linf"])
                maxima["return"] = max(maxima["return"], row["ideal_return_incremental_linf"])
                maxima["total"] = max(maxima["total"], row["total_normalized_action_abs"])
                maxima["current"] = max(maxima["current"], row["predicted_current_utilization"])
                maxima["off_basis"] = max(maxima["off_basis"], row["relative_off_basis_residual"])
            negative, positive = signed_rows
            coordinate_exact = np.array_equal(
                np.asarray(positive["requested_coordinate"]),
                -np.asarray(negative["requested_coordinate"]),
            )
            field_exact = np.array_equal(
                np.asarray(positive["actual_signed_delta_field_kAt_tsc"]),
                -np.asarray(negative["actual_signed_delta_field_kAt_tsc"]),
            )
            pair_rows.append(
                {
                    "source_d1r13_experiment_id": context_id,
                    "issue_task_step": issue_step,
                    "coordinate_exact": bool(coordinate_exact),
                    "physical_field_exact": bool(field_exact),
                    "passed": bool(coordinate_exact and field_exact),
                }
            )
    pass_count = sum(bool(row["passed"]) for row in rows)
    pair_pass_count = sum(bool(row["passed"]) for row in pair_rows)
    passed = bool(
        len(baseline_specs) == int(issue_cfg["expected_context_count"])
        and len(rows) == int(issue_cfg["expected_signed_construction_count"])
        and pass_count == len(rows)
        and len(pair_rows) == int(issue_cfg["expected_antipodal_pair_count"])
        and pair_pass_count == len(pair_rows)
    )
    return {
        "context_count": len(baseline_specs),
        "issue_time_count": len(cfg["candidate_contract"]["issue_task_steps"]),
        "construction_count": len(rows),
        "construction_pass_count": pass_count,
        "antipodal_pair_count": len(pair_rows),
        "antipodal_pair_pass_count": pair_pass_count,
        "maximum_issue_incremental_normalized_action_linf": maxima["issue"],
        "maximum_ideal_return_incremental_linf": maxima["return"],
        "maximum_total_normalized_action_abs": maxima["total"],
        "maximum_predicted_current_utilization": maxima["current"],
        "maximum_relative_off_basis_residual": maxima["off_basis"],
        "online_cancellation_proved": False,
        "construction_rows": rows,
        "antipodal_pair_rows": pair_rows,
        "passed": passed,
    }


def run_audit(args: argparse.Namespace) -> dict[str, Any]:
    project = args.project.expanduser().resolve()
    config_path = args.config.expanduser().resolve()
    design_path = args.design_document.expanduser().resolve()
    run = args.source_r4_run.expanduser().resolve()
    r2_run = args.source_r2_run.expanduser().resolve()
    output = args.output.expanduser().resolve()
    cfg = _read_json(config_path)
    _validate_design(cfg)
    if _sha256(design_path) != cfg["design_document_sha256"]:
        raise ValueError("D1R14R5 design-document hash mismatch")
    if output.exists():
        raise ValueError("D1R14R5 output directory must be new")
    source, specs, results, paths, r4_cfg = _authenticate_source(
        project,
        run,
        r2_run,
        args.source_r4_real_log.expanduser().resolve(),
        args.source_r4_postprocess_log.expanduser().resolve(),
        cfg,
    )
    matrix = _fixed_matrix(cfg, r4_cfg)
    construction = _static_preflight(cfg, specs, results, paths)
    passed = bool(source["passed"] and matrix["passed"] and construction["passed"])
    route = cfg["routes"]["pass"] if passed else cfg["routes"]["preflight_fail"]
    detailed = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "source_authentication": source,
        "fixed_matrix": matrix,
        "static_issue_preflight": construction,
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
        "source_r4_authenticated": source["passed"],
        "source_raw_count": source["strict_raw_count"],
        "candidate_matrix_digest": matrix["matrix_digest"],
        "construction_pass_count": construction["construction_pass_count"],
        "construction_count": construction["construction_count"],
        "antipodal_pair_pass_count": construction["antipodal_pair_pass_count"],
        "antipodal_pair_count": construction["antipodal_pair_count"],
        "maximum_issue_incremental_normalized_action_linf": construction[
            "maximum_issue_incremental_normalized_action_linf"
        ],
        "maximum_ideal_return_incremental_linf": construction[
            "maximum_ideal_return_incremental_linf"
        ],
        "maximum_predicted_current_utilization": construction[
            "maximum_predicted_current_utilization"
        ],
        "maximum_relative_off_basis_residual": construction[
            "maximum_relative_off_basis_residual"
        ],
        "online_cancellation_proved": False,
        "new_raw_count": 0,
        "tsc_executed": False,
        "passed": passed,
        "route": route,
    }
    output.mkdir(parents=True)
    detailed_path = output / "stage4_2r3c3t13s24d1r14r5_detailed_v1.json"
    summary_path = output / "stage4_2r3c3t13s24d1r14r5_summary_v1.json"
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
        "source_r4_run": str(run),
        "source_r2_run": str(r2_run),
        "source_raw_read_in_place": True,
        "new_raw_files_created": 0,
        "ray_gotsc_tsc_plant_or_controller_executed": False,
        "outputs": {
            detailed_path.name: _sha256(detailed_path),
            summary_path.name: _sha256(summary_path),
        },
        "route": route,
    }
    _write_json(output / "stage4_2r3c3t13s24d1r14r5_manifest_v1.json", manifest)
    return summary


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--design-document", type=Path, required=True)
    parser.add_argument("--source-r4-run", type=Path, required=True)
    parser.add_argument("--source-r2-run", type=Path, required=True)
    parser.add_argument("--source-r4-real-log", type=Path, required=True)
    parser.add_argument("--source-r4-postprocess-log", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main() -> None:
    print(json.dumps(run_audit(_parser().parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
