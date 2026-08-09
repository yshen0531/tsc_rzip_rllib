#!/usr/bin/env python3
"""Scalar independent raw/formal replay of the R8R51R4 reporting repair."""

from __future__ import annotations

import gzip
import hashlib
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r8r51r3_independent_forensics as r51r3_ind,
)
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
RAW_PRIMARY_SHA256 = "9611590b0627ba0598fcbd7ce1aa14ee8072e4f0ad8a3a8912b251a7bb247c19"
RAW_INDEPENDENT_SHA256 = "c3f76ce90fba1578b87fc78d5051511809ba090c0848e73af0a5c0e90c14cc70"
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
FORMAL_DETAILED_NAME = PREFIX + "formal_primary_detailed.json"
FORMAL_SUMMARY_NAME = PREFIX + "formal_primary_summary.json"
FORMAL_INDEPENDENT_NAME = PREFIX + "formal_independent.json"

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


def _root() -> Path:
    return Path(__file__).resolve().parents[3]


def _fail_constant(value: str) -> Any:
    raise ValueError(f"non-finite JSON constant: {value}")


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"), parse_constant=_fail_constant)


def _read_gzip(path: Path) -> dict[str, Any]:
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        return json.load(stream, parse_constant=_fail_constant)


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            block = stream.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    ).hexdigest()


def _inventory(path: Path) -> dict[str, Any]:
    rows = []
    combined = hashlib.sha256()
    for item in sorted(path.glob("*.json.gz"), key=lambda candidate: candidate.name):
        row = {"name": item.name, "size": item.stat().st_size, "sha256": _sha(item)}
        combined.update(
            f"{row['name']}\0{row['size']}\0{row['sha256']}\n".encode("utf-8")
        )
        rows.append(row)
    return {
        "count": len(rows),
        "bytes": sum(int(row["size"]) for row in rows),
        "digest": combined.hexdigest(),
        "rows": rows,
    }


def _vector(value: Any) -> list[float]:
    if not isinstance(value, list) or len(value) != N_COILS:
        raise ValueError("R8R51R4 independent reporting-hotfix vector shape changed")
    vector = [float(component) for component in value]
    if not all(math.isfinite(component) for component in vector):
        raise ValueError("R8R51R4 independent reporting-hotfix vector is non-finite")
    return vector


def _close(left: list[float], right: list[float]) -> bool:
    return all(
        math.isclose(a, b, rel_tol=0.0, abs_tol=ATOL_A)
        for a, b in zip(left, right)
    )


def _maximum_difference(left: list[float], right: list[float]) -> float:
    return max(abs(a - b) for a, b in zip(left, right))


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
        raise ValueError(f"R8R51R4 independent raw changed: {spec['experiment_id']}")
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
    event_gate_exact = all(
        detail.get("passed") is True
        and all(value is True for value in (detail.get("criteria") or {}).values())
        for detail in details
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
        action_detail_exact &= detail_action == trace_action
        action_effect_exact &= effect_action == trace_action
        key = (
            "nominal_issue_readback_current_a_tsc"
            if name == "candidate_issue"
            else "nominal_readback_current_a_tsc"
        )
        physical = _vector(trajectory[step + 1].get("currents_a_tsc"))
        nominal = _vector(detail.get(key))
        maximum_current_difference = max(
            maximum_current_difference, _maximum_difference(physical, nominal)
        )
        current_binary_count += int(physical == nominal)
        current_numerical &= _close(physical, nominal)
    q0 = details[0]
    issue = details[2]
    q0_physical = _vector(trajectory[Q0_STEP + 1].get("currents_a_tsc"))
    q0_nominal = _vector(q0.get("nominal_readback_current_a_tsc"))
    q0_binary = q0_physical == q0_nominal
    previous_action_exact = (
        _vector(trajectory[Q0_STEP].get("action_norm_tsc"))
        == _vector(trace[Q0_STEP - 1].get("action_norm_tsc"))
    )
    candidate_physical = _vector(trajectory[ISSUE_STEP + 1].get("currents_a_tsc"))
    candidate_changed = candidate_physical != _vector(
        trajectory[ISSUE_STEP].get("currents_a_tsc")
    )
    dwell_zero = True
    dwell_physical_exact = True
    dwell_nominal_binary = True
    for step in dwell_steps:
        detail = trace[step].get("r3c3t13s24d1r14r8r51r4_event_detail") or {}
        physical = _vector(trajectory[step + 1].get("currents_a_tsc"))
        dwell_zero &= _vector(detail.get("action_norm_tsc")) == [0.0] * N_COILS
        dwell_physical_exact &= physical == candidate_physical
        dwell_nominal_binary &= physical == _vector(
            issue.get("nominal_issue_readback_current_a_tsc")
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
    return_center_exact = returned_physical == q0_physical
    return_event_exact = bool(
        returned.get("event") == "stored_pretransport_center_return"
        and returned.get("stored_center_card15_fields")
        == issue.get("center_card15_fields")
        and returned.get("issue_target_card15_fields")
        == issue.get("target_card15_fields")
    )
    refresh_center_exact = all(
        _vector(trajectory[step + 1].get("currents_a_tsc")) == returned_physical
        for step in range(return_step + 1, horizon)
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
            f"R8R51R4 independent cannot reproduce old row: {spec['experiment_id']}"
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
        "q0_nominal_current_numerically_equivalent": _close(q0_physical, q0_nominal),
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


def run_raw(ctx: r4.Context) -> dict[str, Any]:
    root = _root()
    analysis = ctx.paths.analysis
    fixed = {
        ctx.config_path: CONFIG_SHA256,
        root / PRIMARY_PATH: EXECUTED_PRIMARY_SHA256,
        root / INDEPENDENT_PATH: EXECUTED_INDEPENDENT_SHA256,
        root / CONTRACT_PATH: CONTRACT_SHA256,
        ctx.paths.manifest: STAGE_MANIFEST_SHA256,
        ctx.paths.state: STAGE_STATE_SHA256,
        analysis / "raw_integrity_primary.json": RAW_PRIMARY_SHA256,
        analysis / "raw_integrity_independent.json": RAW_INDEPENDENT_SHA256,
    }
    if any(not path.is_file() or _sha(path) != expected for path, expected in fixed.items()):
        raise ValueError("R8R51R4 independent reporting-hotfix authentication failed")
    output = analysis / RAW_INDEPENDENT_NAME
    if output.exists():
        raise ValueError("R8R51R4 independent reporting-hotfix output exists")
    primary_path = analysis / RAW_PRIMARY_NAME
    if not primary_path.is_file():
        raise ValueError("R8R51R4 reporting-hotfix primary is missing")
    primary = _read(primary_path)
    old_primary = _read(analysis / "raw_integrity_primary.json")
    old_independent = _read(analysis / "raw_integrity_independent.json")
    inventory = _inventory(ctx.paths.raw)
    if (
        inventory["count"] != RAW_COUNT
        or inventory["bytes"] != RAW_BYTES
        or inventory["digest"] != RAW_DIGEST
        or inventory != old_primary.get("raw_inventory")
        or inventory != old_independent.get("raw_inventory")
        or old_primary.get("event_stream_digest") != ORIGINAL_EVENT_DIGEST
        or old_independent.get("independent_event_stream_digest")
        != ORIGINAL_EVENT_DIGEST
        or old_independent.get("primary_agreement") is not True
    ):
        raise ValueError("R8R51R4 independent historical evidence changed")
    specs = r4._saved_specs(ctx)
    old_rows = {str(row["experiment_id"]): row for row in old_primary["rows"]}
    rows = []
    for spec in specs:
        experiment_id = str(spec["experiment_id"])
        result = _read_gzip(ctx.paths.raw / f"{experiment_id}.json.gz")
        old = old_rows.get(experiment_id)
        if old is None:
            raise ValueError(f"R8R51R4 independent old row missing: {experiment_id}")
        rows.append(_measure(result, spec, old))
    event_count = sum(int(row["event_count"]) for row in rows)
    dwell_count = sum(int(row["dwell_event_count"]) for row in rows)
    refresh_count = sum(int(row["refresh_event_count"]) for row in rows)
    q0_binary = sum(row["q0_nominal_current_binary_exact"] for row in rows)
    dwell_binary = sum(row["dwell_nominal_current_binary_exact"] for row in rows)
    maximum = max(row["maximum_event_nominal_current_difference_a"] for row in rows)
    passed_count = sum(row["passed"] for row in rows)
    report = {
        "schema_version": 1,
        "stage": STAGE,
        "phase": "current_equivalence_reporting_hotfix_raw_independent",
        "hotfix_kind": "scalar_binary64_nominal_current_reconstruction_reporting_only",
        "original_route": OLD_ROUTE,
        "route": RAW_HOTFIX_ROUTE if passed_count == RAW_COUNT else OLD_ROUTE,
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
        "raw_unchanged": _inventory(ctx.paths.raw) == inventory,
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
    }
    compare_keys = (
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
    agreement = all(primary.get(key) == report.get(key) for key in compare_keys)
    passed = bool(
        len(rows) == RAW_COUNT
        and event_count == EXPECTED_EVENT_COUNT
        and dwell_count == EXPECTED_DWELL_EVENT_COUNT
        and refresh_count == EXPECTED_REFRESH_EVENT_COUNT
        and q0_binary == ORIGINAL_Q0_BINARY_COUNT
        and dwell_binary == ORIGINAL_DWELL_BINARY_COUNT
        and passed_count == RAW_COUNT
        and maximum <= ATOL_A
        and primary.get("passed") is True
        and agreement
    )
    report.update(
        {
            "primary_sha256": _sha(primary_path),
            "primary_agreement": agreement,
            "passed": passed,
        }
    )
    output.write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return report


def _authority(rows: list[Mapping[str, Any]], baseline_pass: int) -> dict[str, Any]:
    groups: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(str(row["pair_id"]), str(row["history_member"]))].append(row)
    context_rows = []
    for key, group in sorted(groups.items()):
        baseline = next(row for row in group if row["partition"] == "baseline")
        candidates = [row for row in group if row["partition"] == "candidate"]
        best = max(
            candidates,
            key=lambda row: (
                float(row["formal_minimum_signed_margin"]),
                float(row["formal_mean_signed_margin"]),
                -int(row["candidate_index"]),
                -int(row["return_task_step"]),
            ),
        )
        repair = bool(any(bool(row["formal_contract_pass"]) for row in candidates))
        gain = float(best["formal_minimum_signed_margin"]) - float(
            baseline["formal_minimum_signed_margin"]
        )
        context_rows.append(
            {
                "pair_id": key[0],
                "history_member": key[1],
                "best_candidate_index": int(best["candidate_index"]),
                "best_candidate_id": str(best["candidate_id"]),
                "best_return_task_step": int(best["return_task_step"]),
                "gain": gain,
                "repair": repair,
            }
        )
    repairs = sum(bool(row["repair"]) for row in context_rows)
    gains = [float(row["gain"]) for row in context_rows]
    return {
        "context_count": len(groups),
        "candidate_formal_pass_count": sum(
            bool(row["formal_contract_pass"])
            for row in rows
            if row["partition"] == "candidate"
        ),
        "candidate_formal_pass_context_count": sum(
            any(
                bool(row["formal_contract_pass"])
                for row in group
                if row["partition"] == "candidate"
            )
            for group in groups.values()
        ),
        "repaired_failed_baseline_count": repairs,
        "failed_baseline_strict_margin_improvement_count": sum(
            float(row["gain"]) > 1e-12 for row in context_rows
        ),
        "measured_oracle_formal_pass_count": baseline_pass + repairs,
        "best_candidate_minimum_margin_gain_minimum": min(gains),
        "best_candidate_minimum_margin_gain_median": statistics.median(gains),
        "best_candidate_minimum_margin_gain_maximum": max(gains),
        "independent_context_outcome_digest": _digest(context_rows),
    }


def run_formal(ctx: r4.Context) -> dict[str, Any]:
    analysis = ctx.paths.analysis
    root = _root()
    fixed = {
        ctx.config_path: CONFIG_SHA256,
        root / PRIMARY_PATH: EXECUTED_PRIMARY_SHA256,
        root / INDEPENDENT_PATH: EXECUTED_INDEPENDENT_SHA256,
        root / CONTRACT_PATH: CONTRACT_SHA256,
        ctx.paths.manifest: STAGE_MANIFEST_SHA256,
        ctx.paths.state: STAGE_STATE_SHA256,
        analysis / "raw_integrity_primary.json": RAW_PRIMARY_SHA256,
        analysis / "raw_integrity_independent.json": RAW_INDEPENDENT_SHA256,
    }
    if any(not path.is_file() or _sha(path) != expected for path, expected in fixed.items()):
        raise ValueError("R8R51R4 independent hotfix formal authentication failed")
    inventory = _inventory(ctx.paths.raw)
    if (
        inventory["count"] != RAW_COUNT
        or inventory["bytes"] != RAW_BYTES
        or inventory["digest"] != RAW_DIGEST
    ):
        raise ValueError("R8R51R4 independent hotfix formal raw changed")
    primary = _read(analysis / FORMAL_DETAILED_NAME)
    summary_path = analysis / FORMAL_SUMMARY_NAME
    summary = _read(summary_path)
    integrity = _read(analysis / RAW_INDEPENDENT_NAME)
    if integrity.get("raw_inventory") != inventory:
        raise ValueError("R8R51R4 independent hotfix integrity inventory changed")
    specs = r4._saved_specs(ctx)
    _, sources = r4.r51._source_baselines(ctx.base_ctx)
    rows = []
    for baseline_id in ctx.cfg["matrix_contract"]["failed_source_baseline_ids"]:
        result = sources[str(baseline_id)]
        spec = result["spec"]
        rows.append(
            {
                "experiment_id": str(baseline_id),
                "partition": "baseline",
                "pair_id": str(spec["pair_id"]),
                "history_member": str(spec["history_member"]),
                "candidate_index": -1,
                "candidate_id": "baseline",
                "return_task_step": -1,
                **r51r3_ind.scalar_formal_metric(
                    spec, result["trajectory"], ctx.cfg["formal_contract"]
                ),
            }
        )
    for spec in specs:
        result = _read_gzip(
            ctx.paths.raw / f"{spec['experiment_id']}.json.gz"
        )
        rows.append(
            {
                "experiment_id": str(spec["experiment_id"]),
                "partition": "candidate",
                "pair_id": str(spec["pair_id"]),
                "history_member": str(spec["history_member"]),
                "candidate_index": int(spec["r8r51r4_candidate_index"]),
                "candidate_id": str(spec["r8r51r4_candidate_id"]),
                "return_task_step": int(spec["r8r51r4_return_task_step"]),
                "source_baseline_experiment_id": str(
                    spec["source_r8r7_baseline_experiment_id"]
                ),
                **r51r3_ind.scalar_formal_metric(
                    spec, result["trajectory"], ctx.cfg["formal_contract"]
                ),
            }
        )
    rows.sort(
        key=lambda row: (
            row["pair_id"],
            row["history_member"],
            0 if row["partition"] == "baseline" else 1,
            int(row["candidate_index"]),
            int(row["return_task_step"]),
            row["experiment_id"],
        )
    )
    result = _authority(
        rows, int(ctx.cfg["known_aggregate_contract"]["baseline_formal_pass_count"])
    )
    expected = {str(row["experiment_id"]): row for row in primary["formal_rows"]}
    tolerance = float(ctx.cfg["formal_contract"]["metric_equivalence_absolute_tolerance"])
    discrete = len(expected) == len(rows)
    maximum = 0.0
    for row in rows:
        other = expected.get(str(row["experiment_id"]))
        if other is None:
            discrete = False
            continue
        discrete = bool(
            discrete
            and row["partition"] == other["partition"]
            and row["candidate_id"] == other["candidate_id"]
            and int(row["return_task_step"]) == int(other["return_task_step"])
            and bool(row["formal_contract_pass"]) == bool(other["formal_contract_pass"])
            and int(row["formal_best_arrival_ms"])
            == int(other["formal_best_arrival_ms"])
        )
        for key in ("formal_minimum_signed_margin", "formal_mean_signed_margin"):
            maximum = max(maximum, abs(float(row[key]) - float(other[key])))
    compare_keys = (
        "candidate_formal_pass_count",
        "candidate_formal_pass_context_count",
        "repaired_failed_baseline_count",
        "failed_baseline_strict_margin_improvement_count",
        "measured_oracle_formal_pass_count",
    )
    outcome = all(result[key] == primary[key] for key in compare_keys)
    for key in (
        "best_candidate_minimum_margin_gain_minimum",
        "best_candidate_minimum_margin_gain_median",
        "best_candidate_minimum_margin_gain_maximum",
    ):
        difference = abs(float(result[key]) - float(primary[key]))
        maximum = max(maximum, difference)
        outcome &= difference <= tolerance
    numerical = maximum <= tolerance
    integrity_passed = bool(
        integrity.get("passed") is True
        and len(rows) == 110
        and result["context_count"] == 10
        and discrete
        and numerical
        and outcome
    )
    scientific = bool(
        integrity_passed
        and result["repaired_failed_baseline_count"] >= 1
        and result["measured_oracle_formal_pass_count"] >= 7
    )
    route = ctx.cfg["routes"][
        "execution_fail"
        if not integrity_passed
        else ("pass" if scientific else "authority_insufficient")
    ]
    report = {
        "schema_version": 1,
        "stage": STAGE,
        "phase": "current_equivalence_reporting_hotfix_formal_independent",
        "formal_row_count": len(rows),
        "independent_formal_metric_digest": _digest(rows),
        **result,
        "primary_discrete_agreement": discrete,
        "primary_numerical_agreement": numerical,
        "primary_outcome_agreement": outcome,
        "maximum_primary_numerical_difference": maximum,
        "comparison_absolute_tolerance": tolerance,
        "integrity_gate_passed": integrity_passed,
        "scientific_gate_passed": scientific,
        "route": route,
        "audit_passed": integrity_passed,
        "primary_summary_route_agreement": route == summary.get("route"),
        "primary_summary_sha256": _sha(summary_path),
    }
    output = analysis / FORMAL_INDEPENDENT_NAME
    if output.exists():
        raise ValueError("R8R51R4 independent hotfix formal output exists")
    output.write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> None:
    args = r4._parser().parse_args()
    ctx = r4.load_context(args)
    if args.command == "run":
        result = run_raw(ctx)
    elif args.command == "finalize-primary":
        result = run_formal(ctx)
    else:
        raise ValueError(
            "R8R51R4 independent reporting-hotfix command must be run or "
            "finalize-primary"
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
        "primary_agreement",
        "audit_passed",
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
