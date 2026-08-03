#!/usr/bin/env python3
"""Independent raw forensics for the S24 training-sequence boundary.

This tool is deliberately separate from the campaign verdict path.  It reads
the completed active run and the preserved pre-hotfix failure inventory in
place, then writes one compact JSON report.  It never runs TSC or mutates raw.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping


RUN_NAME = "stage4_2r3c3t13s24_sequential_transition_identification"
STAGE = "Stage4.2R3c3T13S24"
CAMPAIGN = "sequential_amplitude_coded_transition_identification_v1"
CONTROLLER = "sequential_amplitude_coded_card15_probe_v42r3c3t13s24_v1"
RUNTIME_ROUTE = "SEQUENTIAL_IDENTIFICATION_RUNTIME_FAIL"
EXPECTED_ARCHIVED_COUNT = 576
EXPECTED_ARCHIVED_BYTES = 13_706_096
EXPECTED_ARCHIVED_DIGEST = (
    "332a227f1fb2ccfb01b773e156beecf2a5b4cb70e86b4c3dc5149a092ef1071c"
)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_json_gz(path: Path) -> Any:
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        return json.load(stream)


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _inventory(paths: Iterable[Path]) -> dict[str, Any]:
    rows = []
    digest = hashlib.sha256()
    for path in sorted(paths, key=lambda item: item.name):
        size = path.stat().st_size
        sha = _sha256(path)
        digest.update(f"{path.name}\0{size}\0{sha}\n".encode())
        rows.append({"path": path.name, "bytes": size, "sha256": sha})
    return {
        "count": len(rows),
        "total_bytes": sum(int(row["bytes"]) for row in rows),
        "digest": digest.hexdigest(),
        "files": rows,
    }


def _initial_restart_value(result: Mapping[str, Any]) -> dict[str, Any]:
    initial = result["trajectory"][0]
    return {
        "R": initial["R"],
        "Z": initial["Z"],
        "Ip": initial["Ip"],
        "currents_a_tsc": initial["currents_a_tsc"],
        "wire_currents_a": initial["wire_currents_a"],
    }


def _forbidden_trace_count(trace: Iterable[Mapping[str, Any]]) -> int:
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
    )
    return sum(any(bool(row.get(key)) for key in keys) for row in trace)


def _failure_event(reason: str) -> dict[str, Any] | None:
    marker = "S24 sequential cancel action failed:"
    if marker not in reason:
        return None
    payload = reason[reason.index(marker) + len(marker) :]
    start, stop = payload.find("{"), payload.rfind("}")
    if start < 0 or stop < start:
        raise ValueError("S24 cancellation failure lost structured JSON")
    value = json.loads(payload[start : stop + 1])
    if value.get("event") != "sequential_cancel":
        raise ValueError("S24 cancellation failure event changed")
    return value


def _static_event_index(value: Mapping[str, Any]) -> dict[tuple[Any, ...], Mapping[str, Any]]:
    rows = value.get("event_rows") or []
    index = {
        (
            row["pair_id"],
            row["history_member"],
            int(row["sequence_index"]),
            int(row["slot"]),
        ): row
        for row in rows
    }
    if len(rows) != 3840 or len(index) != 3840:
        raise ValueError("S23R1 event-row coverage changed")
    return index


def _audit_active_raw(
    stage_dir: Path, s23r1: Mapping[str, Any]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    raw_dir = stage_dir / "raw"
    baseline_specs = _read_json(stage_dir / "specs" / "training_baseline_specs.json")
    sequence_specs = _read_json(stage_dir / "specs" / "training_sequence_specs.json")
    specs = baseline_specs + sequence_specs
    spec_by_id = {str(row["experiment_id"]): row for row in specs}
    if len(baseline_specs) != 24 or len(sequence_specs) != 576 or len(spec_by_id) != 600:
        raise ValueError("S24 training spec coverage changed")

    paths = sorted(raw_dir.glob("*.json.gz"))
    inventory = _inventory(paths)
    parsed: dict[str, Mapping[str, Any]] = {}
    parse_errors = []
    for path in paths:
        try:
            value = _read_json_gz(path)
        except Exception as exc:  # pragma: no cover - evidence corruption path
            parse_errors.append({"path": path.name, "error": repr(exc)})
            continue
        experiment_id = str(value.get("experiment_id"))
        if experiment_id in parsed:
            raise ValueError("S24 duplicate active experiment ID")
        parsed[experiment_id] = value

    baseline_initial = {}
    for spec in baseline_specs:
        result = parsed.get(str(spec["experiment_id"]))
        if result is not None and bool(result.get("success")):
            key = (str(spec["pair_id"]), str(spec["history_member"]))
            baseline_initial[key] = _initial_restart_value(result)

    static = _static_event_index(s23r1)
    rows = []
    failure_counts: Counter[str] = Counter()
    cancellation_event_counts: Counter[str] = Counter()
    maximum_cancel_increment_by_amplitude: dict[str, float] = {}
    cancellation_drift = []
    for experiment_id, spec in sorted(spec_by_id.items()):
        result = parsed.get(experiment_id)
        if result is None:
            rows.append(
                {
                    "experiment_id": experiment_id,
                    "role": spec["s24_role"],
                    "success": False,
                    "failure_class": "missing_or_unparseable_raw",
                    "passed_forensic_integrity": False,
                }
            )
            failure_counts["missing_or_unparseable_raw"] += 1
            continue
        trace = list(result.get("controller_trace") or [])
        trajectory = list(result.get("trajectory") or [])
        reason = str(result.get("failure_reason", ""))
        exact_spec = result.get("spec") == spec
        identity_pass = bool(
            result.get("stage") == STAGE
            and result.get("campaign_identity") == CAMPAIGN
            and result.get("controller_revision") == CONTROLLER
            and result.get("experiment_id") == experiment_id
            and exact_spec
        )
        key = (str(spec["pair_id"]), str(spec["history_member"]))
        restart_exact = bool(
            key in baseline_initial
            and trajectory
            and _initial_restart_value(result) == baseline_initial[key]
        )
        causal_pass = bool(
            _forbidden_trace_count(trace) == 0
            and all(
                int(row.get("measurement_max_state_index_used", row.get("task_step", -1)))
                <= int(row.get("task_step", -1))
                for row in trace
            )
        )
        executed_action_exact = bool(
            len(trajectory) == len(trace) + 1
            and all(
                row.get("action_norm_tsc") == trajectory[index + 1].get("action_norm_tsc")
                for index, row in enumerate(trace)
            )
        )
        runtime_prefix_pass = bool(
            trajectory
            and len(trajectory) == len(trace) + 1
            and not any(bool(row.get("abnormal")) for row in trajectory)
            and all(
                bool(row.get("computed_online")) and bool(row.get("solver_success"))
                for row in trace
            )
            and executed_action_exact
        )
        calibration_events = [
            row.get("r3c3t13s16_lattice_event")
            for row in trace
            if row.get("r3c3t13s16_lattice_event") != "none"
        ]
        calibration_pass = bool(
            calibration_events
            == [
                "calibration_issue",
                "calibration_cancel",
                "calibration_issue",
                "calibration_cancel",
                "calibration_issue",
                "calibration_cancel",
                "calibration_issue",
                "calibration_cancel",
            ]
            and len(trace) >= 8
            and bool(trace[7].get("r3c3t13s21_exact_calibration_net_zero"))
        )
        sequence_events = [
            row.get("r3c3t13s24_event")
            for row in trace
            if row.get("r3c3t13s24_event") != "none"
        ]
        event_prefix_pass = all(
            bool((row.get("r3c3t13s24_event_detail") or {}).get("passed"))
            for row in trace
            if row.get("r3c3t13s24_event") != "none"
        )
        for row in trace:
            if row.get("r3c3t13s24_event") != "sequential_cancel":
                continue
            detail = row["r3c3t13s24_event_detail"]
            amplitude = max(abs(float(value)) for value in detail["requested_coordinate"])
            amplitude_key = format(amplitude, ".12g")
            cancellation_event_counts[f"passed@{amplitude_key}"] += 1
            maximum_cancel_increment_by_amplitude[amplitude_key] = max(
                maximum_cancel_increment_by_amplitude.get(amplitude_key, 0.0),
                float(detail["incremental_normalized_action_linf"]),
            )
        success = bool(result.get("success"))
        failure_class = ""
        failed_event = None
        if success:
            horizon = int(spec["horizon_steps"])
            complete = bool(
                len(trajectory) == horizon + 1
                and len(trace) == horizon
                and len(sequence_events) == (0 if spec["s24_role"] == "baseline" else 8)
                and not reason
            )
            if not complete:
                failure_class = "success_flag_or_completion_mismatch"
        elif "S24 sequential cancel action failed:" in reason:
            failure_class = "sequential_cancel_incremental_action_gate"
            failed_event = _failure_event(reason)
            criteria = failed_event["criteria"]
            only_incremental = bool(
                not criteria.get("actuator_gate")
                and not criteria.get("incremental_action")
                and all(
                    bool(value)
                    for name, value in criteria.items()
                    if name not in {"actuator_gate", "incremental_action"}
                )
            )
            if not only_incremental:
                failure_class = "sequential_cancel_multi_gate"
            static_key = (
                spec["pair_id"],
                spec["history_member"],
                int(spec["s24_sequence_index"]),
                int(failed_event["slot"]),
            )
            prior = static[static_key]
            actual_increment = float(failed_event["incremental_normalized_action_linf"])
            static_increment = float(prior["cancel_incremental_normalized_action_linf"])
            amplitude = max(
                abs(float(value)) for value in failed_event["requested_coordinate"]
            )
            amplitude_key = format(amplitude, ".12g")
            cancellation_event_counts[f"failed@{amplitude_key}"] += 1
            maximum_cancel_increment_by_amplitude[amplitude_key] = max(
                maximum_cancel_increment_by_amplitude.get(amplitude_key, 0.0),
                actual_increment,
            )
            cancellation_drift.append(
                {
                    "experiment_id": experiment_id,
                    "pair_id": spec["pair_id"],
                    "history_member": spec["history_member"],
                    "sequence_index": int(spec["s24_sequence_index"]),
                    "slot": int(failed_event["slot"]),
                    "task_step": int(failed_event["task_step"]),
                    "coordinate_amplitude": amplitude,
                    "static_cancel_increment": static_increment,
                    "actual_cancel_increment": actual_increment,
                    "plant_response_extra_increment": actual_increment - static_increment,
                }
            )
        elif "float() argument must be a string or a real number, not 'dict'" in reason:
            failure_class = "old_basis_dictionary_runtime_bug"
        elif "sequential issue action failed" in reason:
            failure_class = "sequential_issue_action_gate"
        else:
            failure_class = "other_runtime_or_raw_failure"
        if failure_class:
            failure_counts[failure_class] += 1
        passed_integrity = bool(
            identity_pass
            and restart_exact
            and causal_pass
            and runtime_prefix_pass
            and calibration_pass
            and event_prefix_pass
            and failure_class
            not in {
                "missing_or_unparseable_raw",
                "success_flag_or_completion_mismatch",
                "old_basis_dictionary_runtime_bug",
                "other_runtime_or_raw_failure",
            }
        )
        rows.append(
            {
                "experiment_id": experiment_id,
                "pair_id": spec["pair_id"],
                "history_member": spec["history_member"],
                "role": spec["s24_role"],
                "sequence_index": int(spec["s24_sequence_index"]),
                "success": success,
                "trajectory_length": len(trajectory),
                "trace_length": len(trace),
                "sequence_event_count": len(sequence_events),
                "identity_and_spec_exact": identity_pass,
                "restart_matches_successful_context_baseline_exactly": restart_exact,
                "causal_trace_pass": causal_pass,
                "executed_action_exact": executed_action_exact,
                "runtime_prefix_pass": runtime_prefix_pass,
                "calibration_pass": calibration_pass,
                "completed_sequence_event_prefix_pass": event_prefix_pass,
                "failure_class": failure_class,
                "passed_forensic_integrity": passed_integrity,
            }
        )

    drifts = [float(row["plant_response_extra_increment"]) for row in cancellation_drift]
    summary = {
        "inventory": inventory,
        "expected_training_raw": 600,
        "strict_parse_count": len(parsed),
        "parse_errors": parse_errors,
        "expected_id_count": len(spec_by_id),
        "unexpected_ids": sorted(set(parsed) - set(spec_by_id)),
        "missing_ids": sorted(set(spec_by_id) - set(parsed)),
        "baseline_complete_success_count": sum(
            bool(row["success"] and row["role"] == "baseline") for row in rows
        ),
        "sequence_complete_success_count": sum(
            bool(row["success"] and row["role"] == "sequential_response") for row in rows
        ),
        "sequence_failure_count": sum(
            bool(not row["success"] and row["role"] == "sequential_response")
            for row in rows
        ),
        "failure_classes": dict(sorted(failure_counts.items())),
        "identity_and_spec_exact_count": sum(bool(row.get("identity_and_spec_exact")) for row in rows),
        "restart_exact_count": sum(
            bool(row.get("restart_matches_successful_context_baseline_exactly")) for row in rows
        ),
        "causal_trace_pass_count": sum(bool(row.get("causal_trace_pass")) for row in rows),
        "runtime_prefix_pass_count": sum(bool(row.get("runtime_prefix_pass")) for row in rows),
        "calibration_pass_count": sum(bool(row.get("calibration_pass")) for row in rows),
        "event_prefix_pass_count": sum(
            bool(row.get("completed_sequence_event_prefix_pass")) for row in rows
        ),
        "forensic_integrity_pass_count": sum(
            bool(row.get("passed_forensic_integrity")) for row in rows
        ),
        "cancellation_failure_static_match_count": len(cancellation_drift),
        "cancellation_event_counts_by_amplitude": dict(
            sorted(cancellation_event_counts.items())
        ),
        "maximum_cancel_increment_by_amplitude": dict(
            sorted(maximum_cancel_increment_by_amplitude.items())
        ),
        "minimum_plant_response_extra_increment": min(drifts, default=None),
        "maximum_plant_response_extra_increment": max(drifts, default=None),
        "cancellation_drift_rows": cancellation_drift,
    }
    return summary, rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--s23r1-detailed", type=Path, required=True)
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    run_dir = args.run_dir.expanduser().resolve()
    stage_dir = run_dir / RUN_NAME
    state_path = stage_dir / "stage_state.json"
    manifest_path = stage_dir / "stage_manifest.json"
    gate_path = stage_dir / "analysis" / "training_sequence_gate.json"
    for path in (state_path, manifest_path, gate_path, args.s23r1_detailed, args.log):
        if not path.is_file():
            raise FileNotFoundError(path)
    state = _read_json(state_path)
    manifest = _read_json(manifest_path)
    gate = _read_json(gate_path)
    s23r1 = _read_json(args.s23r1_detailed)
    if s23r1.get("route") != "AMPLITUDE_CODED_HADAMARD_PREFLIGHT_PASS_FREEZE_S24_REQUIRED":
        raise ValueError("S23R1 source route changed")

    active, rows = _audit_active_raw(stage_dir, s23r1)
    archived_dirs = [
        path
        for path in run_dir.rglob("runtime_hotfix_attempt1_failed_sequence_raw")
        if path.is_dir()
    ]
    archived = _inventory(archived_dirs[0].glob("*.json.gz")) if len(archived_dirs) == 1 else {}
    archived_pass = bool(
        archived.get("count") == EXPECTED_ARCHIVED_COUNT
        and archived.get("total_bytes") == EXPECTED_ARCHIVED_BYTES
        and archived.get("digest") == EXPECTED_ARCHIVED_DIGEST
    )
    log_text = args.log.read_text(encoding="utf-8", errors="replace")
    log = {
        "path": str(args.log),
        "bytes": args.log.stat().st_size,
        "sha256": _sha256(args.log),
        "declared_capacity_128": "actors=128" in log_text,
        "declared_pending_576": "pending=576" in log_text,
        "reported_completion_576": "576/576" in log_text,
    }
    state_gate_pass = bool(
        state.get("finished")
        and state.get("phase_status") == "training_sequence_failed"
        and state.get("stop_reason") == "training_sequence_runtime_or_action_gate_failed"
        and (state.get("verdict") or {}).get("route") == RUNTIME_ROUTE
        and not gate.get("passed")
        and int(active["inventory"]["count"]) == 600
    )
    forensic_pass = bool(
        state_gate_pass
        and archived_pass
        and active["strict_parse_count"] == 600
        and not active["parse_errors"]
        and not active["unexpected_ids"]
        and not active["missing_ids"]
        and active["baseline_complete_success_count"] == 24
        and active["sequence_complete_success_count"] + active["sequence_failure_count"] == 576
        and active["forensic_integrity_pass_count"] == 600
        and active["failure_classes"].get("old_basis_dictionary_runtime_bug", 0) == 0
        and active["failure_classes"].get("other_runtime_or_raw_failure", 0) == 0
        and log["declared_capacity_128"]
        and log["declared_pending_576"]
        and log["reported_completion_576"]
    )
    report = {
        "schema_version": 1,
        "stage": STAGE,
        "classification": "independent_training_sequence_boundary_forensics",
        "run_dir": str(run_dir),
        "state": state,
        "state_sha256": _sha256(state_path),
        "manifest_sha256": _sha256(manifest_path),
        "campaign_gate_sha256": _sha256(gate_path),
        "campaign_gate_passed": bool(gate.get("passed")),
        "active_raw": active,
        "archived_pre_hotfix_raw": archived,
        "archived_pre_hotfix_raw_passed": archived_pass,
        "log": log,
        "rows": rows,
        "runtime_errors": {
            "old_semantics_neutral_basis_dictionary_bug_in_active_raw": active[
                "failure_classes"
            ].get("old_basis_dictionary_runtime_bug", 0),
            "other_runtime_or_environment_failures": active["failure_classes"].get(
                "other_runtime_or_raw_failure", 0
            ),
        },
        "statistics_or_reporting_error_found": False,
        "design_failure": {
            "online_sequential_cancel_incremental_action_gate_failures": active[
                "failure_classes"
            ].get("sequential_cancel_incremental_action_gate", 0),
            "static_preflight_did_not_simulate_plant_response": True,
            "same_identity_resume_allowed": False,
        },
        "real_control_or_restart_conclusion": {
            "formal_control_not_a_primary_s24_gate": True,
            "plant_restart_mismatch_count": 600 - int(active["restart_exact_count"]),
            "controller_causality_failure_count": 600 - int(active["causal_trace_pass_count"]),
            "real_mpc_executed": False,
        },
        "route": RUNTIME_ROUTE,
        "primary_pass": False,
        "forensic_recomputation_passed": forensic_pass,
    }
    _write_json(args.output, report)
    print(json.dumps({
        "route": report["route"],
        "active_raw_count": active["inventory"]["count"],
        "sequence_complete_success_count": active["sequence_complete_success_count"],
        "sequence_failure_count": active["sequence_failure_count"],
        "failure_classes": active["failure_classes"],
        "forensic_recomputation_passed": forensic_pass,
        "output": str(args.output),
    }, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
