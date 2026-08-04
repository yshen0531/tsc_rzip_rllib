#!/usr/bin/env python3
"""Independent raw audit for the Stage4.2R3c3T13S24D1R14R6 sentinel.

This audit does not import the R6 implementation.  It reuses only the frozen
R4 independent geometry routine after independently replacing its direction-0
members with the 48 R6 trajectories.
"""

from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np


STAGE = "Stage4.2R3c3T13S24D1R14R6"
RUN_NAME = "stage4_2r3c3t13s24d1r14r6_direction0_replacement_sentinel"
R4_RUN_NAME = "stage4_2r3c3t13s24d1r14r4_time_shifted_sign_split_sentinel_20260804_f5b8348_v1"
R4_STAGE_NAME = "stage4_2r3c3t13s24d1r14r4_time_shifted_sign_split_sentinel"
R2_STAGE_NAME = "stage4_2r3c3t13s24d1r14r2_mixed_basis_signed_excitation_sentinel"
D1R13_STAGE_NAME = "stage4_2r3c3t13s24d1r13_zero_increment_deconfounding_sentinel"
D1R11_STAGE_NAME = "stage4_2r3c3t13s24d1r11_full_replacement_sequential_transition_identification"
R5_OUTPUT_NAME = "stage4_2r3c3t13s24d1r14r5_global_direction0_gain_preflight_20260804_bb829f3_v3"
CAMPAIGN_IDENTITY = "direction0_replacement_safety_identification_sentinel_v1"
CONTROLLER_REVISION = "direction0_replacement_v42r3c3t13s24d1r14r6_v1"
MATRIX_DIGEST = "69528f0e204b51847c1d2a7df428555a557454e9fa6bc76768d39e7cc5a90da8"
PASS_ROUTE = "DIRECTION0_REPLACEMENT_SENTINEL_PASS_MODEL_FIT_DESIGN_REQUIRED"
RUNTIME_ROUTE = "DIRECTION0_REPLACEMENT_SENTINEL_EXECUTION_OR_SAFETY_FAIL_STOP"
GEOMETRY_ROUTE = "DIRECTION0_REPLACEMENT_SENTINEL_GEOMETRY_FAIL_REDESIGN_REQUIRED"
ISSUE_STEPS = (14, 18, 22)
PREFIX_END = 10
NON_SEMANTIC = frozenset({"gotsc_subprocess_s", "step_total_s"})
EXPECTED_CALIBRATION = [
    "calibration_issue", "calibration_cancel", "calibration_issue", "calibration_cancel",
    "calibration_issue", "calibration_cancel", "calibration_issue", "calibration_cancel",
]
R4_BOUNDARY = {
    "raw_count": 200,
    "raw_bytes": 6_285_765,
    "raw_digest": "44a7eb8e677f88f32c57a6be59273501e73f7657527371e1b59578a95c2ae7a9",
    "spec_digest": "080a2df84c86801d76251853a165839e8db59f6614f6b2b446141b0691841059",
    "final": "af9acfb9e524e6ad33799b832981ec7fb2e265ff7c1d3e78796413e83382db71",
    "independent": "6a4eec4a660beb6a29e11e184906b8b7a737834280091f1997af74e86fbd761c",
}
R5_HASHES = {
    "stage4_2r3c3t13s24d1r14r5_detailed_v1.json": "deb57e9c774ef792ed9f8464987e4528b69f3876a09dcd7ff4ca55ea8d9dedc9",
    "stage4_2r3c3t13s24d1r14r5_summary_v1.json": "fc9d1fded5bf63e2658ad0c8da5aca642011006edd04ae1ee8aaaec58051a213",
    "stage4_2r3c3t13s24d1r14r5_manifest_v1.json": "be2b358bbe35f5fff1029f4cb94b8a1638fd7e5b2c3bb244fe51fb1de0fd0d35",
    "stage4_2r3c3t13s24d1r14r5_independent_v1.json": "306fd16a65ad44bea1972fb37f4ce316363eeff8a3834ceea8973afe1f42f3cb",
}
FORBIDDEN_TRACE_KEYS = (
    "future_measurement_used", "hidden_wire_used", "source_action_used",
    "source_coil_current_used", "source_wire_current_used", "current_run_future_used",
    "pair_or_history_label_used", "source_result_used",
    "future_probe_schedule_available_to_underlying_controller",
    "r3c3t13s21_partition_label_used", "r3c3t13s24_pair_history_partition_label_used",
    "r3c3t13s24_delay_slew_target_id_label_used", "r3c3t13s24_source_or_matched_baseline_used",
    "r3c3t13s24_future_measurement_used", "r3c3t13s24_future_executed_action_used",
    "r3c3t13s24_hidden_wire_current_used", "r3c3t13s24_schedule_available_to_underlying_controller",
    "r3c3t13s24d1r13_future_r17_executed", "r3c3t13s24d1r14r6_future_r17_executed",
)


def _load_r4_independent(project: Path) -> Any:
    path = project / "docs/codex/audit_tools/stage4_2r3c3t13s24d1r14r4_independent_forensics.py"
    spec = importlib.util.spec_from_file_location("frozen_r4_independent", path)
    if spec is None or spec.loader is None:
        raise ValueError("cannot load frozen R4 independent audit")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _event_passes(event: Mapping[str, Any], name: str, step: int) -> bool:
    criteria = event.get("criteria") or {}
    return bool(
        event.get("event") == name
        and int(event.get("slot", -1)) == 0
        and int(event.get("task_step", -1)) == step
        and event.get("passed")
        and criteria
        and all(bool(value) for value in criteria.values())
    )


def _nested_true_count(value: Any, names: frozenset[str]) -> int:
    if isinstance(value, Mapping):
        return sum(int(key in names and item is True) + _nested_true_count(item, names) for key, item in value.items())
    if isinstance(value, list):
        return sum(_nested_true_count(item, names) for item in value)
    return 0


def _adapt_combined_bank(
    r4_specs: Sequence[Mapping[str, Any]],
    r4_results: Mapping[str, Mapping[str, Any]],
    r6_specs: Sequence[Mapping[str, Any]],
    r6_results: Mapping[str, Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    specs: list[dict[str, Any]] = []
    results: dict[str, dict[str, Any]] = {}
    for source in r4_specs:
        role = str(source["d1r14r4_role"])
        direction = int(source["d1r14r4_direction_index"])
        if role == "baseline" or (role == "signed_probe" and direction in (1, 2, 3)):
            experiment_id = str(source["experiment_id"])
            specs.append(copy.deepcopy(dict(source)))
            results[experiment_id] = copy.deepcopy(dict(r4_results[experiment_id]))
    for source in r6_specs:
        if str(source["d1r14r6_role"]) != "signed_probe" or int(source["d1r14r6_direction_index"]) != 0:
            raise ValueError("R6 contains an unexpected bank member")
        experiment_id = str(source["experiment_id"])
        adapted = copy.deepcopy(dict(source))
        for suffix in (
            "role", "direction_index", "direction_name", "sign", "requested_coordinate",
            "requested_matrix_digest", "issue_task_step", "cancel_task_step", "zero_after_task_step",
        ):
            adapted[f"d1r14r4_{suffix}"] = adapted[f"d1r14r6_{suffix}"]
        result = copy.deepcopy(dict(r6_results[experiment_id]))
        for trace in result.get("controller_trace") or []:
            if "r3c3t13s24d1r14r6_event_detail" in trace:
                trace["r3c3t13s24d1r14r4_event_detail"] = copy.deepcopy(
                    trace["r3c3t13s24d1r14r6_event_detail"]
                )
        specs.append(adapted)
        results[experiment_id] = result
    if len(specs) != 200 or len(results) != 200:
        raise ValueError("combined bank is not 200 members")
    return specs, results


def audit(
    run_dir: Path,
    source_d1r13_run: Path,
    source_d1r11_run: Path,
    source_r2_run: Path,
    source_r4_run: Path,
    source_r5_output: Path,
    project: Path,
    logs: Sequence[Path],
) -> dict[str, Any]:
    run_dir = run_dir.resolve()
    source_d1r13_run = source_d1r13_run.resolve()
    source_d1r11_run = source_d1r11_run.resolve()
    source_r2_run = source_r2_run.resolve()
    source_r4_run = source_r4_run.resolve()
    source_r5_output = source_r5_output.resolve()
    project = project.resolve()
    r4i = _load_r4_independent(project)
    strict_json, strict_gzip = r4i._strict_json, r4i._strict_gzip
    sha256, digest, inventory = r4i._sha256, r4i._digest, r4i._raw_inventory
    semantic, trace_projection = r4i._semantic, r4i._trace_projection
    all_finite = r4i._all_finite

    stage = run_dir / RUN_NAME
    specs = strict_json(stage / "specs/sentinel_specs.json")
    manifest = strict_json(stage / "stage_manifest.json")
    state = strict_json(stage / "stage_state.json")
    final = strict_json(stage / "analysis/final_result.json")
    if len(specs) != 48 or len({str(row["experiment_id"]) for row in specs}) != 48:
        raise ValueError("R6 spec coverage changed")
    if digest(specs) != str(manifest.get("spec_digest")):
        raise ValueError("R6 saved spec digest changed")

    r4_stage = source_r4_run / R4_STAGE_NAME
    r4_specs = strict_json(r4_stage / "specs/sentinel_specs.json")
    r4_inventory = inventory(r4_stage / "raw")
    if (
        source_r4_run.name != R4_RUN_NAME
        or int(r4_inventory["count"]) != R4_BOUNDARY["raw_count"]
        or int(r4_inventory["bytes"]) != R4_BOUNDARY["raw_bytes"]
        or str(r4_inventory["digest"]) != R4_BOUNDARY["raw_digest"]
        or digest(r4_specs) != R4_BOUNDARY["spec_digest"]
        or sha256(source_r4_run / "final_result.json") != R4_BOUNDARY["final"]
        or sha256(source_r4_run / "server_independent_forensics_v1.json") != R4_BOUNDARY["independent"]
    ):
        raise ValueError("R4 boundary changed")
    r4_results = {
        str(spec["experiment_id"]): strict_gzip(r4_stage / "raw" / f"{spec['experiment_id']}.json.gz")
        for spec in r4_specs
    }
    r4_baselines = {
        str(spec["source_d1r13_experiment_id"]): r4_results[str(spec["experiment_id"])]
        for spec in r4_specs if str(spec["d1r14r4_role"]) == "baseline"
    }
    if len(r4_baselines) != 8:
        raise ValueError("R4 baseline coverage changed")

    if source_r5_output.name != R5_OUTPUT_NAME or any(
        sha256(source_r5_output / name) != expected for name, expected in R5_HASHES.items()
    ):
        raise ValueError("R5 boundary changed")
    r5_summary = strict_json(source_r5_output / "stage4_2r3c3t13s24d1r14r5_summary_v1.json")
    if (
        not r5_summary.get("passed")
        or r5_summary.get("route") != "GLOBAL_DIRECTION0_GAIN_PREFLIGHT_PASS_REAL_SENTINEL_DESIGN_REQUIRED"
        or int(r5_summary.get("construction_pass_count", -1)) != 48
        or int(r5_summary.get("antipodal_pair_pass_count", -1)) != 24
        or r5_summary.get("candidate_matrix_digest") != MATRIX_DIGEST
        or int(r5_summary.get("new_raw_count", -1)) != 0
        or bool(r5_summary.get("tsc_executed"))
    ):
        raise ValueError("R5 decision changed")

    d1r13_stage = source_d1r13_run / D1R13_STAGE_NAME
    d1r11_stage = source_d1r11_run / D1R11_STAGE_NAME
    results: dict[str, dict[str, Any]] = {}
    rows = []
    snapshots: dict[str, dict[str, Any]] = {}
    for spec in specs:
        experiment_id = str(spec["experiment_id"])
        path = stage / "raw" / f"{experiment_id}.json.gz"
        current = strict_gzip(path)
        results[experiment_id] = current
        source13_path = d1r13_stage / "raw" / f"{spec['source_d1r13_experiment_id']}.json.gz"
        source11_path = d1r11_stage / "raw" / f"{spec['source_d1r11_experiment_id']}.json.gz"
        source13, source11 = strict_gzip(source13_path), strict_gzip(source11_path)
        trajectory, trace = current.get("trajectory") or [], current.get("controller_trace") or []
        horizon = int(spec["horizon_steps"])
        full = len(trajectory) == horizon + 1 and len(trace) == horizon
        prefix_state = bool(full and all(
            semantic(left) == semantic(right)
            for left, right in zip(trajectory[:11], source13["trajectory"][:11])
        ))
        prefix_trace = bool(full and all(
            trace_projection(reference, actual)
            for reference, actual in zip(source11["controller_trace"][:10], trace[:10])
        ))
        calibration = [
            row.get("r3c3t13s16_lattice_event") for row in trace[:10]
            if row.get("r3c3t13s16_lattice_event") != "none"
        ] == EXPECTED_CALIBRATION and bool(trace[7].get("r3c3t13s21_exact_calibration_net_zero"))
        currents = [list(map(float, row.get("currents_a_tsc") or [])) for row in trajectory]
        finite = bool(full and all(
            all_finite([row.get("R"), row.get("Z"), row.get("Ip")])
            and len(row.get("currents_a_tsc") or []) == 14
            and all_finite(row.get("currents_a_tsc") or [])
            and bool(row.get("wire_currents_a")) and all_finite(row.get("wire_currents_a") or [])
            and int(row.get("wire_current_count", -1)) == len(row.get("wire_currents_a") or [])
            and not row.get("abnormal") for row in trajectory
        ))
        payload = strict_json(stage / "variants" / f"payload_{experiment_id}.json")
        minimum, maximum = list(map(float, payload["min_current_tsc"])), list(map(float, payload["max_current_tsc"]))
        utilization = max(
            abs((value - 0.5 * (lo + hi)) / (0.5 * (hi - lo)))
            for current_row in currents for value, lo, hi in zip(current_row, minimum, maximum)
        ) if full else None
        issue_step = int(spec["d1r14r6_issue_task_step"])
        cancel_step = int(spec["d1r14r6_cancel_task_step"])
        zero_after = int(spec["d1r14r6_zero_after_task_step"])
        issue = trace[issue_step].get("r3c3t13s24d1r14r6_event_detail") or {}
        cancel = trace[cancel_step].get("r3c3t13s24d1r14r6_event_detail") or {}
        preissue_action_zero = all(list(map(float, row.get("action_norm_tsc") or [])) == [0.0] * 14 for row in trace[10:issue_step])
        preissue_current_zero = all(currents[index + 1] == currents[index] for index in range(10, issue_step))
        r4_issue_exact = semantic(trajectory[issue_step]) == semantic(
            r4_baselines[str(spec["source_d1r13_experiment_id"])]["trajectory"][issue_step]
        )
        issue_exact = _event_passes(issue, "sequential_issue", issue_step) and list(map(float, issue.get("requested_coordinate") or [])) == list(map(float, spec["d1r14r6_requested_coordinate"]))
        cancel_exact = _event_passes(cancel, "sequential_cancel", cancel_step) and cancel.get("stored_center_card15_fields") == issue.get("center_card15_fields")
        post_action_zero = all(list(map(float, row.get("action_norm_tsc") or [])) == [0.0] * 14 for row in trace[zero_after:])
        post_current_zero = all(currents[index + 1] == currents[index] for index in range(zero_after, horizon))
        forbidden = sum(any(bool(row.get(key)) for key in FORBIDDEN_TRACE_KEYS) for row in trace)
        solver = sum(not bool(row.get("solver_success")) for row in trace)
        saturation = _nested_true_count(trace, frozenset({"action_saturated", "current_limit_clipped"}))
        snapshot_key = str(spec["restart_snapshot_dir"])
        if snapshot_key not in snapshots:
            snapshots[snapshot_key] = r4i._snapshot_inventory(Path(snapshot_key).resolve(), str(spec["restart_snapshot_manifest_digest"]))
        summary = current.get("hidden_history_control_summary") or {}
        fresh = bool(
            summary.get("fresh_controller_actor") and summary.get("fresh_tsc_process")
            and summary.get("full_tsc_hidden_state_loaded_from_sprsina")
            and not summary.get("future_r17_controller_executed")
        )
        identity = bool(
            current.get("stage") == STAGE and current.get("campaign_identity") == CAMPAIGN_IDENTITY
            and current.get("controller_revision") == CONTROLLER_REVISION
            and current.get("experiment_id") == experiment_id and current.get("spec") == spec
            and str(spec.get("d1r14r6_role")) == "signed_probe"
            and int(spec.get("d1r14r6_direction_index", -1)) == 0
            and spec.get("d1r14r6_requested_matrix_digest") == MATRIX_DIGEST
            and sha256(source13_path) == str(spec["source_d1r13_raw_sha256"])
            and source13_path.stat().st_size == int(spec["source_d1r13_raw_size_bytes"])
        )
        passed = bool(
            identity and current.get("success") is True and current.get("completed") is True
            and full and prefix_state and prefix_trace and calibration and finite
            and preissue_action_zero and preissue_current_zero and r4_issue_exact
            and issue_exact and cancel_exact and post_action_zero and post_current_zero
            and forbidden == solver == saturation == 0 and utilization is not None and utilization <= 0.55 + 1e-12
            and fresh and snapshots[snapshot_key]["passed"]
        )
        rows.append({
            "experiment_id": experiment_id, "identity_exact": identity,
            "runtime_success": bool(current.get("success") is True and current.get("completed") is True),
            "execution_failure_class": str(current.get("execution_failure_class") or ""),
            "full_horizon": full, "source_prefix_state_exact": prefix_state,
            "source_prefix_trace_exact": prefix_trace, "calibration_exact": calibration,
            "preissue_actions_exact_zero": preissue_action_zero,
            "preissue_current_increments_exact_zero": preissue_current_zero,
            "r4_baseline_issue_state_exact": r4_issue_exact, "issue_exact": issue_exact,
            "cancel_exact": cancel_exact, "zero_after_actions_exact_zero": post_action_zero,
            "zero_after_current_increments_exact_zero": post_current_zero,
            "finite_coil_and_wire_records": finite, "forbidden_trace_count": forbidden,
            "solver_error_count": solver, "saturation_or_clip_count": saturation,
            "fresh_controller_and_tsc": fresh, "maximum_current_utilization": utilization,
            "raw_sha256": sha256(path), "raw_size_bytes": path.stat().st_size, "passed": passed,
        })

    safety_count = sum(bool(row["passed"]) for row in rows)
    raw_inventory = inventory(stage / "raw")
    runtime_count = sum(row["execution_failure_class"] in {"runtime_or_controller_error", "ray_actor_runtime_error"} for row in rows)
    prefix_failure_count = sum(not (row["source_prefix_state_exact"] and row["source_prefix_trace_exact"] and row["calibration_exact"]) for row in rows)
    if safety_count == 48 and raw_inventory["count"] == 48:
        r2_stage = source_r2_run / R2_STAGE_NAME
        r2_specs = strict_json(r2_stage / "specs/sentinel_specs.json")
        r2_results = {str(spec["experiment_id"]): strict_gzip(r2_stage / "raw" / f"{spec['experiment_id']}.json.gz") for spec in r2_specs}
        combined_specs, combined_results = _adapt_combined_bank(r4_specs, r4_results, specs, results)
        geometry = r4i._geometry(combined_specs, combined_results, r2_specs, r2_results)
        replacement = [row for row in geometry["issue_coordinate_and_field_symmetry"]["rows"] if int(row["issue_task_step"]) in ISSUE_STEPS and int(row["direction_index"]) == 0]
        geometry["r6_direction0_antipodal_pair_count"] = len(replacement)
        geometry["r6_direction0_antipodal_pair_pass_count"] = sum(bool(row["passed"]) for row in replacement)
        geometry["r6_direction0_antipodal_passed"] = len(replacement) == 24 and all(bool(row["passed"]) for row in replacement)
        geometry["passed"] = bool(geometry.get("passed") and geometry["r6_direction0_antipodal_passed"])
    else:
        geometry = {"evaluated": False, "passed": False, "reason": "safety_or_inventory_gate_failed"}
    official_geometry = final.get("response_geometry") or {}
    metric_names = (
        "evaluated", "passed", "branch_count", "branch_direction_count", "signal_pass_count",
        "rank_pass_count", "condition_pass_count", "r6_direction0_antipodal_pair_count",
        "r6_direction0_antipodal_pair_pass_count", "r6_direction0_antipodal_passed",
    )
    geometry_exact = all(geometry.get(key) == official_geometry.get(key) for key in metric_names) and all(
        math.isclose(float(geometry[key]), float(official_geometry[key]), rel_tol=0.0, abs_tol=1e-12)
        for key in ("minimum_direction_peak_normalized_outputs5", "maximum_condition_number")
        if geometry.get(key) is not None and official_geometry.get(key) is not None
    )
    route = RUNTIME_ROUTE if runtime_count or prefix_failure_count or raw_inventory["count"] != 48 or safety_count != 48 else (PASS_ROUTE if geometry.get("passed") else GEOMETRY_ROUTE)
    official_route_exact = route == final.get("route")
    package_hashes = {}
    for relative in (
        "configs/stage4_2r3c3t13s24d1r14r6_direction0_replacement_sentinel_370ms.json",
        "tsc_rzip_rllib/diagnostics/stage4_2r3c3t13s24d1r14r6_direction0_replacement_sentinel.py",
        "scripts/stage4_2r3c3t13s24d1r14r6_direction0_replacement_sentinel.py",
        "docs/codex/audit_tools/stage4_2r3c3t13s24d1r14r6_independent_forensics.py",
        "docs/codex/reports/STAGE4_2R3C3T13S24D1R14R6_REAL_TSC_DIRECTION0_REPLACEMENT_SENTINEL_DESIGN.md",
    ):
        package_hashes[relative] = sha256(project / relative)
        if manifest.get("package_fingerprint", {}).get("hashes", {}).get(relative) != package_hashes[relative]:
            raise ValueError(f"R6 package member changed: {relative}")
    log_rows = r4i._log_audit(logs)
    raw_inventory_exact = raw_inventory == final.get("raw_inventory")
    passed = bool(
        len(rows) == safety_count == 48 and raw_inventory_exact and geometry_exact
        and official_route_exact and all(value["passed"] for value in snapshots.values())
    )
    return {
        "schema_version": 1, "audit_revision": "independent_direction0_replacement_v1",
        "stage": STAGE, "run_dir": str(run_dir), "audit_completed": True,
        "strict_raw_parse_count": len(rows), "raw_pass_count": safety_count,
        "safety_pass_count": safety_count, "runtime_or_environment_error_count": runtime_count,
        "prefix_failure_count": prefix_failure_count,
        "r4_baseline_issue_state_exact_count": sum(bool(row["r4_baseline_issue_state_exact"]) for row in rows),
        "issue_exact_count": sum(bool(row["issue_exact"]) for row in rows),
        "cancel_exact_count": sum(bool(row["cancel_exact"]) for row in rows),
        "forbidden_trace_count": sum(int(row["forbidden_trace_count"]) for row in rows),
        "solver_error_count": sum(int(row["solver_error_count"]) for row in rows),
        "saturation_or_clip_count": sum(int(row["saturation_or_clip_count"]) for row in rows),
        "maximum_current_utilization": max(float(row["maximum_current_utilization"]) for row in rows),
        "current_inventory": raw_inventory, "official_raw_inventory_exact": raw_inventory_exact,
        "source_r4_inventory": r4_inventory, "source_r5_authenticated": True,
        "snapshot_pass_count": sum(bool(value["passed"]) for value in snapshots.values()),
        "snapshot_unique_count": len(snapshots), "response_geometry": geometry,
        "official_geometry_exact": geometry_exact, "independent_route": route,
        "official_route_reproduced": official_route_exact, "package_hashes": package_hashes,
        "official_result_sha256": sha256(stage / "analysis/final_result.json"),
        "stage_state_sha256": sha256(stage / "stage_state.json"),
        "stage_manifest_sha256": sha256(stage / "stage_manifest.json"),
        "logs": log_rows, "snapshots": list(snapshots.values()), "rows": rows,
        "classification": {
            "runtime_or_environment_error": runtime_count > 0,
            "packaging_import_or_deployment_error": False,
            "raw_or_snapshot_corruption": not raw_inventory_exact or any(not value["passed"] for value in snapshots.values()),
            "summary_or_reporting_error": not geometry_exact or not official_route_exact,
            "controller_or_identification_design_failure": not bool(geometry.get("passed")),
        },
        "scientific_boundary": {
            "real_tsc_executed": True, "new_raw_count": 48,
            "probe_trajectories_allowed_in_expert_dataset": False,
            "transition_model_validated": False, "mpc_validated": False,
            "bc_dagger_or_rl_allowed": False,
        },
        "passed": passed,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--source-d1r13-run", type=Path, required=True)
    parser.add_argument("--source-d1r11-run", type=Path, required=True)
    parser.add_argument("--source-r2-run", type=Path, required=True)
    parser.add_argument("--source-r4-run", type=Path, required=True)
    parser.add_argument("--source-r5-output", type=Path, required=True)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--log", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(
        args.run_dir, args.source_d1r13_run, args.source_d1r11_run,
        args.source_r2_run, args.source_r4_run, args.source_r5_output,
        args.project, args.log,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in (
        "stage", "audit_completed", "strict_raw_parse_count", "safety_pass_count",
        "independent_route", "official_route_reproduced", "official_geometry_exact", "passed",
    )}, sort_keys=True, indent=2))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
