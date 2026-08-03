"""Retrospective all-raw prefix forensics for the completed D1R2 sentinel.

This reporting-only audit does not replace the prospectively frozen independent
audit.  It closes that audit's aggregation gap for structured safe-stop raws by
checking their executed prefixes and counting all 216 cancellation attempts.
"""

from __future__ import annotations

from collections import Counter
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r2_real_tsc_safety_sentinel_forensics as prospective,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r2_real_tsc_safety_sentinel as stage,
)


EXPECTED_RUN_NAME = (
    "stage4_2r3c3t13s24d1r2_geometry_restored_amplitude_safety_sentinel_"
    "20260803_160327_9e6bba2_v2"
)
EXPECTED_RAW_INVENTORY_DIGEST = (
    "eb4ac8c0e606ce0d8899f0a512b594877f59cc9424c0f6a87e3450bcd036cc83"
)
EXPECTED_RAW_TOTAL_BYTES = 3_078_383
EXPECTED_PROSPECTIVE_AUDIT_SHA256 = (
    "a506dde9cf0f57607cda8af3e12c7e26c2f0e731f32e6b1da74ab8c3016a6dcd"
)
EXPECTED_COMPLETE_LOG_SHA256 = (
    "89b23c022580ec70fb4df1d8367759685b610ccd319eb59b6383a3c14e5321ff"
)
EXPECTED_PACKAGE_REVISION = (
    "r42r3c3t13s24d1r2_geometry_restored_amplitude_safety_sentinel_v2"
)
EXPECTED_IMPLEMENTATION_CHECKPOINT = "9a8ce4d"
EXPECTED_ROUTE = "GEOMETRY_RESTORED_SENTINEL_ACTION_MARGIN_FAIL_REDESIGN_REQUIRED"


def _all_finite(value: Any) -> bool:
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return True
    if isinstance(value, (int, float)):
        return math.isfinite(float(value))
    if isinstance(value, Mapping):
        return all(_all_finite(item) for item in value.values())
    if isinstance(value, Sequence):
        return all(_all_finite(item) for item in value)
    return True


def _initial_restart_exact(
    result: Mapping[str, Any], state_map: Mapping[str, Mapping[str, Any]]
) -> tuple[bool, bool, bool]:
    initial = result["trajectory"][0]
    generated = state_map[str(result["spec"]["state_generation_experiment_id"])]
    generated_visible = np.asarray(
        [
            generated["R"],
            generated["Z"],
            generated["Ip"],
            *generated["coil_currents_a"],
        ],
        dtype=float,
    )
    restarted_visible = np.asarray(
        [initial["R"], initial["Z"], initial["Ip"], *initial["currents_a_tsc"]],
        dtype=float,
    )
    generated_wire = np.asarray(generated["wire_currents_a"], dtype=float)
    restarted_wire = np.asarray(initial["wire_currents_a"], dtype=float)
    visible = bool(np.array_equal(generated_visible, restarted_visible))
    wire = bool(
        generated_wire.shape == restarted_wire.shape
        and np.array_equal(generated_wire, restarted_wire)
    )
    return visible, wire, bool(visible and wire)


def _audit_row(
    ctx: stage.Context,
    spec: Mapping[str, Any],
    result: Mapping[str, Any],
    state_map: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    trajectory = list(result.get("trajectory") or [])
    trace = list(result.get("controller_trace") or [])
    currents = np.asarray([row["currents_a_tsc"] for row in trajectory], dtype=float)
    actions = np.asarray([row["action_norm_tsc"] for row in trace], dtype=float)
    recorded = np.asarray(
        [row["action_norm_tsc"] for row in trajectory[1:]], dtype=float
    )
    payload = stage._payload(ctx, spec)
    minimum, maximum = stage.s24.s21.s13._current_limits_tsc(payload)
    center, half = 0.5 * (minimum + maximum), 0.5 * (maximum - minimum)
    utilization = float(np.max(np.abs((currents - center) / half)))
    visible, wire, restart = _initial_restart_exact(result, state_map)
    phase = stage.s24.s21.s16.s9.t11.t1.r3c1._phase_trace_valid(result)
    calibration = stage.s24.s21._dynamic_calibration_trace_audit(
        result, ctx.base_s24_ctx.base_ctx.cfg
    )
    calibration_events = [
        row.get("r3c3t13s16_lattice_event")
        for row in trace
        if row.get("r3c3t13s16_lattice_event") != "none"
    ]
    sequence_events = [
        row.get("r3c3t13s24d1r2_event")
        for row in trace
        if row.get("r3c3t13s24d1r2_event") != "none"
    ]
    event_details = [
        row["r3c3t13s24d1r2_event_detail"]
        for row in trace
        if row.get("r3c3t13s24d1r2_event") != "none"
    ]
    issues = [row for row in event_details if row.get("event") == "sequential_issue"]
    cancels = [row for row in event_details if row.get("event") == "sequential_cancel"]
    success = bool(result.get("success"))
    failure = result.get("action_failure_event") or {}
    failure_criteria = failure.get("criteria") or {}
    structured = bool(
        not success
        and result.get("completed")
        and result.get("failure_class") == "structured_action_schedule_gate"
        and failure.get("event") == "sequential_cancel"
        and failure.get("task_step") == 18
        and failure.get("slot") == 3
        and not failure.get("passed")
        and failure_criteria.get("online_cancel_margin") is False
    )
    expected_sequence = prospective._expected_sequence()
    horizon = int(spec["horizon_steps"])
    length_pass = bool(
        len(trajectory) == len(trace) + 1
        and currents.shape == (len(trace) + 1, 14)
        and actions.shape == recorded.shape == (len(trace), 14)
        and (
            (success and len(trace) == horizon)
            or (structured and len(trace) == int(failure["task_step"]))
        )
    )
    failure_not_applied = bool(
        success
        or (
            structured
            and len(trace) == int(failure["task_step"])
            and int(trace[-1]["task_step"]) == int(failure["task_step"]) - 1
            and int(trajectory[-1]["step_index"]) == int(failure["task_step"])
        )
    )
    sequence_pass = bool(
        (success and sequence_events == expected_sequence)
        or (
            structured
            and sequence_events == expected_sequence[:-1]
            and failure.get("event") == expected_sequence[-1]
        )
    )
    numeric_pass = bool(
        np.all(np.isfinite(currents))
        and np.all(np.isfinite(actions))
        and _all_finite(trajectory)
        and _all_finite(trace)
        and _all_finite(failure)
    )
    execution_pass = bool(
        length_pass
        and numeric_pass
        and np.array_equal(actions, recorded)
        and not any(bool(row.get("abnormal")) for row in trajectory)
        and all(
            bool(row.get("computed_online")) and bool(row.get("solver_success"))
            for row in trace
        )
        and all(float(row.get("gotsc_subprocess_s", 0.0)) > 0.0 for row in trajectory[1:])
    )
    issue_pass = sum(prospective._issue_gate(row, ctx.cfg) for row in issues)
    cancel_pass = sum(prospective._cancel_gate(row, ctx.cfg) for row in cancels)
    forbidden = stage._forbidden_trace_count(trace)
    common_pass = bool(
        execution_pass
        and restart
        and phase["passed"]
        and calibration["passed"]
        and calibration_events == prospective._expected_calibration()
        and sequence_pass
        and len(issues) == 4
        and issue_pass == 4
        and len(cancels) == (4 if success else 3)
        and cancel_pass == len(cancels)
        and forbidden == 0
        and utilization
        <= float(ctx.cfg["schedule_contract"]["maximum_current_utilization"])
        + 1e-12
        and failure_not_applied
        and (success or structured)
    )
    attempted_cancel_values = [
        float(row["incremental_normalized_action_linf"]) for row in cancels
    ]
    if structured:
        attempted_cancel_values.append(
            float(failure["incremental_normalized_action_linf"])
        )
    return {
        "experiment_id": spec["experiment_id"],
        "pair_id": spec["pair_id"],
        "history_member": spec["history_member"],
        "sequence_index": int(spec["s24_sequence_index"]),
        "result_success": success,
        "structured_safe_stop": structured,
        "trajectory_count": len(trajectory),
        "trace_count": len(trace),
        "restart_visible_exact": visible,
        "restart_wire_exact": wire,
        "restart_exact": restart,
        "causality_pass": bool(phase["passed"]),
        "calibration_pass": bool(calibration["passed"]),
        "execution_prefix_pass": execution_pass,
        "failure_action_not_applied": failure_not_applied,
        "issue_event_count": len(issues),
        "issue_gate_pass_count": issue_pass,
        "successful_cancel_event_count": len(cancels),
        "successful_cancel_gate_pass_count": cancel_pass,
        "failed_cancel_attempt_count": int(structured),
        "failed_cancel_incremental_normalized_action_linf": (
            float(failure["incremental_normalized_action_linf"])
            if structured
            else None
        ),
        "failed_cancel_original_cap_pass": (
            bool(failure_criteria.get("incremental_action")) if structured else None
        ),
        "successful_cancel_maximum_incremental_normalized_action_linf": max(
            (
                float(row["incremental_normalized_action_linf"])
                for row in cancels
            ),
            default=0.0,
        ),
        "attempted_cancel_maximum_incremental_normalized_action_linf": max(
            attempted_cancel_values, default=0.0
        ),
        "maximum_current_utilization": utilization,
        "forbidden_trace_count": forbidden,
        "common_prefix_forensic_pass": common_pass,
    }


def _aggregate(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    failures = [row for row in rows if row.get("structured_safe_stop")]
    successful_cancel_count = sum(
        int(row["successful_cancel_event_count"]) for row in rows
    )
    return {
        "raw_count": len(rows),
        "full_horizon_success_count": sum(bool(row.get("result_success")) for row in rows),
        "structured_safe_stop_count": len(failures),
        "common_prefix_forensic_pass_count": sum(
            bool(row.get("common_prefix_forensic_pass")) for row in rows
        ),
        "restart_exact_count": sum(bool(row.get("restart_exact")) for row in rows),
        "causality_pass_count": sum(bool(row.get("causality_pass")) for row in rows),
        "calibration_pass_count": sum(bool(row.get("calibration_pass")) for row in rows),
        "issue_event_count": sum(int(row["issue_event_count"]) for row in rows),
        "issue_gate_pass_count": sum(int(row["issue_gate_pass_count"]) for row in rows),
        "successful_cancel_event_count": successful_cancel_count,
        "successful_cancel_gate_pass_count": sum(
            int(row["successful_cancel_gate_pass_count"]) for row in rows
        ),
        "failed_cancel_attempt_count": sum(
            int(row["failed_cancel_attempt_count"]) for row in rows
        ),
        "total_cancel_attempt_count": successful_cancel_count + len(failures),
        "cancel_margin_pass_count": successful_cancel_count,
        "cancel_margin_failure_count": len(failures),
        "original_cancel_cap_pass_count": successful_cancel_count
        + sum(bool(row.get("failed_cancel_original_cap_pass")) for row in failures),
        "original_cancel_cap_failure_count": sum(
            row.get("failed_cancel_original_cap_pass") is False for row in failures
        ),
        "maximum_successful_cancel_incremental_normalized_action_linf": max(
            (
                float(row["successful_cancel_maximum_incremental_normalized_action_linf"])
                for row in rows
            ),
            default=0.0,
        ),
        "maximum_attempted_cancel_incremental_normalized_action_linf": max(
            (
                float(row["attempted_cancel_maximum_incremental_normalized_action_linf"])
                for row in rows
            ),
            default=0.0,
        ),
        "maximum_current_utilization": max(
            (float(row["maximum_current_utilization"]) for row in rows), default=0.0
        ),
        "forbidden_trace_count": sum(int(row["forbidden_trace_count"]) for row in rows),
        "failure_pair_history_counts": [
            {"pair_id": key[0], "history_member": key[1], "count": value}
            for key, value in sorted(
                Counter(
                    (str(row["pair_id"]), str(row["history_member"]))
                    for row in failures
                ).items()
            )
        ],
        "failure_sequence_counts": [
            {"sequence_index": key, "count": value}
            for key, value in sorted(
                Counter(int(row["sequence_index"]) for row in failures).items()
            )
        ],
    }


def run_audit(ctx: stage.Context, complete_log: Path) -> dict[str, Any]:
    if ctx.paths.run_dir.name != EXPECTED_RUN_NAME:
        raise ValueError("retrospective D1R2 run identity mismatch")
    if stage.PACKAGE_REVISION != EXPECTED_PACKAGE_REVISION:
        raise ValueError("retrospective D1R2 execution package revision mismatch")
    prospective_path = ctx.paths.analysis / "independent_server_forensics.json"
    if stage._sha256(prospective_path) != EXPECTED_PROSPECTIVE_AUDIT_SHA256:
        raise ValueError("retrospective D1R2 prospective audit hash mismatch")
    complete_log = complete_log.expanduser().resolve()
    if stage._sha256(complete_log) != EXPECTED_COMPLETE_LOG_SHA256:
        raise ValueError("retrospective D1R2 complete log hash mismatch")
    prior = stage._read_json(prospective_path)
    if (
        prior["raw_inventory"]["count"] != 54
        or prior["raw_inventory"]["total_bytes"] != EXPECTED_RAW_TOTAL_BYTES
        or prior["raw_inventory"]["digest"] != EXPECTED_RAW_INVENTORY_DIGEST
        or prior["route"] != EXPECTED_ROUTE
    ):
        raise ValueError("retrospective D1R2 raw boundary mismatch")
    run_manifest = stage._read_json(ctx.paths.manifest)
    package_manifest = stage._read_json(stage._project_root() / "PACKAGE_MANIFEST.json")
    current_package = stage.s24.s21._package_fingerprint()
    package_pass = bool(
        package_manifest.get("package_revision") == EXPECTED_PACKAGE_REVISION
        and package_manifest.get("implementation_checkpoint")
        == EXPECTED_IMPLEMENTATION_CHECKPOINT
        and run_manifest.get("package_fingerprint", {}).get("digest")
        == current_package.get("digest")
    )
    specs = stage._saved_specs(ctx)
    state_map = stage.s24.s21.s13._source_state_map(
        ctx.base_s24_ctx.base_ctx.base_ctx.base_ctx
    )
    rows = [
        _audit_row(
            ctx,
            spec,
            stage._read_raw(ctx.paths.raw / f"{spec['experiment_id']}.json.gz"),
            state_map,
        )
        for spec in specs
    ]
    summary = _aggregate(rows)
    log_text = complete_log.read_text(encoding="utf-8", errors="replace")
    log_pass = bool(
        "pending=54 actors=54" in log_text
        and "54/54" in log_text
        and "Traceback" not in log_text
        and "GEOMETRY_RESTORED_SENTINEL_ACTION_MARGIN_FAIL_REDESIGN_REQUIRED"
        in log_text
    )
    expected_summary = bool(
        summary["raw_count"] == 54
        and summary["full_horizon_success_count"] == 45
        and summary["structured_safe_stop_count"] == 9
        and summary["common_prefix_forensic_pass_count"] == 54
        and summary["restart_exact_count"] == 54
        and summary["causality_pass_count"] == 54
        and summary["calibration_pass_count"] == 54
        and summary["issue_event_count"] == summary["issue_gate_pass_count"] == 216
        and summary["successful_cancel_event_count"]
        == summary["successful_cancel_gate_pass_count"]
        == summary["cancel_margin_pass_count"]
        == 207
        and summary["failed_cancel_attempt_count"]
        == summary["cancel_margin_failure_count"]
        == 9
        and summary["total_cancel_attempt_count"] == 216
        and summary["original_cancel_cap_pass_count"] == 211
        and summary["original_cancel_cap_failure_count"] == 5
        and summary["forbidden_trace_count"] == 0
    )
    forensic_pass = bool(package_pass and log_pass and expected_summary)
    return {
        "schema_version": 1,
        "stage": stage.STAGE,
        "classification": "retrospective_reporting_only_all_raw_prefix_forensics",
        "execution_package_revision": EXPECTED_PACKAGE_REVISION,
        "execution_implementation_checkpoint": EXPECTED_IMPLEMENTATION_CHECKPOINT,
        "execution_package_fingerprint_passed": package_pass,
        "prospective_audit_path": str(prospective_path),
        "prospective_audit_sha256": EXPECTED_PROSPECTIVE_AUDIT_SHA256,
        "complete_log_path": str(complete_log),
        "complete_log_sha256": EXPECTED_COMPLETE_LOG_SHA256,
        "raw_inventory_digest": EXPECTED_RAW_INVENTORY_DIGEST,
        **summary,
        "log_authentication_passed": log_pass,
        "prospective_aggregation_coverage_bug_found": True,
        "prospective_route_changed": False,
        "experiment_route": EXPECTED_ROUTE,
        "experiment_passed": False,
        "runtime_or_environment_error_found": False,
        "raw_snapshot_or_restart_corruption_found": False,
        "real_action_schedule_design_failure_found": True,
        "forensic_recomputation_passed": forensic_pass,
        "rows": rows,
    }


def main() -> None:
    args = prospective._parser().parse_args()
    ctx = stage.load_config(
        args.config,
        source_d1r1_output=args.source_d1r1_output,
        source_d1r1_log=args.source_d1r1_log,
        source_s21_run=args.source_s21_run,
        source_s23r1_output=args.source_s23r1_output,
        run_dir=args.run_dir,
        **stage._source_kwargs(args),
    )
    output = args.output.expanduser().resolve()
    if output.exists():
        raise ValueError("retrospective D1R2 output must be new")
    result = run_audit(ctx, args.complete_log)
    stage._write_json(output, result)
    print(json.dumps(result, sort_keys=True, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
