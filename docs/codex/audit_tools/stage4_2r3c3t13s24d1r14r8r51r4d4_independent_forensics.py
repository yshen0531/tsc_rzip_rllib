"""Independent offline, raw, and scalar-formal audit for R8R51R4D4."""
from __future__ import annotations

from collections import defaultdict
import json
import math
import statistics
from typing import Any, Mapping, Sequence

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r8r51r3_independent_forensics as r51r3_ind,
    stage4_2r3c3t13s24d1r14r8r51r4d3_independent_forensics as d3_ind,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r51r4d4_center_bridged_two_pulse_response_sentinel
    as d4,
)


def _event_equal(actual: Mapping[str, Any], expected: Mapping[str, Any]) -> bool:
    keys = (
        "task_step", "event", "candidate_id", "requested_coordinate",
        "action_norm_tsc", "target_card15_fields", "stored_target_card15_fields",
        "q0_center_card15_fields", "stored_center_card15_fields",
        "issue_target_card15_fields", "center_card15_fields", "passed", "criteria",
    )
    return all(actual.get(key) == expected.get(key) for key in keys)


def offline(ctx: d4.Context) -> dict[str, Any]:
    state = d4._read(ctx.paths.state)
    primary = d4._read(ctx.paths.analysis / "offline_primary.json")
    saved = d4._read(ctx.paths.analysis / "offline_construction.json")
    source = d4.authenticate_sources(ctx)
    specs = d4._saved_specs(ctx)
    source_rows = d4.d3.d1._source_specs(ctx.d3_ctx.d1_ctx)
    by_id = {str(row["experiment_id"]): row for row in source_rows}
    cache: dict[str, dict[str, Any]] = {}
    rows = [d3_ind._construct_row(ctx.d3_ctx, spec, by_id, cache) for spec in specs]
    primary_rows = {str(row["experiment_id"]): row for row in saved["rows"]}
    maximum = 0.0
    discrete = len(rows) == len(primary_rows) == 250
    for row in rows:
        other = primary_rows.get(str(row["experiment_id"]))
        if other is None:
            discrete = False
            continue
        discrete = bool(
            discrete
            and row["action_stream_digest"] == other["action_stream_digest"]
            and int(row["event_count"]) == int(other["event_count"])
            and bool(row["eligible"]) == bool(other["passed"])
        )
        maximum = max(
            maximum,
            abs(float(row["maximum_incremental_action_linf"]) - float(other["maximum_incremental_action_linf"])),
            abs(float(row["maximum_current_utilization"]) - float(other["maximum_current_utilization"])),
        )
    action_digest = d4._digest([(row["experiment_id"], row["action_stream_digest"]) for row in rows])
    agreement = bool(
        discrete and maximum <= 1e-10
        and action_digest == primary.get("action_stream_digest")
        and primary.get("construction_count") == 250
        and primary.get("construction_pass_count") == 250
        and primary.get("passed") is True
        and state.get("phase_status") == "offline_primary_ready"
    )
    report = {
        "schema_version": 1, "stage": d4.STAGE, "phase": "offline_independent",
        "source_authenticated": bool(source["passed"]),
        "design_authenticated": (
            d4._sha(ctx.config_path) == d4._read(ctx.paths.manifest).get("config_sha256")
        ),
        "conditional_d5_design_authenticated": (
            d4._sha(d4._root() / ctx.cfg["conditional_d5_design"])
            == ctx.cfg["conditional_d5_design_sha256"]
        ),
        "spec_count": len(specs), "construction_count": len(rows),
        "construction_pass_count": sum(bool(row["eligible"]) for row in rows),
        "independent_action_stream_digest": action_digest,
        "primary_agreement": agreement,
        "maximum_primary_numerical_difference": maximum,
        "new_raw_count": 0, "plant_step_count": 0,
        "real_tsc_executed": False,
        "passed": bool(
            source["passed"] and agreement and len(rows) == 250
            and all(bool(row["eligible"]) for row in rows)
        ),
    }
    d4._write(ctx.paths.analysis / "offline_independent.json", report)
    return report


def raw(ctx: d4.Context) -> dict[str, Any]:
    primary = d4._read(ctx.paths.analysis / "raw_integrity_primary.json")
    primary_rows = {str(row["experiment_id"]): row for row in primary["rows"]}
    specs = d4._saved_specs(ctx)
    offline_rows = {
        str(row["experiment_id"]): row
        for row in d4._read(ctx.paths.analysis / "offline_construction.json")["rows"]
    }
    _, sources = d4.r4.r51._source_baselines(ctx.r4_ctx.base_ctx)
    contract = ctx.cfg["controller_contract"]
    rows = []
    q0_prefixes: dict[tuple[str, str], list[str]] = defaultdict(list)
    first_prefixes: dict[tuple[str, str, str], list[str]] = defaultdict(list)
    expected_names = [
        "q0_exact_issue", "q0_observe_hold", "first_candidate_issue",
        "first_candidate_hold", "first_candidate_hold", "first_candidate_hold",
        "first_stored_center_return", "center_bridge_hold", "second_candidate_issue",
        "second_candidate_hold", "second_candidate_hold", "second_candidate_hold",
        "second_stored_center_return",
    ]
    for spec in specs:
        experiment_id = str(spec["experiment_id"])
        result = d4.r4.r51.r8r7.r8._read_gz(ctx.paths.raw / f"{experiment_id}.json.gz")
        trajectory = result.get("trajectory") or []
        trace = result.get("controller_trace") or []
        horizon = int(spec["horizon_steps"])
        full = len(trajectory) == horizon + 1 and len(trace) == horizon
        source = sources[str(spec["source_r8r7_baseline_experiment_id"])]
        restart = bool(
            full
            and d4.r4.r51.r8r7.r8.r4._semantic_state(trajectory[0])
            == d4.r4.r51.r8r7.r8.r4._semantic_state(source["trajectory"][0])
        )
        source_prefix_state = bool(
            full
            and all(
                d4.r4.r51.r8r7.r8.r4._semantic_state(actual)
                == d4.r4.r51.r8r7.r8.r4._semantic_state(reference)
                for actual, reference in zip(
                    trajectory[: d4.PREFIX_END + 1],
                    source["trajectory"][: d4.PREFIX_END + 1],
                )
            )
        )
        source_prefix_trace = bool(
            full
            and all(
                d4.r4.r51.r8r22._source_trace_semantic_projection(reference, actual)
                for actual, reference in zip(
                    trace[: d4.PREFIX_END], source["controller_trace"][: d4.PREFIX_END]
                )
            )
        )
        calibration = bool(full and d4.r4.r51.r8r7.r8.r4._calibration_exact(trace))
        details = [
            trace[step].get("r3c3t13s24d1r14r8r51r4d4_event_detail") or {}
            for step in range(d4.PREFIX_END, horizon)
        ] if full else []
        names = [
            trace[step].get("r3c3t13s24d1r14r8r51r4d4_event")
            for step in range(d4.PREFIX_END, horizon)
        ] if full else []
        sequence = bool(
            names[:13] == expected_names
            and all(name == "center_refresh" for name in names[13:])
            and len(details) == horizon - d4.PREFIX_END
        )
        gates = bool(
            sequence
            and all(
                detail.get("passed") is True
                and all(bool(value) for value in (detail.get("criteria") or {}).values())
                for detail in details
            )
        )
        expected_events = offline_rows[experiment_id]["events"]
        offline_semantics = bool(
            sequence
            and len(details) == len(expected_events)
            and all(_event_equal(actual, expected) for actual, expected in zip(details, expected_events))
        )
        action_exact = bool(
            sequence
            and all(
                list(detail.get("action_norm_tsc") or []) == list(trace[step]["action_norm_tsc"])
                and list(trace[step]["action_norm_tsc"]) == list(trajectory[step + 1]["action_norm_tsc"])
                for step, detail in zip(range(d4.PREFIX_END, horizon), details)
            )
        )
        maximum_current_difference = 0.0 if sequence else None
        currents = sequence
        if sequence:
            for step, detail in zip(range(d4.PREFIX_END, horizon), details):
                nominal = list(map(float, d4._nominal_current(detail)))
                physical = list(map(float, trajectory[step + 1]["currents_a_tsc"]))
                if len(nominal) != d4.N_COILS or len(physical) != d4.N_COILS:
                    currents = False
                    continue
                difference = max(abs(a - b) for a, b in zip(nominal, physical))
                maximum_current_difference = max(
                    float(maximum_current_difference or 0.0), difference
                )
                currents = bool(currents and difference <= d4.CURRENT_ATOL_A)
        finite = bool(
            full
            and all(math.isfinite(float(row[key])) for row in trajectory for key in ("R", "Z", "Ip"))
            and all(math.isfinite(float(value)) for row in trajectory for value in row["currents_a_tsc"])
            and not any(bool(row.get("abnormal")) for row in trajectory)
        )
        payload = d4._read(ctx.paths.variants / f"payload_{experiment_id}.json")
        minimum, maximum = d4.r4.r51.r8r7.r8.d1r11.s21.s13._current_limits_tsc(payload)
        minimum = [float(value) for value in minimum]
        maximum = [float(value) for value in maximum]
        maximum_utilization = 0.0
        current_shape = full and all(len(row.get("currents_a_tsc") or []) == d4.N_COILS for row in trajectory)
        if current_shape:
            for state in trajectory:
                for value, low, high in zip(state["currents_a_tsc"], minimum, maximum):
                    center = 0.5 * (low + high)
                    half = 0.5 * (high - low)
                    if half <= 0.0:
                        current_shape = False
                        continue
                    maximum_utilization = max(maximum_utilization, abs((float(value) - center) / half))
        action_shape = full and all(len(row.get("action_norm_tsc") or []) == d4.N_COILS for row in trace)
        total_actions = bool(
            action_shape
            and all(
                max(abs(float(value)) for value in row["action_norm_tsc"])
                <= float(contract["maximum_total_normalized_action_abs"]) + 1e-12
                for row in trace
            )
        )
        incremental_actions = bool(
            sequence
            and all(
                float(detail.get("incremental_normalized_action_linf", math.inf))
                <= float(contract["maximum_incremental_normalized_action_linf"]) + 1e-12
                for detail in details
            )
        )
        current_limit = bool(
            current_shape
            and maximum_utilization <= float(contract["maximum_current_utilization"]) + 1e-12
        )
        forbidden = sum(any(bool(row.get(key)) for key in d4.FORBIDDEN_KEYS) for row in trace)
        first_effect = bool(
            full
            and trajectory[d4.FIRST_ISSUE + 1]["action_norm_tsc"] == trace[d4.FIRST_ISSUE]["action_norm_tsc"]
            and trajectory[d4.FIRST_ISSUE + 1]["currents_a_tsc"] != trajectory[d4.FIRST_ISSUE]["currents_a_tsc"]
        )
        second_effect = bool(
            full
            and trajectory[d4.SECOND_ISSUE + 1]["action_norm_tsc"] == trace[d4.SECOND_ISSUE]["action_norm_tsc"]
            and trajectory[d4.SECOND_ISSUE + 1]["currents_a_tsc"] != trajectory[d4.SECOND_ISSUE]["currents_a_tsc"]
        )
        q0_digest = d4._digest(d4._prefix_payload(result, 13, 12)) if full else ""
        first_digest = d4._digest(d4._prefix_payload(result, 19, 18)) if full else ""
        context_key = (str(spec["pair_id"]), str(spec["history_member"]))
        first_key = (*context_key, str(spec["first_candidate_id"]))
        q0_prefixes[context_key].append(q0_digest)
        first_prefixes[first_key].append(first_digest)
        event_digest = d4._digest(details) if details else ""
        passed = bool(
            result.get("completed") and result.get("success")
            and result.get("spec") == spec and full and restart
            and source_prefix_state and source_prefix_trace and calibration
            and sequence and gates and offline_semantics
            and action_exact and currents and finite and forbidden == 0
            and first_effect and second_effect
            and total_actions and incremental_actions and current_limit
        )
        rows.append(
            {
                "experiment_id": experiment_id, "pair_id": str(spec["pair_id"]),
                "history_member": str(spec["history_member"]),
                "first_candidate_id": str(spec["first_candidate_id"]),
                "event_stream_digest": event_digest,
                "authentic_restart": restart,
                "source_prefix_state_exact": source_prefix_state,
                "source_prefix_trace_exact": source_prefix_trace,
                "calibration_exact": calibration,
                "offline_event_semantics_exact": offline_semantics,
                "forbidden_trace_count": forbidden,
                "maximum_event_nominal_current_difference_a": maximum_current_difference,
                "maximum_current_utilization": maximum_utilization if current_shape else None,
                "q0_prefix_digest": q0_digest, "first_prefix_digest": first_digest,
                "passed": passed,
            }
        )
    q0_exact = {
        key: len(values) == 25 and len(set(values)) == 1 and bool(values[0])
        for key, values in q0_prefixes.items()
    }
    first_exact = {
        key: len(values) == 5 and len(set(values)) == 1 and bool(values[0])
        for key, values in first_prefixes.items()
    }
    for row in rows:
        context_key = (str(row["pair_id"]), str(row["history_member"]))
        first_key = (*context_key, str(row["first_candidate_id"]))
        row["within_context_q0_prefix_exact"] = bool(q0_exact.get(context_key))
        row["within_first_candidate_prefix_exact"] = bool(first_exact.get(first_key))
        row["passed"] = bool(
            row["passed"]
            and row["within_context_q0_prefix_exact"]
            and row["within_first_candidate_prefix_exact"]
        )
    agreement = bool(
        len(rows) == len(primary_rows) == 250
        and all(
            row["passed"] == primary_rows[row["experiment_id"]]["passed"]
            and row["event_stream_digest"] == primary_rows[row["experiment_id"]]["event_stream_digest"]
            and row["authentic_restart"] == primary_rows[row["experiment_id"]]["authentic_restart"]
            and row["source_prefix_state_exact"] == primary_rows[row["experiment_id"]]["source_prefix_state_exact"]
            and row["source_prefix_trace_exact"] == primary_rows[row["experiment_id"]]["source_prefix_trace_exact"]
            and row["calibration_exact"] == primary_rows[row["experiment_id"]]["calibration_exact"]
            and row["offline_event_semantics_exact"] == primary_rows[row["experiment_id"]]["offline_event_semantics_exact"]
            and row["forbidden_trace_count"] == primary_rows[row["experiment_id"]]["forbidden_trace_count"]
            and row["within_context_q0_prefix_exact"] == primary_rows[row["experiment_id"]]["within_context_q0_prefix_exact"]
            and row["within_first_candidate_prefix_exact"] == primary_rows[row["experiment_id"]]["within_first_candidate_prefix_exact"]
            for row in rows
        )
    )
    inventory = d4.r4.r51.r8r7.r8._inventory(ctx.paths.raw)
    report = {
        "schema_version": 1, "stage": d4.STAGE,
        "phase": "raw_integrity_independent", "raw_inventory": inventory,
        "strict_parse_count": len(rows),
        "passed_count": sum(bool(row["passed"]) for row in rows),
        "authentic_restart_count": sum(bool(row["authentic_restart"]) for row in rows),
        "source_prefix_state_exact_count": sum(bool(row["source_prefix_state_exact"]) for row in rows),
        "source_prefix_trace_exact_count": sum(bool(row["source_prefix_trace_exact"]) for row in rows),
        "calibration_exact_count": sum(bool(row["calibration_exact"]) for row in rows),
        "offline_event_semantics_exact_count": sum(bool(row["offline_event_semantics_exact"]) for row in rows),
        "independent_event_stream_digest": d4._digest([(row["experiment_id"], row["event_stream_digest"]) for row in rows]),
        "maximum_event_nominal_current_difference_a": max(
            (
                float(row["maximum_event_nominal_current_difference_a"])
                for row in rows
                if row["maximum_event_nominal_current_difference_a"] is not None
            ),
            default=None,
        ),
        "primary_agreement": agreement, "response_outcomes_opened": False,
        "passed": bool(
            inventory.get("count") == 250 and len(rows) == 250
            and all(bool(row["passed"]) for row in rows) and agreement
        ),
    }
    d4._write(ctx.paths.analysis / "raw_integrity_independent.json", report)
    return report


def _authority(rows: Sequence[Mapping[str, Any]], baseline_pass: int) -> dict[str, Any]:
    groups: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(str(row["pair_id"]), str(row["history_member"]))].append(row)
    contexts = []
    for key, group in sorted(groups.items()):
        baseline = next(row for row in group if row["partition"] == "baseline")
        candidates = [row for row in group if row["partition"] == "candidate"]
        best = max(
            candidates,
            key=lambda row: (
                float(row["formal_minimum_signed_margin"]),
                float(row["formal_mean_signed_margin"]),
                -int(row["first_candidate_index"]), -int(row["second_candidate_index"]),
            ),
        )
        gain = float(best["formal_minimum_signed_margin"]) - float(baseline["formal_minimum_signed_margin"])
        contexts.append(
            {
                "pair_id": key[0], "history_member": key[1],
                "best_first_candidate_id": str(best["first_candidate_id"]),
                "best_second_candidate_id": str(best["second_candidate_id"]),
                "gain": gain,
                "repair": any(bool(row["formal_contract_pass"]) for row in candidates),
            }
        )
    repairs = sum(bool(row["repair"]) for row in contexts)
    gains = [float(row["gain"]) for row in contexts]
    return {
        "context_count": len(groups),
        "candidate_formal_pass_count": sum(bool(row["formal_contract_pass"]) for row in rows if row["partition"] == "candidate"),
        "candidate_formal_pass_context_count": sum(
            any(bool(row["formal_contract_pass"]) for row in group if row["partition"] == "candidate")
            for group in groups.values()
        ),
        "repaired_failed_baseline_count": repairs,
        "failed_baseline_strict_margin_improvement_count": sum(float(row["gain"]) > 1e-12 for row in contexts),
        "measured_oracle_formal_pass_count": baseline_pass + repairs,
        "best_candidate_minimum_margin_gain_minimum": min(gains),
        "best_candidate_minimum_margin_gain_median": statistics.median(gains),
        "best_candidate_minimum_margin_gain_maximum": max(gains),
    }


def formal(ctx: d4.Context) -> dict[str, Any]:
    primary = d4._read(ctx.paths.analysis / "primary_detailed.json")
    integrity = d4._read(ctx.paths.analysis / "raw_integrity_independent.json")
    specs = d4._saved_specs(ctx)
    _, sources = d4.r4.r51._source_baselines(ctx.r4_ctx.base_ctx)
    rows = []
    for baseline_id in ctx.cfg["matrix_contract"]["failed_source_baseline_ids"]:
        result = sources[str(baseline_id)]
        spec = result["spec"]
        rows.append(
            {
                "experiment_id": str(baseline_id), "partition": "baseline",
                "pair_id": str(spec["pair_id"]), "history_member": str(spec["history_member"]),
                "first_candidate_id": "baseline", "second_candidate_id": "baseline",
                **r51r3_ind.scalar_formal_metric(spec, result["trajectory"], ctx.cfg["formal_contract"]),
            }
        )
    for spec in specs:
        result = d4.r4.r51.r8r7.r8._read_gz(ctx.paths.raw / f"{spec['experiment_id']}.json.gz")
        rows.append(
            {
                "experiment_id": str(spec["experiment_id"]), "partition": "candidate",
                "pair_id": str(spec["pair_id"]), "history_member": str(spec["history_member"]),
                "first_candidate_id": str(spec["first_candidate_id"]),
                "second_candidate_id": str(spec["second_candidate_id"]),
                "first_candidate_index": int(spec["first_candidate_index"]),
                "second_candidate_index": int(spec["second_candidate_index"]),
                **r51r3_ind.scalar_formal_metric(spec, result["trajectory"], ctx.cfg["formal_contract"]),
            }
        )
    rows.sort(key=lambda row: (
        row["pair_id"], row["history_member"],
        0 if row["partition"] == "baseline" else 1,
        int(row.get("first_candidate_index", -1)), int(row.get("second_candidate_index", -1)),
        row["experiment_id"],
    ))
    result = _authority(rows, int(ctx.cfg["known_aggregate_contract"]["baseline_formal_pass_count"]))
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
            and row["first_candidate_id"] == other["first_candidate_id"]
            and row["second_candidate_id"] == other["second_candidate_id"]
            and bool(row["formal_contract_pass"]) == bool(other["formal_contract_pass"])
            and int(row["formal_best_arrival_ms"]) == int(other["formal_best_arrival_ms"])
        )
        for key in ("formal_minimum_signed_margin", "formal_mean_signed_margin"):
            maximum = max(maximum, abs(float(row[key]) - float(other[key])))
    compare_keys = (
        "candidate_formal_pass_count", "candidate_formal_pass_context_count",
        "repaired_failed_baseline_count", "failed_baseline_strict_margin_improvement_count",
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
        integrity.get("passed") is True and len(rows) == 260
        and result["context_count"] == 10 and discrete and numerical and outcome
    )
    scientific = bool(
        integrity_passed and result["repaired_failed_baseline_count"] >= 1
        and result["measured_oracle_formal_pass_count"] >= 7
    )
    route = ctx.cfg["routes"][
        "execution_fail" if not integrity_passed
        else ("pass" if scientific else "authority_insufficient")
    ]
    report = {
        "schema_version": 1, "stage": d4.STAGE, "phase": "formal_independent",
        **result, "independent_formal_metric_digest": d4._digest(rows),
        "primary_discrete_agreement": discrete,
        "primary_numerical_agreement": numerical,
        "primary_outcome_agreement": outcome,
        "maximum_primary_numerical_difference": maximum,
        "audit_passed": integrity_passed, "scientific_gate_passed": scientific,
        "route": route, "passed": scientific,
    }
    d4._write(ctx.paths.analysis / "formal_independent.json", report)
    return report


def main() -> None:
    args = d4._parser().parse_args()
    ctx = d4.load_context(args)
    if args.command == "offline":
        report = offline(ctx)
    elif args.command == "run":
        report = raw(ctx)
    elif args.command == "finalize-primary":
        report = formal(ctx)
    else:
        raise ValueError(f"unsupported R8R51R4D4 independent command: {args.command}")
    print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
