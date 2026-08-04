#!/usr/bin/env python3
"""Independent server-side raw forensics for the D1R10 safety sentinel."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r10_exact_row_completion_safety_sentinel as stage,
)


def _inventory(raw_dir: Path) -> dict[str, Any]:
    files = []
    digest = hashlib.sha256()
    for path in sorted(raw_dir.glob("*.json.gz")):
        sha = stage._sha256(path)
        size = path.stat().st_size
        digest.update(f"{path.name}\0{size}\0{sha}\n".encode())
        files.append({"path": path.name, "bytes": size, "sha256": sha})
    return {
        "count": len(files),
        "total_bytes": sum(int(row["bytes"]) for row in files),
        "digest": digest.hexdigest(),
        "files": files,
    }


def _decimal_exact_zero(cancel: Mapping[str, Any]) -> bool:
    centers = cancel.get("stored_center_card15_fields") or []
    targets = cancel.get("issue_target_card15_fields") or []
    return bool(
        len(centers) == len(targets) == 14
        and all(len(str(value)) == 10 for value in [*centers, *targets])
        and all(
            (Decimal(str(target)) - Decimal(str(center)))
            + (Decimal(str(center)) - Decimal(str(target)))
            == 0
            for center, target in zip(centers, targets)
        )
    )


def _issue_gate(event: Mapping[str, Any], cfg: Mapping[str, Any]) -> bool:
    schedule = cfg["schedule_contract"]
    criteria = event.get("criteria") or {}
    values = [
        *(event.get("actual_coordinate") or []),
        float(event.get("maximum_absolute_coordinate_error", math.inf)),
        float(event.get("minimum_active_absolute_coordinate", -math.inf)),
        float(event.get("desired_applied_current_cosine", -math.inf)),
        float(event.get("relative_off_basis_residual", math.inf)),
        float(event.get("incremental_normalized_action_linf", math.inf)),
        float(event.get("total_normalized_action_abs", math.inf)),
        float(event.get("predicted_current_utilization", math.inf)),
    ]
    return bool(
        event.get("event") == "sequential_issue"
        and all(math.isfinite(float(value)) for value in values)
        and len(event.get("center_card15_fields") or []) == 14
        and len(event.get("target_card15_fields") or []) == 14
        and all(len(str(value)) == 10 for value in event["center_card15_fields"])
        and all(len(str(value)) == 10 for value in event["target_card15_fields"])
        and float(event["maximum_absolute_coordinate_error"])
        <= float(schedule["maximum_absolute_coordinate_error"]) + 1e-12
        and float(event["minimum_active_absolute_coordinate"])
        >= float(schedule["minimum_active_absolute_coordinate"]) - 1e-12
        and float(event["desired_applied_current_cosine"])
        >= float(schedule["minimum_desired_applied_current_cosine"]) - 1e-12
        and float(event["relative_off_basis_residual"])
        <= float(schedule["maximum_relative_off_basis_residual"]) + 1e-12
        and float(event["incremental_normalized_action_linf"])
        <= float(schedule["maximum_incremental_normalized_action_linf"]) + 1e-12
        and float(event["total_normalized_action_abs"])
        <= float(schedule["maximum_total_normalized_action_abs"]) + 1e-12
        and float(event["predicted_current_utilization"])
        <= float(schedule["maximum_current_utilization"]) + 1e-12
        and all(bool(value) for value in criteria.values())
        and bool(event.get("passed"))
    )


def _cancel_gate(event: Mapping[str, Any], cfg: Mapping[str, Any]) -> bool:
    schedule = cfg["schedule_contract"]
    criteria = event.get("criteria") or {}
    return bool(
        event.get("event") == "sequential_cancel"
        and _decimal_exact_zero(event)
        and math.isfinite(float(event.get("incremental_normalized_action_linf", math.inf)))
        and float(event["incremental_normalized_action_linf"])
        <= float(schedule["maximum_incremental_normalized_action_linf"]) + 1e-12
        and float(event["incremental_normalized_action_linf"])
        <= float(schedule["maximum_online_cancel_incremental_normalized_action_linf"])
        + 1e-12
        and float(event["total_normalized_action_abs"])
        <= float(schedule["maximum_total_normalized_action_abs"]) + 1e-12
        and float(event["predicted_current_utilization"])
        <= float(schedule["maximum_current_utilization"]) + 1e-12
        and criteria.get("target_exact") is True
        and criteria.get("exact_fields") is True
        and criteria.get("exact_zero_target_jump_net") is True
        and criteria.get("incremental_action") is True
        and criteria.get("online_cancel_margin") is True
        and criteria.get("total_action") is True
        and criteria.get("current_utilization") is True
        and criteria.get("actuator_gate") is True
        and criteria.get("no_saturation") is True
        and criteria.get("no_current_clip") is True
        and bool(event.get("passed"))
    )


def _expected_sequence() -> list[str]:
    return [
        "sequential_issue",
        "sequential_cancel",
        "sequential_issue",
        "sequential_cancel",
        "sequential_issue",
        "sequential_cancel",
        "sequential_issue",
        "sequential_cancel",
    ]


def _expected_calibration() -> list[str]:
    return [
        "calibration_issue",
        "calibration_cancel",
        "calibration_issue",
        "calibration_cancel",
        "calibration_issue",
        "calibration_cancel",
        "calibration_issue",
        "calibration_cancel",
    ]


def _restart_and_causal_prefix_audit(
    result: Mapping[str, Any],
    spec: Mapping[str, Any],
    generated_state: Mapping[str, Any],
) -> dict[str, Any]:
    """Audit evidence that remains meaningful after a structured safe stop.

    The inherited R3b ``_control_row`` deliberately returns before inspecting
    any trajectory when ``success`` is false.  A D1R10 action-gate stop is a
    completed, partial trajectory, so treating those unevaluated fields as
    restart or causality failures is a reporting error.  This helper directly
    audits the immutable initial state and every action that actually advanced
    the plant; it does not infer a full-horizon result.
    """

    r3b = stage.s24.s21.s16.s9.t11.t1.r3b
    trajectory = list(result.get("trajectory") or [])
    trace = list(result.get("controller_trace") or [])
    initial = trajectory[0] if trajectory else {}
    try:
        generated_visible = np.asarray(
            [
                generated_state["R"],
                generated_state["Z"],
                generated_state["Ip"],
                *generated_state["coil_currents_a"],
            ],
            dtype=float,
        )
        restart_visible = np.asarray(
            [
                initial["R"],
                initial["Z"],
                initial["Ip"],
                *initial["currents_a_tsc"],
            ],
            dtype=float,
        )
        generated_wire = np.asarray(
            generated_state["wire_currents_a"], dtype=float
        ).reshape(-1)
        restart_wire = np.asarray(
            initial.get("wire_currents_a"), dtype=float
        ).reshape(-1)
        visible_exact = bool(
            generated_visible.shape == restart_visible.shape == (17,)
            and np.array_equal(generated_visible, restart_visible)
        )
        wire_exact = bool(
            generated_wire.shape == restart_wire.shape == (r3b.N_WIRES,)
            and np.array_equal(generated_wire, restart_wire)
        )
    except (KeyError, TypeError, ValueError):
        visible_exact = False
        wire_exact = False

    causal, causal_trace_count = r3b._trace_is_causal(result)
    forbidden_spec_paths = r3b._forbidden_future_paths(spec)
    forbidden_trace_count = stage._forbidden_trace_count(trace)
    try:
        actions = np.asarray(
            [value["action_norm_tsc"] for value in trace], dtype=float
        )
        recorded = np.asarray(
            [value["action_norm_tsc"] for value in trajectory[1:]], dtype=float
        )
        action_prefix_exact = bool(
            len(trajectory) == len(trace) + 1
            and actions.shape == recorded.shape == (len(trace), stage.N_COILS)
            and np.all(np.isfinite(actions))
            and np.array_equal(actions, recorded)
        )
    except (KeyError, TypeError, ValueError):
        action_prefix_exact = False

    authentic_tsc_rows = 0
    for value in trajectory:
        try:
            wire = np.asarray(value["wire_currents_a"], dtype=float).reshape(-1)
            gotsc_seconds = float(value["gotsc_subprocess_s"])
            if (
                wire.shape == (r3b.N_WIRES,)
                and np.all(np.isfinite(wire))
                and math.isfinite(gotsc_seconds)
                and gotsc_seconds >= 0.0
            ):
                authentic_tsc_rows += 1
        except (KeyError, TypeError, ValueError):
            pass
    computed_prefix = bool(
        trace
        and all(
            bool(value.get("computed_online"))
            and bool(value.get("solver_success"))
            for value in trace
        )
    )
    no_abnormal_prefix = bool(
        trajectory and not any(bool(value.get("abnormal")) for value in trajectory)
    )
    causal_prefix = bool(
        causal
        and causal_trace_count == len(trace)
        and not forbidden_spec_paths
        and forbidden_trace_count == 0
    )
    return {
        "initial_restart_visible_exact": visible_exact,
        "initial_restart_wire_exact": wire_exact,
        "initial_restart_exact": bool(visible_exact and wire_exact),
        "causal_trace_prefix_pass": causal_prefix,
        "causal_trace_prefix_count": causal_trace_count,
        "forbidden_spec_paths": forbidden_spec_paths,
        "forbidden_trace_count": forbidden_trace_count,
        "applied_action_prefix_exact": action_prefix_exact,
        "computed_online_prefix_pass": computed_prefix,
        "no_abnormal_plant_prefix": no_abnormal_prefix,
        "authentic_tsc_state_row_count": authentic_tsc_rows,
        "authentic_tsc_prefix_evidence_pass": bool(
            trajectory and authentic_tsc_rows == len(trajectory)
        ),
        "physical_prefix_integrity_pass": bool(
            visible_exact
            and wire_exact
            and causal_prefix
            and action_prefix_exact
            and computed_prefix
            and no_abnormal_prefix
            and authentic_tsc_rows == len(trajectory)
        ),
    }


def run_forensics(ctx: stage.Context, complete_log: Path) -> dict[str, Any]:
    specs = stage._saved_specs(ctx)
    inventory = _inventory(ctx.paths.raw)
    state = stage._read_json(ctx.paths.state)
    manifest = stage._read_json(ctx.paths.manifest)
    final = stage._read_json(ctx.paths.final)
    context_rows = stage._selected_context_table(specs)
    snapshots = stage._selected_snapshot_audit(context_rows)
    state_map = stage.s24.s21.s13._source_state_map(
        ctx.base_s24_ctx.base_ctx.base_ctx.base_ctx
    )
    base_source_ctx = (
        ctx.base_s24_ctx.base_ctx.base_ctx.base_ctx.base_ctx.base_ctx.base_ctx
        .source_ctx.source_ctx
    )
    rows = []
    for spec in specs:
        path = ctx.paths.raw / f"{spec['experiment_id']}.json.gz"
        row: dict[str, Any] = {
            "experiment_id": spec["experiment_id"],
            "pair_id": spec["pair_id"],
            "history_member": spec["history_member"],
            "sequence_index": int(spec["s24_sequence_index"]),
        }
        if not path.is_file():
            rows.append({**row, "classification": "runtime_or_raw_error", "passed": False})
            continue
        try:
            result = stage._read_raw(path)
        except Exception as exc:
            rows.append(
                {
                    **row,
                    "classification": "runtime_or_raw_error",
                    "failure_reason": repr(exc),
                    "passed": False,
                }
            )
            continue
        identity = bool(
            result.get("completed")
            and result.get("stage") == stage.STAGE
            and result.get("campaign_identity") == stage.CAMPAIGN_IDENTITY
            and result.get("controller_revision") == stage.CONTROLLER_REVISION
            and result.get("probe_primitive_revision") == stage.CONTROLLER_REVISION
            and result.get("experiment_id") == spec["experiment_id"]
            and result.get("spec") == dict(spec)
        )
        trajectory = result.get("trajectory") or []
        trace = result.get("controller_trace") or []
        if not identity:
            rows.append(
                {
                    **row,
                    "strict_parse_pass": True,
                    "identity_pass": False,
                    "classification": "runtime_or_raw_error",
                    "passed": False,
                }
            )
            continue
        generated_state = state_map[str(spec["state_generation_experiment_id"])]
        prefix = _restart_and_causal_prefix_audit(result, spec, generated_state)
        phase = stage.s24.s21.s16.s9.t11.t1.r3c1._phase_trace_valid(result)
        calibration = stage.s24.s21._dynamic_calibration_trace_audit(
            result, ctx.base_s24_ctx.base_ctx.cfg
        )
        calibration_events = [
            value.get("r3c3t13s16_lattice_event")
            for value in trace
            if value.get("r3c3t13s16_lattice_event") != "none"
        ]
        fresh_summary = result.get("hidden_history_control_summary") or {}
        if not result.get("success"):
            event = result.get("action_failure_event") or {}
            criteria = event.get("criteria") or {}
            applied_events = [
                value.get("r3c3t13s24d1r10_event_detail") or {}
                for value in trace
                if value.get("r3c3t13s24d1r10_event") != "none"
            ]
            attempted_events = [*applied_events, event]
            attempted_issues = [
                value
                for value in attempted_events
                if value.get("event") == "sequential_issue"
            ]
            attempted_cancels = [
                value
                for value in attempted_events
                if value.get("event") == "sequential_cancel"
            ]
            applied_issues = [
                value
                for value in applied_events
                if value.get("event") == "sequential_issue"
            ]
            applied_cancels = [
                value
                for value in applied_events
                if value.get("event") == "sequential_cancel"
            ]
            structured = bool(
                result.get("failure_class") == "structured_action_schedule_gate"
                and event.get("event") in {"sequential_issue", "sequential_cancel"}
                and not bool(event.get("passed"))
                and len(trajectory) == len(trace) + 1
                and [value.get("event") for value in attempted_events]
                == _expected_sequence()[: len(attempted_events)]
                and all(bool(value.get("passed")) for value in applied_events)
            )
            rows.append(
                {
                    **row,
                    "strict_parse_pass": True,
                    "identity_pass": True,
                    "result_success": False,
                    **prefix,
                    "causality_pass": bool(prefix["causal_trace_prefix_pass"]),
                    "phase_prefix_pass": bool(phase["passed"]),
                    "calibration_pass": bool(
                        calibration["passed"]
                        and calibration_events == _expected_calibration()
                    ),
                    "fresh_actor_process_summary_emitted": bool(fresh_summary),
                    "fresh_actor_process_summary_status": (
                        "reported"
                        if fresh_summary
                        else "not_emitted_by_structured_exception_handler"
                    ),
                    "structured_action_failure": structured,
                    "online_margin_failure": bool(
                        event.get("event") == "sequential_cancel"
                        and criteria.get("online_cancel_margin") is False
                    ),
                    "original_action_gate_failure": bool(
                        structured
                        and any(
                            value is False
                            for key, value in criteria.items()
                            if key != "online_cancel_margin"
                        )
                    ),
                    "failure_event": event,
                    "issue_event_count": len(attempted_issues),
                    "cancel_event_count": len(attempted_cancels),
                    "applied_issue_event_count": len(applied_issues),
                    "applied_cancel_event_count": len(applied_cancels),
                    "issue_gate_pass_count": sum(
                        _issue_gate(value, ctx.cfg) for value in attempted_issues
                    ),
                    "cancel_gate_pass_count": sum(
                        _cancel_gate(value, ctx.cfg) for value in attempted_cancels
                    ),
                    "cancel_margin_pass_count": sum(
                        bool(value.get("criteria", {}).get("online_cancel_margin"))
                        for value in attempted_cancels
                    ),
                    "maximum_cancel_incremental_normalized_action_linf": max(
                        (
                            float(value.get("incremental_normalized_action_linf", 0.0))
                            for value in attempted_cancels
                        ),
                        default=0.0,
                    ),
                    "failed_action_applied": False if structured else None,
                    "plant_advance_after_failed_action": False if structured else None,
                    "attempted_event_prefix_order_pass": bool(
                        [value.get("event") for value in attempted_events]
                        == _expected_sequence()[: len(attempted_events)]
                    ),
                    "classification": (
                        "action_schedule_design_failure"
                        if structured
                        else "runtime_or_environment_error"
                    ),
                    "passed": False,
                }
            )
            continue
        try:
            horizon = int(spec["horizon_steps"])
            currents = np.asarray(
                [value["currents_a_tsc"] for value in trajectory], dtype=float
            )
            actions = np.asarray(
                [value["action_norm_tsc"] for value in trace], dtype=float
            )
            recorded = np.asarray(
                [value["action_norm_tsc"] for value in trajectory[1:]], dtype=float
            )
            payload = stage._payload(ctx, spec)
            minimum, maximum = stage.s24.s21.s13._current_limits_tsc(payload)
            center, half = 0.5 * (minimum + maximum), 0.5 * (maximum - minimum)
            utilization = float(np.max(np.abs((currents - center) / half)))
            restart = stage.s24.s21.s16.s9.t11.t1.r3b._control_row(
                base_source_ctx,
                result,
                state_map[str(spec["state_generation_experiment_id"])],
            )
            sequence_events = [
                value.get("r3c3t13s24d1r10_event")
                for value in trace
                if value.get("r3c3t13s24d1r10_event") != "none"
            ]
            events = [
                value["r3c3t13s24d1r10_event_detail"]
                for value in trace
                if value.get("r3c3t13s24d1r10_event") != "none"
            ]
            issues = [value for value in events if value.get("event") == "sequential_issue"]
            cancels = [value for value in events if value.get("event") == "sequential_cancel"]
            full = bool(
                len(trajectory) == horizon + 1
                and len(trace) == horizon
                and currents.shape == (horizon + 1, 14)
                and actions.shape == recorded.shape == (horizon, 14)
                and np.all(np.isfinite(currents))
                and np.all(np.isfinite(actions))
                and np.array_equal(actions, recorded)
                and not any(bool(value.get("abnormal")) for value in trajectory)
                and all(
                    bool(value.get("computed_online"))
                    and bool(value.get("solver_success"))
                    for value in trace
                )
            )
            restart_pass = bool(
                restart.get("fresh_controller")
                and restart.get("fresh_tsc_process")
                and restart.get("initial_restart_exact")
                and restart.get("controller_trace_causal")
            )
            issue_pass = sum(_issue_gate(value, ctx.cfg) for value in issues)
            cancel_pass = sum(_cancel_gate(value, ctx.cfg) for value in cancels)
            forbidden = stage._forbidden_trace_count(trace)
            passed = bool(
                full
                and restart_pass
                and phase["passed"]
                and calibration["passed"]
                and calibration_events == _expected_calibration()
                and sequence_events == _expected_sequence()
                and len(issues) == len(cancels) == 4
                and issue_pass == cancel_pass == 4
                and forbidden == 0
                and utilization
                <= float(ctx.cfg["schedule_contract"]["maximum_current_utilization"])
                + 1e-12
            )
            rows.append(
                {
                    **row,
                    "strict_parse_pass": True,
                    "identity_pass": True,
                    "result_success": True,
                    **prefix,
                    "full_horizon_pass": full,
                    "restart_pass": restart_pass,
                    "causality_pass": bool(phase["passed"]),
                    "phase_prefix_pass": bool(phase["passed"]),
                    "calibration_pass": bool(calibration["passed"]),
                    "fresh_actor_process_summary_emitted": bool(fresh_summary),
                    "fresh_actor_process_summary_status": "reported",
                    "issue_event_count": len(issues),
                    "cancel_event_count": len(cancels),
                    "issue_gate_pass_count": issue_pass,
                    "cancel_gate_pass_count": cancel_pass,
                    "cancel_margin_pass_count": sum(
                        float(value["incremental_normalized_action_linf"])
                        <= 0.24 + 1e-12
                        for value in cancels
                    ),
                    "maximum_cancel_incremental_normalized_action_linf": max(
                        (float(value["incremental_normalized_action_linf"]) for value in cancels),
                        default=0.0,
                    ),
                    "maximum_current_utilization": utilization,
                    "formal_contract_pass_diagnostic": bool(
                        restart.get("formal_contract_pass")
                    ),
                    "classification": "pass" if passed else "runtime_or_audit_error",
                    "passed": passed,
                }
            )
        except Exception as exc:
            rows.append(
                {
                    **row,
                    "strict_parse_pass": True,
                    "identity_pass": True,
                    "result_success": True,
                    "classification": "runtime_or_audit_error",
                    "failure_reason": repr(exc),
                    "passed": False,
                }
            )
    action_failures = [
        row for row in rows if row.get("classification") == "action_schedule_design_failure"
    ]
    runtime_failures = [
        row
        for row in rows
        if row.get("classification") not in {"pass", "action_schedule_design_failure"}
    ]
    raw_pass = len(rows) == len(specs) and all(bool(row.get("passed")) for row in rows)
    if raw_pass:
        route = ctx.cfg["routes"]["pass"]
    elif runtime_failures:
        route = ctx.cfg["routes"]["runtime_fail"]
    else:
        route = ctx.cfg["routes"]["action_fail"]
    final_consistent = bool(
        state.get("finished")
        and int(state.get("new_raw_count", -1)) == inventory["count"]
        and state.get("verdict", {}).get("route") == route
        and final.get("route") == route
        and bool(state.get("primary_pass")) == raw_pass
        and bool(final.get("passed")) == raw_pass
        and manifest.get("route") == route
        and bool(manifest.get("passed")) == raw_pass
    )
    complete_log = complete_log.expanduser().resolve()
    log_auth = {
        "path": str(complete_log),
        "exists": complete_log.is_file(),
        "bytes": complete_log.stat().st_size if complete_log.is_file() else 0,
        "sha256": stage._sha256(complete_log) if complete_log.is_file() else "",
    }
    passed = bool(
        raw_pass
        and inventory["count"]
        == int(ctx.cfg["execution_gate"]["raw_files_required"])
        and snapshots.get("passed")
        and int(snapshots.get("pass_count", -1)) == 18
        and final_consistent
        and log_auth["exists"]
    )
    return {
        "schema_version": 1,
        "stage": stage.STAGE,
        "classification": "independent_server_raw_snapshot_manifest_log_forensics",
        "raw_inventory": inventory,
        "expected_raw_count": int(ctx.cfg["execution_gate"]["raw_files_required"]),
        "strict_parse_count": sum(bool(row.get("strict_parse_pass")) for row in rows),
        "identity_pass_count": sum(bool(row.get("identity_pass")) for row in rows),
        "success_count": sum(bool(row.get("result_success")) for row in rows),
        "full_pass_count": sum(bool(row.get("passed")) for row in rows),
        "action_schedule_failure_count": len(action_failures),
        "runtime_or_audit_failure_count": len(runtime_failures),
        "restart_pass_count": sum(bool(row.get("restart_pass")) for row in rows),
        "initial_restart_exact_count": sum(
            bool(row.get("initial_restart_exact")) for row in rows
        ),
        "causality_pass_count": sum(bool(row.get("causality_pass")) for row in rows),
        "causal_trace_prefix_pass_count": sum(
            bool(row.get("causal_trace_prefix_pass")) for row in rows
        ),
        "phase_prefix_pass_count": sum(
            bool(row.get("phase_prefix_pass")) for row in rows
        ),
        "calibration_pass_count": sum(bool(row.get("calibration_pass")) for row in rows),
        "physical_prefix_integrity_pass_count": sum(
            bool(row.get("physical_prefix_integrity_pass")) for row in rows
        ),
        "authentic_tsc_prefix_evidence_pass_count": sum(
            bool(row.get("authentic_tsc_prefix_evidence_pass")) for row in rows
        ),
        "fresh_actor_process_summary_emitted_count": sum(
            bool(row.get("fresh_actor_process_summary_emitted")) for row in rows
        ),
        "fresh_actor_process_summary_not_emitted_count": sum(
            row.get("fresh_actor_process_summary_status")
            == "not_emitted_by_structured_exception_handler"
            for row in rows
        ),
        "issue_event_count": sum(int(row.get("issue_event_count", 0)) for row in rows),
        "cancel_event_count": sum(int(row.get("cancel_event_count", 0)) for row in rows),
        "applied_issue_event_count": sum(
            int(row.get("applied_issue_event_count", row.get("issue_event_count", 0)))
            for row in rows
        ),
        "applied_cancel_event_count": sum(
            int(row.get("applied_cancel_event_count", row.get("cancel_event_count", 0)))
            for row in rows
        ),
        "issue_gate_pass_count": sum(
            int(row.get("issue_gate_pass_count", 0)) for row in rows
        ),
        "cancel_gate_pass_count": sum(
            int(row.get("cancel_gate_pass_count", 0)) for row in rows
        ),
        "cancel_margin_pass_count": sum(
            int(row.get("cancel_margin_pass_count", 0)) for row in rows
        ),
        "maximum_cancel_incremental_normalized_action_linf": max(
            (
                float(row.get("maximum_cancel_incremental_normalized_action_linf", 0.0))
                for row in rows
            ),
            default=0.0,
        ),
        "maximum_current_utilization": max(
            (float(row.get("maximum_current_utilization", 0.0)) for row in rows),
            default=0.0,
        ),
        "forbidden_trace_count": sum(
            int(row.get("forbidden_trace_count", 0)) for row in rows
        ),
        "failed_action_applied_count": sum(
            bool(row.get("failed_action_applied")) for row in rows
        ),
        "plant_advance_after_failed_action_count": sum(
            bool(row.get("plant_advance_after_failed_action")) for row in rows
        ),
        "formal_tracking_pass_count_diagnostic_only": sum(
            bool(row.get("formal_contract_pass_diagnostic")) for row in rows
        ),
        "snapshot_audit": snapshots,
        "state_manifest_final_consistent": final_consistent,
        "complete_log": log_auth,
        "route": route,
        "passed": passed,
        "rows": rows,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--source-d1r9-output", type=Path, required=True)
    parser.add_argument("--source-d1r9-log", type=Path, required=True)
    parser.add_argument("--source-s21-run", type=Path, required=True)
    parser.add_argument("--source-s23r1-output", type=Path, required=True)
    parser.add_argument("--source-stage42r3b-run", type=Path, required=True)
    parser.add_argument("--source-stage42r3c3-run", type=Path, required=True)
    parser.add_argument("--source-stage42r3c3-bank-dir", type=Path, required=True)
    parser.add_argument("--source-stage42r3c3t1-run", type=Path, required=True)
    parser.add_argument("--source-stage42r3c3t1-audit-dir", type=Path, required=True)
    parser.add_argument("--source-stage42r3c3t3-controller-bank", type=Path, required=True)
    parser.add_argument("--q1-run", type=Path, required=True)
    parser.add_argument("--q2-run", type=Path, required=True)
    parser.add_argument("--q1-audit", type=Path, required=True)
    parser.add_argument("--q2-audit", type=Path, required=True)
    parser.add_argument("--r3b-server-audit", type=Path, required=True)
    parser.add_argument("--r3b-snapshot-checks", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--complete-log", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main() -> None:
    args = _parser().parse_args()
    ctx = stage.load_config(
        args.config,
        source_d1r9_output=args.source_d1r9_output,
        source_d1r9_log=args.source_d1r9_log,
        source_s21_run=args.source_s21_run,
        source_s23r1_output=args.source_s23r1_output,
        run_dir=args.run_dir,
        **stage._source_kwargs(args),
    )
    result = run_forensics(ctx, args.complete_log)
    stage._write_json(args.output.expanduser().resolve(), result)
    print(json.dumps(result, sort_keys=True, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
