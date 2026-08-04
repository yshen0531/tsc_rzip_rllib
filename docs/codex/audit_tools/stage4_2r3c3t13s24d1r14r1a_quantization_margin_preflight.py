#!/usr/bin/env python3
"""Zero-TSC fixed quantization-margin replay for D1R14R1A."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r1_pooled_mixed_basis_preflight as r1,
)


STAGE = "Stage4.2R3c3T13S24D1R14R1A"
IDENTITY = "fixed_third_column_quantization_margin_preflight_v1"


def _sha256(path: Path) -> str:
    return r1._sha256(path)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        + "\n",
        encoding="utf-8",
    )


def _validate_design(cfg: Mapping[str, Any]) -> None:
    source = cfg["source_r1_contract"]
    repair = cfg["repair_contract"]
    response = cfg["response_contract"]
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
        != "r42r3c3t13s24d1r14r1a_quantization_margin_preflight_v1"
        or cfg.get("selection_status")
        != "frozen_after_r1_failure_and_disclosed_development_grid_before_r1a_implementation"
        or source["output_name"]
        != "stage4_2r3c3t13s24d1r14r1_pooled_mixed_basis_preflight_20260804_36f0d41_v1"
        or source["package_checkpoint"] != "36f0d41"
        or source["implementation_checkpoint"] != "7c4002c"
        or source["required_route"]
        != "POOLED_MIXED_BASIS_PREFLIGHT_FAIL_REDESIGN_REQUIRED"
        or not bool(source["required_source_authentication_pass"])
        or not bool(source["required_search_pass"])
        or tuple(int(source[key]) for key in (
            "required_static_issue_pass_count", "required_static_issue_count",
            "required_failed_direction_index",
        )) != (48, 64, 2)
        or source["required_failure_criterion"] != "off_basis"
        or int(repair["scaled_column_index"]) != 2
        or float(repair["fixed_scale"]) != 1.275
        or tuple(float(repair[key]) for key in (
            "selection_grid_start", "selection_grid_stop", "selection_grid_step",
        )) != (1.0, 2.0, 0.025)
        or not bool(repair["selection_grid_is_disclosed_development_only"])
        or any(bool(repair[key]) for key in (
            "grid_reexecution_in_r1a_allowed", "alternate_scale_allowed",
            "alternate_column_allowed", "adaptive_refinement_allowed",
        ))
        or matrix.shape != (4, 4)
        or not np.all(np.isfinite(matrix))
        or r1._matrix_digest(matrix) != cfg["selected_matrix_float64_le_c_sha256"]
        or float(response["original_requested_coordinate_amplitude"]) != 0.25
        or float(response["minimum_predicted_odd_peak"]) != 0.006
        or float(response["maximum_predicted_unit_column_condition"]) != 4.0
        or int(response["context_count"]) != 8
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
        )) != (25, 35, 27, 37)
        or bool(formal["arrival_deadline_expansion_allowed"])
        or bool(formal["evaluated_in_r1a"])
        or not bool(execution["server_side_only_for_large_raw"])
        or not bool(execution["source_raw_read_in_place"])
        or int(execution["new_raw_count"]) != 0
        or int(execution["plant_steps_executed"]) != 0
        or any(bool(execution[key]) for key in (
            "controller_executed", "ray_executed", "gotsc_executed",
            "tsc_executed", "snapshot_creation_allowed",
        ))
        or not bool(scope["development_data_consumed"])
        or not bool(scope["fixed_candidate_replay_only"])
        or any(bool(scope[key]) for key in (
            "symmetry_validated", "online_cancellation_validated",
            "plant_response_validated", "transition_model_validated",
            "mpc_validated", "expert_data_allowed", "bc_dagger_or_rl_allowed",
        ))
        or not bool(scope["pass_authorizes_r2_design_only"])
    ):
        raise ValueError("D1R14R1A frozen design changed")


def _authenticate_r1(
    project: Path, output: Path, cfg: Mapping[str, Any]
) -> tuple[dict[str, Any], Mapping[str, Any], Mapping[str, Any]]:
    source = cfg["source_r1_contract"]
    r1_config = project / source["config"]
    r1_implementation = project / source["implementation"]
    paths = {
        "detailed": output / source["detailed_filename"],
        "summary": output / source["summary_filename"],
        "manifest": output / source["manifest_filename"],
    }
    hashes = {name: _sha256(path) for name, path in paths.items()}
    expected = {
        "detailed": source["detailed_sha256"],
        "summary": source["summary_sha256"],
        "manifest": source["manifest_sha256"],
    }
    if (
        output.name != source["output_name"]
        or any(not path.is_file() for path in paths.values())
        or _sha256(r1_config) != source["config_sha256"]
        or _sha256(r1_implementation) != source["implementation_sha256"]
        or hashes != expected
    ):
        raise ValueError("D1R14R1A immutable R1 source changed")
    detailed = _read_json(paths["detailed"])
    summary = _read_json(paths["summary"])
    manifest = _read_json(paths["manifest"])
    issue_rows = detailed["static_issue_preflight"]["construction_rows"]
    failures = [row for row in issue_rows if not row["passed"]]
    if (
        detailed.get("route") != source["required_route"]
        or summary.get("route") != source["required_route"]
        or manifest.get("route") != source["required_route"]
        or not bool(detailed["source_authentication"]["passed"])
        or not bool(detailed["search"]["passed"])
        or int(summary.get("static_issue_construction_pass_count", -1)) != 48
        or int(summary.get("static_issue_construction_count", -1)) != 64
        or len(failures) != 16
        or any(int(row["direction_index"]) != 2 for row in failures)
        or any(
            {key for key, passed in row["criteria"].items() if not passed}
            != {"off_basis"}
            for row in failures
        )
        or int(summary.get("new_raw_count", -1)) != 0
        or bool(summary.get("tsc_executed"))
        or bool(manifest.get("ray_gotsc_tsc_plant_or_controller_executed"))
    ):
        raise ValueError("D1R14R1A R1 failure boundary changed")
    r1_cfg = _read_json(r1_config)
    r1._validate_design(r1_cfg)
    return {
        "output": str(output),
        "hashes": hashes,
        "failure_count": len(failures),
        "failure_direction_index": 2,
        "failure_criterion": "off_basis",
        "passed": True,
    }, r1_cfg, detailed


def _fixed_matrix(cfg: Mapping[str, Any], r1_cfg: Mapping[str, Any]) -> dict[str, Any]:
    repair = cfg["repair_contract"]
    base = np.asarray(r1_cfg["selected_requested_coordinate_matrix_columns"], dtype=float)
    generated = base.copy()
    generated[:, int(repair["scaled_column_index"])] *= float(repair["fixed_scale"])
    selected = np.asarray(cfg["selected_requested_coordinate_matrix_columns"], dtype=float)
    exact = bool(
        np.array_equal(generated, selected)
        and r1._matrix_digest(generated) == cfg["selected_matrix_float64_le_c_sha256"]
    )
    return {
        "scaled_column_index": int(repair["scaled_column_index"]),
        "fixed_scale": float(repair["fixed_scale"]),
        "generated_matrix": generated.tolist(),
        "selected_matrix": selected.tolist(),
        "matrix_float64_le_c_sha256": r1._matrix_digest(generated),
        "exact": exact,
        "passed": exact,
    }


def run_audit(args: argparse.Namespace) -> dict[str, Any]:
    project = args.project.expanduser().resolve()
    config_path = args.config.expanduser().resolve()
    design_path = args.design_document.expanduser().resolve()
    source_r1_output = args.source_r1_output.expanduser().resolve()
    source_d1r14_run = args.source_d1r14_run.expanduser().resolve()
    output = args.output.expanduser().resolve()
    cfg = _read_json(config_path)
    _validate_design(cfg)
    if _sha256(design_path) != cfg["design_document_sha256"]:
        raise ValueError("D1R14R1A design-document hash mismatch")
    if output.exists():
        raise ValueError("D1R14R1A output directory must be new")
    source_r1, r1_cfg, _ = _authenticate_r1(project, source_r1_output, cfg)
    source_d1r14, specs, results, paths = r1._authenticate_source(
        source_d1r14_run, project, r1_cfg
    )
    source_cfg = _read_json(project / r1_cfg["source_contract"]["config"])
    context_ids, matrices = r1._response_matrices(source_cfg, specs, results)
    matrix = _fixed_matrix(cfg, r1_cfg)
    selected = np.asarray(cfg["selected_requested_coordinate_matrix_columns"], dtype=float)
    amplitude = float(cfg["response_contract"]["original_requested_coordinate_amplitude"])
    minimum_peak, maximum_condition, context_rows = r1._candidate_metrics(
        matrices, selected / amplitude
    )
    response_pass = bool(
        minimum_peak >= float(cfg["response_contract"]["minimum_predicted_odd_peak"]) - 5e-12
        and maximum_condition
        <= float(cfg["response_contract"]["maximum_predicted_unit_column_condition"]) + 1e-12
    )
    response = {
        "context_count": len(context_rows),
        "minimum_predicted_odd_peak": minimum_peak,
        "maximum_predicted_unit_column_condition": maximum_condition,
        "context_rows": context_rows,
        "passed": response_pass,
    }
    adapter = copy.deepcopy(r1_cfg)
    adapter["selected_requested_coordinate_matrix_columns"] = selected.tolist()
    adapter["static_issue_contract"] = copy.deepcopy(cfg["static_issue_contract"])
    issue = r1._static_issue_preflight(
        project, paths, adapter, source_cfg, specs, results
    )
    passed = bool(
        source_r1["passed"]
        and source_d1r14["passed"]
        and matrix["passed"]
        and response["passed"]
        and issue["passed"]
    )
    route = cfg["routes"]["pass"] if passed else cfg["routes"]["preflight_fail"]
    detailed = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "source_r1_authentication": source_r1,
        "source_d1r14_authentication": source_d1r14,
        "context_ids": context_ids,
        "fixed_matrix": matrix,
        "predicted_response": response,
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
        "source_r1_authenticated": source_r1["passed"],
        "source_raw_count": source_d1r14["strict_raw_count"],
        "matrix_digest": matrix["matrix_float64_le_c_sha256"],
        "predicted_minimum_odd_peak": minimum_peak,
        "predicted_maximum_unit_column_condition": maximum_condition,
        "static_issue_construction_pass_count": issue["construction_pass_count"],
        "static_issue_construction_count": issue["construction_count"],
        "maximum_off_basis_residual": max(row["relative_off_basis_residual"] for row in issue["construction_rows"]),
        "maximum_issue_incremental_normalized_action_linf": issue["maximum_issue_incremental_normalized_action_linf"],
        "maximum_linearized_cancel_incremental_linf_diagnostic_only": issue["maximum_linearized_cancel_incremental_linf_diagnostic_only"],
        "online_cancellation_proved": False,
        "new_raw_count": 0,
        "tsc_executed": False,
        "passed": passed,
        "route": route,
    }
    output.mkdir(parents=True)
    detailed_path = output / "stage4_2r3c3t13s24d1r14r1a_detailed_v1.json"
    summary_path = output / "stage4_2r3c3t13s24d1r14r1a_summary_v1.json"
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
        "source_r1_output": str(source_r1_output),
        "source_d1r14_run": str(source_d1r14_run),
        "source_raw_read_in_place": True,
        "new_raw_files_created": 0,
        "ray_gotsc_tsc_plant_or_controller_executed": False,
        "outputs": {
            detailed_path.name: _sha256(detailed_path),
            summary_path.name: _sha256(summary_path),
        },
        "route": route,
    }
    _write_json(output / "stage4_2r3c3t13s24d1r14r1a_manifest_v1.json", manifest)
    return summary


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--design-document", type=Path, required=True)
    parser.add_argument("--source-r1-output", type=Path, required=True)
    parser.add_argument("--source-d1r14-run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main() -> None:
    summary = run_audit(_parser().parse_args())
    print(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
