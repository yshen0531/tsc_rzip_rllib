"""Independent scalar R8R51R4D1 exact schedule reconstruction."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r51r4_failed_context_sustained_transport_dwell_sentinel
    as r4,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r51r4d1_two_transport_exact_return_schedule_preflight
    as d1,
)


def _read(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream, parse_constant=lambda token: (_ for _ in ()).throw(
            ValueError(f"non-finite JSON token {token} in {path}")
        ))


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode(
            "utf-8"
        )
    ).hexdigest()


def _write_new(path: Path, value: Any) -> None:
    if path.exists():
        raise ValueError(f"R8R51R4D1 independent output exists: {path}")
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _payload_inventory(path: Path) -> dict[str, Any]:
    rows = []
    for item in sorted(path.glob("payload_*.json")):
        rows.append({"name": item.name, "size": item.stat().st_size, "sha256": _sha(item)})
    return {
        "count": len(rows),
        "bytes": sum(int(row["size"]) for row in rows),
        "digest": _digest(rows),
    }


def authenticate_source(ctx: d1.Context) -> dict[str, Any]:
    expected = ctx.cfg["source_r51r4"]
    inherited = r4.authenticate_sources(ctx.r4_ctx)
    hashes = {}
    for key, relative in d1.ARTIFACTS.items():
        path = ctx.r4_stage / relative
        if not path.is_file():
            raise d1.SourceBlockedError(f"R8R51R4D1 independent source missing: {relative}")
        hashes[key] = _sha(path)
        if hashes[key] != expected[f"{key}_sha256"]:
            raise d1.SourceBlockedError(f"R8R51R4D1 independent source changed: {relative}")
    raw = r4.r51.r8r7.r8._inventory(ctx.r4_stage / "raw")
    payload = _payload_inventory(ctx.r4_stage / "variants")
    if (
        int(raw["count"]) != int(expected["raw_count"])
        or int(raw["bytes"]) != int(expected["raw_bytes"])
        or raw["digest"] != expected["raw_digest"]
        or int(payload["count"]) != int(expected["payload_count"])
        or int(payload["bytes"]) != int(expected["payload_bytes"])
        or payload["digest"] != expected["payload_digest"]
    ):
        raise d1.SourceBlockedError("R8R51R4D1 independent source inventory changed")
    raw_primary = _read(ctx.r4_stage / d1.ARTIFACTS["hotfix_raw_primary"])
    raw_independent = _read(ctx.r4_stage / d1.ARTIFACTS["hotfix_raw_independent"])
    summary = _read(ctx.r4_stage / d1.ARTIFACTS["hotfix_formal_summary"])
    formal_independent = _read(ctx.r4_stage / d1.ARTIFACTS["hotfix_formal_independent"])
    final = _read(ctx.r4_stage / d1.ARTIFACTS["hotfix_final"])
    server = _read(ctx.r4_stage / d1.ARTIFACTS["hotfix_server_evidence"])
    valid = (
        inherited.get("passed") is True
        and raw_primary.get("passed") is True
        and raw_independent.get("passed") is True
        and raw_independent.get("primary_agreement") is True
        and int(raw_primary.get("passed_count", -1)) == 100
        and summary.get("integrity_gate_passed") is True
        and summary.get("scientific_gate_passed") is False
        and int(summary.get("candidate_formal_pass_count", -1)) == 0
        and int(summary.get("repaired_failed_baseline_count", -1)) == 0
        and int(summary.get("measured_oracle_formal_pass_count", -1)) == 6
        and formal_independent.get("audit_passed") is True
        and formal_independent.get("primary_discrete_agreement") is True
        and formal_independent.get("primary_numerical_agreement") is True
        and final.get("audit_passed") is True
        and final.get("independent_agreement") is True
        and final.get("passed") is False
        and final.get("route") == expected["required_route"]
        and final.get("all_stage_trajectories_allowed_in_expert_dataset") is False
        and (server.get("final") or {}).get("r51r5_executed") is False
        and (server.get("final") or {}).get("route") == expected["required_route"]
    )
    if not valid:
        raise d1.SourceBlockedError("R8R51R4D1 independent final provenance changed")
    return {
        "hashes": hashes,
        "raw_count": int(raw["count"]),
        "raw_digest": raw["digest"],
        "payload_count": int(payload["count"]),
        "payload_digest": payload["digest"],
        "inherited_digest": _digest(inherited),
        "required_route": expected["required_route"],
        "response_values_available_to_construction": False,
        "passed": True,
    }


def _dot(left: Sequence[float], right: Sequence[float]) -> float:
    return sum(float(a) * float(b) for a, b in zip(left, right))


def _norm(values: Sequence[float]) -> float:
    return math.sqrt(sum(float(value) * float(value) for value in values))


def _solve(matrix: list[list[float]], vector: list[float]) -> list[float]:
    n = len(vector)
    augmented = [list(map(float, matrix[row])) + [float(vector[row])] for row in range(n)]
    for column in range(n):
        pivot = max(range(column, n), key=lambda row: abs(augmented[row][column]))
        if abs(augmented[pivot][column]) <= 1e-24:
            raise ValueError("R8R51R4D1 independent basis is singular")
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        scale = augmented[column][column]
        augmented[column] = [value / scale for value in augmented[column]]
        for row in range(n):
            if row == column:
                continue
            factor = augmented[row][column]
            augmented[row] = [
                augmented[row][index] - factor * augmented[column][index]
                for index in range(n + 1)
            ]
    return [augmented[row][-1] for row in range(n)]


def _geometry(
    before: Sequence[float],
    after: Sequence[float],
    desired_target: Sequence[float],
    field_basis: Sequence[Sequence[float]],
    turns: Sequence[float],
) -> tuple[float, float]:
    desired = [float(target) - float(start) for target, start in zip(desired_target, before)]
    actual = [float(end) - float(start) for end, start in zip(after, before)]
    if all(value == 0.0 for value in actual):
        return 1.0, 0.0
    basis = [
        [float(field_basis[row][column]) * 1000.0 / float(turns[row]) for column in range(4)]
        for row in range(d1.N_COILS)
    ]
    gram = [[sum(basis[row][i] * basis[row][j] for row in range(d1.N_COILS)) for j in range(4)] for i in range(4)]
    rhs = [sum(basis[row][i] * actual[row] for row in range(d1.N_COILS)) for i in range(4)]
    coordinate = _solve(gram, rhs)
    reconstructed = [sum(basis[row][column] * coordinate[column] for column in range(4)) for row in range(d1.N_COILS)]
    residual = [actual[index] - reconstructed[index] for index in range(d1.N_COILS)]
    cosine = _dot(desired, actual) / max(_norm(desired) * _norm(actual), 1e-300)
    off_basis = _norm(residual) / max(_norm(actual), 1e-300)
    return float(cosine), float(off_basis)


def _canonical_event(event: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "event": str(event.get("event", "")),
        "task_step": int(event["task_step"]),
        "target_card15_fields": list(event.get("target_card15_fields") or event.get("stored_target_card15_fields") or ()),
        "action_norm_tsc": [float(value) for value in event.get("action_norm_tsc") or ()],
        "nominal_readback_current_a_tsc": [float(value) for value in event.get("nominal_readback_current_a_tsc") or event.get("nominal_issue_readback_current_a_tsc") or ()],
        "criteria": {str(key): bool(value) for key, value in sorted((event.get("criteria") or {}).items())},
        "passed": bool(event.get("passed")),
    }


def _runtime_parts(ctx: d1.Context, source_spec: Mapping[str, Any]) -> tuple[Any, Any, list[list[float]], Mapping[str, Any], Mapping[str, Any]]:
    _, sources = r4.r51._source_baselines(ctx.r4_ctx.base_ctx)
    source = sources[str(source_spec["source_r8r7_baseline_experiment_id"])]
    execution = r4._execution_context(ctx.r4_ctx)
    lattice = execution.d1r11_ctx.base_ctx.base_ctx.cfg["lattice_probe"]
    contract = r4._controller_contract(ctx.r4_ctx)
    payload = _read(ctx.r4_stage / "variants" / f"payload_{source_spec['experiment_id']}.json")
    actuator = r4.r51.r8r22.mpc.actuator_from_payload(payload, lattice)
    raw_basis = r4.r51.r8r22._fixed_basis(source)
    field_basis = [[float(raw_basis[row, column]) for column in range(4)] for row in range(d1.N_COILS)]
    return actuator, source, field_basis, lattice, contract


def _construct_row(
    ctx: d1.Context,
    spec: Mapping[str, Any],
    source_by_experiment: Mapping[str, Mapping[str, Any]],
    cache: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    first_spec = source_by_experiment[str(spec["first_source_experiment_id"])]
    second_spec = source_by_experiment[str(spec["second_source_experiment_id"])]
    for source_spec in (first_spec, second_spec):
        key = str(source_spec["experiment_id"])
        if key not in cache:
            cache[key] = r4.construct_event_stream(ctx.r4_ctx, source_spec, include_events=True)
    first_base = cache[str(first_spec["experiment_id"])]
    second_base = cache[str(second_spec["experiment_id"])]
    first_events = first_base["events"]
    second_events = second_base["events"]
    first_issue = next(event for event in first_events if int(event["task_step"]) == d1.FIRST_ISSUE_STEP)
    second_source_issue = next(event for event in second_events if int(event["task_step"]) == d1.FIRST_ISSUE_STEP)
    prefix = [json.loads(json.dumps(event, allow_nan=False)) for event in first_events if int(event["task_step"]) <= 15]
    if tuple(int(event["task_step"]) for event in prefix) != (10, 11, 12, 13, 14, 15):
        raise ValueError("R8R51R4D1 independent prefix changed")
    actuator, _, field_basis, lattice, contract = _runtime_parts(ctx, first_spec)
    current = [float(value) for value in prefix[-1]["nominal_readback_current_a_tsc"]]
    second = r4.r51.r8r22._refresh_event(
        task_step=d1.SECOND_ISSUE_STEP,
        currents=current,
        target_fields=second_source_issue["target_card15_fields"],
        actuator=actuator,
        turns_tsc=actuator.turns_tsc,
        max_delta_a=actuator.max_slew_step_a,
        minimum_current=actuator.minimum_current_a_tsc,
        maximum_current=actuator.maximum_current_a_tsc,
        lattice_cfg=lattice,
        contract=contract,
    )
    second["event"] = "second_transport_exact_target_issue"
    second["candidate_id"] = str(spec["second_candidate_id"])
    second["target_card15_fields"] = list(second["stored_target_card15_fields"])
    after_second = [float(value) for value in second["nominal_readback_current_a_tsc"]]
    cosine, off_basis = _geometry(
        current,
        after_second,
        [float(value) for value in second_source_issue["nominal_issue_readback_current_a_tsc"]],
        field_basis,
        [float(value) for value in actuator.turns_tsc],
    )
    equal_pair = str(spec["first_candidate_id"]) == str(spec["second_candidate_id"])
    zero_second = all(float(value) == 0.0 for value in second["action_norm_tsc"])
    second["desired_applied_current_cosine"] = cosine
    second["relative_off_basis_residual"] = off_basis
    second["criteria"].update(
        {
            "cosine": cosine >= float(contract["minimum_desired_applied_current_cosine"]) - 1e-12,
            "off_basis": off_basis <= float(contract["maximum_relative_off_basis_residual"]) + 1e-12,
            "equal_pair_zero_increment": (not equal_pair) or zero_second,
            "distinct_pair_nonzero_increment": equal_pair or (not zero_second),
            "source_target_exact": list(second["stored_target_card15_fields"])
            == list(second_source_issue["target_card15_fields"]),
        }
    )
    second["passed"] = all(bool(value) for value in second["criteria"].values())
    events = prefix + [second]
    current = after_second
    for step in (17, 18, 19):
        hold = r4.r51._observe_event(
            task_step=step,
            currents=current,
            target_fields=second["stored_target_card15_fields"],
            actuator=actuator,
            contract=contract,
            event="second_transport_exact_target_hold",
        )
        events.append(hold)
        current = [float(value) for value in hold["nominal_readback_current_a_tsc"]]
    returned = r4.r51._return_event(
        task_step=d1.RETURN_STEP,
        currents=current,
        center_fields=first_events[0]["q0_center_card15_fields"],
        issue_event={
            "target_card15_fields": list(second["stored_target_card15_fields"]),
            "center_nominal_readback_current_a_tsc": list(first_issue["center_nominal_readback_current_a_tsc"]),
        },
        field_basis=field_basis,
        actuator=actuator,
        lattice=lattice,
        contract=contract,
    )
    returned["event"] = "two_transport_stored_center_return"
    events.append(returned)
    current = [float(value) for value in returned["nominal_readback_current_a_tsc"]]
    for step in range(d1.RETURN_STEP + 1, int(spec["horizon_steps"])):
        refresh = r4.r51.r8r22._refresh_event(
            task_step=step,
            currents=current,
            target_fields=first_events[0]["q0_center_card15_fields"],
            actuator=actuator,
            turns_tsc=actuator.turns_tsc,
            max_delta_a=actuator.max_slew_step_a,
            minimum_current=actuator.minimum_current_a_tsc,
            maximum_current=actuator.maximum_current_a_tsc,
            lattice_cfg=lattice,
            contract=contract,
        )
        refresh["event"] = "post_two_transport_exact_center_refresh"
        events.append(refresh)
        current = [float(value) for value in refresh["nominal_readback_current_a_tsc"]]
    center_current = [float(value) for value in first_issue["center_nominal_readback_current_a_tsc"]]
    post_return = events[events.index(returned) + 1 :]
    numerical = [
        float(event[key])
        for event in events
        for key in ("incremental_normalized_action_linf", "total_normalized_action_abs", "predicted_current_utilization")
        if key in event
    ] + [cosine, off_basis]
    criteria = {
        "source_first_event_stream_pass": bool(first_base["passed"]),
        "source_second_event_stream_pass": bool(second_base["passed"]),
        "fixed_task_clock": tuple(int(event["task_step"]) for event in events)
        == tuple(range(d1.Q0_STEP, int(spec["horizon_steps"]))),
        "q0_integration_action": float(events[0]["incremental_normalized_action_linf"])
        <= float(ctx.cfg["action_contract"]["maximum_q0_integration_action_linf"]) + 1e-12,
        "second_target_exact": list(second["stored_target_card15_fields"])
        == list(second_source_issue["target_card15_fields"]),
        "equal_pair_zero_increment": (not equal_pair) or zero_second,
        "distinct_pair_nonzero_increment": equal_pair or (not zero_second),
        "all_event_gates": all(bool(event.get("passed")) for event in events),
        "stored_center_return": bool(returned["passed"]),
        "stored_center_current_exact": [
            float(value) for value in returned["nominal_readback_current_a_tsc"]
        ] == center_current,
        "post_return_center_exact": all(
            list(event["stored_target_card15_fields"]) == list(first_events[0]["q0_center_card15_fields"])
            and [float(value) for value in event["nominal_readback_current_a_tsc"]] == center_current
            for event in post_return
        ),
        "incremental_action_limits": all(
            float(event["incremental_normalized_action_linf"])
            <= float(ctx.cfg["action_contract"]["maximum_incremental_normalized_action_linf"]) + 1e-12
            for event in events
        ),
        "total_action_limits": all(
            max(abs(float(value)) for value in (event.get("action_norm_tsc") or [math.inf]))
            <= float(ctx.cfg["action_contract"]["maximum_total_normalized_action_abs"]) + 1e-12
            for event in events
        ),
        "current_utilization_limits": all(
            float(event["predicted_current_utilization"])
            <= float(ctx.cfg["action_contract"]["maximum_current_utilization"]) + 1e-12
            for event in events
        ),
        "finite": all(math.isfinite(value) for value in numerical),
        "no_response_input": spec.get("source_result_available_to_construction") is False,
        "learning_forbidden": spec.get("allowed_in_expert_dataset") is False,
    }
    return {
        "experiment_id": str(spec["experiment_id"]),
        "context_index": int(spec["context_index"]),
        "pair_id": str(spec["pair_id"]),
        "history_member": str(spec["history_member"]),
        "first_candidate_id": str(spec["first_candidate_id"]),
        "second_candidate_id": str(spec["second_candidate_id"]),
        "equal_pair": equal_pair,
        "event_count": len(events),
        "action_stream_digest": _digest([_canonical_event(event) for event in events]),
        "maximum_incremental_action_linf": max(float(event.get("incremental_normalized_action_linf", 0.0)) for event in events),
        "maximum_total_normalized_action_abs": max(float(event.get("total_normalized_action_abs", 0.0)) for event in events),
        "maximum_predicted_current_utilization": max(float(event.get("predicted_current_utilization", 0.0)) for event in events),
        "second_transition_cosine": cosine,
        "second_transition_relative_off_basis_residual": off_basis,
        "second_transition_incremental_action_linf": float(second["incremental_normalized_action_linf"]),
        "return_incremental_action_linf": float(returned["incremental_normalized_action_linf"]),
        "post_return_refresh_zero_increment_diagnostic": all(
            all(float(value) == 0.0 for value in event["action_norm_tsc"])
            for event in post_return
        ),
        "criteria": criteria,
        "eligible": all(bool(value) for value in criteria.values()),
    }


def _coverage(rows: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]) -> dict[str, Any]:
    candidate_set = set(d1.CANDIDATE_IDS)
    contexts = []
    for context_index in range(10):
        current = [row for row in rows if int(row["context_index"]) == context_index]
        eligible = [row for row in current if row["eligible"]]
        first = {str(row["first_candidate_id"]) for row in eligible}
        second = {str(row["second_candidate_id"]) for row in eligible}
        successor_counts = {}
        for candidate in d1.CANDIDATE_IDS:
            successor_counts[candidate] = len({
                str(row["second_candidate_id"])
                for row in eligible
                if str(row["first_candidate_id"]) == candidate
                and str(row["second_candidate_id"]) != candidate
            })
        gates = {
            "all_ordered_pairs_reported": len(current) == 25,
            "minimum_eligible_pairs": len(eligible) >= int(cfg["coverage_gate"]["minimum_eligible_ordered_pairs_per_context"]),
            "all_first_candidates_supported": first == candidate_set,
            "all_second_candidates_supported": second == candidate_set,
            "distinct_successor_per_first": all(value >= 1 for value in successor_counts.values()),
        }
        contexts.append({
            "context_index": context_index,
            "pair_id": str(current[0]["pair_id"]),
            "history_member": str(current[0]["history_member"]),
            "eligible_pair_count": len(eligible),
            "eligible_pair_ids": sorted(f"{row['first_candidate_id']}->{row['second_candidate_id']}" for row in eligible),
            "first_candidate_count": len(first),
            "second_candidate_count": len(second),
            "distinct_successor_counts": successor_counts,
            "gates": gates,
            "passed": all(gates.values()),
        })
    history_pairs = []
    for pair_id in sorted({str(row["pair_id"]) for row in contexts}):
        members = [row for row in contexts if row["pair_id"] == pair_id]
        equal = len(members) == 2 and members[0]["eligible_pair_ids"] == members[1]["eligible_pair_ids"]
        history_pairs.append({"pair_id": pair_id, "eligible_pair_set_equal": equal})
    gates = {
        "all_specifications_reported": len(rows) == 250,
        "all_context_gates": len(contexts) == 10 and all(row["passed"] for row in contexts),
        "history_pair_count": len(history_pairs) == int(cfg["coverage_gate"]["required_history_pair_count"]),
        "history_pair_eligible_sets_equal": all(row["eligible_pair_set_equal"] for row in history_pairs),
    }
    return {
        "eligible_specification_count": sum(bool(row["eligible"]) for row in rows),
        "context_pass_count": sum(bool(row["passed"]) for row in contexts),
        "history_pair_pass_count": sum(bool(row["eligible_pair_set_equal"]) for row in history_pairs),
        "contexts": contexts,
        "history_pairs": history_pairs,
        "gates": gates,
        "passed": all(gates.values()),
    }


def run_independent(ctx: d1.Context) -> dict[str, Any]:
    primary_path = ctx.paths.analysis / "offline_primary.json"
    construction_path = ctx.paths.analysis / "offline_construction_primary.json"
    specs_path = ctx.paths.specs / "all_specs.json"
    if not all(path.is_file() for path in (primary_path, construction_path, specs_path, ctx.paths.manifest, ctx.paths.state)):
        raise ValueError("R8R51R4D1 primary artifacts missing")
    primary = _read(primary_path)
    primary_construction = _read(construction_path)
    manifest = _read(ctx.paths.manifest)
    specs = _read(specs_path)
    if (
        len(specs) != 250
        or _digest(specs) != manifest.get("spec_digest")
        or _sha(ctx.config_path) != manifest.get("config_sha256")
    ):
        raise ValueError("R8R51R4D1 primary identity changed")
    authentication = authenticate_source(ctx)
    source_rows = _read(ctx.r4_stage / "specs/all_specs.json")
    source_by_experiment = {str(row["experiment_id"]): row for row in source_rows}
    cache: dict[str, dict[str, Any]] = {}
    rows = [_construct_row(ctx, spec, source_by_experiment, cache) for spec in specs]
    coverage = _coverage(rows, ctx.cfg)
    primary_by_id = {str(row["experiment_id"]): row for row in primary_construction["rows"]}
    discrete_agreement = len(primary_by_id) == len(rows) and all(
        str(row["experiment_id"]) in primary_by_id
        and bool(primary_by_id[str(row["experiment_id"])]["eligible"]) == bool(row["eligible"])
        and primary_by_id[str(row["experiment_id"])]["criteria"] == row["criteria"]
        and primary_by_id[str(row["experiment_id"])]["action_stream_digest"] == row["action_stream_digest"]
        and bool(primary_by_id[str(row["experiment_id"])]["post_return_refresh_zero_increment_diagnostic"])
        == bool(row["post_return_refresh_zero_increment_diagnostic"])
        for row in rows
    )
    numerical_keys = (
        "maximum_incremental_action_linf", "maximum_total_normalized_action_abs",
        "maximum_predicted_current_utilization", "second_transition_cosine",
        "second_transition_relative_off_basis_residual",
        "second_transition_incremental_action_linf", "return_incremental_action_linf",
    )
    maximum_difference = max(
        abs(float(row[key]) - float(primary_by_id[str(row["experiment_id"])][key]))
        for row in rows for key in numerical_keys
    )
    primary_coverage = primary_construction["coverage"]
    coverage_agreement = (
        coverage["eligible_specification_count"] == primary_coverage["eligible_specification_count"]
        and coverage["context_pass_count"] == primary_coverage["context_pass_count"]
        and coverage["history_pair_pass_count"] == primary_coverage["history_pair_pass_count"]
        and [row["eligible_pair_ids"] for row in coverage["contexts"]]
        == [row["eligible_pair_ids"] for row in primary_coverage["contexts"]]
        and coverage["gates"] == primary_coverage["gates"]
    )
    numerical_agreement = maximum_difference <= 1e-10
    action_stream_digest = _digest([(row["experiment_id"], row["action_stream_digest"]) for row in rows])
    action_stream_preserved = bool(
        action_stream_digest == ctx.cfg["reporting_fix_required_action_stream_digest"]
        and primary.get("action_stream_digest") == action_stream_digest
    )
    audit_passed = bool(
        authentication["passed"] and discrete_agreement and coverage_agreement
        and numerical_agreement and action_stream_preserved
    )
    scientific_passed = bool(audit_passed and coverage["passed"] and primary.get("passed") is True)
    route = ctx.cfg["routes"]["pass" if scientific_passed else "geometry_fail"]
    report = {
        "schema_version": 1,
        "stage": d1.STAGE,
        "phase": "offline_independent",
        "source_authenticated": True,
        "specification_count": len(rows),
        "eligible_specification_count": coverage["eligible_specification_count"],
        "context_pass_count": coverage["context_pass_count"],
        "history_pair_pass_count": coverage["history_pair_pass_count"],
        "action_stream_digest": action_stream_digest,
        "primary_action_stream_digest": primary.get("action_stream_digest"),
        "frozen_action_stream_preserved": action_stream_preserved,
        "primary_discrete_agreement": discrete_agreement,
        "primary_coverage_agreement": coverage_agreement,
        "primary_numerical_agreement": numerical_agreement,
        "maximum_primary_numerical_difference": maximum_difference,
        "coverage": coverage,
        "rows": rows,
        "audit_passed": audit_passed,
        "scientific_gate_passed": scientific_passed,
        "new_tsc_count": 0,
        "plant_step_count": 0,
        "response_values_used": False,
        "route": route,
        "passed": audit_passed,
    }
    _write_new(ctx.paths.analysis / "offline_independent.json", report)
    final = {
        "schema_version": 1,
        "stage": d1.STAGE,
        "phase": "final",
        "source_authenticated": True,
        "audit_passed": audit_passed,
        "scientific_gate_passed": scientific_passed,
        "specification_count": len(rows),
        "eligible_specification_count": coverage["eligible_specification_count"],
        "context_pass_count": coverage["context_pass_count"],
        "history_pair_pass_count": coverage["history_pair_pass_count"],
        "primary_independent_maximum_numerical_difference": maximum_difference,
        "new_tsc_count": 0,
        "new_raw_count": 0,
        "plant_step_count": 0,
        "controller_execution_count": 0,
        "model_fit_count": 0,
        "optimization_count": 0,
        "response_values_used": False,
        "all_stage_trajectories_allowed_in_expert_dataset": False,
        "route": route,
        "passed": scientific_passed,
    }
    _write_new(ctx.paths.analysis / "final_report.json", final)
    state = _read(ctx.paths.state)
    state.update({
        "phase_status": "complete" if audit_passed else "independent_integrity_failed",
        "finished": True,
        "real_tsc_executed": False,
        "plant_step_count": 0,
        "new_raw_count": 0,
        "response_outcomes_opened": False,
        "route": route,
        "verdict": {"route": route, "passed": scientific_passed},
        "stop_reason": "" if scientific_passed else "two_transport_schedule_geometry_gate_failed",
        "offline_independent_sha256": _sha(ctx.paths.analysis / "offline_independent.json"),
        "final_report_sha256": _sha(ctx.paths.analysis / "final_report.json"),
    })
    d1._write(ctx.paths.state, state, replace=True)
    return final


def main() -> None:
    args = d1._parser().parse_args()
    if args.command != "offline":
        raise ValueError("R8R51R4D1 independent is zero-TSC and supports only offline")
    result = run_independent(d1.load_context(args))
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
