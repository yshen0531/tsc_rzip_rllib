#!/usr/bin/env python3
"""Reporting-only all-raw prefix forensics for the completed D1R4 sentinel.

The prospectively frozen D1R4 audits intentionally routed every structured
split-finish stop to the scientific-failure branch, but then aggregated only
full-success rows.  This audit preserves their route and raw boundary while
recomputing the executed 20-state/19-trace prefixes and the unapplied finish
attempts from all nine raw files.
"""

from __future__ import annotations

from collections import Counter
import copy
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r4_independent_forensics as prospective,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r2_real_tsc_safety_sentinel as d1r2,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r4_causal_split_return_safety_sentinel as stage,
)


EXPECTED_RUN_NAME = (
    "stage4_2r3c3t13s24d1r4_causal_split_return_safety_sentinel_"
    "20260803_1802_da3f4b4_v1h2"
)
EXPECTED_RAW_INVENTORY_DIGEST = (
    "9327a301498349eaebdb834d1c0f243bcc1939b5efb5d059ee6d6ec43b036190"
)
EXPECTED_RAW_TOTAL_BYTES = 363_807
EXPECTED_PROSPECTIVE_AUDIT_SHA256 = (
    "58dc2ac72e59e98a7fc4f496bdc6679b098b9f2a857db9028ce889a32a99688d"
)
EXPECTED_COMPLETE_LOG_SHA256 = (
    "ca86693375685e4c6d1d21b37b39c405b79ff3f391a1c888bcca00592d00536d"
)
EXPECTED_STAGE_MANIFEST_SHA256 = (
    "d008d8f94bf6f5bfebb9ad827d1a801e6e0ffd80a34b6eab03b180225270e6a3"
)
EXPECTED_PACKAGE_REVISION = (
    "r42r3c3t13s24d1r4_causal_split_return_safety_sentinel_v1h2"
)
EXPECTED_PACKAGE_FINGERPRINT = {
    "config_sha256": (
        "8b402a48f15b6f5c783719bd7216cda8ae8eea459e5e797c2769e38cd88da683"
    ),
    "file_count": 432,
    "implementation_sha256": (
        "7e1b29aa3e37d2751946a5c8f04e7f59d19d033b1018ade7bde4dc7719394694"
    ),
    "package_manifest_sha256": (
        "93bde8503a85e6de5138cd60eb92a6a8c2638794350753a2b068a39583064abe"
    ),
    "package_revision": EXPECTED_PACKAGE_REVISION,
    "passed": True,
    "sha256sums_sha256": (
        "a5eb857eb3eba1e921dec5d6cb2da1026af2dc95c4abb07b8945c18a9edc7be0"
    ),
}
EXPECTED_ROUTE = "CAUSAL_SPLIT_RETURN_SENTINEL_FAIL_REDESIGN_REQUIRED"
EXPECTED_FALSE_FINISH_CRITERIA = {
    "actuator_gate",
    "finish_increment",
    "original_increment",
}


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
        [generated["R"], generated["Z"], generated["Ip"], *generated["coil_currents_a"]],
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


def _projection(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: copy.deepcopy(value)
        for key, value in row.items()
        if not key.startswith("r3c3t13s24d1r4_")
    }


def _structured_finish_failure(result: Mapping[str, Any]) -> bool:
    event = result.get("action_failure_event") or {}
    criteria = event.get("criteria") or {}
    false_criteria = {key for key, value in criteria.items() if not bool(value)}
    return bool(
        not result.get("success")
        and result.get("completed")
        and result.get("failure_class") == "structured_action_schedule_gate"
        and event.get("event") == "sequential_cancel_split_finish"
        and int(event.get("task_step", -1)) == 19
        and int(event.get("split_start_task_step", -1)) == 18
        and int(event.get("slot", -1)) == 3
        and not bool(event.get("passed"))
        and false_criteria == EXPECTED_FALSE_FINISH_CRITERIA
        and float(event.get("incremental_normalized_action_linf", math.inf)) > 0.25
    )


def _audit_row(
    ctx: stage.Context,
    spec: Mapping[str, Any],
    result: Mapping[str, Any],
    state_map: Mapping[str, Mapping[str, Any]],
    source_raw_dir: Path,
    d1r3_starts: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    trajectory = list(result.get("trajectory") or [])
    trace = list(result.get("controller_trace") or [])
    currents = np.asarray([row["currents_a_tsc"] for row in trajectory], dtype=float)
    actions = np.asarray([row["action_norm_tsc"] for row in trace], dtype=float)
    recorded = np.asarray(
        [row["action_norm_tsc"] for row in trajectory[1:]], dtype=float
    )
    event = result.get("action_failure_event") or {}
    structured = _structured_finish_failure(result)
    identity = bool(
        result.get("stage") == stage.STAGE
        and result.get("campaign_identity") == stage.CAMPAIGN_IDENTITY
        and result.get("controller_revision") == stage.CONTROLLER_REVISION
        and result.get("probe_primitive_revision") == stage.CONTROLLER_REVISION
        and result.get("experiment_id") == spec["experiment_id"]
        and result.get("spec") == dict(spec)
    )
    payload = stage._payload(ctx, spec)
    minimum, maximum = d1r2.s24.s21.s13._current_limits_tsc(payload)
    center, half = 0.5 * (minimum + maximum), 0.5 * (maximum - minimum)
    utilization = float(np.max(np.abs((currents - center) / half)))
    visible, wire, restart = _initial_restart_exact(result, state_map)
    phase = d1r2.s24.s21.s16.s9.t11.t1.r3c1._phase_trace_valid(result)
    calibration = d1r2.s24.s21._dynamic_calibration_trace_audit(
        result, ctx.base_d1r2_ctx.base_s24_ctx.base_ctx.cfg
    )
    calibration_events = [
        row.get("r3c3t13s16_lattice_event")
        for row in trace
        if row.get("r3c3t13s16_lattice_event") != "none"
    ]
    expected_calibration = [
        "calibration_issue",
        "calibration_cancel",
        "calibration_issue",
        "calibration_cancel",
        "calibration_issue",
        "calibration_cancel",
        "calibration_issue",
        "calibration_cancel",
    ]
    details = [
        row["r3c3t13s24d1r4_event_detail"]
        for row in trace
        if row.get("r3c3t13s24d1r4_event") != "none"
    ]
    events = [str(row.get("event")) for row in details]
    expected_events = [
        "sequential_issue",
        "sequential_cancel",
        "sequential_issue",
        "sequential_cancel",
        "sequential_issue",
        "sequential_cancel",
        "sequential_issue",
        "sequential_cancel_split_start",
    ]
    issues = [row for row in details if row.get("event") == "sequential_issue"]
    direct = [row for row in details if row.get("event") == "sequential_cancel"]
    starts = [
        row
        for row in details
        if row.get("event") == "sequential_cancel_split_start"
    ]
    source_id = str(spec["d1r4_source_d1r2_experiment_id"])
    source = stage._read_raw(source_raw_dir / f"{source_id}.json.gz")
    source_trace = list(source.get("controller_trace") or [])
    prefix_action = bool(
        len(source_trace) == 18
        and np.array_equal(
            np.asarray([row["action_norm_tsc"] for row in trace[:18]]),
            np.asarray([row["action_norm_tsc"] for row in source_trace]),
        )
    )
    prefix_trace = bool(
        len(source_trace) == 18
        and all(
            _projection(current) == prior
            for current, prior in zip(trace[:18], source_trace)
        )
    )
    start = starts[0] if len(starts) == 1 else {}
    start_ref = d1r3_starts[source_id]
    start_exact = bool(
        len(starts) == 1
        and np.array_equal(
            np.asarray(start.get("split_start_action_norm_tsc")),
            np.asarray(start_ref["split_start_action_norm_tsc"]),
        )
        and start.get("intermediate_card15_fields")
        == start_ref["intermediate_card15_fields"]
        and math.isclose(float(start.get("alpha", math.inf)), float(start_ref["alpha"]), abs_tol=1e-12, rel_tol=0.0)
        and float(start.get("split_start_incremental_normalized_action_linf", math.inf))
        == 0.175
        and bool(start.get("passed"))
        and all(bool(value) for value in (start.get("criteria") or {}).values())
    )
    failure_not_applied = bool(
        structured
        and len(trajectory) == 20
        and len(trace) == 19
        and int(trace[-1]["task_step"]) == 18
        and int(trajectory[-1]["step_index"]) == 19
        and np.array_equal(actions, recorded)
    )
    numeric = bool(
        currents.shape == (20, 14)
        and actions.shape == recorded.shape == (19, 14)
        and np.all(np.isfinite(currents))
        and np.all(np.isfinite(actions))
        and _all_finite(trajectory)
        and _all_finite(trace)
        and _all_finite(event)
    )
    execution = bool(
        numeric
        and not any(bool(row.get("abnormal")) for row in trajectory)
        and all(
            bool(row.get("computed_online")) and bool(row.get("solver_success"))
            for row in trace
        )
        and all(float(row.get("gotsc_subprocess_s", 0.0)) > 0.0 for row in trajectory[1:])
        and failure_not_applied
    )
    finish_increment = float(event["incremental_normalized_action_linf"])
    predicted_utilization = float(event["predicted_current_utilization"])
    finish_action = np.asarray(event["finish_action_norm_tsc"], dtype=float)
    previous_action = np.asarray(trace[-1]["action_norm_tsc"], dtype=float)
    physical_command_delta = float(np.max(np.abs(finish_action - previous_action)))
    forbidden = prospective._forbidden(trace)
    common = bool(
        identity
        and structured
        and execution
        and restart
        and phase["passed"]
        and calibration["passed"]
        and calibration_events == expected_calibration
        and events == expected_events
        and len(issues) == 4
        and len(direct) == 3
        and all(bool(row.get("passed")) for row in details)
        and prefix_action
        and prefix_trace
        and start_exact
        and forbidden == 0
        and utilization <= 0.55 + 1e-12
        and predicted_utilization <= 0.55 + 1e-12
        and float(np.max(np.abs(actions))) <= 1.0 + 1e-12
    )
    return {
        "experiment_id": spec["experiment_id"],
        "source_experiment_id": source_id,
        "pair_id": spec["pair_id"],
        "history_member": spec["history_member"],
        "sequence_index": int(spec["s24_sequence_index"]),
        "identity_pass": identity,
        "structured_split_finish_safe_stop": structured,
        "trajectory_count": len(trajectory),
        "trace_count": len(trace),
        "execution_prefix_pass": execution,
        "failure_action_not_applied": failure_not_applied,
        "restart_visible_exact": visible,
        "restart_wire_exact": wire,
        "restart_exact": restart,
        "causality_pass": bool(phase["passed"]),
        "calibration_pass": bool(calibration["passed"]),
        "source_prefix_action_exact": prefix_action,
        "source_prefix_trace_exact": prefix_trace,
        "d1r3_split_start_exact": start_exact,
        "issue_event_count": len(issues),
        "direct_cancel_event_count": len(direct),
        "split_start_event_count": len(starts),
        "failed_split_finish_attempt_count": int(structured),
        "split_start_incremental_normalized_action_linf": float(
            start.get("split_start_incremental_normalized_action_linf", math.inf)
        ),
        "failed_finish_incremental_normalized_action_linf": finish_increment,
        "failed_finish_original_cap_pass": finish_increment <= 0.25 + 1e-12,
        "failed_finish_margin_pass": finish_increment <= 0.24 + 1e-12,
        "unapplied_finish_from_previous_command_linf_diagnostic": physical_command_delta,
        "maximum_executed_current_utilization": utilization,
        "failed_finish_predicted_current_utilization": predicted_utilization,
        "forbidden_trace_count": forbidden,
        "formal_tracking_evaluable": False,
        "common_prefix_forensic_pass": common,
    }


def _aggregate(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    failures = [row for row in rows if row.get("structured_split_finish_safe_stop")]
    return {
        "raw_count": len(rows),
        "full_horizon_success_count": 0,
        "structured_split_finish_safe_stop_count": len(failures),
        "common_prefix_forensic_pass_count": sum(
            bool(row.get("common_prefix_forensic_pass")) for row in rows
        ),
        "identity_pass_count": sum(bool(row.get("identity_pass")) for row in rows),
        "restart_exact_count": sum(bool(row.get("restart_exact")) for row in rows),
        "causality_pass_count": sum(bool(row.get("causality_pass")) for row in rows),
        "calibration_pass_count": sum(bool(row.get("calibration_pass")) for row in rows),
        "source_prefix_action_exact_count": sum(
            bool(row.get("source_prefix_action_exact")) for row in rows
        ),
        "source_prefix_trace_exact_count": sum(
            bool(row.get("source_prefix_trace_exact")) for row in rows
        ),
        "d1r3_split_start_exact_count": sum(
            bool(row.get("d1r3_split_start_exact")) for row in rows
        ),
        "issue_event_count": sum(int(row["issue_event_count"]) for row in rows),
        "direct_cancel_event_count": sum(
            int(row["direct_cancel_event_count"]) for row in rows
        ),
        "split_start_event_count": sum(int(row["split_start_event_count"]) for row in rows),
        "failed_split_finish_attempt_count": sum(
            int(row["failed_split_finish_attempt_count"]) for row in rows
        ),
        "failure_action_not_applied_count": sum(
            bool(row.get("failure_action_not_applied")) for row in rows
        ),
        "finish_margin_pass_count": sum(
            bool(row.get("failed_finish_margin_pass")) for row in failures
        ),
        "finish_margin_failure_count": sum(
            row.get("failed_finish_margin_pass") is False for row in failures
        ),
        "original_finish_cap_pass_count": sum(
            bool(row.get("failed_finish_original_cap_pass")) for row in failures
        ),
        "original_finish_cap_failure_count": sum(
            row.get("failed_finish_original_cap_pass") is False for row in failures
        ),
        "minimum_failed_finish_incremental_normalized_action_linf": min(
            (float(row["failed_finish_incremental_normalized_action_linf"]) for row in failures),
            default=0.0,
        ),
        "maximum_failed_finish_incremental_normalized_action_linf": max(
            (float(row["failed_finish_incremental_normalized_action_linf"]) for row in failures),
            default=0.0,
        ),
        "maximum_unapplied_finish_from_previous_command_linf_diagnostic": max(
            (
                float(row["unapplied_finish_from_previous_command_linf_diagnostic"])
                for row in failures
            ),
            default=0.0,
        ),
        "maximum_executed_current_utilization": max(
            (float(row["maximum_executed_current_utilization"]) for row in rows),
            default=0.0,
        ),
        "maximum_failed_finish_predicted_current_utilization": max(
            (float(row["failed_finish_predicted_current_utilization"]) for row in failures),
            default=0.0,
        ),
        "forbidden_trace_count": sum(int(row["forbidden_trace_count"]) for row in rows),
        "formal_tracking_evaluable_count": sum(
            bool(row.get("formal_tracking_evaluable")) for row in rows
        ),
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
        raise ValueError("retrospective D1R4 run identity mismatch")
    if stage.PACKAGE_REVISION != EXPECTED_PACKAGE_REVISION:
        raise ValueError("retrospective D1R4 execution revision mismatch")
    prospective_path = ctx.paths.analysis / "independent_server_forensics.json"
    if stage._sha256(prospective_path) != EXPECTED_PROSPECTIVE_AUDIT_SHA256:
        raise ValueError("retrospective D1R4 prospective audit hash mismatch")
    complete_log = complete_log.expanduser().resolve()
    if stage._sha256(complete_log) != EXPECTED_COMPLETE_LOG_SHA256:
        raise ValueError("retrospective D1R4 complete log hash mismatch")
    if stage._sha256(ctx.paths.manifest) != EXPECTED_STAGE_MANIFEST_SHA256:
        raise ValueError("retrospective D1R4 stage manifest hash mismatch")
    prior = stage._read_json(prospective_path)
    if (
        prior["raw_inventory"]["count"] != 9
        or prior["raw_inventory"]["total_bytes"] != EXPECTED_RAW_TOTAL_BYTES
        or prior["raw_inventory"]["digest"] != EXPECTED_RAW_INVENTORY_DIGEST
        or prior["route"] != EXPECTED_ROUTE
    ):
        raise ValueError("retrospective D1R4 raw boundary mismatch")
    manifest = stage._read_json(ctx.paths.manifest)
    package_pass = manifest.get("package_fingerprint") == EXPECTED_PACKAGE_FINGERPRINT
    specs = stage._saved_specs(ctx)
    state_map = d1r2.s24.s21.s13._source_state_map(
        ctx.base_d1r2_ctx.base_s24_ctx.base_ctx.base_ctx.base_ctx
    )
    source_raw_dir = ctx.source_d1r2_run / d1r2.RUN_NAME / "raw"
    d1r3_detail = stage._read_json(
        ctx.source_d1r3_output / "stage4_2r3c3t13s24d1r3_detailed_v1.json"
    )
    d1r3_starts = {
        str(row["source_experiment_id"]): row["split_start_event"]
        for row in d1r3_detail["rows"]
        if row.get("split_branch_selected")
    }
    rows = [
        _audit_row(
            ctx,
            spec,
            stage._read_raw(ctx.paths.raw / f"{spec['experiment_id']}.json.gz"),
            state_map,
            source_raw_dir,
            d1r3_starts,
        )
        for spec in specs
    ]
    summary = _aggregate(rows)
    log_text = complete_log.read_text(encoding="utf-8", errors="strict")
    log_pass = bool(
        "pending=9 actors=9" in log_text
        and "[T13S24D1R4] 9/9" in log_text
        and EXPECTED_ROUTE in log_text
        and "Traceback (most recent call last)" not in log_text
    )
    expected_summary = bool(
        summary["raw_count"] == 9
        and summary["full_horizon_success_count"] == 0
        and summary["structured_split_finish_safe_stop_count"] == 9
        and summary["common_prefix_forensic_pass_count"] == 9
        and summary["identity_pass_count"] == 9
        and summary["restart_exact_count"] == 9
        and summary["causality_pass_count"] == 9
        and summary["calibration_pass_count"] == 9
        and summary["source_prefix_action_exact_count"] == 9
        and summary["source_prefix_trace_exact_count"] == 9
        and summary["d1r3_split_start_exact_count"] == 9
        and summary["issue_event_count"] == 36
        and summary["direct_cancel_event_count"] == 27
        and summary["split_start_event_count"] == 9
        and summary["failed_split_finish_attempt_count"] == 9
        and summary["failure_action_not_applied_count"] == 9
        and summary["finish_margin_pass_count"] == 0
        and summary["finish_margin_failure_count"] == 9
        and summary["original_finish_cap_pass_count"] == 0
        and summary["original_finish_cap_failure_count"] == 9
        and summary["forbidden_trace_count"] == 0
        and summary["formal_tracking_evaluable_count"] == 0
    )
    forensic_pass = bool(package_pass and log_pass and expected_summary)
    return {
        "schema_version": 1,
        "stage": stage.STAGE,
        "classification": "retrospective_reporting_only_all_raw_prefix_forensics",
        "execution_package_revision": EXPECTED_PACKAGE_REVISION,
        "execution_package_fingerprint": copy.deepcopy(EXPECTED_PACKAGE_FINGERPRINT),
        "execution_package_fingerprint_passed": package_pass,
        "prospective_audit_path": str(prospective_path),
        "prospective_audit_sha256": EXPECTED_PROSPECTIVE_AUDIT_SHA256,
        "complete_log_path": str(complete_log),
        "complete_log_sha256": EXPECTED_COMPLETE_LOG_SHA256,
        "stage_manifest_sha256": EXPECTED_STAGE_MANIFEST_SHA256,
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
        "formal_tracking_test_not_run_to_endpoint": True,
        "forensic_recomputation_passed": forensic_pass,
        "rows": rows,
    }


def run(args: Any) -> dict[str, Any]:
    ctx = stage.load_config(
        args.config,
        source_d1r2_run=args.source_d1r2_run,
        source_d1r3_output=args.source_d1r3_output,
        source_d1r3_primary_log=args.source_d1r3_primary_log,
        source_d1r3_repeat_log=args.source_d1r3_repeat_log,
        source_d1r1_output=args.source_d1r1_output,
        source_d1r1_log=args.source_d1r1_log,
        source_s21_run=args.source_s21_run,
        source_s23r1_output=args.source_s23r1_output,
        run_dir=args.run_dir,
        **stage._source_kwargs(args),
    )
    output = args.output.expanduser().resolve()
    if output.exists():
        raise ValueError("retrospective D1R4 output must be new")
    result = run_audit(ctx, args.complete_log)
    prospective._write(output, result)
    return result


def main() -> None:
    result = run(prospective._parser().parse_args())
    print(
        json.dumps(
            {key: value for key, value in result.items() if key != "rows"},
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
    )


if __name__ == "__main__":
    main()
