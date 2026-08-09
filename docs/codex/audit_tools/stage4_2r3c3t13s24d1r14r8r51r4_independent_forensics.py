#!/usr/bin/env python3
"""Independent offline, raw-integrity, and scalar-formal audits for R8R51R4."""

from __future__ import annotations

from collections import defaultdict
import copy
import json
import math
import statistics
from typing import Any, Mapping, Sequence

import numpy as np

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r8r51r3_independent_forensics as r51r3_ind,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r51r4_failed_context_sustained_transport_dwell_sentinel
    as r4,
)


def _independent_event_stream(
    ctx: r4.Context, spec: Mapping[str, Any]
) -> dict[str, Any]:
    _, sources = r4.r51._source_baselines(ctx.base_ctx)
    source = sources[str(spec["source_r8r7_baseline_experiment_id"])]
    execution = r4._execution_context(ctx)
    lattice = execution.d1r11_ctx.base_ctx.base_ctx.cfg["lattice_probe"]
    contract = r4._controller_contract(ctx)
    payload = r4._read(ctx.paths.variants / f"payload_{spec['experiment_id']}.json")
    actuator = r4.r51.r8r22.mpc.actuator_from_payload(payload, lattice)
    basis = r4.r51.r8r22._fixed_basis(source)
    current = np.asarray(source["trajectory"][r4.Q0_STEP]["currents_a_tsc"], dtype=float)
    events = []
    q0 = r4.r51._q0_event(
        task_step=r4.Q0_STEP, currents=current, actuator=actuator,
        lattice=lattice, contract=contract,
    )
    events.append(q0)
    center_fields = list(q0["q0_center_card15_fields"])
    current = np.asarray(q0["nominal_readback_current_a_tsc"], dtype=float)
    q0_observe = r4.r51._observe_event(
        task_step=11, currents=current, target_fields=center_fields,
        actuator=actuator, contract=contract, event="q0_observe_hold",
    )
    events.append(q0_observe)
    current = np.asarray(q0_observe["nominal_readback_current_a_tsc"], dtype=float)
    issue = r4.r51.r8r22._construct_coordinate_issue(
        task_step=r4.ISSUE_STEP, currents_a_tsc=current,
        fixed_basis_delta_field_kat_tsc=basis.T,
        requested_coordinate=spec["r8r51r4_requested_coordinate"],
        candidate_id=str(spec["r8r51r4_candidate_id"]), actuator=actuator,
        controller_cfg=contract, lattice_cfg=lattice,
    )
    issue["center_nominal_readback_current_a_tsc"] = current.tolist()
    events.append(issue)
    current = np.asarray(issue["nominal_issue_readback_current_a_tsc"], dtype=float)
    return_step = int(spec["r8r51r4_return_task_step"])
    for step in range(13, return_step):
        hold = r4.r51._observe_event(
            task_step=step, currents=current,
            target_fields=issue["target_card15_fields"], actuator=actuator,
            contract=contract, event="candidate_current_dwell_hold",
        )
        events.append(hold)
        current = np.asarray(hold["nominal_readback_current_a_tsc"], dtype=float)
    returned = r4.r51._return_event(
        task_step=return_step, currents=current, center_fields=center_fields,
        issue_event=issue, field_basis=basis, actuator=actuator,
        lattice=lattice, contract=contract,
    )
    events.append(returned)
    current = np.asarray(returned["nominal_readback_current_a_tsc"], dtype=float)
    for step in range(return_step + 1, int(spec["horizon_steps"])):
        refresh = r4.r51.r8r22._refresh_event(
            task_step=step, currents=current, target_fields=center_fields,
            actuator=actuator, turns_tsc=actuator.turns_tsc,
            max_delta_a=actuator.max_slew_step_a,
            minimum_current=actuator.minimum_current_a_tsc,
            maximum_current=actuator.maximum_current_a_tsc,
            lattice_cfg=lattice, contract=contract,
        )
        refresh["event"] = "post_return_exact_center_refresh"
        events.append(refresh)
        current = np.asarray(refresh["nominal_readback_current_a_tsc"], dtype=float)
    criteria = {
        "all_event_gates": all(
            event.get("passed") is True
            and all(bool(value) for value in (event.get("criteria") or {}).values())
            for event in events
        ),
        "q0_constructor": set(q0.get("criteria") or {}) == r4.r51.Q0_CRITERIA_KEYS,
        "candidate_identity": issue.get("candidate_id") == spec["r8r51r4_candidate_id"],
        "candidate_coordinate": np.array_equal(
            np.asarray(issue.get("requested_coordinate"), dtype=float),
            np.asarray(spec["r8r51r4_requested_coordinate"], dtype=float),
        ),
        "dwell_count": len(events[3 : 3 + return_step - 13]) == return_step - 13,
        "dwell_zero": all(
            np.array_equal(np.asarray(event["action_norm_tsc"]), np.zeros(r4.N_COILS))
            for event in events[3 : 3 + return_step - 13]
        ),
        "return": returned.get("passed") is True,
    }
    return {
        "experiment_id": str(spec["experiment_id"]),
        "q0_event_digest": r4._digest(q0),
        "q0_action_norm_tsc": list(q0["action_norm_tsc"]),
        "q0_criteria_keys": sorted(q0["criteria"]),
        "event_stream_digest": r4._digest(events),
        "event_count": len(events),
        "dwell_hold_count": return_step - 13,
        "maximum_incremental_action_linf": max(
            float(event["incremental_normalized_action_linf"]) for event in events
        ),
        "maximum_predicted_current_utilization": max(
            float(event["predicted_current_utilization"]) for event in events
        ),
        "criteria": criteria,
        "passed": all(bool(value) for value in criteria.values()),
    }


def offline(ctx: r4.Context) -> dict[str, Any]:
    state = r4._read(ctx.paths.state)
    primary = r4._read(ctx.paths.analysis / "offline_primary.json")
    saved = r4._read(ctx.paths.analysis / "offline_construction.json")
    source = r4.authenticate_sources(ctx)
    specs = r4._saved_specs(ctx)
    rows = [_independent_event_stream(ctx, spec) for spec in specs]
    primary_rows = {
        str(row["experiment_id"]): row for row in saved["rows"]
    }
    comparable = (
        "q0_event_digest", "q0_action_norm_tsc", "q0_criteria_keys",
        "event_stream_digest", "event_count", "dwell_hold_count",
        "maximum_incremental_action_linf", "maximum_predicted_current_utilization",
        "passed",
    )
    agreement = bool(
        len(rows) == len(primary_rows) == 100
        and all(
            all(row[key] == primary_rows[row["experiment_id"]][key] for key in comparable)
            for row in rows
        )
        and primary.get("construction_count") == 100
        and primary.get("construction_pass_count") == 100
        and primary.get("passed") is True
        and state.get("phase_status") == "offline_primary_ready"
    )
    report = {
        "schema_version": 1, "stage": r4.STAGE, "phase": "offline_independent",
        "source_route_authenticated": bool(source["passed"]),
        "design_authenticated": (
            r4._sha(ctx.config_path) == r4._read(ctx.paths.manifest).get("config_sha256")
        ),
        "spec_count": len(specs), "construction_count": len(rows),
        "construction_pass_count": sum(bool(row["passed"]) for row in rows),
        "independent_event_stream_digest": r4._digest([
            (row["experiment_id"], row["event_stream_digest"]) for row in rows
        ]),
        "primary_agreement": agreement,
        "new_raw_count": 0, "plant_step_count": 0,
        "real_tsc_executed": False,
        "passed": bool(
            source["passed"] and agreement and len(rows) == 100
            and all(bool(row["passed"]) for row in rows)
        ),
    }
    r4._write(ctx.paths.analysis / "offline_independent.json", report)
    return report


def raw(ctx: r4.Context) -> dict[str, Any]:
    primary = r4._read(ctx.paths.analysis / "raw_integrity_primary.json")
    specs = r4._saved_specs(ctx)
    offline = {
        str(row["experiment_id"]): row
        for row in r4._read(ctx.paths.analysis / "offline_construction.json")["rows"]
    }
    rows = []
    for spec in specs:
        path = ctx.paths.raw / f"{spec['experiment_id']}.json.gz"
        result = r4.r51.r8r7.r8._read_gz(path)
        trajectory = result.get("trajectory") or []
        trace = result.get("controller_trace") or []
        horizon = int(spec["horizon_steps"])
        return_step = int(spec["r8r51r4_return_task_step"])
        dwell_count = return_step - 13
        details = [
            trace[step].get("r3c3t13s24d1r14r8r51r4_event_detail") or {}
            for step in range(10, horizon)
        ] if len(trace) == horizon else []
        names = [
            trace[step].get("r3c3t13s24d1r14r8r51r4_event")
            for step in range(10, horizon)
        ] if len(trace) == horizon else []
        sequence = bool(
            names[:3] == ["q0_exact_issue", "q0_observe_hold", "candidate_issue"]
            and names[3 : 3 + dwell_count] == ["candidate_dwell_hold"] * dwell_count
            and names[3 + dwell_count] == "stored_center_return"
            and all(name == "center_refresh" for name in names[4 + dwell_count :])
        )
        finite = bool(
            len(trajectory) == horizon + 1 and len(trace) == horizon
            and all(
                math.isfinite(float(row[key])) for row in trajectory
                for key in ("R", "Z", "Ip")
            )
            and all(
                math.isfinite(float(value))
                for row in trajectory for value in row.get("currents_a_tsc", [])
            )
        )
        forbidden = sum(
            any(bool(row.get(key)) for key in r4.FORBIDDEN_KEYS) for row in trace
        )
        event_digest = r4._digest(details) if details else ""
        passed = bool(
            result.get("completed") and result.get("success")
            and result.get("spec") == spec and finite and sequence
            and len(details) == horizon - 10
            and all(detail.get("passed") is True for detail in details)
            and event_digest == offline[str(spec["experiment_id"])]["event_stream_digest"]
            and forbidden == 0
        )
        rows.append(
            {
                "experiment_id": str(spec["experiment_id"]),
                "event_stream_digest": event_digest,
                "forbidden_trace_count": forbidden,
                "passed": passed,
            }
        )
    primary_rows = {str(row["experiment_id"]): row for row in primary["rows"]}
    agreement = bool(
        len(rows) == len(primary_rows) == 100
        and all(
            row["passed"] == primary_rows[row["experiment_id"]]["passed"]
            and row["event_stream_digest"]
            == primary_rows[row["experiment_id"]]["event_stream_digest"]
            and row["forbidden_trace_count"]
            == primary_rows[row["experiment_id"]]["forbidden_trace_count"]
            for row in rows
        )
    )
    inventory = r4.r51.r8r7.r8._inventory(ctx.paths.raw)
    report = {
        "schema_version": 1, "stage": r4.STAGE,
        "phase": "raw_integrity_independent", "raw_inventory": inventory,
        "strict_parse_count": len(rows),
        "passed_count": sum(bool(row["passed"]) for row in rows),
        "independent_event_stream_digest": r4._digest([
            (row["experiment_id"], row["event_stream_digest"]) for row in rows
        ]),
        "primary_agreement": agreement,
        "response_outcomes_opened": False,
        "passed": bool(
            inventory.get("count") == 100 and len(rows) == 100
            and all(bool(row["passed"]) for row in rows) and agreement
        ),
    }
    r4._write(ctx.paths.analysis / "raw_integrity_independent.json", report)
    return report


def _authority(rows: Sequence[Mapping[str, Any]], baseline_pass: int) -> dict[str, Any]:
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
                -int(row["candidate_index"]), -int(row["return_task_step"]),
            ),
        )
        repair = bool(any(bool(row["formal_contract_pass"]) for row in candidates))
        gain = float(best["formal_minimum_signed_margin"]) - float(
            baseline["formal_minimum_signed_margin"]
        )
        context_rows.append(
            {
                "pair_id": key[0], "history_member": key[1],
                "best_candidate_index": int(best["candidate_index"]),
                "best_candidate_id": str(best["candidate_id"]),
                "best_return_task_step": int(best["return_task_step"]),
                "gain": gain, "repair": repair,
            }
        )
    repairs = sum(bool(row["repair"]) for row in context_rows)
    gains = [float(row["gain"]) for row in context_rows]
    return {
        "context_count": len(groups),
        "candidate_formal_pass_count": sum(
            bool(row["formal_contract_pass"]) for row in rows
            if row["partition"] == "candidate"
        ),
        "candidate_formal_pass_context_count": sum(
            any(bool(row["formal_contract_pass"]) for row in group
                if row["partition"] == "candidate")
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
        "independent_context_outcome_digest": r4._digest(context_rows),
    }


def formal(ctx: r4.Context) -> dict[str, Any]:
    primary = r4._read(ctx.paths.analysis / "primary_detailed.json")
    summary = r4._read(ctx.paths.analysis / "primary_summary.json")
    integrity = r4._read(ctx.paths.analysis / "raw_integrity_independent.json")
    specs = r4._saved_specs(ctx)
    _, sources = r4.r51._source_baselines(ctx.base_ctx)
    rows = []
    for baseline_id in ctx.cfg["matrix_contract"]["failed_source_baseline_ids"]:
        result = sources[str(baseline_id)]
        spec = result["spec"]
        rows.append(
            {
                "experiment_id": str(baseline_id), "partition": "baseline",
                "pair_id": str(spec["pair_id"]),
                "history_member": str(spec["history_member"]),
                "candidate_index": -1, "candidate_id": "baseline",
                "return_task_step": -1,
                **r51r3_ind.scalar_formal_metric(
                    spec, result["trajectory"], ctx.cfg["formal_contract"]
                ),
            }
        )
    for spec in specs:
        result = r4.r51.r8r7.r8._read_gz(
            ctx.paths.raw / f"{spec['experiment_id']}.json.gz"
        )
        rows.append(
            {
                "experiment_id": str(spec["experiment_id"]),
                "partition": "candidate", "pair_id": str(spec["pair_id"]),
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
    rows.sort(key=lambda row: (
        row["pair_id"], row["history_member"],
        0 if row["partition"] == "baseline" else 1,
        int(row["candidate_index"]), int(row["return_task_step"]), row["experiment_id"],
    ))
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
            discrete and row["partition"] == other["partition"]
            and row["candidate_id"] == other["candidate_id"]
            and int(row["return_task_step"]) == int(other["return_task_step"])
            and bool(row["formal_contract_pass"]) == bool(other["formal_contract_pass"])
            and int(row["formal_best_arrival_ms"]) == int(other["formal_best_arrival_ms"])
        )
        for key in ("formal_minimum_signed_margin", "formal_mean_signed_margin"):
            maximum = max(maximum, abs(float(row[key]) - float(other[key])))
    compare_keys = (
        "candidate_formal_pass_count", "candidate_formal_pass_context_count",
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
        outcome = bool(outcome and difference <= tolerance)
    numerical = maximum <= tolerance
    integrity_passed = bool(
        integrity.get("passed") is True and len(rows) == 110
        and result["context_count"] == 10 and discrete and numerical and outcome
    )
    scientific = bool(
        integrity_passed
        and result["repaired_failed_baseline_count"] >= 1
        and result["measured_oracle_formal_pass_count"] >= 7
    )
    route = ctx.cfg["routes"][
        "execution_fail" if not integrity_passed
        else ("pass" if scientific else "authority_insufficient")
    ]
    report = {
        "schema_version": 1, "stage": r4.STAGE, "phase": "formal_independent",
        "formal_row_count": len(rows),
        "independent_formal_metric_digest": r4._digest(rows),
        **result, "primary_discrete_agreement": discrete,
        "primary_numerical_agreement": numerical,
        "primary_outcome_agreement": outcome,
        "maximum_primary_numerical_difference": maximum,
        "comparison_absolute_tolerance": tolerance,
        "integrity_gate_passed": integrity_passed,
        "scientific_gate_passed": scientific,
        "route": route, "audit_passed": integrity_passed,
        "primary_summary_route_agreement": route == summary.get("route"),
    }
    r4._write(ctx.paths.analysis / "formal_independent.json", report)
    return report


def main() -> None:
    args = r4._parser().parse_args()
    ctx = r4.load_context(args)
    if args.command == "offline":
        result = offline(ctx)
    elif args.command == "run":
        result = raw(ctx)
    elif args.command == "finalize-primary":
        result = formal(ctx)
    else:
        raise ValueError("R8R51R4 independent command must be offline, run, or finalize-primary")
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
