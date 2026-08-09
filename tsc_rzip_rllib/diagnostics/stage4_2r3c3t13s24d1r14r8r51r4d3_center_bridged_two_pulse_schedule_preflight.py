"""Zero-TSC center-bridged two-pulse action preflight for R8R51R4D3."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping, Sequence

import numpy as np

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r51r4d1_two_transport_exact_return_schedule_preflight
    as d1,
)


SCHEMA_VERSION = 1
STAGE = "Stage4.2R3c3T13S24D1R14R8R51R4D3"
IDENTITY = "center_bridged_two_pulse_schedule_preflight_v1"
RUN_NAME = "stage4_2r3c3t13s24d1r14r8r51r4d3_center_bridged_two_pulse_schedule_preflight"
CANDIDATE_IDS = d1.CANDIDATE_IDS
N_COILS = d1.N_COILS


class SourceBlockedError(RuntimeError):
    pass


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def _read(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream, parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _write(path: Path, value: Any, *, replace: bool = False) -> None:
    if path.exists() and not replace:
        raise ValueError(f"R8R51R4D3 output exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


@dataclass(frozen=True)
class Paths:
    stage: Path
    specs: Path
    source_reference: Path
    analysis: Path
    state: Path
    manifest: Path


def _paths(run_dir: Path) -> Paths:
    stage = run_dir.expanduser().resolve() / RUN_NAME
    return Paths(stage, stage / "specs", stage / "source_reference", stage / "analysis", stage / "stage_state.json", stage / "stage_manifest.json")


@dataclass(frozen=True)
class Context:
    cfg: dict[str, Any]
    config_path: Path
    paths: Paths
    d1_ctx: d1.Context
    d1_stage: Path


ARTIFACTS = {
    "specs": "specs/all_specs.json",
    "source_authentication": "source_reference/source_authentication.json",
    "offline_primary": "analysis/offline_primary.json",
    "offline_construction": "analysis/offline_construction_primary.json",
    "offline_independent": "analysis/offline_independent.json",
    "final_report": "analysis/final_report.json",
    "stage_state": "stage_state.json",
    "stage_manifest": "stage_manifest.json",
    "compact_forensics": "analysis/refresh_reporting_fix_compact_forensics.json",
    "server_evidence": "analysis/refresh_reporting_fix_server_evidence.json",
}


def validate_config(cfg: Mapping[str, Any], project_root: Path) -> None:
    design = project_root / str(cfg.get("design_document", ""))
    source_config = project_root / str(cfg.get("source_r51r4d1_config", ""))
    source_impl = project_root / "tsc_rzip_rllib/diagnostics/stage4_2r3c3t13s24d1r14r8r51r4d1_two_transport_exact_return_schedule_preflight.py"
    source_ind = project_root / "docs/codex/audit_tools/stage4_2r3c3t13s24d1r14r8r51r4d1_independent_forensics.py"
    matrix, schedule, action, coverage, routes, scope = (cfg.get(key, {}) for key in ("matrix_contract", "schedule_contract", "action_contract", "coverage_gate", "routes", "scientific_scope"))
    invalid = (
        cfg.get("schema_version") != 1 or cfg.get("stage") != STAGE or cfg.get("identity") != IDENTITY
        or cfg.get("run_name") != RUN_NAME
        or cfg.get("package_revision") != "r42r3c3t13s24d1r14r8r51r4d3_center_bridged_two_pulse_preflight_v1"
        or not design.is_file() or _sha(design) != cfg.get("design_document_sha256")
        or not source_config.is_file() or _sha(source_config) != cfg.get("source_r51r4d1_config_sha256")
        or not source_impl.is_file() or _sha(source_impl) != cfg.get("source_r51r4d1_implementation_sha256")
        or not source_ind.is_file() or _sha(source_ind) != cfg.get("source_r51r4d1_independent_sha256")
        or tuple(matrix.get("candidate_ids", ())) != CANDIDATE_IDS
        or tuple(int(matrix.get(k, -1)) for k in ("context_count", "candidate_count", "ordered_pair_count_per_context", "specification_count")) != (10, 5, 25, 250)
        or tuple(int(schedule.get(k, -1)) for k in ("q0_issue_task_step", "q0_observe_task_step", "first_issue_task_step", "first_return_task_step", "center_bridge_hold_task_step", "second_issue_task_step", "second_return_task_step", "dynamic_exact_search_radius")) != (10, 11, 12, 16, 17, 18, 22, 16)
        or tuple(schedule.get("first_hold_task_steps", ())) != (13, 14, 15)
        or tuple(schedule.get("second_hold_task_steps", ())) != (19, 20, 21)
        or tuple(float(action.get(k, -1)) for k in ("maximum_q0_integration_action_linf", "maximum_incremental_normalized_action_linf", "maximum_total_normalized_action_abs", "maximum_current_utilization", "minimum_desired_applied_current_cosine", "maximum_relative_off_basis_residual", "numerical_tolerance")) != (1e-5, .25, 1.0, .55, .98, .10, 1e-12)
        or tuple(int(coverage.get(k, -1)) for k in ("required_eligible_specification_count", "required_eligible_ordered_pairs_per_context", "required_first_candidate_count_per_context", "required_second_candidate_count_per_context", "required_history_pair_count")) != (250, 25, 5, 5, 5)
        or coverage.get("require_equal_eligible_pair_set_within_history_pair") is not True
        or routes != {
            "source_blocked": "REDUCED_Q0_TRANSPORT_BRIDGE_R51R4D3_BLOCKED_BY_SOURCE_OR_INTEGRITY",
            "geometry_fail": "REDUCED_Q0_TRANSPORT_BRIDGE_R51R4D3_CENTER_BRIDGED_TWO_PULSE_GEOMETRY_INSUFFICIENT_NO_REAL_TSC",
            "pass": "REDUCED_Q0_TRANSPORT_BRIDGE_R51R4D3_CENTER_BRIDGED_TWO_PULSE_SCHEDULE_PREFLIGHT_COMPLETE_R51R4D4_DESIGN_REQUIRED",
        }
        or any(scope.get(k) is not False for k in ("response_values_used", "model_fit_allowed", "controller_executed", "real_mpc_executed", "gate_a_qualified", "expert_data_allowed", "bc_dagger_or_rl_allowed", "all_source_trajectories_allowed_in_expert_dataset", "global_plant_reachability_claimed"))
        or scope.get("zero_new_tsc") is not True
    )
    if invalid:
        raise ValueError("R8R51R4D3 frozen design changed")


def load_context(args: argparse.Namespace) -> Context:
    config_path = args.config.expanduser().resolve()
    cfg = _read(config_path)
    validate_config(cfg, _root())
    source_args = SimpleNamespace(**vars(args))
    source_args.config = (_root() / cfg["source_r51r4d1_config"]).resolve()
    source_args.run_dir = args.r51r4d1_run.expanduser().resolve()
    d1_ctx = d1.load_context(source_args)
    expected = cfg["source_r51r4d1"]
    if d1_ctx.paths.stage.parent.name != expected["run_name"] or d1_ctx.paths.stage.name != expected["stage_directory"]:
        raise ValueError("R8R51R4D3 source D1 identity changed")
    return Context(cfg, config_path, _paths(args.run_dir), d1_ctx, d1_ctx.paths.stage)


def authenticate_source(ctx: Context) -> dict[str, Any]:
    inherited = d1.authenticate_source(ctx.d1_ctx)
    expected = ctx.cfg["source_r51r4d1"]
    hashes = {}
    for key, relative in ARTIFACTS.items():
        path = ctx.d1_stage / relative
        if not path.is_file() or _sha(path) != expected[f"{key}_sha256"]:
            raise SourceBlockedError(f"R8R51R4D3 D1 source changed: {relative}")
        hashes[key] = _sha(path)
    primary = _read(ctx.d1_stage / ARTIFACTS["offline_primary"])
    independent = _read(ctx.d1_stage / ARTIFACTS["offline_independent"])
    final = _read(ctx.d1_stage / ARTIFACTS["final_report"])
    compact = _read(ctx.d1_stage / ARTIFACTS["compact_forensics"])
    evidence = _read(ctx.d1_stage / ARTIFACTS["server_evidence"])
    valid = (
        inherited.get("passed") is True and primary.get("source_authenticated") is True
        and primary.get("action_stream_digest") == expected["action_stream_digest"]
        and int(primary.get("eligible_specification_count", -1)) == 68
        and int(primary.get("context_pass_count", -1)) == 0 and primary.get("passed") is False
        and independent.get("audit_passed") is True and independent.get("scientific_gate_passed") is False
        and independent.get("frozen_action_stream_preserved") is True
        and final.get("route") == expected["required_route"] and final.get("passed") is False
        and compact.get("audit_passed") is True and compact.get("eligible_specification_count") == 68
        and compact.get("context_pass_count") == 0 and evidence.get("audit_passed") is True
        and evidence.get("route") == expected["required_route"] and evidence.get("new_tsc_count") == 0
    )
    if not valid:
        raise SourceBlockedError("R8R51R4D3 final D1 provenance changed")
    return {"hashes": hashes, "inherited_r51r4_digest": _digest(inherited), "required_route": expected["required_route"], "response_values_available_to_construction": False, "passed": True}


def build_specs(ctx: Context) -> list[dict[str, Any]]:
    rows = d1.build_specs(ctx.d1_ctx)
    result = []
    for row in rows:
        item = copy.deepcopy(row)
        item.update({"stage": STAGE, "identity": IDENTITY, "experiment_id": row["experiment_id"].replace("r8r51r4d1_", "r8r51r4d3_"), "decision_task_steps": [12, 16, 18, 22], "source_d1_result_available_to_construction": False, "allowed_in_expert_dataset": False})
        result.append(item)
    if len(result) != 250 or len({row["experiment_id"] for row in result}) != 250:
        raise ValueError("R8R51R4D3 matrix changed")
    return result


def construct_schedule(ctx: Context, spec: Mapping[str, Any], source_by_id: Mapping[str, Mapping[str, Any]], cache: dict[str, dict[str, Any]]) -> dict[str, Any]:
    first_spec = source_by_id[str(spec["first_source_experiment_id"])]
    second_spec = source_by_id[str(spec["second_source_experiment_id"])]
    for source_spec in (first_spec, second_spec):
        key = str(source_spec["experiment_id"])
        if key not in cache:
            cache[key] = d1.r4.construct_event_stream(ctx.d1_ctx.r4_ctx, source_spec, include_events=True)
    first_base, second_base = cache[str(first_spec["experiment_id"])], cache[str(second_spec["experiment_id"])]
    first_events, second_events = first_base["events"], second_base["events"]
    events = [copy.deepcopy(event) for event in first_events if int(event["task_step"]) <= 16]
    if tuple(int(event["task_step"]) for event in events) != tuple(range(10, 17)):
        raise ValueError("R8R51R4D3 first pulse clock changed")
    first_issue = next(event for event in events if int(event["task_step"]) == 12)
    first_return = events[-1]
    actuator, _, field_basis, lattice, contract = d1._runtime_parts(ctx.d1_ctx, first_spec)
    center_fields = list(events[0]["q0_center_card15_fields"])
    center_current = np.asarray(first_issue["center_nominal_readback_current_a_tsc"], dtype=float)
    current = np.asarray(first_return["nominal_readback_current_a_tsc"], dtype=float)
    bridge = d1.r4.r51._observe_event(task_step=17, currents=current, target_fields=center_fields, actuator=actuator, contract=contract, event="exact_q0_center_bridge_hold")
    events.append(bridge); current = np.asarray(bridge["nominal_readback_current_a_tsc"], dtype=float)
    second = d1.r4.r51.r8r22._construct_coordinate_issue(task_step=18, currents_a_tsc=current, fixed_basis_delta_field_kat_tsc=field_basis.T, requested_coordinate=spec["second_requested_coordinate"], candidate_id=str(spec["second_candidate_id"]), actuator=actuator, controller_cfg=contract, lattice_cfg=lattice)
    second["center_nominal_readback_current_a_tsc"] = current.tolist()
    second["event"] = "second_center_bridged_candidate_issue"
    second_before = current.copy()
    events.append(second); current = np.asarray(second["nominal_issue_readback_current_a_tsc"], dtype=float)
    for step in (19, 20, 21):
        hold = d1.r4.r51._observe_event(task_step=step, currents=current, target_fields=second["target_card15_fields"], actuator=actuator, contract=contract, event="second_candidate_exact_hold")
        events.append(hold); current = np.asarray(hold["nominal_readback_current_a_tsc"], dtype=float)
    returned = d1.r4.r51._return_event(task_step=22, currents=current, center_fields=center_fields, issue_event=second, field_basis=field_basis, actuator=actuator, lattice=lattice, contract=contract)
    returned["event"] = "second_pulse_stored_center_return"
    events.append(returned); current = np.asarray(returned["nominal_readback_current_a_tsc"], dtype=float)
    post_return = []
    for step in range(23, int(spec["horizon_steps"])):
        refresh = d1.r4.r51.r8r22._refresh_event(task_step=step, currents=current, target_fields=center_fields, actuator=actuator, turns_tsc=actuator.turns_tsc, max_delta_a=actuator.max_slew_step_a, minimum_current=actuator.minimum_current_a_tsc, maximum_current=actuator.maximum_current_a_tsc, lattice_cfg=lattice, contract=contract)
        refresh["event"] = "post_second_pulse_exact_center_refresh"
        events.append(refresh); post_return.append(refresh); current = np.asarray(refresh["nominal_readback_current_a_tsc"], dtype=float)
    source_second_issue = next(event for event in second_events if int(event["task_step"]) == 12)
    second_cosine, second_off_basis = d1._transition_geometry(before=second_before, after=np.asarray(second["nominal_issue_readback_current_a_tsc"], dtype=float), desired_target=np.asarray(source_second_issue["nominal_issue_readback_current_a_tsc"], dtype=float), field_basis=field_basis, turns=np.asarray(actuator.turns_tsc, dtype=float))
    criteria = {
        "source_first_stream_pass": bool(first_base["passed"]), "source_second_stream_pass": bool(second_base["passed"]),
        "fixed_task_clock": tuple(int(event["task_step"]) for event in events) == tuple(range(10, int(spec["horizon_steps"]))),
        "q0_integration_action": float(events[0]["incremental_normalized_action_linf"]) <= float(ctx.cfg["action_contract"]["maximum_q0_integration_action_linf"]) + 1e-12,
        "first_return_exact": bool(first_return["passed"]) and np.array_equal(np.asarray(first_return["nominal_readback_current_a_tsc"]), center_current),
        "center_bridge_exact": bool(bridge["passed"]) and np.array_equal(np.asarray(bridge["nominal_readback_current_a_tsc"]), center_current),
        "center_bridge_zero_increment": np.array_equal(np.asarray(bridge["action_norm_tsc"]), np.zeros(N_COILS)),
        "second_candidate_identity": second.get("candidate_id") == spec["second_candidate_id"],
        "second_coordinate_exact": np.array_equal(np.asarray(second.get("requested_coordinate"), dtype=float), np.asarray(spec["second_requested_coordinate"], dtype=float)),
        "second_target_exact": list(second["target_card15_fields"]) == list(source_second_issue["target_card15_fields"]),
        "second_scalar_cosine": second_cosine >= .98 - 1e-12,
        "second_scalar_off_basis": second_off_basis <= .10 + 1e-12,
        "second_return_exact": bool(returned["passed"]) and np.array_equal(np.asarray(returned["nominal_readback_current_a_tsc"]), center_current),
        "post_return_center_exact": all(bool(event["passed"]) and list(event["stored_target_card15_fields"]) == center_fields and np.array_equal(np.asarray(event["nominal_readback_current_a_tsc"]), center_current) for event in post_return),
        "all_event_gates": all(bool(event.get("passed")) and all(bool(value) for value in (event.get("criteria") or {}).values()) for event in events),
        "incremental_action_limits": all(float(event["incremental_normalized_action_linf"]) <= .25 + 1e-12 for event in events),
        "total_action_limits": all(max(map(abs, event.get("action_norm_tsc") or [math.inf])) <= 1.0 + 1e-12 for event in events),
        "current_utilization_limits": all(float(event["predicted_current_utilization"]) <= .55 + 1e-12 for event in events),
        "no_response_input": spec.get("source_d1_result_available_to_construction") is False,
        "learning_forbidden": spec.get("allowed_in_expert_dataset") is False,
    }
    return {"experiment_id": spec["experiment_id"], "context_index": spec["context_index"], "pair_id": spec["pair_id"], "history_member": spec["history_member"], "first_candidate_id": spec["first_candidate_id"], "second_candidate_id": spec["second_candidate_id"], "event_count": len(events), "action_stream_digest": _digest([d1._canonical_event(event) for event in events]), "maximum_incremental_action_linf": max(float(event["incremental_normalized_action_linf"]) for event in events), "maximum_current_utilization": max(float(event["predicted_current_utilization"]) for event in events), "second_transition_cosine": second_cosine, "second_transition_relative_off_basis_residual": second_off_basis, "post_return_refresh_zero_increment_diagnostic": all(np.array_equal(np.asarray(event["action_norm_tsc"]), np.zeros(N_COILS)) for event in post_return), "criteria": criteria, "eligible": bool(all(criteria.values()))}


def evaluate_coverage(rows: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]) -> dict[str, Any]:
    contexts = []
    candidates = set(CANDIDATE_IDS)
    for index in range(10):
        current = [row for row in rows if int(row["context_index"]) == index]
        eligible = [row for row in current if row["eligible"]]
        pair_ids = sorted(f"{row['first_candidate_id']}->{row['second_candidate_id']}" for row in eligible)
        first = {row["first_candidate_id"] for row in eligible}; second = {row["second_candidate_id"] for row in eligible}
        gates = {"all_pairs_reported": len(current) == 25, "all_pairs_eligible": len(eligible) == 25, "all_first_candidates": first == candidates, "all_second_candidates": second == candidates}
        contexts.append({"context_index": index, "pair_id": current[0]["pair_id"], "history_member": current[0]["history_member"], "eligible_pair_count": len(eligible), "eligible_pair_ids": pair_ids, "gates": gates, "passed": all(gates.values())})
    history = []
    for pair_id in sorted({row["pair_id"] for row in contexts}):
        members = [row for row in contexts if row["pair_id"] == pair_id]
        history.append({"pair_id": pair_id, "eligible_pair_set_equal": len(members) == 2 and members[0]["eligible_pair_ids"] == members[1]["eligible_pair_ids"]})
    gates = {"all_specs_reported": len(rows) == 250, "all_specs_eligible": sum(bool(row["eligible"]) for row in rows) == 250, "all_contexts_pass": all(row["passed"] for row in contexts), "history_pair_count": len(history) == 5, "history_pair_sets_equal": all(row["eligible_pair_set_equal"] for row in history)}
    return {"eligible_specification_count": sum(bool(row["eligible"]) for row in rows), "context_pass_count": sum(bool(row["passed"]) for row in contexts), "history_pair_pass_count": sum(bool(row["eligible_pair_set_equal"]) for row in history), "contexts": contexts, "history_pairs": history, "gates": gates, "passed": all(gates.values())}


def run_primary(ctx: Context) -> dict[str, Any]:
    if ctx.paths.stage.exists():
        raise ValueError("R8R51R4D3 primary requires fresh output")
    for path in (ctx.paths.stage, ctx.paths.specs, ctx.paths.source_reference, ctx.paths.analysis): path.mkdir(parents=True, exist_ok=True)
    try:
        authentication = authenticate_source(ctx); specs = build_specs(ctx)
        source_rows = d1._source_specs(ctx.d1_ctx); by_id = {row["experiment_id"]: row for row in source_rows}; cache = {}
        rows = [construct_schedule(ctx, spec, by_id, cache) for spec in specs]
        coverage = evaluate_coverage(rows, ctx.cfg)
        construction = {"schema_version": 1, "stage": STAGE, "specification_count": len(rows), "eligible_specification_count": coverage["eligible_specification_count"], "maximum_incremental_action_linf": max(row["maximum_incremental_action_linf"] for row in rows), "maximum_current_utilization": max(row["maximum_current_utilization"] for row in rows), "action_stream_digest": _digest([(row["experiment_id"], row["action_stream_digest"]) for row in rows]), "coverage": coverage, "rows": rows, "passed": coverage["passed"]}
        route = ctx.cfg["routes"]["pass" if construction["passed"] else "geometry_fail"]
        _write(ctx.paths.specs / "all_specs.json", specs); _write(ctx.paths.source_reference / "source_authentication.json", authentication); _write(ctx.paths.analysis / "offline_construction_primary.json", construction)
        manifest = {"schema_version": 1, "stage": STAGE, "identity": IDENTITY, "package_revision": ctx.cfg["package_revision"], "config_sha256": _sha(ctx.config_path), "design_document_sha256": ctx.cfg["design_document_sha256"], "source_d1_stage": str(ctx.d1_stage), "spec_digest": _digest(specs), "construction_digest": _digest(construction), "all_stage_trajectories_allowed_in_expert_dataset": False}
        _write(ctx.paths.manifest, manifest)
        _write(ctx.paths.state, {"schema_version": 1, "stage": STAGE, "phase_status": "offline_primary_complete_independent_required", "finished": False, "real_tsc_executed": False, "plant_step_count": 0, "new_raw_count": 0, "response_outcomes_opened": False, "route": route, "verdict": {"route": route, "passed": construction["passed"]}, "stop_reason": ""})
        report = {"schema_version": 1, "stage": STAGE, "phase": "offline_primary", "source_authenticated": True, "specification_count": len(rows), "eligible_specification_count": coverage["eligible_specification_count"], "context_pass_count": coverage["context_pass_count"], "history_pair_pass_count": coverage["history_pair_pass_count"], "maximum_incremental_action_linf": construction["maximum_incremental_action_linf"], "maximum_current_utilization": construction["maximum_current_utilization"], "action_stream_digest": construction["action_stream_digest"], "new_tsc_count": 0, "plant_step_count": 0, "response_values_used": False, "route": route, "passed": construction["passed"]}
    except SourceBlockedError as exc:
        route = ctx.cfg["routes"]["source_blocked"]
        report = {"schema_version": 1, "stage": STAGE, "phase": "offline_primary", "source_authenticated": False, "new_tsc_count": 0, "plant_step_count": 0, "route": route, "passed": False, "failure_reason": repr(exc)}
        _write(ctx.paths.manifest, {"schema_version": 1, "stage": STAGE, "source_blocked": True})
        _write(ctx.paths.state, {"schema_version": 1, "stage": STAGE, "phase_status": "source_blocked", "finished": True, "real_tsc_executed": False, "plant_step_count": 0, "new_raw_count": 0, "route": route, "verdict": {"route": route, "passed": False}, "stop_reason": "source_authentication_failed"})
    _write(ctx.paths.analysis / "offline_primary.json", report)
    return report


def _parser() -> argparse.ArgumentParser:
    parser = d1._parser()
    parser.add_argument("--r51r4d1-run", type=Path, required=True)
    return parser


def main() -> None:
    args = _parser().parse_args()
    if args.command != "offline": raise ValueError("R8R51R4D3 is zero-TSC and offline only")
    print(json.dumps(run_primary(load_context(args)), indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__": main()
