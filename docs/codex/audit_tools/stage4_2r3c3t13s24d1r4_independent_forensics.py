#!/usr/bin/env python3
"""Independent raw/log forensics for the D1R4 split-return sentinel."""

from __future__ import annotations

import argparse
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
    stage4_2r3c3t13s24d1r4_causal_split_return_safety_sentinel as stage,
)


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
        "r3c3t13s24d1r4_source_selection_label_used",
        "r3c3t13s24d1r4_pair_history_partition_label_used",
        "r3c3t13s24d1r4_source_outcome_used",
        "r3c3t13s24d1r4_future_measurement_used",
        "r3c3t13s24d1r4_future_executed_action_used",
        "r3c3t13s24d1r4_hidden_wire_current_used",
        "r3c3t13s24d1r4_schedule_available_to_underlying_controller",
    )
    return sum(any(bool(row.get(key)) for key in keys) for row in trace)


def _projection(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: copy.deepcopy(value)
        for key, value in row.items()
        if not key.startswith("r3c3t13s24d1r4_")
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
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
    specs = stage._saved_specs(ctx)
    inventory = _inventory(ctx.paths.raw)
    expected_raw_names = sorted(f"{spec['experiment_id']}.json.gz" for spec in specs)
    actual_raw_names = sorted(str(row["path"]) for row in inventory["files"])
    raw_inventory_exact = bool(
        inventory["count"] == len(specs) and actual_raw_names == expected_raw_names
    )
    complete_log = args.complete_log.expanduser().resolve()
    log_text = complete_log.read_text(encoding="utf-8", errors="strict")
    d1r3_detail = _read(
        ctx.source_d1r3_output / "stage4_2r3c3t13s24d1r3_detailed_v1.json"
    )
    d1r3_starts = {
        str(row["source_experiment_id"]): row["split_start_event"]
        for row in d1r3_detail["rows"]
        if row.get("split_branch_selected")
    }
    source_raw_dir = ctx.source_d1r2_run / d1r2.RUN_NAME / "raw"
    state_map = d1r2.s24.s21.s13._source_state_map(
        ctx.base_d1r2_ctx.base_s24_ctx.base_ctx.base_ctx.base_ctx
    )
    base_source_ctx = (
        ctx.base_d1r2_ctx.base_s24_ctx.base_ctx.base_ctx.base_ctx.base_ctx.base_ctx
        .base_ctx.source_ctx.source_ctx
    )
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
    expected_events = [
        "sequential_issue",
        "sequential_cancel",
        "sequential_issue",
        "sequential_cancel",
        "sequential_issue",
        "sequential_cancel",
        "sequential_issue",
        "sequential_cancel_split_start",
        "sequential_cancel_split_finish",
    ]
    rows = []
    for spec in specs:
        path = ctx.paths.raw / f"{spec['experiment_id']}.json.gz"
        row: dict[str, Any] = {
            "experiment_id": spec["experiment_id"],
            "source_experiment_id": spec["d1r4_source_d1r2_experiment_id"],
            "pair_id": spec["pair_id"],
            "history_member": spec["history_member"],
            "sequence_index": int(spec["s24_sequence_index"]),
            "raw_present": path.is_file(),
            "passed": False,
        }
        if not path.is_file():
            row.update(classification="runtime_or_raw_error", failure_reason="missing raw")
            rows.append(row)
            continue
        try:
            result = stage._read_raw(path)
            row["strict_parse_pass"] = True
        except Exception as exc:
            row.update(
                strict_parse_pass=False,
                classification="raw_corruption_error",
                failure_reason=repr(exc),
            )
            rows.append(row)
            continue
        trajectory = result.get("trajectory") or []
        trace = result.get("controller_trace") or []
        identity = bool(
            result.get("completed")
            and result.get("stage") == stage.STAGE
            and result.get("campaign_identity") == stage.CAMPAIGN_IDENTITY
            and result.get("controller_revision") == stage.CONTROLLER_REVISION
            and result.get("probe_primitive_revision") == stage.CONTROLLER_REVISION
            and result.get("experiment_id") == spec["experiment_id"]
            and result.get("spec") == dict(spec)
        )
        row["identity_pass"] = identity
        if not identity:
            row.update(classification="raw_identity_error", failure_reason="identity mismatch")
            rows.append(row)
            continue
        if not result.get("success"):
            event = result.get("action_failure_event")
            structured = bool(
                result.get("failure_class") == "structured_action_schedule_gate"
                and isinstance(event, dict)
                and not bool(event.get("passed"))
            )
            execution_gate = result.get("failure_class") == "runtime_or_execution_gate"
            row.update(
                result_success=False,
                structured_action_failure=structured,
                failure_event=copy.deepcopy(event),
                classification=(
                    "action_schedule_design_failure"
                    if structured
                    else (
                        "scientific_gate_failure"
                        if execution_gate
                        else "runtime_or_environment_error"
                    )
                ),
                failure_reason=result.get("failure_reason", ""),
            )
            rows.append(row)
            continue
        try:
            payload = stage._payload(ctx, spec)
            currents = np.asarray(
                [item["currents_a_tsc"] for item in trajectory], dtype=float
            )
            actions = np.asarray([item["action_norm_tsc"] for item in trace], dtype=float)
            recorded = np.asarray(
                [item["action_norm_tsc"] for item in trajectory[1:]], dtype=float
            )
            minimum, maximum = d1r2.s24.s21.s13._current_limits_tsc(payload)
            center, half = 0.5 * (minimum + maximum), 0.5 * (maximum - minimum)
            utilization = float(np.max(np.abs((currents - center) / half)))
            restart = d1r2.s24.s21.s16.s9.t11.t1.r3b._control_row(
                base_source_ctx,
                result,
                state_map[str(spec["state_generation_experiment_id"])],
            )
            phase = d1r2.s24.s21.s16.s9.t11.t1.r3c1._phase_trace_valid(result)
            calibration = d1r2.s24.s21._dynamic_calibration_trace_audit(
                result, ctx.base_d1r2_ctx.base_s24_ctx.base_ctx.cfg
            )
            calibration_events = [
                item.get("r3c3t13s16_lattice_event")
                for item in trace
                if item.get("r3c3t13s16_lattice_event") != "none"
            ]
            events = [
                item.get("r3c3t13s24d1r4_event")
                for item in trace
                if item.get("r3c3t13s24d1r4_event") != "none"
            ]
            details = [
                item["r3c3t13s24d1r4_event_detail"]
                for item in trace
                if item.get("r3c3t13s24d1r4_event") != "none"
            ]
            issues = [item for item in details if item.get("event") == "sequential_issue"]
            direct = [item for item in details if item.get("event") == "sequential_cancel"]
            starts = [
                item
                for item in details
                if item.get("event") == "sequential_cancel_split_start"
            ]
            finishes = [
                item
                for item in details
                if item.get("event") == "sequential_cancel_split_finish"
            ]
            source_id = str(spec["d1r4_source_d1r2_experiment_id"])
            source = stage._read_raw(source_raw_dir / f"{source_id}.json.gz")
            source_trace = source.get("controller_trace") or []
            prefix_action = bool(
                len(source_trace) == 18
                and np.array_equal(
                    np.asarray([item["action_norm_tsc"] for item in trace[:18]]),
                    np.asarray([item["action_norm_tsc"] for item in source_trace]),
                )
            )
            prefix_trace = bool(
                len(source_trace) == 18
                and all(
                    _projection(current) == prior
                    for current, prior in zip(trace[:18], source_trace)
                )
            )
            start_ref = d1r3_starts[source_id]
            start_exact = bool(
                len(starts) == 1
                and np.array_equal(
                    np.asarray(starts[0]["split_start_action_norm_tsc"]),
                    np.asarray(start_ref["split_start_action_norm_tsc"]),
                )
                and starts[0]["intermediate_card15_fields"]
                == start_ref["intermediate_card15_fields"]
            )
            finish = finishes[0] if len(finishes) == 1 else {}
            finish_pass = bool(
                finish.get("passed")
                and all((finish.get("criteria") or {}).values())
                and float(finish.get("incremental_normalized_action_linf", math.inf))
                <= 0.24 + 1e-12
            )
            summary = result.get("hidden_history_control_summary") or {}
            runtime = bool(
                len(trajectory) == 36
                and len(trace) == 35
                and np.all(np.isfinite(currents))
                and np.all(np.isfinite(actions))
                and not any(bool(item.get("abnormal")) for item in trajectory)
            )
            restart_pass = bool(
                restart.get("fresh_controller")
                and restart.get("fresh_tsc_process")
                and restart.get("initial_restart_exact")
                and restart.get("controller_trace_causal")
            )
            action_pass = bool(
                all(
                    bool(item.get("computed_online"))
                    and bool(item.get("solver_success"))
                    for item in trace
                )
                and calibration_events == expected_calibration
                and events == expected_events
                and len(issues) == 4
                and len(direct) == 3
                and len(starts) == len(finishes) == 1
                and all(bool(item.get("passed")) for item in details)
                and prefix_action
                and prefix_trace
                and start_exact
                and finish_pass
                and _forbidden(trace) == 0
                and bool(phase["passed"])
                and np.array_equal(actions, recorded)
                and float(np.max(np.abs(actions))) <= 1.0 + 1e-12
                and not bool(summary.get("split_pending_at_end"))
            )
            passed = bool(
                runtime
                and restart_pass
                and action_pass
                and calibration["passed"]
                and utilization <= 0.55 + 1e-12
            )
            row.update(
                result_success=True,
                runtime_full_horizon_pass=runtime,
                restart_pass=restart_pass,
                causality_pass=bool(phase["passed"]),
                calibration_pass=bool(calibration["passed"]),
                source_prefix_action_exact=prefix_action,
                source_prefix_trace_exact=prefix_trace,
                d1r3_split_start_exact=start_exact,
                issue_event_count=len(issues),
                direct_cancel_event_count=len(direct),
                split_start_event_count=len(starts),
                split_finish_event_count=len(finishes),
                split_finish_increment=float(
                    finish.get("incremental_normalized_action_linf", math.inf)
                ),
                maximum_current_utilization=utilization,
                forbidden_count=_forbidden(trace),
                formal_tracking_pass_diagnostic=bool(
                    restart.get("formal_contract_pass")
                ),
                classification="pass" if passed else "scientific_gate_failure",
                passed=passed,
            )
        except Exception as exc:
            row.update(
                result_success=True,
                classification="scientific_gate_failure",
                failure_reason=repr(exc),
                passed=False,
            )
        rows.append(row)
    runtime_failures = [
        row
        for row in rows
        if row.get("classification")
        in {"runtime_or_raw_error", "runtime_or_environment_error"}
    ]
    scientific_failures = [
        row
        for row in rows
        if row.get("classification")
        in {
            "action_schedule_design_failure",
            "scientific_gate_failure",
            "raw_corruption_error",
            "raw_identity_error",
        }
    ]
    primary = bool(
        raw_inventory_exact
        and len(rows) == 9
        and all(bool(row.get("passed")) for row in rows)
    )
    if primary:
        route = ctx.cfg["routes"]["pass"]
    elif scientific_failures or not raw_inventory_exact:
        route = ctx.cfg["routes"]["action_fail"]
    else:
        route = ctx.cfg["routes"]["runtime_incomplete"]
    state = _read(ctx.paths.state)
    manifest = _read(ctx.paths.manifest)
    final = _read(ctx.paths.final)
    internal_path = ctx.paths.analysis / "internal_execution_audit.json"
    snapshot_audit_path = ctx.paths.source_reference / "snapshot_audit.json"
    source_auth_path = ctx.paths.source_reference / "source_authentication.json"
    snapshot_audit = _read(snapshot_audit_path)
    source_auth = _read(source_auth_path)
    log_pass = bool(
        "[T13S24D1R4] 9/9" in log_text
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
    passed = bool(primary and log_pass and consistency)
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
        "pass_count": sum(bool(row.get("passed")) for row in rows),
        "runtime_or_raw_failure_count": len(runtime_failures),
        "scientific_or_action_failure_count": len(scientific_failures),
        "full_horizon_pass_count": sum(
            bool(row.get("runtime_full_horizon_pass")) for row in rows
        ),
        "restart_pass_count": sum(bool(row.get("restart_pass")) for row in rows),
        "causality_pass_count": sum(bool(row.get("causality_pass")) for row in rows),
        "calibration_pass_count": sum(
            bool(row.get("calibration_pass")) for row in rows
        ),
        "source_prefix_action_exact_count": sum(
            bool(row.get("source_prefix_action_exact")) for row in rows
        ),
        "source_prefix_trace_exact_count": sum(
            bool(row.get("source_prefix_trace_exact")) for row in rows
        ),
        "d1r3_split_start_exact_count": sum(
            bool(row.get("d1r3_split_start_exact")) for row in rows
        ),
        "issue_event_count": sum(int(row.get("issue_event_count", 0)) for row in rows),
        "direct_cancel_event_count": sum(
            int(row.get("direct_cancel_event_count", 0)) for row in rows
        ),
        "split_start_event_count": sum(
            int(row.get("split_start_event_count", 0)) for row in rows
        ),
        "split_finish_event_count": sum(
            int(row.get("split_finish_event_count", 0)) for row in rows
        ),
        "maximum_split_finish_increment": max(
            (
                float(row.get("split_finish_increment", 0.0))
                for row in rows
                if math.isfinite(float(row.get("split_finish_increment", math.inf)))
            ),
            default=0.0,
        ),
        "maximum_current_utilization": max(
            (float(row.get("maximum_current_utilization", 0.0)) for row in rows),
            default=0.0,
        ),
        "forbidden_count": sum(int(row.get("forbidden_count", 0)) for row in rows),
        "formal_tracking_pass_count_diagnostic_only": sum(
            bool(row.get("formal_tracking_pass_diagnostic")) for row in rows
        ),
        "state_manifest_final_consistency": consistency,
        "formal_timing_unchanged": True,
        "formal_tracking_is_diagnostic_only": True,
        "probe_trajectories_allowed_in_expert_dataset": False,
        "full_replacement_campaign_execution_authorized": False,
        "mpc_or_learning_authorized": False,
        "route": route,
        "forensic_recomputation_passed": passed,
        "rows": rows,
    }
    output_path = args.output.expanduser().resolve()
    if output_path.exists():
        raise ValueError("D1R4 independent forensic output must be new")
    _write(output_path, output)
    return output


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
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
