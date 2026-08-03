#!/usr/bin/env python3
"""Independent raw/log forensics for the D1R6 recursive-return sentinel."""

from __future__ import annotations

import argparse
from collections import Counter
import copy
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r2_real_tsc_safety_sentinel as d1r2,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r6_recursive_split_return_safety_sentinel as stage,
)


EXPECTED_CALIBRATION = [
    "calibration_issue",
    "calibration_cancel",
    "calibration_issue",
    "calibration_cancel",
    "calibration_issue",
    "calibration_cancel",
    "calibration_issue",
    "calibration_cancel",
]
EXPECTED_PREFIX_EVENTS = [
    "sequential_issue",
    "sequential_cancel",
    "sequential_issue",
    "sequential_cancel",
    "sequential_issue",
    "sequential_cancel",
    "sequential_issue",
    "sequential_cancel_split_start",
]


def _read(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
    )


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _inventory(raw_dir: Path) -> dict[str, Any]:
    rows = []
    digest = hashlib.sha256()
    for path in sorted(raw_dir.glob("*.json.gz")):
        sha = _sha(path)
        size = path.stat().st_size
        digest.update(f"{path.name}\0{size}\0{sha}\n".encode())
        rows.append({"path": path.name, "bytes": size, "sha256": sha})
    return {
        "count": len(rows),
        "total_bytes": sum(row["bytes"] for row in rows),
        "digest": digest.hexdigest(),
        "files": rows,
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


def _forbidden(trace: Sequence[Mapping[str, Any]]) -> int:
    keys = (
        "future_measurement_used",
        "hidden_wire_used",
        "source_action_used",
        "source_coil_current_used",
        "source_wire_current_used",
        "current_run_future_used",
        "pair_or_history_label_used",
        "source_result_used",
        "future_probe_schedule_available_to_underlying_controller",
        "r3c3t13s21_partition_label_used",
        "r3c3t13s24_pair_history_partition_label_used",
        "r3c3t13s24_delay_slew_target_id_label_used",
        "r3c3t13s24_source_or_matched_baseline_used",
        "r3c3t13s24_future_measurement_used",
        "r3c3t13s24_future_executed_action_used",
        "r3c3t13s24_hidden_wire_current_used",
        "r3c3t13s24_schedule_available_to_underlying_controller",
        "r3c3t13s24d1r2_source_selection_label_used",
        "r3c3t13s24d1r2_pair_history_partition_label_used",
        "r3c3t13s24d1r2_source_outcome_used",
        "r3c3t13s24d1r2_future_measurement_used",
        "r3c3t13s24d1r2_future_executed_action_used",
        "r3c3t13s24d1r2_hidden_wire_current_used",
        "r3c3t13s24d1r2_schedule_available_to_underlying_controller",
        "r3c3t13s24d1r6_source_selection_label_used",
        "r3c3t13s24d1r6_pair_history_partition_label_used",
        "r3c3t13s24d1r6_source_outcome_used",
        "r3c3t13s24d1r6_future_measurement_used",
        "r3c3t13s24d1r6_future_executed_action_used",
        "r3c3t13s24d1r6_hidden_wire_current_used",
        "r3c3t13s24d1r6_schedule_available_to_underlying_controller",
    )
    return sum(any(bool(row.get(key)) for key in keys) for row in trace)


def _current_projection(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: copy.deepcopy(value)
        for key, value in row.items()
        if not key.startswith("r3c3t13s24d1r6_")
    }


def _source_projection(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: copy.deepcopy(value)
        for key, value in row.items()
        if not key.startswith("r3c3t13s24d1r4_")
    }


def _float_equal(left: Any, right: Any) -> bool:
    return math.isclose(float(left), float(right), rel_tol=0.0, abs_tol=1e-12)


def _restart_exact(
    result: Mapping[str, Any], state_map: Mapping[str, Mapping[str, Any]]
) -> tuple[bool, bool, bool]:
    initial = result["trajectory"][0]
    generated = state_map[str(result["spec"]["state_generation_experiment_id"])]
    visible = bool(
        np.array_equal(
            np.asarray(
                [
                    initial["R"],
                    initial["Z"],
                    initial["Ip"],
                    *initial["currents_a_tsc"],
                ],
                dtype=float,
            ),
            np.asarray(
                [
                    generated["R"],
                    generated["Z"],
                    generated["Ip"],
                    *generated["coil_currents_a"],
                ],
                dtype=float,
            ),
        )
    )
    generated_wire = np.asarray(generated["wire_currents_a"], dtype=float)
    restarted_wire = np.asarray(initial["wire_currents_a"], dtype=float)
    wire = bool(
        generated_wire.shape == restarted_wire.shape
        and np.array_equal(generated_wire, restarted_wire)
    )
    return visible, wire, bool(visible and wire)


def _first_continuation_exact(
    current: Mapping[str, Any], frozen: Mapping[str, Any]
) -> bool:
    direct = current.get("direct_finish_event") or {}
    frozen_direct = frozen.get("direct_finish_prediction") or {}
    return bool(
        int(current.get("task_step", -1)) == 19
        and int(current.get("continuation_count", -1)) == 1
        and np.array_equal(
            np.asarray(current.get("baseline_action_norm_tsc")),
            np.asarray(frozen["baseline_action_norm_tsc"]),
        )
        and np.array_equal(
            np.asarray(current.get("continuation_action_norm_tsc")),
            np.asarray(frozen["continuation_action_norm_tsc"]),
        )
        and current.get("continuation_card15_fields")
        == frozen["continuation_card15_fields"]
        and current.get("previous_intermediate_card15_fields")
        == frozen["previous_intermediate_card15_fields"]
        and current.get("stored_center_card15_fields")
        == frozen["stored_center_card15_fields"]
        and current.get("issue_target_card15_fields")
        == frozen["issue_target_card15_fields"]
        and _float_equal(current.get("alpha"), frozen["alpha"])
        and _float_equal(
            current.get("continuation_incremental_normalized_action_linf"),
            frozen["continuation_incremental_normalized_action_linf"],
        )
        and _float_equal(
            current.get("continuation_total_normalized_action_abs"),
            frozen["continuation_total_normalized_action_abs"],
        )
        and np.array_equal(
            np.asarray(direct.get("finish_action_norm_tsc")),
            np.asarray(frozen_direct["action_norm_tsc"]),
        )
        and _float_equal(
            direct.get("incremental_normalized_action_linf"),
            frozen_direct["incremental_normalized_action_linf"],
        )
        and direct.get("stored_center_card15_fields")
        == frozen_direct["target_fields"]
    )


def _audit_row(
    ctx: stage.Context,
    spec: Mapping[str, Any],
    result: Mapping[str, Any],
    state_map: Mapping[str, Mapping[str, Any]],
    d1r5_rows: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    trajectory = list(result.get("trajectory") or [])
    trace = list(result.get("controller_trace") or [])
    source_id = str(spec["d1r6_source_d1r4_experiment_id"])
    row: dict[str, Any] = {
        "experiment_id": spec["experiment_id"],
        "source_d1r4_experiment_id": source_id,
        "source_d1r2_experiment_id": spec["d1r4_source_d1r2_experiment_id"],
        "pair_id": spec["pair_id"],
        "history_member": spec["history_member"],
        "sequence_index": int(spec["s24_sequence_index"]),
        "strict_parse_pass": True,
        "passed": False,
    }
    identity = bool(
        result.get("completed")
        and result.get("stage") == stage.STAGE
        and result.get("campaign_identity") == stage.CAMPAIGN_IDENTITY
        and result.get("controller_revision") == stage.CONTROLLER_REVISION
        and result.get("probe_primitive_revision") == stage.CONTROLLER_REVISION
        and result.get("experiment_id") == spec["experiment_id"]
        and result.get("spec") == dict(spec)
        and len(trajectory) == len(trace) + 1
    )
    row["identity_pass"] = identity
    if not identity:
        row.update(classification="raw_identity_error", failure_reason="identity mismatch")
        return row
    failure_event = result.get("action_failure_event") or {}
    structured = bool(
        not result.get("success")
        and result.get("failure_class") == "structured_action_schedule_gate"
        and isinstance(failure_event, dict)
        and not bool(failure_event.get("passed"))
    )
    if not result.get("success") and not structured:
        row.update(
            result_success=False,
            classification=(
                "scientific_gate_failure"
                if result.get("failure_class") == "runtime_or_execution_gate"
                else "runtime_or_environment_error"
            ),
            failure_reason=str(result.get("failure_reason", "")),
        )
        return row

    currents = np.asarray(
        [item["currents_a_tsc"] for item in trajectory], dtype=float
    )
    actions = np.asarray([item["action_norm_tsc"] for item in trace], dtype=float)
    recorded = np.asarray(
        [item["action_norm_tsc"] for item in trajectory[1:]], dtype=float
    )
    payload = stage._payload(ctx, spec)
    minimum, maximum = d1r2.s24.s21.s13._current_limits_tsc(payload)
    center, half = 0.5 * (minimum + maximum), 0.5 * (maximum - minimum)
    utilization = float(np.max(np.abs((currents - center) / half)))
    restart_visible, restart_wire, restart = _restart_exact(result, state_map)
    phase = d1r2.s24.s21.s16.s9.t11.t1.r3c1._phase_trace_valid(result)
    calibration = d1r2.s24.s21._dynamic_calibration_trace_audit(
        result, ctx.base_d1r2_ctx.base_s24_ctx.base_ctx.cfg
    )
    calibration_events = [
        item.get("r3c3t13s16_lattice_event")
        for item in trace
        if item.get("r3c3t13s16_lattice_event") != "none"
    ]
    details = [
        item["r3c3t13s24d1r6_event_detail"]
        for item in trace
        if item.get("r3c3t13s24d1r6_event") != "none"
    ]
    events = [str(item.get("event")) for item in details]
    issues = [item for item in details if item.get("event") == "sequential_issue"]
    direct = [item for item in details if item.get("event") == "sequential_cancel"]
    starts = [
        item
        for item in details
        if item.get("event") == "sequential_cancel_split_start"
    ]
    continuations = [
        item
        for item in details
        if item.get("event") == "sequential_cancel_split_continue"
    ]
    finishes = [
        item
        for item in details
        if item.get("event") == "sequential_cancel_split_finish"
    ]
    source = stage._read_raw(ctx.source_d1r4_ctx.paths.raw / f"{source_id}.json.gz")
    source_trace = list(source.get("controller_trace") or [])
    source_trajectory = list(source.get("trajectory") or [])
    prefix_action = bool(
        len(source_trace) == 19
        and len(trace) >= 19
        and np.array_equal(
            np.asarray([item["action_norm_tsc"] for item in trace[:19]]),
            np.asarray([item["action_norm_tsc"] for item in source_trace]),
        )
    )
    source_prefix_trace_exact = bool(
        len(source_trace) == 19
        and len(trace) >= 18
        and all(
            _current_projection(current) == _source_projection(prior)
            for current, prior in zip(trace[:18], source_trace[:18])
        )
    )
    prefix_state = bool(
        len(source_trajectory) == 20
        and len(trajectory) >= 20
        and trajectory[:20] == source_trajectory
    )
    source_starts = [
        item["r3c3t13s24d1r4_event_detail"]
        for item in source_trace
        if item.get("r3c3t13s24d1r4_event")
        == "sequential_cancel_split_start"
    ]
    start = starts[0] if len(starts) == 1 else {}
    start_ref = source_starts[0] if len(source_starts) == 1 else {}
    start_exact = bool(
        start
        and start_ref
        and np.array_equal(
            np.asarray(start.get("split_start_action_norm_tsc")),
            np.asarray(start_ref.get("split_start_action_norm_tsc")),
        )
        and start.get("intermediate_card15_fields")
        == start_ref.get("intermediate_card15_fields")
        and _float_equal(start.get("alpha"), start_ref.get("alpha"))
        and _float_equal(
            start.get("split_start_incremental_normalized_action_linf"), 0.175
        )
        and int(start.get("task_step", -1)) == 18
        and bool(start.get("passed"))
        and all(bool(value) for value in (start.get("criteria") or {}).values())
    )
    first_exact = bool(
        continuations
        and _first_continuation_exact(
            continuations[0], d1r5_rows[source_id]["continuation_event"]
        )
    )
    continuation_steps = [int(item.get("task_step", -1)) for item in continuations]
    continuation_schedule = bool(
        1 <= len(continuations) <= 3
        and continuation_steps == list(range(19, 19 + len(continuations)))
        and all(
            int(item.get("continuation_count", -1)) == index
            and bool(item.get("passed"))
            and all(bool(value) for value in (item.get("criteria") or {}).values())
            and _float_equal(
                item.get("continuation_incremental_normalized_action_linf"), 0.175
            )
            for index, item in enumerate(continuations, start=1)
        )
    )
    finish = finishes[0] if len(finishes) == 1 else {}
    finish_pass = bool(
        finish.get("passed")
        and all(bool(value) for value in (finish.get("criteria") or {}).values())
        and float(finish.get("incremental_normalized_action_linf", math.inf))
        <= 0.24 + 1e-12
        and int(finish.get("task_step", -1)) == 19 + len(continuations)
        and 20 <= int(finish.get("task_step", -1)) <= 22
        and int(finish.get("continuation_count", -1)) == len(continuations)
    )
    forbidden = _forbidden(trace)
    numeric = bool(
        _all_finite(result)
        and np.all(np.isfinite(currents))
        and np.all(np.isfinite(actions))
        and np.array_equal(actions, recorded)
    )
    executed = bool(
        numeric
        and not any(bool(item.get("abnormal")) for item in trajectory)
        and all(
            bool(item.get("computed_online")) and bool(item.get("solver_success"))
            for item in trace
        )
        and all(
            float(item.get("gotsc_subprocess_s", 0.0)) > 0.0
            for item in trajectory[1:]
        )
    )
    common = bool(
        restart
        and phase["passed"]
        and calibration["passed"]
        and calibration_events == EXPECTED_CALIBRATION
        and len(issues) == 4
        and len(direct) == 3
        and len(starts) == 1
        and prefix_action
        and source_prefix_trace_exact
        and prefix_state
        and start_exact
        and first_exact
        and continuation_schedule
        and forbidden == 0
        and utilization <= 0.55 + 1e-12
    )
    base = {
        "result_success": bool(result.get("success")),
        "restart_visible_exact": restart_visible,
        "restart_wire_exact": restart_wire,
        "restart_pass": restart,
        "causality_pass": bool(phase["passed"]),
        "calibration_pass": bool(calibration["passed"]),
        "source_prefix_action_exact": prefix_action,
        "source_prefix_trace_exact": source_prefix_trace_exact,
        "source_prefix_state_exact": prefix_state,
        "split_start_exact": start_exact,
        "first_d1r5_continuation_exact": first_exact,
        "continuation_schedule_pass": continuation_schedule,
        "issue_event_count": len(issues),
        "direct_cancel_event_count": len(direct),
        "split_start_event_count": len(starts),
        "continuation_event_count": len(continuations),
        "split_finish_event_count": len(finishes),
        "maximum_current_utilization": utilization,
        "forbidden_count": forbidden,
    }
    if structured:
        action_not_applied = bool(
            executed
            and len(trajectory) == len(trace) + 1
            and int(trajectory[-1].get("step_index", -1)) == len(trace)
            and int(failure_event.get("task_step", -2)) == len(trace)
        )
        deadline = bool(
            failure_event.get("event")
            == "sequential_cancel_recursive_deadline_stop"
            and int(failure_event.get("task_step", -1)) == 22
            and not bool(failure_event.get("failed_candidate_applied", True))
            and not bool(failure_event.get("plant_advance_after_failure", True))
            and len(trajectory) == 23
            and len(trace) == 22
        )
        row.update(
            **base,
            structured_action_failure=True,
            structured_deadline_safe_stop=deadline,
            failure_action_not_applied=action_not_applied,
            executed_prefix_pass=bool(common and action_not_applied),
            formal_tracking_evaluable=False,
            classification="action_schedule_design_failure",
            failure_event=copy.deepcopy(failure_event),
            failure_reason=str(result.get("failure_reason", "")),
        )
        return row

    summary = result.get("hidden_history_control_summary") or {}
    full_horizon = bool(executed and len(trajectory) == 36 and len(trace) == 35)
    schedule = bool(
        events
        == [
            *EXPECTED_PREFIX_EVENTS,
            *(["sequential_cancel_split_continue"] * len(continuations)),
            "sequential_cancel_split_finish",
        ]
        and len(finishes) == 1
        and all(bool(item.get("passed")) for item in details)
    )
    action_pass = bool(
        common
        and schedule
        and finish_pass
        and not bool(summary.get("split_pending_at_end"))
        and int(summary.get("split_start_count", 0)) == 1
        and int(summary.get("split_finish_count", 0)) == 1
        and int(summary.get("recursive_continuation_count", 0))
        == len(continuations)
        and int(summary.get("recursive_finish_count", 0)) == 1
        and int(summary.get("recursive_finish_task_step", -1))
        == int(finish.get("task_step", -2))
    )
    passed = bool(full_horizon and action_pass)
    row.update(
        **base,
        runtime_full_horizon_pass=full_horizon,
        action_trace_pass=action_pass,
        finish_task_step=int(finish.get("task_step", -1)),
        split_finish_increment=float(
            finish.get("incremental_normalized_action_linf", math.inf)
        ),
        expanded_decimal_telescope_pass=bool(
            (finish.get("criteria") or {}).get("expanded_exact_decimal_telescope")
        ),
        formal_tracking_evaluable=True,
        classification="pass" if passed else "scientific_gate_failure",
        passed=passed,
    )
    return row


def run(args: argparse.Namespace) -> dict[str, Any]:
    ctx = stage.load_config(
        args.config,
        source_d1r4_run=args.source_d1r4_run,
        source_d1r4_complete_log=args.source_d1r4_complete_log,
        source_d1r5_primary_output=args.source_d1r5_primary_output,
        source_d1r5_repeat_output=args.source_d1r5_repeat_output,
        source_d1r5_primary_log=args.source_d1r5_primary_log,
        source_d1r5_repeat_log=args.source_d1r5_repeat_log,
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
    specs = stage._saved_specs(ctx)
    inventory = _inventory(ctx.paths.raw)
    expected_names = sorted(f"{spec['experiment_id']}.json.gz" for spec in specs)
    actual_names = sorted(str(row["path"]) for row in inventory["files"])
    raw_inventory_exact = bool(
        inventory["count"] == len(specs) and actual_names == expected_names
    )
    state_map = d1r2.s24.s21.s13._source_state_map(
        ctx.base_d1r2_ctx.base_s24_ctx.base_ctx.base_ctx.base_ctx
    )
    d1r5_detailed = _read(
        ctx.source_d1r5_primary_output
        / "stage4_2r3c3t13s24d1r5_detailed_v1.json"
    )
    d1r5_rows = {
        str(row["source_experiment_id"]): row for row in d1r5_detailed["rows"]
    }
    rows: list[dict[str, Any]] = []
    for spec in specs:
        path = ctx.paths.raw / f"{spec['experiment_id']}.json.gz"
        if not path.is_file():
            rows.append(
                {
                    "experiment_id": spec["experiment_id"],
                    "classification": "runtime_or_raw_error",
                    "failure_reason": "missing raw",
                    "passed": False,
                }
            )
            continue
        try:
            result = stage._read_raw(path)
            rows.append(_audit_row(ctx, spec, result, state_map, d1r5_rows))
        except Exception as exc:
            rows.append(
                {
                    "experiment_id": spec["experiment_id"],
                    "classification": "raw_corruption_error",
                    "failure_reason": repr(exc),
                    "passed": False,
                }
            )
    runtime_classes = {
        "runtime_or_raw_error",
        "runtime_or_environment_error",
        "raw_corruption_error",
        "raw_identity_error",
    }
    design_classes = {"action_schedule_design_failure", "scientific_gate_failure"}
    runtime = [row for row in rows if row.get("classification") in runtime_classes]
    design = [row for row in rows if row.get("classification") in design_classes]
    sentinel_pass = bool(
        raw_inventory_exact
        and len(rows) == 9
        and all(bool(row.get("passed")) for row in rows)
    )
    if sentinel_pass:
        route = ctx.cfg["routes"]["pass"]
    elif runtime or not raw_inventory_exact:
        route = ctx.cfg["routes"]["runtime_incomplete"]
    else:
        route = ctx.cfg["routes"]["action_fail"]

    complete_log = args.complete_log.expanduser().resolve()
    log_text = complete_log.read_text(encoding="utf-8", errors="strict")
    state = _read(ctx.paths.state)
    manifest = _read(ctx.paths.manifest)
    final = _read(ctx.paths.final)
    internal_path = ctx.paths.analysis / "internal_execution_audit.json"
    snapshot_audit_path = ctx.paths.source_reference / "snapshot_audit.json"
    source_auth_path = ctx.paths.source_reference / "source_authentication.json"
    snapshot_audit = _read(snapshot_audit_path)
    source_auth = _read(source_auth_path)
    log_pass = bool(
        "[T13S24D1R6] 9/9" in log_text
        and route in log_text
        and "Traceback (most recent call last)" not in log_text
    )
    consistency = bool(
        state.get("finished")
        and state.get("verdict", {}).get("route") == route
        and manifest.get("route") == route
        and final.get("route") == route
        and final.get("raw_inventory") == inventory
        and manifest.get("raw_inventory") == inventory
        and manifest.get("final_result_sha256") == _sha(ctx.paths.final)
        and internal_path.is_file()
        and manifest.get("internal_execution_audit_sha256") == _sha(internal_path)
        and manifest.get("snapshot_pass_count") == 3
        and snapshot_audit.get("passed")
        and snapshot_audit.get("pass_count") == 3
        and source_auth.get("passed")
        and state.get("package_fingerprint") == manifest.get("package_fingerprint")
        and state.get("source_fingerprint") == manifest.get("source_fingerprint")
    )
    evidence_complete = bool(
        raw_inventory_exact
        and len(rows) == 9
        and not runtime
        and all(bool(row.get("identity_pass")) for row in rows)
        and all(bool(row.get("restart_pass")) for row in rows)
        and all(bool(row.get("causality_pass")) for row in rows)
        and all(bool(row.get("calibration_pass")) for row in rows)
    )
    output = {
        "schema_version": 1,
        "stage": stage.STAGE,
        "classification": "independent_server_raw_log_snapshot_recomputation",
        "complete_log_path": str(complete_log),
        "complete_log_sha256": _sha(complete_log),
        "complete_log_pass": log_pass,
        "raw_inventory": inventory,
        "raw_inventory_exact": raw_inventory_exact,
        "snapshot_audit_sha256": _sha(snapshot_audit_path),
        "source_authentication_sha256": _sha(source_auth_path),
        "expected": 9,
        "strict_parse_count": sum(bool(row.get("strict_parse_pass")) for row in rows),
        "identity_pass_count": sum(bool(row.get("identity_pass")) for row in rows),
        "success_count": sum(bool(row.get("result_success")) for row in rows),
        "sentinel_pass_count": sum(bool(row.get("passed")) for row in rows),
        "runtime_or_raw_failure_count": len(runtime),
        "scientific_or_action_failure_count": len(design),
        "full_horizon_pass_count": sum(
            bool(row.get("runtime_full_horizon_pass")) for row in rows
        ),
        "restart_pass_count": sum(bool(row.get("restart_pass")) for row in rows),
        "causality_pass_count": sum(bool(row.get("causality_pass")) for row in rows),
        "calibration_pass_count": sum(bool(row.get("calibration_pass")) for row in rows),
        "source_prefix_action_exact_count": sum(
            bool(row.get("source_prefix_action_exact")) for row in rows
        ),
        "source_prefix_trace_exact_count": sum(
            bool(row.get("source_prefix_trace_exact")) for row in rows
        ),
        "source_prefix_state_exact_count": sum(
            bool(row.get("source_prefix_state_exact")) for row in rows
        ),
        "split_start_exact_count": sum(bool(row.get("split_start_exact")) for row in rows),
        "first_d1r5_continuation_exact_count": sum(
            bool(row.get("first_d1r5_continuation_exact")) for row in rows
        ),
        "issue_event_count": sum(int(row.get("issue_event_count", 0)) for row in rows),
        "direct_cancel_event_count": sum(
            int(row.get("direct_cancel_event_count", 0)) for row in rows
        ),
        "split_start_event_count": sum(
            int(row.get("split_start_event_count", 0)) for row in rows
        ),
        "continuation_event_count": sum(
            int(row.get("continuation_event_count", 0)) for row in rows
        ),
        "split_finish_event_count": sum(
            int(row.get("split_finish_event_count", 0)) for row in rows
        ),
        "finish_task_step_counts": [
            {"task_step": key, "count": value}
            for key, value in sorted(
                Counter(
                    int(row["finish_task_step"])
                    for row in rows
                    if int(row.get("finish_task_step", -1)) >= 0
                ).items()
            )
        ],
        "structured_deadline_safe_stop_count": sum(
            bool(row.get("structured_deadline_safe_stop")) for row in rows
        ),
        "failure_action_not_applied_count": sum(
            bool(row.get("failure_action_not_applied")) for row in rows
        ),
        "expanded_decimal_telescope_pass_count": sum(
            bool(row.get("expanded_decimal_telescope_pass")) for row in rows
        ),
        "maximum_current_utilization": max(
            (float(row.get("maximum_current_utilization", 0.0)) for row in rows),
            default=0.0,
        ),
        "forbidden_count": sum(int(row.get("forbidden_count", 0)) for row in rows),
        "formal_tracking_evaluable_count": sum(
            bool(row.get("formal_tracking_evaluable")) for row in rows
        ),
        "state_manifest_final_consistency": consistency,
        "evidence_complete_without_runtime_error": evidence_complete,
        "formal_timing_unchanged": True,
        "formal_tracking_is_diagnostic_only": True,
        "probe_trajectories_allowed_in_expert_dataset": False,
        "full_replacement_campaign_design_authorized": sentinel_pass,
        "full_replacement_campaign_execution_authorized": False,
        "mpc_or_learning_authorized": False,
        "route": route,
        "sentinel_passed": sentinel_pass,
        "forensic_recomputation_passed": bool(
            evidence_complete and log_pass and consistency
        ),
        "rows": rows,
    }
    output_path = args.output.expanduser().resolve()
    if output_path.exists():
        raise ValueError("D1R6 independent forensic output must be new")
    _write(output_path, output)
    return output


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--source-d1r4-run", type=Path, required=True)
    parser.add_argument("--source-d1r4-complete-log", type=Path, required=True)
    parser.add_argument("--source-d1r5-primary-output", type=Path, required=True)
    parser.add_argument("--source-d1r5-repeat-output", type=Path, required=True)
    parser.add_argument("--source-d1r5-primary-log", type=Path, required=True)
    parser.add_argument("--source-d1r5-repeat-log", type=Path, required=True)
    parser.add_argument("--source-d1r2-run", type=Path, required=True)
    parser.add_argument("--source-d1r3-output", type=Path, required=True)
    parser.add_argument("--source-d1r3-primary-log", type=Path, required=True)
    parser.add_argument("--source-d1r3-repeat-log", type=Path, required=True)
    parser.add_argument("--source-d1r1-output", type=Path, required=True)
    parser.add_argument("--source-d1r1-log", type=Path, required=True)
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
    result = run(_parser().parse_args())
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
