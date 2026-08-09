#!/usr/bin/env python3
"""Independent offline and server-raw recomputation for frozen R8R51R1."""

from __future__ import annotations

import json
from typing import Any

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r51r1_reduced_q0_transport_bridge_q0_gate_integration_sentinel
    as r49,
)


def _offline(ctx: r49.Context) -> dict[str, Any]:
    state = r49._read(ctx.paths.state)
    primary = r49._read(ctx.paths.analysis / "offline_primary.json")
    source = r49.authenticate_sources(ctx)
    specs = r49._saved_specs(ctx)
    construction = r49._offline_construction(ctx, specs)
    saved = r49._read(ctx.paths.analysis / "offline_construction.json")
    source_route = bool(
        source.get("r8r51_route") == ctx.cfg["source_r8r51"]["required_route"]
        and source.get("r8r48_route") == ctx.cfg["source_r8r48"]["required_route"]
        and source.get("r8r49_route") == ctx.cfg["source_r8r49"]["required_route"]
    )
    q0_gate = bool(
        len(construction.get("rows") or []) == 208
        and all(
            set(row.get("q0_criteria_keys") or ()) == r49.Q0_CRITERIA_KEYS
            and "q0_zero_target" not in (row.get("q0_criteria_keys") or ())
            and float(row.get("q0_increment", float("inf")))
            <= float(ctx.cfg["controller_contract"]["maximum_q0_integration_action_linf"]) + 1e-12
            for row in construction["rows"]
        )
    )
    design = r49._sha(ctx.config_path) == r49._read(ctx.paths.manifest).get("config_sha256")
    agreement = bool(
        construction == saved
        and int(primary.get("construction_count", -1)) == int(construction["construction_count"])
        and int(primary.get("construction_pass_count", -1)) == int(construction["construction_pass_count"])
        and bool(primary.get("passed")) == bool(construction["passed"])
        and state.get("phase_status") == ("offline_primary_ready" if construction["passed"] else "offline_failed")
    )
    report = {
        "schema_version": 1,
        "stage": r49.STAGE,
        "phase": "offline_independent",
        "source_route_authenticated": source_route,
        "design_authenticated": design,
        "spec_count": len(specs),
        "spec_digest": r49._digest(specs),
        "construction_count": construction["construction_count"],
        "construction_pass_count": construction["construction_pass_count"],
        "construction_digest": r49._digest(construction),
        "q0_shared_constructor_gate": q0_gate,
        "primary_agreement": agreement,
        "new_raw_count": 0,
        "plant_step_count": 0,
        "real_tsc_executed": False,
        "passed": bool(source_route and design and agreement and q0_gate and construction["passed"]),
    }
    r49._write(ctx.paths.analysis / "offline_independent.json", report)
    return report


def _raw(ctx: r49.Context) -> dict[str, Any]:
    state = r49._read(ctx.paths.state)
    primary = r49._read(ctx.paths.analysis / "raw_primary.json")
    recomputed = r49.audit_raw(ctx, write=False)
    keys = (
        "raw_inventory", "strict_parse_count", "runtime_success_count",
        "full_horizon_count", "authentic_restart_count",
        "source_prefix_state_exact_count", "source_prefix_trace_exact_count",
        "source_trace_difference_wrapper_only_count",
        "causal_forbidden_pass_count", "q0_exact_count",
        "q0_offline_parity_count", "q0_first_effect_at_issue_plus_one_count",
        "within_context_q0_prefix_exact_count", "candidate_exact_count",
        "candidate_issue_gate_pass_count", "first_effect_at_issue_plus_one_count",
        "finite_response_count", "stored_center_return_exact_count",
        "bridge_coverage_count", "passed_count", "safety_stop_count",
        "runtime_failure_count", "forbidden_trace_count",
        "maximum_current_utilization", "prefix_digest", "response_digest",
        "route", "passed",
    )
    agreement = all(primary.get(key) == recomputed.get(key) for key in keys)
    row_identity = [
        (
            row["experiment_id"], row["candidate_index"], row["candidate_id"],
            row["prefix_digest"], row["q0_offline_parity"],
            row["q0_first_effect_at_issue_plus_one"],
            r49._digest(row["response"]), row["passed"],
        )
        for row in recomputed["rows"]
    ]
    report = {
        "schema_version": 1,
        "stage": r49.STAGE,
        "phase": "raw_independent",
        **{key: recomputed[key] for key in keys if key != "passed"},
        "row_identity_digest": r49._digest(row_identity),
        "primary_agreement": agreement,
        "primary_route_agreement": primary.get("route") == recomputed.get("route"),
        "primary_response_digest_agreement": primary.get("response_digest") == recomputed.get("response_digest"),
        "state_ready": state.get("phase_status") == "raw_primary_ready",
        "passed": bool(
            recomputed["passed"]
            and agreement
            and primary.get("route") == recomputed.get("route")
            and primary.get("response_digest") == recomputed.get("response_digest")
            and state.get("phase_status") == "raw_primary_ready"
        ),
    }
    r49._write(ctx.paths.analysis / "raw_independent.json", report)
    return report


def main() -> None:
    args = r49._parser().parse_args()
    ctx = r49.load_context(args)
    if args.command == "offline":
        result = _offline(ctx)
    elif args.command == "run":
        result = _raw(ctx)
    else:
        raise ValueError("R8R51R1 independent command must be offline or run")
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
