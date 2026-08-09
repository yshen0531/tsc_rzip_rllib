"""Independent scalar reconstruction for the R8R51R4D3 action preflight."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r8r51r4d1_independent_forensics as d1i,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r51r4d3_center_bridged_two_pulse_schedule_preflight
    as d3,
)


def _read(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream, parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _write_new(path: Path, value: Any) -> None:
    if path.exists(): raise ValueError(f"R8R51R4D3 independent output exists: {path}")
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def _construct_row(ctx: d3.Context, spec: Mapping[str, Any], source_by_id: Mapping[str, Mapping[str, Any]], cache: dict[str, dict[str, Any]]) -> dict[str, Any]:
    d1 = d3.d1
    first_spec = source_by_id[str(spec["first_source_experiment_id"])]
    second_spec = source_by_id[str(spec["second_source_experiment_id"])]
    for source_spec in (first_spec, second_spec):
        key = str(source_spec["experiment_id"])
        if key not in cache: cache[key] = d1.r4.construct_event_stream(ctx.d1_ctx.r4_ctx, source_spec, include_events=True)
    first_base, second_base = cache[str(first_spec["experiment_id"])], cache[str(second_spec["experiment_id"])]
    first_events, second_events = first_base["events"], second_base["events"]
    events = [json.loads(json.dumps(event, allow_nan=False)) for event in first_events if int(event["task_step"]) <= 16]
    if tuple(int(event["task_step"]) for event in events) != tuple(range(10, 17)): raise ValueError("R8R51R4D3 independent first clock changed")
    first_issue, first_return = next(event for event in events if int(event["task_step"]) == 12), events[-1]
    actuator, _, raw_basis, lattice, contract = d1._runtime_parts(ctx.d1_ctx, first_spec)
    field_basis = [[float(raw_basis[row, column]) for column in range(4)] for row in range(d3.N_COILS)]
    center_fields = list(events[0]["q0_center_card15_fields"]); center_current = [float(v) for v in first_issue["center_nominal_readback_current_a_tsc"]]
    current = [float(v) for v in first_return["nominal_readback_current_a_tsc"]]
    bridge = d1.r4.r51._observe_event(task_step=17, currents=current, target_fields=center_fields, actuator=actuator, contract=contract, event="exact_q0_center_bridge_hold")
    events.append(bridge); current = [float(v) for v in bridge["nominal_readback_current_a_tsc"]]
    second_before = list(current)
    second = d1.r4.r51.r8r22._construct_coordinate_issue(task_step=18, currents_a_tsc=current, fixed_basis_delta_field_kat_tsc=raw_basis.T, requested_coordinate=spec["second_requested_coordinate"], candidate_id=str(spec["second_candidate_id"]), actuator=actuator, controller_cfg=contract, lattice_cfg=lattice)
    second["center_nominal_readback_current_a_tsc"] = list(current); second["event"] = "second_center_bridged_candidate_issue"
    events.append(second); current = [float(v) for v in second["nominal_issue_readback_current_a_tsc"]]
    for step in (19, 20, 21):
        hold = d1.r4.r51._observe_event(task_step=step, currents=current, target_fields=second["target_card15_fields"], actuator=actuator, contract=contract, event="second_candidate_exact_hold")
        events.append(hold); current = [float(v) for v in hold["nominal_readback_current_a_tsc"]]
    returned = d1.r4.r51._return_event(task_step=22, currents=current, center_fields=center_fields, issue_event=second, field_basis=field_basis, actuator=actuator, lattice=lattice, contract=contract)
    returned["event"] = "second_pulse_stored_center_return"; events.append(returned); current = [float(v) for v in returned["nominal_readback_current_a_tsc"]]
    post_return = []
    for step in range(23, int(spec["horizon_steps"])):
        refresh = d1.r4.r51.r8r22._refresh_event(task_step=step, currents=current, target_fields=center_fields, actuator=actuator, turns_tsc=actuator.turns_tsc, max_delta_a=actuator.max_slew_step_a, minimum_current=actuator.minimum_current_a_tsc, maximum_current=actuator.maximum_current_a_tsc, lattice_cfg=lattice, contract=contract)
        refresh["event"] = "post_second_pulse_exact_center_refresh"; events.append(refresh); post_return.append(refresh); current = [float(v) for v in refresh["nominal_readback_current_a_tsc"]]
    source_second_issue = next(event for event in second_events if int(event["task_step"]) == 12)
    cosine, off_basis = d1i._geometry(second_before, second["nominal_issue_readback_current_a_tsc"], source_second_issue["nominal_issue_readback_current_a_tsc"], field_basis, [float(v) for v in actuator.turns_tsc])
    criteria = {
        "source_first_stream_pass": bool(first_base["passed"]), "source_second_stream_pass": bool(second_base["passed"]),
        "fixed_task_clock": tuple(int(event["task_step"]) for event in events) == tuple(range(10, int(spec["horizon_steps"]))),
        "q0_integration_action": float(events[0]["incremental_normalized_action_linf"]) <= 1e-5 + 1e-12,
        "first_return_exact": bool(first_return["passed"]) and [float(v) for v in first_return["nominal_readback_current_a_tsc"]] == center_current,
        "center_bridge_exact": bool(bridge["passed"]) and [float(v) for v in bridge["nominal_readback_current_a_tsc"]] == center_current,
        "center_bridge_zero_increment": all(float(v) == 0.0 for v in bridge["action_norm_tsc"]),
        "second_candidate_identity": second.get("candidate_id") == spec["second_candidate_id"],
        "second_coordinate_exact": [float(v) for v in second.get("requested_coordinate", [])] == [float(v) for v in spec["second_requested_coordinate"]],
        "second_target_exact": list(second["target_card15_fields"]) == list(source_second_issue["target_card15_fields"]),
        "second_scalar_cosine": cosine >= .98 - 1e-12, "second_scalar_off_basis": off_basis <= .10 + 1e-12,
        "second_return_exact": bool(returned["passed"]) and [float(v) for v in returned["nominal_readback_current_a_tsc"]] == center_current,
        "post_return_center_exact": all(bool(event["passed"]) and list(event["stored_target_card15_fields"]) == center_fields and [float(v) for v in event["nominal_readback_current_a_tsc"]] == center_current for event in post_return),
        "all_event_gates": all(bool(event.get("passed")) and all(bool(value) for value in (event.get("criteria") or {}).values()) for event in events),
        "incremental_action_limits": all(float(event["incremental_normalized_action_linf"]) <= .25 + 1e-12 for event in events),
        "total_action_limits": all(max(abs(float(v)) for v in (event.get("action_norm_tsc") or [float("inf")])) <= 1.0 + 1e-12 for event in events),
        "current_utilization_limits": all(float(event["predicted_current_utilization"]) <= .55 + 1e-12 for event in events),
        "no_response_input": spec.get("source_d1_result_available_to_construction") is False, "learning_forbidden": spec.get("allowed_in_expert_dataset") is False,
    }
    return {"experiment_id": spec["experiment_id"], "context_index": spec["context_index"], "pair_id": spec["pair_id"], "history_member": spec["history_member"], "first_candidate_id": spec["first_candidate_id"], "second_candidate_id": spec["second_candidate_id"], "event_count": len(events), "action_stream_digest": _digest([d1._canonical_event(event) for event in events]), "maximum_incremental_action_linf": max(float(event["incremental_normalized_action_linf"]) for event in events), "maximum_current_utilization": max(float(event["predicted_current_utilization"]) for event in events), "second_transition_cosine": cosine, "second_transition_relative_off_basis_residual": off_basis, "post_return_refresh_zero_increment_diagnostic": all(all(float(v) == 0.0 for v in event["action_norm_tsc"]) for event in post_return), "criteria": criteria, "eligible": all(criteria.values())}


def _coverage(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    contexts=[]; candidates=set(d3.CANDIDATE_IDS)
    for index in range(10):
        current=[row for row in rows if int(row["context_index"])==index]; eligible=[row for row in current if row["eligible"]]
        ids=sorted(f"{r['first_candidate_id']}->{r['second_candidate_id']}" for r in eligible); first={r['first_candidate_id'] for r in eligible}; second={r['second_candidate_id'] for r in eligible}
        gates={"all_pairs_reported":len(current)==25,"all_pairs_eligible":len(eligible)==25,"all_first_candidates":first==candidates,"all_second_candidates":second==candidates}
        contexts.append({"context_index":index,"pair_id":current[0]["pair_id"],"history_member":current[0]["history_member"],"eligible_pair_count":len(eligible),"eligible_pair_ids":ids,"gates":gates,"passed":all(gates.values())})
    history=[]
    for pair_id in sorted({r["pair_id"] for r in contexts}):
        members=[r for r in contexts if r["pair_id"]==pair_id]; history.append({"pair_id":pair_id,"eligible_pair_set_equal":len(members)==2 and members[0]["eligible_pair_ids"]==members[1]["eligible_pair_ids"]})
    gates={"all_specs_reported":len(rows)==250,"all_specs_eligible":sum(bool(r["eligible"]) for r in rows)==250,"all_contexts_pass":all(r["passed"] for r in contexts),"history_pair_count":len(history)==5,"history_pair_sets_equal":all(r["eligible_pair_set_equal"] for r in history)}
    return {"eligible_specification_count":sum(bool(r["eligible"]) for r in rows),"context_pass_count":sum(bool(r["passed"]) for r in contexts),"history_pair_pass_count":sum(bool(r["eligible_pair_set_equal"]) for r in history),"contexts":contexts,"history_pairs":history,"gates":gates,"passed":all(gates.values())}


def run_independent(ctx: d3.Context) -> dict[str, Any]:
    required=[ctx.paths.analysis/"offline_primary.json",ctx.paths.analysis/"offline_construction_primary.json",ctx.paths.specs/"all_specs.json",ctx.paths.manifest,ctx.paths.state]
    if not all(p.is_file() for p in required): raise ValueError("R8R51R4D3 primary artifacts missing")
    primary, construction, specs, manifest = _read(required[0]), _read(required[1]), _read(required[2]), _read(ctx.paths.manifest)
    if _digest(specs)!=manifest["spec_digest"] or _sha(ctx.config_path)!=manifest["config_sha256"]: raise ValueError("R8R51R4D3 primary identity changed")
    authentication=d3.authenticate_source(ctx); source_rows=d3.d1._source_specs(ctx.d1_ctx); by_id={r["experiment_id"]:r for r in source_rows}; cache={}
    rows=[_construct_row(ctx,spec,by_id,cache) for spec in specs]; coverage=_coverage(rows); by_primary={r["experiment_id"]:r for r in construction["rows"]}
    discrete=len(rows)==len(by_primary) and all(r["experiment_id"] in by_primary and by_primary[r["experiment_id"]]["criteria"]==r["criteria"] and by_primary[r["experiment_id"]]["eligible"]==r["eligible"] and by_primary[r["experiment_id"]]["action_stream_digest"]==r["action_stream_digest"] and by_primary[r["experiment_id"]]["post_return_refresh_zero_increment_diagnostic"]==r["post_return_refresh_zero_increment_diagnostic"] for r in rows)
    keys=("maximum_incremental_action_linf","maximum_current_utilization","second_transition_cosine","second_transition_relative_off_basis_residual")
    maximum=max(abs(float(r[k])-float(by_primary[r["experiment_id"]][k])) for r in rows for k in keys)
    coverage_agreement=coverage==construction["coverage"]; action_digest=_digest([(r["experiment_id"],r["action_stream_digest"]) for r in rows]); action_agreement=action_digest==primary["action_stream_digest"]
    audit=bool(authentication["passed"] and discrete and coverage_agreement and maximum<=1e-10 and action_agreement); scientific=bool(audit and coverage["passed"] and primary["passed"] is True); route=ctx.cfg["routes"]["pass" if scientific else "geometry_fail"]
    report={"schema_version":1,"stage":d3.STAGE,"phase":"offline_independent","source_authenticated":True,"specification_count":len(rows),"eligible_specification_count":coverage["eligible_specification_count"],"context_pass_count":coverage["context_pass_count"],"history_pair_pass_count":coverage["history_pair_pass_count"],"action_stream_digest":action_digest,"primary_discrete_agreement":discrete,"primary_coverage_agreement":coverage_agreement,"primary_action_stream_agreement":action_agreement,"primary_numerical_agreement":maximum<=1e-10,"maximum_primary_numerical_difference":maximum,"coverage":coverage,"rows":rows,"audit_passed":audit,"scientific_gate_passed":scientific,"new_tsc_count":0,"plant_step_count":0,"response_values_used":False,"route":route,"passed":audit}
    _write_new(ctx.paths.analysis/"offline_independent.json",report)
    final={"schema_version":1,"stage":d3.STAGE,"phase":"final","source_authenticated":True,"audit_passed":audit,"scientific_gate_passed":scientific,"specification_count":len(rows),"eligible_specification_count":coverage["eligible_specification_count"],"context_pass_count":coverage["context_pass_count"],"history_pair_pass_count":coverage["history_pair_pass_count"],"primary_independent_maximum_numerical_difference":maximum,"new_tsc_count":0,"new_raw_count":0,"plant_step_count":0,"controller_execution_count":0,"model_fit_count":0,"optimization_count":0,"response_values_used":False,"all_stage_trajectories_allowed_in_expert_dataset":False,"route":route,"passed":scientific}
    _write_new(ctx.paths.analysis/"final_report.json",final)
    state=_read(ctx.paths.state); state.update({"phase_status":"complete" if audit else "independent_integrity_failed","finished":True,"route":route,"verdict":{"route":route,"passed":scientific},"stop_reason":"" if scientific else "center_bridged_schedule_geometry_gate_failed","offline_independent_sha256":_sha(ctx.paths.analysis/"offline_independent.json"),"final_report_sha256":_sha(ctx.paths.analysis/"final_report.json")}); d3._write(ctx.paths.state,state,replace=True)
    return final


def main() -> None:
    args=d3._parser().parse_args()
    if args.command!="offline": raise ValueError("R8R51R4D3 independent is offline only")
    print(json.dumps(run_independent(d3.load_context(args)),indent=2,sort_keys=True,allow_nan=False))


if __name__=="__main__": main()
