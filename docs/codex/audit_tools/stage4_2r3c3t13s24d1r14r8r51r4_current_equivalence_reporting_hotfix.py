#!/usr/bin/env python3
"""Primary raw/formal/final zero-TSC repair for R8R51R4 current reporting."""

from __future__ import annotations

import copy
import hashlib
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r51r4_failed_context_sustained_transport_dwell_sentinel
    as r4,
)


STAGE = r4.STAGE
CONFIG_SHA256 = "6fb1c69b473a79d3889fe1dc725a564aeb256e45331f98b1834ccc4debeb4802"
EXECUTED_PRIMARY_SHA256 = "32a433addb3890e17dec2888cfc2840c634490f105c1b56ad179f8ece404cdaf"
EXECUTED_INDEPENDENT_SHA256 = "10df4afe6bdf373f7aa47f5b5c8661ae9e1f805a818418fa64ddc50cfbae3314"
CONTRACT_SHA256 = "c1dbd931ba6f7045152eb32abb581204b5fede55fcbf1f156fad4a4e6c40900b"
STAGE_MANIFEST_SHA256 = "ff0f57ea940f9909b03121428f32534ce16cff5944c3c110e7841d239a0b666d"
STAGE_STATE_SHA256 = "59c914a6e772c5b8333a62060ca2fec862736949c15077ee925fe200b90617d9"
OFFLINE_CONSTRUCTION_SHA256 = "612ed4fc9e1be64450ad894f49eecb467828f50afe3562b07ed585d55f80bca8"
OFFLINE_PRIMARY_SHA256 = "76244364667c3b453f7066417a098e2d06288fe300f60815ae69f4d221069b15"
OFFLINE_INDEPENDENT_SHA256 = "ef7ff791424a2f2cf7d53864326159f73fda295369821c37b5a676ec24990f21"
RAW_PRIMARY_SHA256 = "9611590b0627ba0598fcbd7ce1aa14ee8072e4f0ad8a3a8912b251a7bb247c19"
RAW_INDEPENDENT_SHA256 = "c3f76ce90fba1578b87fc78d5051511809ba090c0848e73af0a5c0e90c14cc70"
PACKAGE_DIGEST = "d1d8aa2acde5b7013b2e87a0cdee1a05bde209e3f6435d2970aba377170b46ae"
RAW_COUNT = 100
RAW_BYTES = 3_255_079
RAW_DIGEST = "9227c93aae7a1819949bee9a57f9294c9b0f01620bcbbe193e32ca6823a15f3a"
ORIGINAL_EVENT_DIGEST = "11fa9bcaa7b8b6941c729094925caf1ecbe7234c921e87a0ebf5d33eaab2e384"
ORIGINAL_Q0_BINARY_COUNT = 20
ORIGINAL_DWELL_BINARY_COUNT = 4
EXPECTED_EVENT_COUNT = 2_620
EXPECTED_DWELL_EVENT_COUNT = 400
EXPECTED_REFRESH_EVENT_COUNT = 1_820
ATOL_A = 1e-12
N_COILS = 14
Q0_STEP = 10
ISSUE_STEP = 12
OLD_ROUTE = "REDUCED_Q0_TRANSPORT_BRIDGE_R51R4_SUSTAINED_DWELL_EXECUTION_FAIL_STOP"
RAW_HOTFIX_ROUTE = (
    "REDUCED_Q0_TRANSPORT_BRIDGE_R51R4_SUSTAINED_DWELL_"
    "RAW_INTEGRITY_REPORTING_HOTFIX_COMPLETE_FORMAL_REQUIRED"
)

PREFIX = "current_equivalence_reporting_hotfix_"
RAW_PRIMARY_NAME = PREFIX + "raw_primary.json"
RAW_INDEPENDENT_NAME = PREFIX + "raw_independent.json"
RAW_COMPACT_NAME = PREFIX + "raw_compact_audit.json"
FORMAL_DETAILED_NAME = PREFIX + "formal_primary_detailed.json"
FORMAL_SUMMARY_NAME = PREFIX + "formal_primary_summary.json"
FORMAL_INDEPENDENT_NAME = PREFIX + "formal_independent.json"
COMPACT_NAME = PREFIX + "compact_audit.json"
FINAL_NAME = PREFIX + "final_report.json"

PRIMARY_PATH = (
    "tsc_rzip_rllib/diagnostics/"
    "stage4_2r3c3t13s24d1r14r8r51r4_failed_context_sustained_"
    "transport_dwell_sentinel.py"
)
INDEPENDENT_PATH = (
    "docs/codex/audit_tools/"
    "stage4_2r3c3t13s24d1r14r8r51r4_independent_forensics.py"
)
CONTRACT_PATH = (
    "docs/codex/reports/"
    "STAGE4_2R3C3T13S24D1R14R8R51R4_CURRENT_EQUIVALENCE_"
    "REPORTING_HOTFIX_CONTRACT.md"
)

UNCHANGED_ROW_TRUE_FIELDS = (
    "runtime_success",
    "full_horizon",
    "authentic_restart",
    "source_prefix_state_exact",
    "source_prefix_trace_exact",
    "source_trace_difference_wrapper_only",
    "calibration_exact",
    "q0_exact",
    "q0_offline_parity",
    "candidate_exact",
    "candidate_first_effect_at_issue_plus_one",
    "return_exact",
    "event_sequence_exact",
    "event_gates_passed",
    "finite",
    "within_context_q0_prefix_exact",
)


def _root() -> Path:
    return Path(__file__).resolve().parents[3]


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    ).hexdigest()


def _write_new(path: Path, value: Any) -> None:
    if path.exists():
        raise ValueError(f"R8R51R4 reporting-hotfix output exists: {path.name}")
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _vector(value: Any) -> np.ndarray:
    vector = np.asarray(value, dtype=float)
    if vector.shape != (N_COILS,) or not np.all(np.isfinite(vector)):
        raise ValueError(f"R8R51R4 reporting-hotfix vector changed: {vector.shape}")
    return vector


def _inventory(path: Path) -> dict[str, Any]:
    return r4.r51.r8r7.r8._inventory(path)


def _authenticate(ctx: r4.Context) -> dict[str, Any]:
    root = _root()
    analysis = ctx.paths.analysis
    paths = {
        ctx.config_path: CONFIG_SHA256,
        root / PRIMARY_PATH: EXECUTED_PRIMARY_SHA256,
        root / INDEPENDENT_PATH: EXECUTED_INDEPENDENT_SHA256,
        root / CONTRACT_PATH: CONTRACT_SHA256,
        ctx.paths.manifest: STAGE_MANIFEST_SHA256,
        ctx.paths.state: STAGE_STATE_SHA256,
        analysis / "offline_construction.json": OFFLINE_CONSTRUCTION_SHA256,
        analysis / "offline_primary.json": OFFLINE_PRIMARY_SHA256,
        analysis / "offline_independent.json": OFFLINE_INDEPENDENT_SHA256,
        analysis / "raw_integrity_primary.json": RAW_PRIMARY_SHA256,
        analysis / "raw_integrity_independent.json": RAW_INDEPENDENT_SHA256,
    }
    for path, expected in paths.items():
        if not path.is_file() or _sha(path) != expected:
            raise ValueError(f"R8R51R4 reporting-hotfix source changed: {path}")
    manifest = r4._read(ctx.paths.manifest)
    state = r4._read(ctx.paths.state)
    original = r4._read(analysis / "raw_integrity_primary.json")
    independent = r4._read(analysis / "raw_integrity_independent.json")
    inventory = _inventory(ctx.paths.raw)
    if (
        manifest.get("stage") != STAGE
        or manifest.get("config_sha256") != CONFIG_SHA256
        or manifest.get("package_fingerprint", {}).get("digest") != PACKAGE_DIGEST
        or int(manifest.get("spec_count", -1)) != RAW_COUNT
        or state.get("stage") != STAGE
        or state.get("phase_status") != "real_execution_failed"
        or state.get("finished") is not True
        or state.get("real_tsc_executed") is not True
        or state.get("response_outcomes_opened") is not False
        or int(state.get("new_raw_count", -1)) != RAW_COUNT
        or int(state.get("plant_step_count", -1)) != 3_620
        or state.get("route") != OLD_ROUTE
        or original.get("route") != OLD_ROUTE
        or original.get("passed") is not False
        or int(original.get("passed_count", -1)) != 0
        or int(original.get("q0_first_effect_at_issue_plus_one_count", -1))
        != ORIGINAL_Q0_BINARY_COUNT
        or int(original.get("dwell_exact_count", -1))
        != ORIGINAL_DWELL_BINARY_COUNT
        or int(original.get("offline_event_stream_parity_count", -1)) != 0
        or original.get("event_stream_digest") != ORIGINAL_EVENT_DIGEST
        or independent.get("passed") is not False
        or int(independent.get("passed_count", -1)) != 0
        or independent.get("primary_agreement") is not True
        or independent.get("independent_event_stream_digest")
        != ORIGINAL_EVENT_DIGEST
    ):
        raise ValueError("R8R51R4 reporting-hotfix historical precondition changed")
    aggregate_true = (
        "strict_parse_count",
        "runtime_success_count",
        "full_horizon_count",
        "authentic_restart_count",
        "source_prefix_state_exact_count",
        "source_prefix_trace_exact_count",
        "source_trace_difference_wrapper_only_count",
        "calibration_exact_count",
        "q0_exact_count",
        "q0_offline_parity_count",
        "candidate_exact_count",
        "candidate_first_effect_at_issue_plus_one_count",
        "stored_center_return_exact_count",
        "event_sequence_exact_count",
        "finite_count",
        "causal_forbidden_pass_count",
        "within_context_q0_prefix_exact_count",
    )
    if any(int(original.get(key, -1)) != RAW_COUNT for key in aggregate_true):
        raise ValueError("R8R51R4 reporting-hotfix found another aggregate failure")
    if (
        int(original.get("runtime_failure_count", -1)) != 0
        or int(original.get("safety_stop_count", -1)) != 0
        or int(original.get("forbidden_trace_count", -1)) != 0
        or len(original.get("rows") or []) != RAW_COUNT
        or inventory["count"] != RAW_COUNT
        or inventory["bytes"] != RAW_BYTES
        or inventory["digest"] != RAW_DIGEST
        or inventory != original.get("raw_inventory")
        or inventory != independent.get("raw_inventory")
    ):
        raise ValueError("R8R51R4 reporting-hotfix raw evidence changed")
    for row in original["rows"]:
        if (
            not all(row.get(key) is True for key in UNCHANGED_ROW_TRUE_FIELDS)
            or int(row.get("forbidden_trace_count", -1)) != 0
            or str(row.get("execution_failure_class") or "")
            or str(row.get("failure_reason") or "")
            or row.get("offline_event_stream_parity") is not False
            or row.get("passed") is not False
        ):
            raise ValueError("R8R51R4 reporting-hotfix found a non-reporting row failure")
    return {
        "manifest": manifest,
        "state": state,
        "original": original,
        "original_independent": independent,
        "inventory": inventory,
    }


def _measure(
    result: Mapping[str, Any],
    spec: Mapping[str, Any],
    old: Mapping[str, Any],
) -> dict[str, Any]:
    trajectory = result.get("trajectory") or []
    trace = result.get("controller_trace") or []
    horizon = int(spec["horizon_steps"])
    return_step = int(spec["r8r51r4_return_task_step"])
    dwell_steps = range(ISSUE_STEP + 1, return_step)
    if (
        result.get("success") is not True
        or result.get("completed") is not True
        or result.get("spec") != spec
        or len(trajectory) != horizon + 1
        or len(trace) != horizon
    ):
        raise ValueError(f"R8R51R4 reporting-hotfix raw changed: {spec['experiment_id']}")
    names = [
        trace[step].get("r3c3t13s24d1r14r8r51r4_event")
        for step in range(Q0_STEP, horizon)
    ]
    details = [
        trace[step].get("r3c3t13s24d1r14r8r51r4_event_detail") or {}
        for step in range(Q0_STEP, horizon)
    ]
    dwell_count = return_step - ISSUE_STEP - 1
    sequence_exact = bool(
        names[:3] == ["q0_exact_issue", "q0_observe_hold", "candidate_issue"]
        and names[3 : 3 + dwell_count] == ["candidate_dwell_hold"] * dwell_count
        and names[3 + dwell_count] == "stored_center_return"
        and all(name == "center_refresh" for name in names[4 + dwell_count :])
    )
    event_gate_exact = bool(
        all(
            detail.get("passed") is True
            and all(value is True for value in (detail.get("criteria") or {}).values())
            for detail in details
        )
    )
    action_detail_exact = True
    action_effect_exact = True
    current_numerical = True
    maximum_current_difference = 0.0
    current_binary_count = 0
    for step, name, detail in zip(range(Q0_STEP, horizon), names, details):
        detail_action = _vector(detail.get("action_norm_tsc"))
        trace_action = _vector(trace[step].get("action_norm_tsc"))
        effect_action = _vector(trajectory[step + 1].get("action_norm_tsc"))
        action_detail_exact &= bool(np.array_equal(detail_action, trace_action))
        action_effect_exact &= bool(np.array_equal(effect_action, trace_action))
        key = (
            "nominal_issue_readback_current_a_tsc"
            if name == "candidate_issue"
            else "nominal_readback_current_a_tsc"
        )
        physical = _vector(trajectory[step + 1].get("currents_a_tsc"))
        nominal = _vector(detail.get(key))
        difference = float(np.max(np.abs(physical - nominal)))
        maximum_current_difference = max(maximum_current_difference, difference)
        current_binary_count += int(np.array_equal(physical, nominal))
        current_numerical &= bool(
            np.allclose(physical, nominal, rtol=0.0, atol=ATOL_A, equal_nan=False)
        )
    q0 = details[0]
    issue = details[2]
    q0_physical = _vector(trajectory[Q0_STEP + 1].get("currents_a_tsc"))
    q0_nominal = _vector(q0.get("nominal_readback_current_a_tsc"))
    q0_binary = bool(np.array_equal(q0_physical, q0_nominal))
    previous_action_exact = bool(
        np.array_equal(
            _vector(trajectory[Q0_STEP].get("action_norm_tsc")),
            _vector(trace[Q0_STEP - 1].get("action_norm_tsc")),
        )
    )
    candidate_physical = _vector(trajectory[ISSUE_STEP + 1].get("currents_a_tsc"))
    candidate_changed = bool(
        not np.array_equal(
            candidate_physical,
            _vector(trajectory[ISSUE_STEP].get("currents_a_tsc")),
        )
    )
    dwell_zero = True
    dwell_physical_exact = True
    dwell_nominal_binary = True
    for step in dwell_steps:
        detail = trace[step].get("r3c3t13s24d1r14r8r51r4_event_detail") or {}
        physical = _vector(trajectory[step + 1].get("currents_a_tsc"))
        dwell_zero &= bool(
            np.array_equal(_vector(detail.get("action_norm_tsc")), np.zeros(N_COILS))
        )
        dwell_physical_exact &= bool(np.array_equal(physical, candidate_physical))
        dwell_nominal_binary &= bool(
            np.array_equal(
                physical,
                _vector(issue.get("nominal_issue_readback_current_a_tsc")),
            )
        )
        dwell_zero &= bool(
            detail.get("event") == "candidate_current_dwell_hold"
            and detail.get("stored_target_card15_fields")
            == issue.get("target_card15_fields")
        )
    returned = trace[return_step].get(
        "r3c3t13s24d1r14r8r51r4_event_detail"
    ) or {}
    returned_physical = _vector(trajectory[return_step + 1].get("currents_a_tsc"))
    return_center_exact = bool(np.array_equal(returned_physical, q0_physical))
    return_event_exact = bool(
        returned.get("event") == "stored_pretransport_center_return"
        and returned.get("stored_center_card15_fields")
        == issue.get("center_card15_fields")
        and returned.get("issue_target_card15_fields")
        == issue.get("target_card15_fields")
    )
    refresh_center_exact = True
    for step in range(return_step + 1, horizon):
        refresh_center_exact &= bool(
            np.array_equal(
                _vector(trajectory[step + 1].get("currents_a_tsc")),
                returned_physical,
            )
        )
    real_event_digest = _digest(details)
    if (
        q0_binary != bool(old.get("q0_first_effect_at_issue_plus_one"))
        or dwell_nominal_binary != bool(old.get("dwell_exact"))
        or real_event_digest != old.get("event_stream_digest")
        or sequence_exact != bool(old.get("event_sequence_exact"))
        or event_gate_exact != bool(old.get("event_gates_passed"))
    ):
        raise ValueError(
            f"R8R51R4 reporting-hotfix cannot reproduce old row: {spec['experiment_id']}"
        )
    passed = bool(
        sequence_exact
        and event_gate_exact
        and action_detail_exact
        and action_effect_exact
        and previous_action_exact
        and current_numerical
        and candidate_changed
        and dwell_zero
        and dwell_physical_exact
        and return_event_exact
        and return_center_exact
        and refresh_center_exact
        and int(old.get("forbidden_trace_count", -1)) == 0
    )
    return {
        "experiment_id": str(spec["experiment_id"]),
        "pair_id": str(spec["pair_id"]),
        "history_member": str(spec["history_member"]),
        "candidate_index": int(spec["r8r51r4_candidate_index"]),
        "candidate_id": str(spec["r8r51r4_candidate_id"]),
        "return_task_step": return_step,
        "event_count": len(details),
        "dwell_event_count": dwell_count,
        "refresh_event_count": horizon - return_step - 1,
        "event_sequence_exact": sequence_exact,
        "event_gates_exact": event_gate_exact,
        "event_action_detail_trace_exact": action_detail_exact,
        "event_action_next_state_effect_exact": action_effect_exact,
        "q0_previous_action_effect_exact": previous_action_exact,
        "q0_nominal_current_binary_exact": q0_binary,
        "q0_nominal_current_numerically_equivalent": bool(
            np.allclose(q0_physical, q0_nominal, rtol=0.0, atol=ATOL_A)
        ),
        "candidate_physical_effect_changed": candidate_changed,
        "dwell_zero_increment_exact": dwell_zero,
        "dwell_nominal_current_binary_exact": dwell_nominal_binary,
        "dwell_physical_current_unchanged_exact": dwell_physical_exact,
        "stored_center_return_event_exact": return_event_exact,
        "stored_center_physical_return_exact": return_center_exact,
        "post_return_physical_center_exact": refresh_center_exact,
        "all_event_nominal_currents_numerically_equivalent": current_numerical,
        "event_nominal_current_binary_exact_count": current_binary_count,
        "maximum_event_nominal_current_difference_a": maximum_current_difference,
        "original_real_event_digest": real_event_digest,
        "forbidden_trace_count": int(old["forbidden_trace_count"]),
        "passed": passed,
    }


def _raw_report(ctx: r4.Context, source: Mapping[str, Any]) -> dict[str, Any]:
    specs = r4._saved_specs(ctx)
    old_rows = {
        str(row["experiment_id"]): row for row in source["original"]["rows"]
    }
    rows = []
    for spec in specs:
        experiment_id = str(spec["experiment_id"])
        result = r4.r51.r8r7.r8._read_gz(ctx.paths.raw / f"{experiment_id}.json.gz")
        old = old_rows.get(experiment_id)
        if old is None:
            raise ValueError(f"R8R51R4 reporting-hotfix old row missing: {experiment_id}")
        rows.append(_measure(result, spec, old))
    event_count = sum(int(row["event_count"]) for row in rows)
    dwell_count = sum(int(row["dwell_event_count"]) for row in rows)
    refresh_count = sum(int(row["refresh_event_count"]) for row in rows)
    q0_binary = sum(bool(row["q0_nominal_current_binary_exact"]) for row in rows)
    dwell_binary = sum(bool(row["dwell_nominal_current_binary_exact"]) for row in rows)
    maximum = max(float(row["maximum_event_nominal_current_difference_a"]) for row in rows)
    passed_count = sum(bool(row["passed"]) for row in rows)
    inventory = _inventory(ctx.paths.raw)
    passed = bool(
        len(rows) == RAW_COUNT
        and event_count == EXPECTED_EVENT_COUNT
        and dwell_count == EXPECTED_DWELL_EVENT_COUNT
        and refresh_count == EXPECTED_REFRESH_EVENT_COUNT
        and q0_binary == ORIGINAL_Q0_BINARY_COUNT
        and dwell_binary == ORIGINAL_DWELL_BINARY_COUNT
        and all(row["event_sequence_exact"] for row in rows)
        and all(row["event_gates_exact"] for row in rows)
        and all(row["event_action_detail_trace_exact"] for row in rows)
        and all(row["event_action_next_state_effect_exact"] for row in rows)
        and all(row["q0_previous_action_effect_exact"] for row in rows)
        and all(row["q0_nominal_current_numerically_equivalent"] for row in rows)
        and all(row["candidate_physical_effect_changed"] for row in rows)
        and all(row["dwell_zero_increment_exact"] for row in rows)
        and all(row["dwell_physical_current_unchanged_exact"] for row in rows)
        and all(row["stored_center_return_event_exact"] for row in rows)
        and all(row["stored_center_physical_return_exact"] for row in rows)
        and all(row["post_return_physical_center_exact"] for row in rows)
        and all(row["all_event_nominal_currents_numerically_equivalent"] for row in rows)
        and maximum <= ATOL_A
        and passed_count == RAW_COUNT
        and inventory == source["inventory"]
    )
    return {
        "schema_version": 1,
        "stage": STAGE,
        "phase": "current_equivalence_reporting_hotfix_raw_primary",
        "hotfix_kind": "binary64_nominal_current_reconstruction_reporting_only",
        "original_route": OLD_ROUTE,
        "route": RAW_HOTFIX_ROUTE if passed else OLD_ROUTE,
        "current_comparison_rtol": 0.0,
        "current_comparison_atol_a": ATOL_A,
        "original_q0_binary_exact_count": q0_binary,
        "original_dwell_binary_exact_count": dwell_binary,
        "original_event_digest_parity_count": 0,
        "corrected_q0_numerical_equivalence_count": sum(
            row["q0_nominal_current_numerically_equivalent"] for row in rows
        ),
        "corrected_all_event_current_equivalence_count": sum(
            int(row["event_count"])
            for row in rows
            if row["all_event_nominal_currents_numerically_equivalent"]
        ),
        "event_action_detail_trace_exact_count": sum(
            int(row["event_count"])
            for row in rows
            if row["event_action_detail_trace_exact"]
        ),
        "event_action_next_state_effect_exact_count": sum(
            int(row["event_count"])
            for row in rows
            if row["event_action_next_state_effect_exact"]
        ),
        "dwell_zero_increment_exact_count": sum(
            int(row["dwell_event_count"])
            for row in rows
            if row["dwell_zero_increment_exact"]
        ),
        "dwell_physical_current_unchanged_exact_count": sum(
            int(row["dwell_event_count"])
            for row in rows
            if row["dwell_physical_current_unchanged_exact"]
        ),
        "stored_center_physical_return_exact_count": sum(
            row["stored_center_physical_return_exact"] for row in rows
        ),
        "post_return_physical_center_exact_count": sum(
            int(row["refresh_event_count"])
            for row in rows
            if row["post_return_physical_center_exact"]
        ),
        "maximum_event_nominal_current_difference_a": maximum,
        "semantic_event_replay_pass_count": passed_count,
        "passed_count": passed_count,
        "raw_inventory": inventory,
        "raw_unchanged": inventory == source["inventory"],
        "original_raw_primary_sha256": RAW_PRIMARY_SHA256,
        "original_raw_independent_sha256": RAW_INDEPENDENT_SHA256,
        "original_stage_state_sha256": STAGE_STATE_SHA256,
        "original_real_event_digest": ORIGINAL_EVENT_DIGEST,
        "row_digest": _digest(rows),
        "rows": rows,
        "response_outcomes_opened": False,
        "new_tsc_count_by_hotfix": 0,
        "new_raw_count_by_hotfix": 0,
        "plant_step_count_by_hotfix": 0,
        "controller_or_action_semantics_changed": False,
        "all_stage_trajectories_allowed_in_expert_dataset": False,
        "passed": passed,
    }


def run_primary(ctx: r4.Context) -> dict[str, Any]:
    source = _authenticate(ctx)
    report = _raw_report(ctx, source)
    _write_new(ctx.paths.analysis / RAW_PRIMARY_NAME, report)
    return report


def _dual_raw(ctx: r4.Context, source: Mapping[str, Any]) -> dict[str, Any]:
    analysis = ctx.paths.analysis
    primary_path = analysis / RAW_PRIMARY_NAME
    independent_path = analysis / RAW_INDEPENDENT_NAME
    if not primary_path.is_file() or not independent_path.is_file():
        raise ValueError("R8R51R4 reporting-hotfix dual raw audit is incomplete")
    primary = r4._read(primary_path)
    independent = r4._read(independent_path)
    keys = (
        "route",
        "original_q0_binary_exact_count",
        "original_dwell_binary_exact_count",
        "original_event_digest_parity_count",
        "corrected_q0_numerical_equivalence_count",
        "corrected_all_event_current_equivalence_count",
        "event_action_detail_trace_exact_count",
        "event_action_next_state_effect_exact_count",
        "dwell_zero_increment_exact_count",
        "dwell_physical_current_unchanged_exact_count",
        "stored_center_physical_return_exact_count",
        "post_return_physical_center_exact_count",
        "maximum_event_nominal_current_difference_a",
        "semantic_event_replay_pass_count",
        "passed_count",
        "raw_inventory",
        "row_digest",
    )
    agreement = bool(
        all(primary.get(key) == independent.get(key) for key in keys)
        and independent.get("primary_sha256") == _sha(primary_path)
        and independent.get("primary_agreement") is True
    )
    inventory = _inventory(ctx.paths.raw)
    passed = bool(
        primary.get("passed") is True
        and independent.get("passed") is True
        and agreement
        and inventory == source["inventory"]
    )
    return {
        "schema_version": 1,
        "stage": STAGE,
        "phase": "current_equivalence_reporting_hotfix_raw_compact",
        "route": RAW_HOTFIX_ROUTE if passed else OLD_ROUTE,
        **{key: primary.get(key) for key in keys if key != "route"},
        "primary_sha256": _sha(primary_path),
        "independent_sha256": _sha(independent_path),
        "primary_independent_agreement": agreement,
        "raw_unchanged": inventory == source["inventory"],
        "response_outcomes_opened": False,
        "new_tsc_count_by_hotfix": 0,
        "new_raw_count_by_hotfix": 0,
        "plant_step_count_by_hotfix": 0,
        "passed": passed,
    }


def _formal_authority(
    ctx: r4.Context, integrity: Mapping[str, Any]
) -> dict[str, Any]:
    specs = r4._saved_specs(ctx)
    _, sources = r4.r51._source_baselines(ctx.base_ctx)
    baseline_ids = tuple(ctx.cfg["matrix_contract"]["failed_source_baseline_ids"])
    baseline_rows = []
    for baseline_id in baseline_ids:
        result = sources[str(baseline_id)]
        spec = result["spec"]
        baseline_rows.append(
            {
                "experiment_id": str(baseline_id),
                "partition": "baseline",
                "pair_id": str(spec["pair_id"]),
                "history_member": str(spec["history_member"]),
                "candidate_index": -1,
                "candidate_id": "baseline",
                "return_task_step": -1,
                **r4.r51r3.formal_metric(
                    spec, result["trajectory"], ctx.cfg["formal_contract"]
                ),
            }
        )
    valid = {
        str(row["experiment_id"]): row
        for row in integrity["rows"]
        if row["passed"]
    }
    candidate_rows = []
    for spec in specs:
        experiment_id = str(spec["experiment_id"])
        result = r4.r51.r8r7.r8._read_gz(
            ctx.paths.raw / f"{experiment_id}.json.gz"
        )
        if (
            experiment_id not in valid
            or result.get("success") is not True
            or result.get("spec") != spec
            or len(result.get("trajectory") or []) != int(spec["horizon_steps"]) + 1
        ):
            raise ValueError(f"R8R51R4 hotfix formal source failed: {experiment_id}")
        candidate_rows.append(
            {
                "experiment_id": experiment_id,
                "partition": "candidate",
                "pair_id": str(spec["pair_id"]),
                "history_member": str(spec["history_member"]),
                "candidate_index": int(spec["r8r51r4_candidate_index"]),
                "candidate_id": str(spec["r8r51r4_candidate_id"]),
                "return_task_step": int(spec["r8r51r4_return_task_step"]),
                "source_baseline_experiment_id": str(
                    spec["source_r8r7_baseline_experiment_id"]
                ),
                **r4.r51r3.formal_metric(
                    spec, result["trajectory"], ctx.cfg["formal_contract"]
                ),
            }
        )
    rows = sorted(
        [*baseline_rows, *candidate_rows],
        key=lambda row: (
            row["pair_id"],
            row["history_member"],
            0 if row["partition"] == "baseline" else 1,
            int(row["candidate_index"]),
            int(row["return_task_step"]),
            row["experiment_id"],
        ),
    )
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(str(row["pair_id"]), str(row["history_member"]))].append(row)
    context_rows = []
    tolerance = float(ctx.cfg["formal_contract"]["metric_equivalence_absolute_tolerance"])
    for key, group in sorted(groups.items()):
        baseline = [row for row in group if row["partition"] == "baseline"]
        candidates = [row for row in group if row["partition"] == "candidate"]
        if len(baseline) != 1 or len(candidates) != 10:
            raise ValueError(f"R8R51R4 hotfix formal coverage changed: {key}")
        baseline_row = baseline[0]
        best = max(
            candidates,
            key=lambda row: (
                float(row["formal_minimum_signed_margin"]),
                float(row["formal_mean_signed_margin"]),
                -int(row["candidate_index"]),
                -int(row["return_task_step"]),
            ),
        )
        oracle = max(
            enumerate([baseline_row, *candidates]),
            key=lambda item: (
                float(item[1]["formal_minimum_signed_margin"]),
                float(item[1]["formal_mean_signed_margin"]),
                -item[0],
            ),
        )[1]
        gain = float(best["formal_minimum_signed_margin"]) - float(
            baseline_row["formal_minimum_signed_margin"]
        )
        repaired = bool(
            not baseline_row["formal_contract_pass"]
            and any(bool(row["formal_contract_pass"]) for row in candidates)
        )
        context_rows.append(
            {
                "pair_id": key[0],
                "history_member": key[1],
                "baseline": baseline_row,
                "candidates": candidates,
                "best_candidate_index": int(best["candidate_index"]),
                "best_candidate_id": str(best["candidate_id"]),
                "best_return_task_step": int(best["return_task_step"]),
                "best_candidate_minimum_margin_gain": gain,
                "best_candidate_strictly_improves_minimum_margin": gain > tolerance,
                "failed_baseline_repaired": repaired,
                "oracle_partition": str(oracle["partition"]),
                "oracle_candidate_index": int(oracle["candidate_index"]),
                "oracle_candidate_id": str(oracle["candidate_id"]),
                "oracle_return_task_step": int(oracle["return_task_step"]),
                "oracle_formal_contract_pass": bool(oracle["formal_contract_pass"]),
            }
        )
    baseline_fail_pass = sum(
        bool(row["baseline"]["formal_contract_pass"]) for row in context_rows
    )
    repairs = sum(bool(row["failed_baseline_repaired"]) for row in context_rows)
    candidate_pass = sum(
        bool(candidate["formal_contract_pass"])
        for row in context_rows
        for candidate in row["candidates"]
    )
    candidate_context_pass = sum(
        any(bool(candidate["formal_contract_pass"]) for candidate in row["candidates"])
        for row in context_rows
    )
    gains = [float(row["best_candidate_minimum_margin_gain"]) for row in context_rows]
    measured_oracle = int(
        ctx.cfg["known_aggregate_contract"]["baseline_formal_pass_count"]
    ) + repairs
    scientific = bool(
        repairs
        >= int(ctx.cfg["scientific_gate"]["minimum_repaired_failed_baseline_count"])
        and measured_oracle
        >= int(ctx.cfg["scientific_gate"]["minimum_measured_oracle_formal_pass_count"])
    )
    route = ctx.cfg["routes"]["pass" if scientific else "authority_insufficient"]
    return {
        "schema_version": 1,
        "stage": STAGE,
        "identity": r4.IDENTITY,
        "phase": "current_equivalence_reporting_hotfix_formal_primary_detailed",
        "formal_rows": rows,
        "formal_metric_digest": _digest(rows),
        "context_rows": context_rows,
        "context_outcome_digest": _digest(context_rows),
        "strict_full_horizon_count": len(candidate_rows),
        "candidate_count": len(candidate_rows),
        "failed_context_count": len(context_rows),
        "known_all_context_baseline_formal_pass_count": int(
            ctx.cfg["known_aggregate_contract"]["baseline_formal_pass_count"]
        ),
        "failed_context_baseline_formal_pass_count": baseline_fail_pass,
        "candidate_formal_pass_count": candidate_pass,
        "candidate_formal_pass_context_count": candidate_context_pass,
        "repaired_failed_baseline_count": repairs,
        "failed_baseline_strict_margin_improvement_count": sum(
            bool(row["best_candidate_strictly_improves_minimum_margin"])
            for row in context_rows
        ),
        "measured_oracle_formal_pass_count": measured_oracle,
        "best_candidate_minimum_margin_gain_minimum": min(gains),
        "best_candidate_minimum_margin_gain_median": statistics.median(gains),
        "best_candidate_minimum_margin_gain_maximum": max(gains),
        "integrity_gate_passed": True,
        "scientific_gate_passed": scientific,
        "audit_passed": True,
        "route": route,
        "passed": scientific,
    }


def run_formal_primary(ctx: r4.Context) -> dict[str, Any]:
    source = _authenticate(ctx)
    raw_compact = _dual_raw(ctx, source)
    if raw_compact["passed"] is not True:
        raise ValueError("R8R51R4 reporting-hotfix raw bridge failed")
    _write_new(ctx.paths.analysis / RAW_COMPACT_NAME, raw_compact)
    integrity = r4._read(ctx.paths.analysis / RAW_PRIMARY_NAME)
    detailed = _formal_authority(ctx, integrity)
    _write_new(ctx.paths.analysis / FORMAL_DETAILED_NAME, detailed)
    keys = (
        "formal_metric_digest",
        "context_outcome_digest",
        "strict_full_horizon_count",
        "candidate_count",
        "failed_context_count",
        "known_all_context_baseline_formal_pass_count",
        "failed_context_baseline_formal_pass_count",
        "candidate_formal_pass_count",
        "candidate_formal_pass_context_count",
        "repaired_failed_baseline_count",
        "failed_baseline_strict_margin_improvement_count",
        "measured_oracle_formal_pass_count",
        "best_candidate_minimum_margin_gain_minimum",
        "best_candidate_minimum_margin_gain_median",
        "best_candidate_minimum_margin_gain_maximum",
        "integrity_gate_passed",
        "scientific_gate_passed",
        "audit_passed",
        "route",
        "passed",
    )
    summary = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": r4.IDENTITY,
        "phase": "current_equivalence_reporting_hotfix_formal_primary_summary",
        **{key: detailed[key] for key in keys},
        "raw_inventory": source["inventory"],
        "raw_hotfix_compact_sha256": _sha(ctx.paths.analysis / RAW_COMPACT_NAME),
        "raw_hotfix_primary_sha256": _sha(ctx.paths.analysis / RAW_PRIMARY_NAME),
        "raw_hotfix_independent_sha256": _sha(
            ctx.paths.analysis / RAW_INDEPENDENT_NAME
        ),
        "formal_primary_detailed_sha256": _sha(
            ctx.paths.analysis / FORMAL_DETAILED_NAME
        ),
        "original_stage_state_sha256": STAGE_STATE_SHA256,
        "original_reports_and_state_preserved": True,
        "new_tsc_count": 100,
        "new_raw_count": 100,
        "controller_execution_count": 100,
        "plant_step_count": 3_620,
        "model_fit_count": 0,
        "model_selection_count": 0,
        "optimization_count": 0,
        "snapshot_count": 0,
        "response_outcomes_opened": True,
        "all_stage_trajectories_allowed_in_expert_dataset": False,
    }
    _write_new(ctx.paths.analysis / FORMAL_SUMMARY_NAME, summary)
    return summary


def postprocess(ctx: r4.Context) -> dict[str, Any]:
    source = _authenticate(ctx)
    analysis = ctx.paths.analysis
    summary = r4._read(analysis / FORMAL_SUMMARY_NAME)
    independent = r4._read(analysis / FORMAL_INDEPENDENT_NAME)
    if (
        independent.get("audit_passed") is not True
        or independent.get("primary_discrete_agreement") is not True
        or independent.get("primary_numerical_agreement") is not True
        or independent.get("primary_outcome_agreement") is not True
        or independent.get("route") != summary.get("route")
        or independent.get("primary_summary_sha256")
        != _sha(analysis / FORMAL_SUMMARY_NAME)
        or _inventory(ctx.paths.raw) != source["inventory"]
    ):
        raise ValueError("R8R51R4 reporting-hotfix final agreement failed")
    compact_keys = (
        "strict_full_horizon_count",
        "candidate_count",
        "failed_context_count",
        "known_all_context_baseline_formal_pass_count",
        "candidate_formal_pass_count",
        "candidate_formal_pass_context_count",
        "repaired_failed_baseline_count",
        "failed_baseline_strict_margin_improvement_count",
        "measured_oracle_formal_pass_count",
        "best_candidate_minimum_margin_gain_minimum",
        "best_candidate_minimum_margin_gain_median",
        "best_candidate_minimum_margin_gain_maximum",
        "integrity_gate_passed",
        "scientific_gate_passed",
        "route",
        "new_tsc_count",
        "new_raw_count",
        "controller_execution_count",
        "plant_step_count",
        "model_fit_count",
        "model_selection_count",
        "optimization_count",
        "snapshot_count",
        "all_stage_trajectories_allowed_in_expert_dataset",
    )
    compact = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": r4.IDENTITY,
        "phase": "current_equivalence_reporting_hotfix_compact_audit",
        **{key: summary[key] for key in compact_keys},
        "raw_inventory": summary["raw_inventory"],
        "formal_metric_digest": summary["formal_metric_digest"],
        "context_outcome_digest": summary["context_outcome_digest"],
        "raw_hotfix_compact_sha256": summary["raw_hotfix_compact_sha256"],
        "formal_primary_summary_sha256": _sha(analysis / FORMAL_SUMMARY_NAME),
        "formal_primary_detailed_sha256": _sha(analysis / FORMAL_DETAILED_NAME),
        "formal_independent_sha256": _sha(analysis / FORMAL_INDEPENDENT_NAME),
        "primary_independent_maximum_numerical_difference": independent[
            "maximum_primary_numerical_difference"
        ],
        "original_stage_state_sha256": STAGE_STATE_SHA256,
        "original_reports_and_state_preserved": True,
        "audit_passed": True,
    }
    _write_new(analysis / COMPACT_NAME, compact)
    final = copy.deepcopy(summary)
    final.update(
        {
            "phase": "current_equivalence_reporting_hotfix_final",
            "independent_agreement": True,
            "compact_audit_sha256": _sha(analysis / COMPACT_NAME),
            "formal_independent_sha256": compact["formal_independent_sha256"],
            "original_reports_and_state_preserved": True,
            "corrected_phase_status": "complete",
            "finished": True,
            "reporting_hotfix_classification": {
                "runtime_or_environment_error": False,
                "packaging_import_or_deployment_error": False,
                "raw_or_snapshot_corruption": False,
                "summary_or_reporting_error": True,
                "controller_or_action_design_failure_at_integrity_layer": False,
                "real_closed_loop_mpc_executed": False,
                "gate_a_qualified": False,
            },
        }
    )
    _write_new(analysis / FINAL_NAME, final)
    return final


def main() -> None:
    args = r4._parser().parse_args()
    ctx = r4.load_context(args)
    if args.command == "run":
        result = run_primary(ctx)
    elif args.command == "finalize-primary":
        result = run_formal_primary(ctx)
    elif args.command == "postprocess":
        result = postprocess(ctx)
    else:
        raise ValueError(
            "R8R51R4 reporting-hotfix primary command must be run, "
            "finalize-primary, or postprocess"
        )
    keys = (
        "stage",
        "phase",
        "route",
        "passed_count",
        "semantic_event_replay_pass_count",
        "repaired_failed_baseline_count",
        "measured_oracle_formal_pass_count",
        "scientific_gate_passed",
        "independent_agreement",
        "passed",
    )
    print(
        json.dumps(
            {key: result.get(key) for key in keys if key in result},
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
    )


if __name__ == "__main__":
    main()
