#!/usr/bin/env python3
"""Structurally separate zero-TSC recomputation for D1R14R5."""

from __future__ import annotations

import argparse
from decimal import Decimal
import gzip
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r4_independent_forensics as frozen_r4,
)
from tsc_rzip_rllib.control.quantized_actuator import QuantizedActuatorModel
from tsc_rzip_rllib.core.coil_order import display_to_tsc
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s20_dynamic_exact_card15_pooled_observer_campaign as s20,
    stage4_2r3c3t13s9_unified_postqueue_q1_identification as s9,
)


STAGE = "Stage4.2R3c3T13S24D1R14R5"
IDENTITY = "global_direction0_gain_exact_safety_preflight_v1"
N_COILS = 14


def _duplicate_guard(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for key, value in pairs:
        if key in output:
            raise ValueError(f"duplicate JSON key: {key}")
        output[key] = value
    return output


def _bad_constant(value: str) -> None:
    raise ValueError(f"nonstandard JSON constant: {value}")


def _loads(text: str) -> Any:
    return json.loads(
        text,
        object_pairs_hook=_duplicate_guard,
        parse_constant=_bad_constant,
    )


def _json(path: Path) -> Any:
    return _loads(path.read_text(encoding="utf-8", errors="strict"))


def _gzip(path: Path) -> dict[str, Any]:
    with gzip.open(path, mode="rt", encoding="utf-8", errors="strict") as stream:
        value = _loads(stream.read())
    if not isinstance(value, dict):
        raise ValueError(f"raw JSON root is not an object: {path}")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _matrix_digest(value: Sequence[Sequence[float]]) -> str:
    matrix = np.ascontiguousarray(np.asarray(value, dtype="<f8"))
    if matrix.shape != (4, 4) or not np.all(np.isfinite(matrix)):
        raise ValueError("D1R14R5 independent matrix is invalid")
    return hashlib.sha256(matrix.tobytes(order="C")).hexdigest()


def _geometry_signature(geometry: Mapping[str, Any]) -> dict[str, Any]:
    symmetry = geometry.get("issue_coordinate_and_field_symmetry") or {}
    return {
        "evaluated": geometry.get("evaluated"),
        "passed": geometry.get("passed"),
        "context_count": geometry.get("context_count"),
        "issue_task_steps": geometry.get("issue_task_steps"),
        "branch_count": geometry.get("branch_count"),
        "branch_direction_count": geometry.get("branch_direction_count"),
        "signal_pass_count": geometry.get("signal_pass_count"),
        "rank_pass_count": geometry.get("rank_pass_count"),
        "condition_pass_count": geometry.get("condition_pass_count"),
        "minimum_direction_peak_normalized_outputs5": geometry.get(
            "minimum_direction_peak_normalized_outputs5"
        ),
        "maximum_condition_number": geometry.get("maximum_condition_number"),
        "source_pair_count": symmetry.get("source_pair_count"),
        "new_pair_count": symmetry.get("new_pair_count"),
        "combined_pair_count": symmetry.get("combined_pair_count"),
        "coordinate_exact_count": symmetry.get("coordinate_exact_count"),
        "physical_field_exact_count": symmetry.get("physical_field_exact_count"),
        "symmetry_passed": symmetry.get("passed"),
    }


def _inventory(directory: Path) -> dict[str, Any]:
    rows = []
    for path in sorted(directory.glob("*.json.gz")):
        rows.append(
            {"name": path.name, "size": path.stat().st_size, "sha256": _sha256(path)}
        )
    digest = hashlib.sha256()
    for row in rows:
        digest.update(f"{row['name']}\0{row['size']}\0{row['sha256']}\n".encode())
    return {
        "count": len(rows),
        "bytes": sum(int(row["size"]) for row in rows),
        "digest": digest.hexdigest(),
        "rows": rows,
    }


def _validate_frozen_contract(cfg: Mapping[str, Any]) -> None:
    candidate = cfg["candidate_contract"]
    issue = cfg["static_issue_contract"]
    timing = cfg["formal_timing_contract"]
    execution = cfg["execution_contract"]
    scope = cfg["scientific_scope"]
    invalid = (
        cfg.get("stage") != STAGE
        or cfg.get("identity") != IDENTITY
        or cfg.get("selection_status")
        != "frozen_after_final_r4_forensics_before_r5_implementation_or_output"
        or int(candidate["scaled_column_index"]) != 0
        or float(candidate["fixed_scale"]) != 1.5
        or tuple(map(int, candidate["issue_task_steps"])) != (14, 18, 22)
        or candidate["direction_name"] != "pooled_mixed_0"
        or any(
            bool(candidate[key])
            for key in (
                "context_dependent_selection_allowed",
                "history_or_pair_label_selection_allowed",
                "sign_dependent_magnitude_allowed",
                "alternate_scale_allowed",
                "alternate_column_allowed",
                "search_allowed",
            )
        )
        or _matrix_digest(cfg["candidate_requested_coordinate_matrix_columns"])
        != candidate["candidate_matrix_float64_le_c_sha256"]
        or tuple(
            int(issue[key])
            for key in (
                "expected_context_count",
                "expected_issue_time_count",
                "expected_signed_construction_count",
                "expected_antipodal_pair_count",
                "dynamic_exact_search_radius",
            )
        )
        != (8, 3, 48, 24, 16)
        or tuple(
            float(issue[key])
            for key in (
                "maximum_incremental_normalized_action_linf",
                "maximum_ideal_return_incremental_linf",
                "maximum_total_normalized_action_abs",
                "maximum_current_utilization",
                "minimum_desired_applied_current_cosine",
                "maximum_relative_off_basis_residual",
            )
        )
        != (0.25, 0.24, 1.0, 0.55, 0.98, 0.10)
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
        or bool(timing["evaluated_in_r5"])
        or int(execution["new_raw_count"]) != 0
        or int(execution["plant_steps_executed"]) != 0
        or any(
            bool(execution[key])
            for key in (
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
            bool(scope[key])
            for key in (
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
        raise ValueError("D1R14R5 independent frozen-contract validation failed")


def _stage(run: Path, cfg: Mapping[str, Any], key: str) -> Path:
    contract = cfg[key]
    if run.name != contract["run_name"]:
        raise ValueError(f"D1R14R5 independent source run changed: {key}")
    return run / contract["stage_directory"]


def _read_bank(
    stage: Path,
    contract: Mapping[str, Any],
    *,
    final_inventory: Sequence[Mapping[str, Any]] | None,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], dict[str, Any]]:
    specs = _json(stage / "specs" / "sentinel_specs.json")
    inventory = _inventory(stage / "raw")
    if (
        not isinstance(specs, list)
        or len(specs) != int(contract["raw_count"])
        or inventory["count"] != int(contract["raw_count"])
        or inventory["bytes"] != int(contract["raw_total_bytes"])
        or inventory["digest"] != contract["raw_inventory_digest"]
    ):
        raise ValueError("D1R14R5 independent source inventory changed")
    expected = (
        {str(row["name"]): row for row in final_inventory}
        if final_inventory is not None
        else None
    )
    results: dict[str, dict[str, Any]] = {}
    for spec in specs:
        experiment_id = str(spec["experiment_id"])
        path = stage / "raw" / f"{experiment_id}.json.gz"
        if expected is not None:
            row = expected.get(path.name)
            if (
                row is None
                or int(row["size"]) != path.stat().st_size
                or str(row["sha256"]) != _sha256(path)
            ):
                raise ValueError(f"D1R14R5 independent raw hash mismatch: {path.name}")
        result = _gzip(path)
        if (
            result.get("experiment_id") != experiment_id
            or result.get("spec") != spec
            or result.get("completed") is not True
            or result.get("success") is not True
        ):
            raise ValueError(f"D1R14R5 independent raw identity mismatch: {path.name}")
        results[experiment_id] = result
    return specs, results, inventory


def _fixed_basis(result: Mapping[str, Any]) -> np.ndarray:
    values = [
        row.get("r3c3t13s16_fixed_basis_delta_field_kAt_tsc")
        for row in result["controller_trace"][:11]
        if row.get("r3c3t13s16_fixed_basis_delta_field_kAt_tsc") is not None
    ]
    if not values or any(value != values[0] for value in values[1:]):
        raise ValueError("D1R14R5 independent fixed basis changed")
    matrix = np.asarray(values[0], dtype=float).T
    if matrix.shape != (N_COILS, 4) or not np.all(np.isfinite(matrix)):
        raise ValueError("D1R14R5 independent fixed basis invalid")
    return matrix


def _recompute_construction(
    cfg: Mapping[str, Any],
    stage: Path,
    specs: Sequence[Mapping[str, Any]],
    results: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    issue_cfg = cfg["static_issue_contract"]
    matrix = np.asarray(cfg["candidate_requested_coordinate_matrix_columns"], dtype=float)
    baselines = {
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
    antipodal: list[dict[str, Any]] = []
    maxima = {"issue": 0.0, "return": 0.0, "total": 0.0, "current": 0.0, "off": 0.0}
    for context_id, spec in sorted(baselines.items()):
        baseline = results[str(spec["experiment_id"])]
        payload = _json(stage / "variants" / f"payload_{spec['experiment_id']}.json")
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
            center = actuator.apply(currents, np.zeros(N_COILS))
            old_members = probes.get((context_id, issue_step), [])
            source_center_exact = len(old_members) == 8
            for _, member in old_members:
                event = member["controller_trace"][issue_step][
                    "r3c3t13s24d1r14r4_event_detail"
                ]
                source_center_exact = bool(
                    source_center_exact
                    and member["trajectory"][issue_step]["currents_a_tsc"]
                    == baseline["trajectory"][issue_step]["currents_a_tsc"]
                    and event["center_card15_fields"] == list(center.card15_fields)
                )
            signed_rows: dict[int, dict[str, Any]] = {}
            for sign in (-1, 1):
                requested = matrix[:, 0] * sign
                desired_field = field_basis @ requested
                targets, actual_decimal, integer_counts = s20._dynamic_exact_target(
                    center.card15_fields,
                    tuple(Decimal(str(value)) for value in desired_field),
                    search_radius=int(issue_cfg["dynamic_exact_search_radius"]),
                )
                chosen = s9.exact_stored_center_action(
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
                actual_field = np.asarray([float(value) for value in actual_decimal])
                actual_current = actual_field * 1000.0 / turns
                desired_current = current_basis @ requested
                coordinate = np.linalg.lstsq(current_basis, actual_current, rcond=None)[0]
                projected = current_basis @ coordinate
                cosine = float(
                    np.dot(desired_current, actual_current)
                    / max(np.linalg.norm(desired_current) * np.linalg.norm(actual_current), 1e-300)
                )
                residual = float(
                    np.linalg.norm(actual_current - projected)
                    / max(np.linalg.norm(actual_current), 1e-300)
                )
                returned = s9.exact_stored_center_action(
                    stored_fields=center.card15_fields,
                    measured_current_a_tsc=np.asarray(issued.card15_target_current_a_tsc),
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
                        np.array_equal(requested, matrix[:, 0] * sign)
                    ),
                    "source_probe_center_reproduction": source_center_exact,
                    "center_exact": all(len(value) == 10 for value in center.card15_fields),
                    "target_exact": all(len(value) == 10 for value in targets),
                    "target_reproduction": list(issued.card15_fields) == list(targets),
                    "no_saturation": not any(issued.action_saturated),
                    "no_current_clip": not any(issued.current_limit_clipped),
                    "incremental_action": float(chosen["incremental_normalized_action_linf"])
                    <= float(issue_cfg["maximum_incremental_normalized_action_linf"]) + 1e-12,
                    "ideal_return_increment": float(returned["incremental_normalized_action_linf"])
                    <= float(issue_cfg["maximum_ideal_return_incremental_linf"]) + 1e-12,
                    "total_action": float(chosen["total_normalized_action_abs"])
                    <= float(issue_cfg["maximum_total_normalized_action_abs"]) + 1e-12,
                    "current_utilization": float(chosen["predicted_maximum_current_utilization"])
                    <= float(issue_cfg["maximum_current_utilization"]) + 1e-12,
                    "cosine": cosine
                    >= float(issue_cfg["minimum_desired_applied_current_cosine"]) - 1e-12,
                    "off_basis": residual
                    <= float(issue_cfg["maximum_relative_off_basis_residual"]) + 1e-12,
                    "actuator_gate": bool(chosen["passed"] and returned["passed"]),
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
                        returned["incremental_normalized_action_linf"]
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
                signed_rows[sign] = row
                maxima["issue"] = max(maxima["issue"], row["incremental_normalized_action_linf"])
                maxima["return"] = max(maxima["return"], row["ideal_return_incremental_linf"])
                maxima["total"] = max(maxima["total"], row["total_normalized_action_abs"])
                maxima["current"] = max(maxima["current"], row["predicted_current_utilization"])
                maxima["off"] = max(maxima["off"], row["relative_off_basis_residual"])
            negative, positive = signed_rows[-1], signed_rows[1]
            coordinate_exact = bool(
                np.array_equal(
                    np.asarray(positive["requested_coordinate"]),
                    -np.asarray(negative["requested_coordinate"]),
                )
            )
            field_exact = bool(
                np.array_equal(
                    np.asarray(positive["actual_signed_delta_field_kAt_tsc"]),
                    -np.asarray(negative["actual_signed_delta_field_kAt_tsc"]),
                )
            )
            antipodal.append(
                {
                    "source_d1r13_experiment_id": context_id,
                    "issue_task_step": issue_step,
                    "coordinate_exact": coordinate_exact,
                    "physical_field_exact": field_exact,
                    "passed": coordinate_exact and field_exact,
                }
            )
    pass_count = sum(bool(row["passed"]) for row in rows)
    pair_pass_count = sum(bool(row["passed"]) for row in antipodal)
    passed = bool(
        len(baselines) == int(issue_cfg["expected_context_count"])
        and len(rows) == int(issue_cfg["expected_signed_construction_count"])
        and pass_count == len(rows)
        and len(antipodal) == int(issue_cfg["expected_antipodal_pair_count"])
        and pair_pass_count == len(antipodal)
    )
    return {
        "context_count": len(baselines),
        "issue_time_count": len(cfg["candidate_contract"]["issue_task_steps"]),
        "construction_count": len(rows),
        "construction_pass_count": pass_count,
        "antipodal_pair_count": len(antipodal),
        "antipodal_pair_pass_count": pair_pass_count,
        "maximum_issue_incremental_normalized_action_linf": maxima["issue"],
        "maximum_ideal_return_incremental_linf": maxima["return"],
        "maximum_total_normalized_action_abs": maxima["total"],
        "maximum_predicted_current_utilization": maxima["current"],
        "maximum_relative_off_basis_residual": maxima["off"],
        "online_cancellation_proved": False,
        "construction_rows": rows,
        "antipodal_pair_rows": antipodal,
        "passed": passed,
    }


def audit(args: argparse.Namespace) -> dict[str, Any]:
    project = args.project.resolve()
    cfg_path = args.config.resolve()
    design_path = args.design_document.resolve()
    r4_run = args.source_r4_run.resolve()
    r2_run = args.source_r2_run.resolve()
    primary_output = args.primary_output.resolve()
    output = args.output.resolve()
    cfg = _json(cfg_path)
    _validate_frozen_contract(cfg)
    if _sha256(design_path) != cfg["design_document_sha256"]:
        raise ValueError("D1R14R5 independent design hash mismatch")
    source = cfg["source_r4_contract"]
    r4_stage = _stage(r4_run, cfg, "source_r4_contract")
    r2_stage = _stage(r2_run, cfg, "source_r2_contract")
    paths = {
        "config": project / source["config"],
        "implementation": project / source["implementation"],
        "independent_implementation": project / source["independent_implementation"],
        "specs": r4_stage / "specs" / "sentinel_specs.json",
        "manifest": r4_stage / "stage_manifest.json",
        "state": r4_stage / "stage_state.json",
        "final": r4_stage / "analysis" / "final_result.json",
        "root_final": r4_run / "final_result.json",
        "source_independent": r4_run / "server_independent_forensics_v1.json",
        "real_log": args.source_r4_real_log.resolve(),
        "post_log": args.source_r4_postprocess_log.resolve(),
    }
    expected_hashes = {
        "config": source["config_sha256"],
        "implementation": source["implementation_sha256"],
        "independent_implementation": source["independent_implementation_sha256"],
        "specs": source["sentinel_specs_sha256"],
        "manifest": source["stage_manifest_sha256"],
        "state": source["stage_state_sha256"],
        "final": source["final_result_sha256"],
        "root_final": source["final_result_sha256"],
        "source_independent": source["independent_result_sha256"],
        "real_log": source["real_log_sha256"],
        "post_log": source["postprocess_log_sha256"],
    }
    hashes = {name: _sha256(path) for name, path in paths.items()}
    if hashes != expected_hashes:
        raise ValueError("D1R14R5 independent immutable source hash mismatch")
    final = _json(paths["final"])
    source_independent = _json(paths["source_independent"])
    stage_manifest = _json(paths["manifest"])
    state = _json(paths["state"])
    if (
        final.get("route") != source["required_route"]
        or state.get("phase_status") != "failed"
        or state.get("stop_reason") != source["required_route"]
        or stage_manifest.get("package_fingerprint", {}).get("digest")
        != source["package_digest"]
        or stage_manifest.get("spec_digest") != source["spec_digest"]
        or source_independent.get("official_geometry_exact") is not True
        or source_independent.get("official_route_reproduced") is not True
    ):
        raise ValueError("D1R14R5 independent R4 result boundary changed")
    r4_specs, r4_results, r4_inventory = _read_bank(
        r4_stage,
        source,
        final_inventory=final["raw_inventory"]["rows"],
    )
    r2_specs, r2_results, r2_inventory = _read_bank(
        r2_stage,
        cfg["source_r2_contract"],
        final_inventory=None,
    )
    geometry = frozen_r4._geometry(r4_specs, r4_results, r2_specs, r2_results)
    failures = sorted(
        (
            {
                "experiment_id": str(direction["experiment_id"]),
                "peak": float(direction["peak_normalized_outputs5"]),
            }
            for branch in geometry["branch_rows"]
            for direction in branch["directions"]
            if not direction["signal_pass"]
        ),
        key=lambda row: row["experiment_id"],
    )
    expected_failure_map = dict(
        zip(source["required_failed_experiment_ids"], source["required_failed_peaks"])
    )
    if (
        geometry != final["response_geometry"]
        or _geometry_signature(geometry)
        != _geometry_signature(source_independent["response_geometry"])
        or geometry["signal_pass_count"] != int(source["required_signal_pass_count"])
        or geometry["rank_pass_count"] != int(source["required_rank_pass_count"])
        or geometry["condition_pass_count"] != int(source["required_condition_pass_count"])
        or {row["experiment_id"]: row["peak"] for row in failures}
        != expected_failure_map
    ):
        raise ValueError("D1R14R5 independent R4 geometry mismatch")
    source_matrix = np.asarray(_json(paths["config"])["controller_contract"]["requested_coordinate_matrix_columns"])
    generated = source_matrix.copy()
    generated[:, 0] *= 1.5
    configured = np.asarray(cfg["candidate_requested_coordinate_matrix_columns"])
    matrix_pass = bool(
        np.array_equal(generated, configured)
        and np.array_equal(source_matrix[:, 1:], configured[:, 1:])
        and _matrix_digest(source_matrix) == cfg["candidate_contract"]["source_matrix_float64_le_c_sha256"]
        and _matrix_digest(configured) == cfg["candidate_contract"]["candidate_matrix_float64_le_c_sha256"]
    )
    construction = _recompute_construction(cfg, r4_stage, r4_specs, r4_results)
    detailed_path = primary_output / "stage4_2r3c3t13s24d1r14r5_detailed_v1.json"
    summary_path = primary_output / "stage4_2r3c3t13s24d1r14r5_summary_v1.json"
    manifest_path = primary_output / "stage4_2r3c3t13s24d1r14r5_manifest_v1.json"
    primary_detailed = _json(detailed_path)
    primary_summary = _json(summary_path)
    primary_manifest = _json(manifest_path)
    primary_hashes = {
        detailed_path.name: _sha256(detailed_path),
        summary_path.name: _sha256(summary_path),
    }
    primary_exact = bool(
        primary_manifest["outputs"] == primary_hashes
        and primary_detailed["static_issue_preflight"] == construction
        and primary_detailed["fixed_matrix"]["candidate_matrix"] == configured.tolist()
        and primary_detailed["fixed_matrix"]["matrix_digest"]
        == cfg["candidate_contract"]["candidate_matrix_float64_le_c_sha256"]
        and primary_summary["construction_pass_count"] == construction["construction_pass_count"]
        and primary_summary["construction_count"] == construction["construction_count"]
        and primary_summary["antipodal_pair_pass_count"] == construction["antipodal_pair_pass_count"]
        and primary_summary["antipodal_pair_count"] == construction["antipodal_pair_count"]
        and primary_summary["maximum_issue_incremental_normalized_action_linf"]
        == construction["maximum_issue_incremental_normalized_action_linf"]
        and primary_summary["maximum_ideal_return_incremental_linf"]
        == construction["maximum_ideal_return_incremental_linf"]
        and primary_summary["maximum_predicted_current_utilization"]
        == construction["maximum_predicted_current_utilization"]
        and primary_summary["maximum_relative_off_basis_residual"]
        == construction["maximum_relative_off_basis_residual"]
    )
    passed = bool(matrix_pass and construction["passed"] and primary_exact)
    expected_route = cfg["routes"]["pass"] if passed else cfg["routes"]["preflight_fail"]
    route_exact = bool(
        primary_detailed["route"] == expected_route
        and primary_summary["route"] == expected_route
        and primary_manifest["route"] == expected_route
        and primary_detailed["passed"] is passed
        and primary_summary["passed"] is passed
    )
    passed = bool(passed and route_exact)
    return {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "audit_revision": "independent_zero_tsc_static_exact_recomputation_v1",
        "source_hashes": hashes,
        "source_r4_raw_inventory": r4_inventory,
        "source_r2_raw_inventory": r2_inventory,
        "source_r4_geometry_exact": True,
        "source_r4_failed_signal_rows": failures,
        "candidate_matrix_digest": _matrix_digest(configured),
        "candidate_matrix_exact": matrix_pass,
        "static_issue_preflight": construction,
        "primary_output_hashes": primary_hashes,
        "primary_exact": primary_exact,
        "primary_route_exact": route_exact,
        "new_raw_count": 0,
        "plant_steps_executed": 0,
        "controller_executed": False,
        "ray_executed": False,
        "gotsc_executed": False,
        "tsc_executed": False,
        "online_cancellation_proved": False,
        "formal_tracking_evaluated": False,
        "expert_dataset_authorized": False,
        "bc_dagger_or_rl_authorized": False,
        "passed": passed,
        "route": expected_route,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--design-document", type=Path, required=True)
    parser.add_argument("--source-r4-run", type=Path, required=True)
    parser.add_argument("--source-r2-run", type=Path, required=True)
    parser.add_argument("--source-r4-real-log", type=Path, required=True)
    parser.add_argument("--source-r4-postprocess-log", type=Path, required=True)
    parser.add_argument("--primary-output", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main() -> None:
    args = _parser().parse_args()
    if args.output.exists():
        raise ValueError("D1R14R5 independent output must be new")
    result = audit(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "output": str(args.output.resolve()),
                "sha256": _sha256(args.output),
                "passed": result["passed"],
                "route": result["route"],
                "new_raw_count": result["new_raw_count"],
                "tsc_executed": result["tsc_executed"],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
