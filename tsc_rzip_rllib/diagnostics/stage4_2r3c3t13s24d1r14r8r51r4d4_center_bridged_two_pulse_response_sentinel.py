"""Prospective center-bridged two-pulse real-response sentinel for R8R51R4D4."""
from __future__ import annotations

import argparse
from collections import defaultdict
import copy
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import statistics
import time
import traceback
from types import SimpleNamespace
from typing import Any, Mapping, Sequence

import numpy as np

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r51r4_failed_context_sustained_transport_dwell_sentinel
    as r4,
    stage4_2r3c3t13s24d1r14r8r51r4d3_center_bridged_two_pulse_schedule_preflight
    as d3,
)


SCHEMA_VERSION = 1
STAGE = "Stage4.2R3c3T13S24D1R14R8R51R4D4"
IDENTITY = "center_bridged_two_pulse_response_sentinel_v1_runtime_hotfix1"
RUN_NAME = "stage4_2r3c3t13s24d1r14r8r51r4d4_center_bridged_two_pulse_response_sentinel"
CONTROLLER_REVISION = "center_bridged_two_pulse_response_v42r3c3t13s24d1r14r8r51r4d4_v1_runtime_hotfix1"
N_COILS = 14
PREFIX_END = 10
Q0_STEP = 10
FIRST_ISSUE = 12
FIRST_RETURN = 16
BRIDGE_STEP = 17
SECOND_ISSUE = 18
SECOND_RETURN = 22
CANDIDATE_IDS = d3.CANDIDATE_IDS
CURRENT_ATOL_A = 1e-12


class SourceBlockedError(RuntimeError):
    pass


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def _read(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as stream:
        return json.load(
            stream,
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
        )


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def _write(path: Path, value: Any, *, replace: bool = False) -> None:
    if path.exists() and not replace:
        raise ValueError(f"R8R51R4D4 output exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


@dataclass(frozen=True)
class Paths:
    stage: Path
    variants: Path
    specs: Path
    source_reference: Path
    raw: Path
    analysis: Path
    state: Path
    manifest: Path


def _paths(run_dir: Path) -> Paths:
    stage = run_dir.expanduser().resolve() / RUN_NAME
    return Paths(
        stage=stage,
        variants=stage / "variants",
        specs=stage / "specs",
        source_reference=stage / "source_reference",
        raw=stage / "raw",
        analysis=stage / "analysis",
        state=stage / "stage_state.json",
        manifest=stage / "stage_manifest.json",
    )


@dataclass(frozen=True)
class Context:
    cfg: dict[str, Any]
    config_path: Path
    paths: Paths
    d3_ctx: d3.Context
    d3_stage: Path
    r4_ctx: r4.Context
    failed_attempt_stage: Path


def validate_config(cfg: Mapping[str, Any], project_root: Path) -> None:
    design = project_root / str(cfg.get("design_document", ""))
    original_design = project_root / str(cfg.get("original_design_document", ""))
    d5_design = project_root / str(cfg.get("conditional_d5_design", ""))
    d3_config = project_root / str(cfg.get("source_r51r4d3_config", ""))
    d3_impl = project_root / "tsc_rzip_rllib/diagnostics/stage4_2r3c3t13s24d1r14r8r51r4d3_center_bridged_two_pulse_schedule_preflight.py"
    d3_ind = project_root / "docs/codex/audit_tools/stage4_2r3c3t13s24d1r14r8r51r4d3_independent_forensics.py"
    r4_config = project_root / str(cfg.get("source_r51r4_config", ""))
    r4_impl = project_root / "tsc_rzip_rllib/diagnostics/stage4_2r3c3t13s24d1r14r8r51r4_failed_context_sustained_transport_dwell_sentinel.py"
    matrix = cfg.get("matrix_contract", {})
    schedule = cfg.get("schedule_contract", {})
    controller = cfg.get("controller_contract", {})
    formal = cfg.get("formal_contract", {})
    known = cfg.get("known_aggregate_contract", {})
    gate = cfg.get("scientific_gate", {})
    scope = cfg.get("scientific_scope", {})
    failed = cfg.get("failed_attempt_contract", {})
    frozen_offline = cfg.get("frozen_offline_contract", {})
    expected_routes = {
        "source_blocked": "REDUCED_Q0_TRANSPORT_BRIDGE_R51R4D4_BLOCKED_BY_SOURCE_OR_DESIGN",
        "offline_fail": "REDUCED_Q0_TRANSPORT_BRIDGE_R51R4D4_CENTER_BRIDGED_TWO_PULSE_OFFLINE_FAIL_NO_REAL_TSC",
        "execution_fail": "REDUCED_Q0_TRANSPORT_BRIDGE_R51R4D4_CENTER_BRIDGED_TWO_PULSE_EXECUTION_FAIL_STOP",
        "authority_insufficient": "REDUCED_Q0_TRANSPORT_BRIDGE_R51R4D4_CENTER_BRIDGED_TWO_PULSE_AUTHORITY_INSUFFICIENT_CAUSAL_FEEDBACK_REDESIGN_REQUIRED",
        "pass": "REDUCED_Q0_TRANSPORT_BRIDGE_R51R4D4_CENTER_BRIDGED_TWO_PULSE_AUTHORITY_PRESENT_R51R4D5_MODEL_CONTROLLER_PREFLIGHT_REQUIRED",
    }
    invalid = (
        cfg.get("schema_version") != 1
        or cfg.get("stage") != STAGE
        or cfg.get("identity") != IDENTITY
        or cfg.get("run_name") != RUN_NAME
        or cfg.get("controller_revision") != CONTROLLER_REVISION
        or cfg.get("package_revision") != "r42r3c3t13s24d1r14r8r51r4d4_center_bridged_two_pulse_response_v1_runtime_hotfix1"
        or not design.is_file()
        or _sha(design) != cfg.get("design_document_sha256")
        or cfg.get("design_checkpoint") != "bcb4c5f"
        or not original_design.is_file()
        or _sha(original_design) != cfg.get("original_design_document_sha256")
        or cfg.get("original_design_checkpoint") != "d6356ca"
        or not d5_design.is_file()
        or _sha(d5_design) != cfg.get("conditional_d5_design_sha256")
        or cfg.get("conditional_d5_design_checkpoint") != "dd764cb"
        or not d3_config.is_file()
        or _sha(d3_config) != cfg.get("source_r51r4d3_config_sha256")
        or not d3_impl.is_file()
        or _sha(d3_impl) != cfg.get("source_r51r4d3_implementation_sha256")
        or not d3_ind.is_file()
        or _sha(d3_ind) != cfg.get("source_r51r4d3_independent_sha256")
        or not r4_config.is_file()
        or _sha(r4_config) != cfg.get("source_r51r4_config_sha256")
        or not r4_impl.is_file()
        or _sha(r4_impl) != cfg.get("source_r51r4_implementation_sha256")
        or tuple(matrix.get("candidate_ids", ())) != CANDIDATE_IDS
        or tuple(int(matrix.get(key, -1)) for key in (
            "context_count", "candidate_count", "ordered_pair_count_per_context", "trajectory_count"
        )) != (10, 5, 25, 250)
        or tuple(int(failed.get(key, -1)) for key in (
            "raw_count", "raw_bytes", "plant_step_count",
        )) != (250, 6318347, 2750)
        or failed.get("route") != expected_routes["execution_fail"]
        or failed.get("raw_inventory_digest") != "5f4e56dda413898f2ccd40e03fbf36d9a2f1a4e0bb7c829fcd3b8342fa1d826c"
        or failed.get("raw_byte_authentication_digest") != "4936faea52386b3422a93ce708b7163b3a876c5e49740acca8695b8d09bd92c6"
        or failed.get("response_outcomes_opened") is not False
        or failed.get("formal_metrics_computed") is not False
        or failed.get("same_output_rerun_forbidden") is not True
        or int(frozen_offline.get("specification_count", -1)) != 250
        or frozen_offline.get("action_stream_digest") != "26823bfc79fd3ca9e40a73d471010f55fad166f4d1fede9990632101f3bc36a5"
        or frozen_offline.get("event_stream_digest") != "52a2185df769259ac15449a73b9d53751e7025c936505a7a71eca8ed89c29521"
        or float(frozen_offline.get("maximum_incremental_action_linf", -1)) != 0.2111111111111112
        or float(frozen_offline.get("maximum_current_utilization", -1)) != 0.3912
        or tuple(matrix.get("failed_source_baseline_ids", ()))
        != tuple(f"r8r7_baseline_{index:02d}" for index in (*range(8), 12, 13))
        or tuple(int(schedule.get(key, -1)) for key in (
            "prefix_end_task_step", "q0_issue_task_step", "q0_observe_task_step",
            "first_issue_task_step", "first_return_task_step",
            "center_bridge_hold_task_step", "second_issue_task_step",
            "second_return_task_step", "first_effect_state_step",
            "second_effect_state_step", "dynamic_exact_search_radius",
        )) != (10, 10, 11, 12, 16, 17, 18, 22, 13, 19, 16)
        or tuple(schedule.get("first_hold_task_steps", ())) != (13, 14, 15)
        or tuple(schedule.get("second_hold_task_steps", ())) != (19, 20, 21)
        or tuple(float(controller.get(key, -1)) for key in (
            "maximum_q0_integration_action_linf", "maximum_incremental_normalized_action_linf",
            "maximum_total_normalized_action_abs", "maximum_current_utilization",
            "minimum_desired_applied_current_cosine", "maximum_relative_off_basis_residual",
        )) != (1e-5, .25, 1.0, .55, .98, .10)
        or any(controller.get(key) is not True for key in (
            "require_exact_card15_issue", "require_exact_card15_refresh",
            "require_exact_stored_center_return", "safe_stop_before_failed_advance",
        ))
        or tuple(int(formal.get(key, -1)) for key in (
            "normal_arrival_deadline_step", "normal_hold_through_step",
            "weak_arrival_deadline_step", "weak_hold_through_step", "arrival_streak_steps",
        )) != (25, 35, 27, 37, 3)
        or tuple(float(formal.get(key, -1)) for key in (
            "position_tolerance_m", "endpoint_speed_tolerance_m_per_s",
            "rms_speed_tolerance_m_per_s", "metric_equivalence_absolute_tolerance",
        )) != (.03, .1, .1, 1e-12)
        or formal.get("arrival_deadline_expansion_allowed") is not False
        or tuple(int(known.get(key, -1)) for key in (
            "baseline_formal_pass_count", "failed_baseline_count", "trajectory_count",
            "candidate_count_per_failed_context", "maximum_successful_plant_steps",
        )) != (6, 10, 250, 25, 9050)
        or tuple(int(gate.get(key, -1)) for key in (
            "minimum_repaired_failed_baseline_count", "minimum_measured_oracle_formal_pass_count"
        )) != (1, 7)
        or cfg.get("routes") != expected_routes
        or any(scope.get(key) is not False for key in (
            "model_fit_allowed", "real_mpc_executed", "gate_a_qualified",
            "expert_data_allowed", "bc_dagger_or_rl_allowed",
            "all_stage_trajectories_allowed_in_expert_dataset",
            "global_plant_reachability_claimed",
        ))
        or scope.get("identification_only") is not True
    )
    if invalid:
        raise ValueError("R8R51R4D4 frozen design changed")


def load_context(args: argparse.Namespace) -> Context:
    config_path = args.config.expanduser().resolve()
    cfg = _read(config_path)
    validate_config(cfg, _root())
    source_args = SimpleNamespace(**vars(args))
    source_args.config = (_root() / cfg["source_r51r4d3_config"]).resolve()
    source_args.run_dir = args.r51r4d3_run.expanduser().resolve()
    d3_ctx = d3.load_context(source_args)
    expected = cfg["source_r51r4d3"]
    if (
        d3_ctx.paths.stage.parent.name != expected["run_name"]
        or d3_ctx.paths.stage.name != expected["stage_directory"]
    ):
        raise ValueError("R8R51R4D4 source D3 identity changed")
    failed_attempt_stage = args.failed_r51r4d4_run.expanduser().resolve() / RUN_NAME
    failed_expected = cfg["failed_attempt_contract"]
    if (
        failed_attempt_stage.parent.name != failed_expected["run_name"]
        or failed_attempt_stage.name != failed_expected["stage_directory"]
    ):
        raise ValueError("R8R51R4D4 failed-attempt identity changed")
    return Context(
        cfg=cfg,
        config_path=config_path,
        paths=_paths(args.run_dir),
        d3_ctx=d3_ctx,
        d3_stage=d3_ctx.paths.stage,
        r4_ctx=d3_ctx.d1_ctx.r4_ctx,
        failed_attempt_stage=failed_attempt_stage,
    )


D3_ARTIFACTS = {
    "specs": "specs/all_specs.json",
    "source_authentication": "source_reference/source_authentication.json",
    "offline_primary": "analysis/offline_primary.json",
    "offline_construction": "analysis/offline_construction_primary.json",
    "offline_independent": "analysis/offline_independent.json",
    "final_report": "analysis/final_report.json",
    "stage_state": "stage_state.json",
    "stage_manifest": "stage_manifest.json",
    "final_server_evidence": "analysis/final_server_evidence.json",
}

FAILED_ATTEMPT_ARTIFACTS = {
    "stage_manifest": "stage_manifest.json",
    "stage_state": "stage_state.json",
    "failed_attempt_server_evidence": "analysis/failed_attempt_server_evidence.json",
    "failed_attempt_final_server_evidence": "analysis/failed_attempt_final_server_evidence.json",
    "raw_integrity_primary": "analysis/raw_integrity_primary.json",
    "raw_integrity_independent": "analysis/raw_integrity_independent.json",
}


def _failed_attempt_byte_authentication(raw: Path) -> dict[str, Any]:
    digest = hashlib.sha256()
    total = 0
    paths = sorted(raw.glob("*.json.gz"))
    for path in paths:
        data = path.read_bytes()
        total += len(data)
        digest.update(path.name.encode())
        digest.update(b"\0")
        digest.update(hashlib.sha256(data).digest())
    return {"count": len(paths), "bytes": total, "digest": digest.hexdigest()}


def authenticate_failed_attempt(ctx: Context) -> dict[str, Any]:
    expected = ctx.cfg["failed_attempt_contract"]
    hashes: dict[str, str] = {}
    for key, relative in FAILED_ATTEMPT_ARTIFACTS.items():
        path = ctx.failed_attempt_stage / relative
        if not path.is_file() or _sha(path) != expected[f"{key}_sha256"]:
            raise SourceBlockedError(f"R8R51R4D4 failed-attempt source changed: {relative}")
        hashes[key] = _sha(path)
    state = _read(ctx.failed_attempt_stage / FAILED_ATTEMPT_ARTIFACTS["stage_state"])
    primary = _read(ctx.failed_attempt_stage / FAILED_ATTEMPT_ARTIFACTS["raw_integrity_primary"])
    independent = _read(ctx.failed_attempt_stage / FAILED_ATTEMPT_ARTIFACTS["raw_integrity_independent"])
    evidence = _read(
        ctx.failed_attempt_stage / FAILED_ATTEMPT_ARTIFACTS["failed_attempt_final_server_evidence"]
    )
    inventory = r4.r51.r8r7.r8._inventory(ctx.failed_attempt_stage / "raw")
    byte_authentication = _failed_attempt_byte_authentication(ctx.failed_attempt_stage / "raw")
    valid = bool(
        state.get("finished") is True
        and state.get("phase_status") == "real_execution_failed"
        and state.get("route") == expected["route"]
        and int(state.get("plant_step_count", -1)) == int(expected["plant_step_count"])
        and state.get("response_outcomes_opened") is False
        and primary.get("passed") is False
        and primary.get("runtime_failure_count") == 250
        and primary.get("runtime_success_count") == 0
        and primary.get("full_horizon_count") == 0
        and independent.get("passed") is False
        and independent.get("primary_agreement") is True
        and evidence.get("classification")
        == "CONTROLLER_IMPLEMENTATION_RUNTIME_ERROR_NO_SCIENTIFIC_RESPONSE_RESULT"
        and evidence.get("response_outcomes_opened") is False
        and evidence.get("formal_metrics_computed") is False
        and evidence.get("same_output_rerun_forbidden") is True
        and evidence.get("first_candidate_event_count") == 0
        and evidence.get("second_candidate_event_count") == 0
        and evidence.get("partial_integrity_pass_count") == 250
        and inventory.get("count") == int(expected["raw_count"])
        and inventory.get("bytes") == int(expected["raw_bytes"])
        and inventory.get("digest") == expected["raw_inventory_digest"]
        and byte_authentication["digest"] == expected["raw_byte_authentication_digest"]
    )
    if not valid:
        raise SourceBlockedError("R8R51R4D4 immutable failed-attempt provenance changed")
    return {
        "stage": str(ctx.failed_attempt_stage),
        "hashes": hashes,
        "raw_inventory": {
            "count": inventory["count"],
            "bytes": inventory["bytes"],
            "digest": inventory["digest"],
        },
        "raw_byte_authentication": byte_authentication,
        "route": state["route"],
        "response_outcomes_opened": False,
        "formal_metrics_computed": False,
        "same_output_rerun_forbidden": True,
        "passed": True,
    }


def authenticate_sources(ctx: Context) -> dict[str, Any]:
    inherited = d3.authenticate_source(ctx.d3_ctx)
    failed_attempt = authenticate_failed_attempt(ctx)
    expected = ctx.cfg["source_r51r4d3"]
    hashes: dict[str, str] = {}
    for key, relative in D3_ARTIFACTS.items():
        path = ctx.d3_stage / relative
        if not path.is_file() or _sha(path) != expected[f"{key}_sha256"]:
            raise SourceBlockedError(f"R8R51R4D4 D3 source changed: {relative}")
        hashes[key] = _sha(path)
    primary = _read(ctx.d3_stage / D3_ARTIFACTS["offline_primary"])
    construction = _read(ctx.d3_stage / D3_ARTIFACTS["offline_construction"])
    independent = _read(ctx.d3_stage / D3_ARTIFACTS["offline_independent"])
    final = _read(ctx.d3_stage / D3_ARTIFACTS["final_report"])
    state = _read(ctx.d3_stage / D3_ARTIFACTS["stage_state"])
    evidence = _read(ctx.d3_stage / D3_ARTIFACTS["final_server_evidence"])
    valid = (
        inherited.get("passed") is True
        and primary.get("passed") is True
        and primary.get("action_stream_digest") == expected["action_stream_digest"]
        and construction.get("passed") is True
        and len(construction.get("rows") or []) == 250
        and independent.get("audit_passed") is True
        and independent.get("scientific_gate_passed") is True
        and final.get("passed") is True
        and final.get("route") == expected["required_route"]
        and state.get("finished") is True
        and state.get("route") == expected["required_route"]
        and evidence.get("audit_passed") is True
        and evidence.get("scientific_gate_passed") is True
        and evidence.get("eligible_specification_count") == 250
        and evidence.get("new_tsc_count") == 0
        and evidence.get("raw_or_snapshot_file_count") == 0
        and evidence.get("route") == expected["required_route"]
    )
    if not valid:
        raise SourceBlockedError("R8R51R4D4 final D3 provenance changed")
    return {
        "d3_stage": str(ctx.d3_stage),
        "d3_hashes": hashes,
        "inherited_digest": _digest(inherited),
        "action_stream_digest": expected["action_stream_digest"],
        "conditional_d5_design_sha256": ctx.cfg["conditional_d5_design_sha256"],
        "failed_attempt": failed_attempt,
        "response_values_available_to_construction": False,
        "passed": True,
    }


def build_specs(ctx: Context) -> list[dict[str, Any]]:
    d3_specs = _read(ctx.d3_stage / D3_ARTIFACTS["specs"])
    baselines, _ = r4.r51._source_baselines(ctx.r4_ctx.base_ctx)
    baseline_by_id = {str(row["experiment_id"]): row for row in baselines}
    rows = []
    for source in d3_specs:
        baseline_id = str(source["source_r8r7_baseline_experiment_id"])
        spec = copy.deepcopy(baseline_by_id[baseline_id])
        spec.update(copy.deepcopy(source))
        spec.update(
            {
                "kind": "stage4_2r3c3t13s24d1r14r8r51r4d4_center_bridged_two_pulse",
                "stage": STAGE,
                "campaign_identity": IDENTITY,
                "controller_revision": CONTROLLER_REVISION,
                "experiment_id": str(source["experiment_id"]).replace("r8r51r4d3_", "r8r51r4d4_"),
                "r8r51r4d4_allowed_in_expert_dataset": False,
                "pair_or_history_label_available_to_controller": False,
                "source_result_available_to_controller": False,
                "future_measurement_count": 0,
                "future_action_count": 0,
                "formal_timing_unchanged": True,
                # Compatibility fields initialize the inherited exact first issue.
                "r8r51r1_candidate_id": str(source["first_candidate_id"]),
                "r8r51r1_requested_coordinate": copy.deepcopy(source["first_requested_coordinate"]),
                "r8r51r4_return_task_step": FIRST_RETURN,
            }
        )
        rows.append(spec)
    coverage = {
        (
            row["source_r8r7_baseline_experiment_id"],
            row["first_candidate_id"],
            row["second_candidate_id"],
        )
        for row in rows
    }
    if len(rows) != 250 or len(coverage) != 250 or len({row["experiment_id"] for row in rows}) != 250:
        raise ValueError("R8R51R4D4 matrix changed")
    return rows


def _execution_context(ctx: Context) -> Any:
    return r4._execution_context(ctx.r4_ctx)


def _controller_contract(ctx: Context) -> dict[str, Any]:
    contract = copy.deepcopy(ctx.cfg["controller_contract"])
    contract["dynamic_exact_search_radius"] = int(ctx.cfg["schedule_contract"]["dynamic_exact_search_radius"])
    source_cfg = ctx.r4_ctx.base_ctx.r8r48_ctx.source_ctx.cfg
    contract["requested_coordinate_matrix_columns"] = copy.deepcopy(
        source_cfg["candidate_contract"]["canonical_matrix_columns"]
    )
    contract["requested_matrix_float64_le_c_sha256"] = str(
        source_cfg["candidate_contract"]["canonical_matrix_float64_le_c_sha256"]
    )
    return contract


def _payload(ctx: Context, spec: Mapping[str, Any]) -> dict[str, Any]:
    payload = r4.r51.r8r7.r8._payload(_execution_context(ctx), spec)
    experiment_id = str(spec["experiment_id"])
    payload.update(
        {
            "variant_id": f"stage4_2r3c3t13s24d1r14r8r51r4d4_{experiment_id}",
            "stage4_2r3c3t13s24d1r14r8r51r4d4_first_candidate_id": str(spec["first_candidate_id"]),
            "stage4_2r3c3t13s24d1r14r8r51r4d4_second_candidate_id": str(spec["second_candidate_id"]),
            "stage4_2r3c3t13s24d1r14r8r51r4d4_pair_history_label_available_to_controller": False,
        }
    )
    _write(ctx.paths.variants / f"payload_{experiment_id}.json", payload, replace=True)
    return payload


def _events(ctx: Context, spec: Mapping[str, Any]) -> list[dict[str, Any]]:
    source_rows = d3.d1._source_specs(ctx.d3_ctx.d1_ctx)
    by_id = {str(row["experiment_id"]): row for row in source_rows}
    first_spec = by_id[str(spec["first_source_experiment_id"])]
    second_spec = by_id[str(spec["second_source_experiment_id"])]
    first_base = r4.construct_event_stream(ctx.r4_ctx, first_spec, include_events=True)
    second_base = r4.construct_event_stream(ctx.r4_ctx, second_spec, include_events=True)
    events = [copy.deepcopy(event) for event in first_base["events"] if int(event["task_step"]) <= FIRST_RETURN]
    first_issue = next(event for event in events if int(event["task_step"]) == FIRST_ISSUE)
    first_return = events[-1]
    actuator, _, field_basis, lattice, contract = d3.d1._runtime_parts(ctx.d3_ctx.d1_ctx, first_spec)
    center_fields = list(events[0]["q0_center_card15_fields"])
    current = np.asarray(first_return["nominal_readback_current_a_tsc"], dtype=float)
    bridge = r4.r51._observe_event(
        task_step=BRIDGE_STEP, currents=current, target_fields=center_fields,
        actuator=actuator, contract=contract, event="exact_q0_center_bridge_hold",
    )
    events.append(bridge)
    current = np.asarray(bridge["nominal_readback_current_a_tsc"], dtype=float)
    second = r4.r51.r8r22._construct_coordinate_issue(
        task_step=SECOND_ISSUE, currents_a_tsc=current,
        fixed_basis_delta_field_kat_tsc=field_basis.T,
        requested_coordinate=spec["second_requested_coordinate"],
        candidate_id=str(spec["second_candidate_id"]), actuator=actuator,
        controller_cfg=contract, lattice_cfg=lattice,
    )
    second["center_nominal_readback_current_a_tsc"] = current.tolist()
    second["event"] = "second_center_bridged_candidate_issue"
    events.append(second)
    current = np.asarray(second["nominal_issue_readback_current_a_tsc"], dtype=float)
    for step in (19, 20, 21):
        hold = r4.r51._observe_event(
            task_step=step, currents=current, target_fields=second["target_card15_fields"],
            actuator=actuator, contract=contract, event="second_candidate_exact_hold",
        )
        events.append(hold)
        current = np.asarray(hold["nominal_readback_current_a_tsc"], dtype=float)
    returned = r4.r51._return_event(
        task_step=SECOND_RETURN, currents=current, center_fields=center_fields,
        issue_event=second, field_basis=field_basis, actuator=actuator,
        lattice=lattice, contract=contract,
    )
    returned["event"] = "second_pulse_stored_center_return"
    events.append(returned)
    current = np.asarray(returned["nominal_readback_current_a_tsc"], dtype=float)
    for step in range(23, int(spec["horizon_steps"])):
        refresh = r4.r51.r8r22._refresh_event(
            task_step=step, currents=current, target_fields=center_fields,
            actuator=actuator, turns_tsc=actuator.turns_tsc,
            max_delta_a=actuator.max_slew_step_a,
            minimum_current=actuator.minimum_current_a_tsc,
            maximum_current=actuator.maximum_current_a_tsc,
            lattice_cfg=lattice, contract=contract,
        )
        refresh["event"] = "post_second_pulse_exact_center_refresh"
        events.append(refresh)
        current = np.asarray(refresh["nominal_readback_current_a_tsc"], dtype=float)
    if tuple(int(event["task_step"]) for event in events) != tuple(range(10, int(spec["horizon_steps"]))):
        raise ValueError("R8R51R4D4 event clock changed")
    source_second = next(event for event in second_base["events"] if int(event["task_step"]) == 12)
    if list(second["target_card15_fields"]) != list(source_second["target_card15_fields"]):
        raise ValueError("R8R51R4D4 second target changed")
    if not first_issue.get("passed") or not all(event.get("passed") is True for event in events):
        raise ValueError("R8R51R4D4 offline event failed")
    return events


def _offline_construction(ctx: Context, specs: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    d3_rows = {
        str(row["experiment_id"]).replace("r8r51r4d3_", "r8r51r4d4_"): row
        for row in _read(ctx.d3_stage / D3_ARTIFACTS["offline_construction"])["rows"]
    }
    rows = []
    for spec in specs:
        events = _events(ctx, spec)
        source = d3_rows[str(spec["experiment_id"])]
        action_digest = _digest([d3.d1._canonical_event(event) for event in events])
        criteria = {
            "source_d3_eligible": source.get("eligible") is True,
            "event_count": len(events) == int(spec["horizon_steps"]) - 10,
            "all_event_gates": all(
                event.get("passed") is True
                and all(bool(value) for value in (event.get("criteria") or {}).values())
                for event in events
            ),
            "action_stream_matches_d3": action_digest == source.get("action_stream_digest"),
            "learning_forbidden": spec.get("r8r51r4d4_allowed_in_expert_dataset") is False,
            "no_response_input": spec.get("source_result_available_to_controller") is False,
        }
        rows.append(
            {
                "experiment_id": str(spec["experiment_id"]),
                "context_index": int(spec["context_index"]),
                "pair_id": str(spec["pair_id"]),
                "history_member": str(spec["history_member"]),
                "first_candidate_id": str(spec["first_candidate_id"]),
                "second_candidate_id": str(spec["second_candidate_id"]),
                "event_count": len(events),
                "event_stream_digest": _digest(events),
                "action_stream_digest": action_digest,
                "maximum_incremental_action_linf": max(float(event["incremental_normalized_action_linf"]) for event in events),
                "maximum_current_utilization": max(float(event["predicted_current_utilization"]) for event in events),
                "criteria": criteria,
                "events": events,
                "passed": all(criteria.values()),
            }
        )
    return {
        "schema_version": 1,
        "stage": STAGE,
        "construction_count": len(rows),
        "construction_pass_count": sum(bool(row["passed"]) for row in rows),
        "event_stream_digest": _digest([(row["experiment_id"], row["event_stream_digest"]) for row in rows]),
        "action_stream_digest": _digest([(row["experiment_id"], row["action_stream_digest"]) for row in rows]),
        "maximum_incremental_action_linf": max(float(row["maximum_incremental_action_linf"]) for row in rows),
        "maximum_current_utilization": max(float(row["maximum_current_utilization"]) for row in rows),
        "rows": rows,
        "passed": len(rows) == 250 and all(bool(row["passed"]) for row in rows),
    }


def _set_state(ctx: Context, **updates: Any) -> dict[str, Any]:
    state = _read(ctx.paths.state)
    state.update(updates)
    _write(ctx.paths.state, state, replace=True)
    return state


def prepare_offline(ctx: Context) -> dict[str, Any]:
    if ctx.paths.stage.exists():
        raise ValueError("R8R51R4D4 offline requires fresh output")
    for path in (ctx.paths.stage, ctx.paths.variants, ctx.paths.specs, ctx.paths.source_reference, ctx.paths.raw, ctx.paths.analysis):
        path.mkdir(parents=True, exist_ok=True)
    try:
        source = authenticate_sources(ctx)
        specs = build_specs(ctx)
        for spec in specs:
            _payload(ctx, spec)
        construction = _offline_construction(ctx, specs)
        frozen = ctx.cfg["frozen_offline_contract"]
        frozen_offline_identity = bool(
            construction["construction_count"] == int(frozen["specification_count"])
            and construction["action_stream_digest"] == frozen["action_stream_digest"]
            and construction["event_stream_digest"] == frozen["event_stream_digest"]
            and float(construction["maximum_incremental_action_linf"])
            == float(frozen["maximum_incremental_action_linf"])
            and float(construction["maximum_current_utilization"])
            == float(frozen["maximum_current_utilization"])
        )
        _write(ctx.paths.specs / "all_specs.json", specs)
        _write(ctx.paths.source_reference / "source_authentication.json", source)
        _write(ctx.paths.analysis / "offline_construction.json", construction)
        package = r4.r51.r8r7._package_fingerprint()
        manifest = {
            "schema_version": 1, "stage": STAGE, "identity": IDENTITY,
            "controller_revision": CONTROLLER_REVISION,
            "package_revision": ctx.cfg["package_revision"],
            "config_sha256": _sha(ctx.config_path),
            "design_document_sha256": ctx.cfg["design_document_sha256"],
            "design_checkpoint": ctx.cfg["design_checkpoint"],
            "original_design_document_sha256": ctx.cfg["original_design_document_sha256"],
            "conditional_d5_design_sha256": ctx.cfg["conditional_d5_design_sha256"],
            "source_d3_run": str(ctx.d3_stage.parent),
            "failed_attempt_run": str(ctx.failed_attempt_stage.parent),
            "source_authentication_digest": _digest(source),
            "spec_count": len(specs), "spec_digest": _digest(specs),
            "offline_construction_digest": _digest(construction),
            "package_fingerprint": package,
            "all_stage_trajectories_allowed_in_expert_dataset": False,
        }
        _write(ctx.paths.manifest, manifest)
        passed = bool(construction["passed"] and frozen_offline_identity)
        route = ctx.cfg["routes"]["pass" if passed else "offline_fail"]
        _write(
            ctx.paths.state,
            {
                "schema_version": 1, "stage": STAGE,
                "phase_status": "offline_primary_ready" if passed else "offline_failed",
                "finished": not passed, "real_tsc_executed": False,
                "plant_step_count": 0, "new_raw_count": 0,
                "response_outcomes_opened": False,
                "spec_digest": manifest["spec_digest"],
                "package_digest": package["digest"],
                "route": route, "verdict": {"route": route, "passed": passed},
                "stop_reason": "" if passed else "offline_action_construction_failed",
            },
        )
        report = {
            "schema_version": 1, "stage": STAGE, "phase": "offline_primary",
            "source_authenticated": True, "spec_count": len(specs),
            "construction_count": construction["construction_count"],
            "construction_pass_count": construction["construction_pass_count"],
            "event_stream_digest": construction["event_stream_digest"],
            "action_stream_digest": construction["action_stream_digest"],
            "maximum_incremental_action_linf": construction["maximum_incremental_action_linf"],
            "maximum_current_utilization": construction["maximum_current_utilization"],
            "frozen_offline_identity_passed": frozen_offline_identity,
            "new_raw_count": 0, "plant_step_count": 0,
            "real_tsc_executed": False, "route": route, "passed": passed,
        }
    except SourceBlockedError as exc:
        route = ctx.cfg["routes"]["source_blocked"]
        report = {
            "schema_version": 1, "stage": STAGE, "phase": "offline_primary",
            "source_authenticated": False, "spec_count": 0,
            "construction_count": 0, "construction_pass_count": 0,
            "new_raw_count": 0, "plant_step_count": 0,
            "real_tsc_executed": False, "route": route, "passed": False,
            "failure_reason": repr(exc),
        }
        _write(ctx.paths.manifest, {"schema_version": 1, "stage": STAGE, "source_blocked": True})
        _write(ctx.paths.state, {
            "schema_version": 1, "stage": STAGE, "phase_status": "source_blocked",
            "finished": True, "real_tsc_executed": False, "plant_step_count": 0,
            "new_raw_count": 0, "response_outcomes_opened": False,
            "route": route, "verdict": {"route": route, "passed": False},
            "stop_reason": "source_authentication_failed",
        })
    _write(ctx.paths.analysis / "offline_primary.json", report)
    return report


def _saved_specs(ctx: Context) -> list[dict[str, Any]]:
    specs = _read(ctx.paths.specs / "all_specs.json")
    manifest = _read(ctx.paths.manifest)
    if len(specs) != 250 or _digest(specs) != manifest.get("spec_digest") or _sha(ctx.config_path) != manifest.get("config_sha256"):
        raise ValueError("R8R51R4D4 saved spec identity changed")
    return specs


def authorize_real(ctx: Context) -> dict[str, Any]:
    state = _read(ctx.paths.state)
    primary = _read(ctx.paths.analysis / "offline_primary.json")
    independent = _read(ctx.paths.analysis / "offline_independent.json")
    if (
        state.get("phase_status") != "offline_primary_ready"
        or primary.get("passed") is not True
        or independent.get("passed") is not True
        or independent.get("primary_agreement") is not True
        or independent.get("source_authenticated") is not True
        or independent.get("conditional_d5_design_authenticated") is not True
    ):
        raise ValueError("R8R51R4D4 offline independent authorization gate failed")
    _set_state(
        ctx, phase_status="real_authorized",
        offline_independent_sha256=_sha(ctx.paths.analysis / "offline_independent.json"),
    )
    return {"stage": STAGE, "phase": "real_authorized", "passed": True}


class TwoPulseController(r4.SustainedDwellController):
    """Exact first pulse, center bridge, exact second pulse, and return."""

    def __init__(self, *args: Any, spec: Mapping[str, Any], **kwargs: Any):
        super().__init__(*args, spec=spec, **kwargs)
        self.r8r51r4_return_step = FIRST_RETURN
        self._first_candidate_id = str(spec["first_candidate_id"])
        self._first_coordinate = np.asarray(spec["first_requested_coordinate"], dtype=float)
        self._second_candidate_id = str(spec["second_candidate_id"])
        self._second_coordinate = np.asarray(spec["second_requested_coordinate"], dtype=float)
        self.r8r51r1_candidate_id = self._first_candidate_id
        self.r8r51r1_requested_coordinate = self._first_coordinate.copy()

    def action(self, current_state: Mapping[str, Any]) -> tuple[np.ndarray, dict[str, Any]]:
        if int(current_state["step_index"]) != self.step:
            raise ValueError("R8R51R4D4 controller/current state index mismatch")
        if self.step < PREFIX_END:
            action, trace = super(r4.r51.BridgeController, self).action(current_state)
            event_name, event, delegated = "none", {}, True
        else:
            currents = np.asarray(current_state["currents_a_tsc"], dtype=float)
            delegated = False
            if self.step == Q0_STEP:
                action, event = self._q0(currents)
                event_name = "q0_exact_issue"
            elif self.step == 11:
                event = r4.r51._observe_event(
                    task_step=self.step, currents=currents,
                    target_fields=self.r8r51r1_center_fields or [],
                    actuator=self.actuator, contract=self.r8r51r1_contract,
                    event="q0_observe_hold",
                )
                action, event_name = np.zeros(N_COILS), "q0_observe_hold"
            elif self.step == FIRST_ISSUE:
                self.r8r51r1_candidate_id = self._first_candidate_id
                self.r8r51r1_requested_coordinate = self._first_coordinate.copy()
                action, event = self._issue_candidate(currents)
                event_name = "first_candidate_issue"
            elif FIRST_ISSUE < self.step < FIRST_RETURN:
                if self.r8r51r1_issue_event is None:
                    raise ValueError("R8R51R4D4 first hold has no issue")
                event = r4.r51._observe_event(
                    task_step=self.step, currents=currents,
                    target_fields=self.r8r51r1_issue_event["target_card15_fields"],
                    actuator=self.actuator, contract=self.r8r51r1_contract,
                    event="candidate_current_dwell_hold",
                )
                action, event_name = np.zeros(N_COILS), "first_candidate_hold"
            elif self.step == FIRST_RETURN:
                action, event = self._return(currents)
                event_name = "first_stored_center_return"
            elif self.step == BRIDGE_STEP:
                event = r4.r51._observe_event(
                    task_step=self.step, currents=currents,
                    target_fields=self.r8r51r1_center_fields or [],
                    actuator=self.actuator, contract=self.r8r51r1_contract,
                    event="exact_q0_center_bridge_hold",
                )
                action, event_name = np.zeros(N_COILS), "center_bridge_hold"
            elif self.step == SECOND_ISSUE:
                self.r8r51r1_candidate_id = self._second_candidate_id
                self.r8r51r1_requested_coordinate = self._second_coordinate.copy()
                action, event = self._issue_candidate(currents)
                event["event"] = "second_center_bridged_candidate_issue"
                event_name = "second_candidate_issue"
            elif SECOND_ISSUE < self.step < SECOND_RETURN:
                if self.r8r51r1_issue_event is None:
                    raise ValueError("R8R51R4D4 second hold has no issue")
                event = r4.r51._observe_event(
                    task_step=self.step, currents=currents,
                    target_fields=self.r8r51r1_issue_event["target_card15_fields"],
                    actuator=self.actuator, contract=self.r8r51r1_contract,
                    event="second_candidate_exact_hold",
                )
                action, event_name = np.zeros(N_COILS), "second_candidate_hold"
            elif self.step == SECOND_RETURN:
                action, event = self._return(currents)
                event["event"] = "second_pulse_stored_center_return"
                event_name = "second_stored_center_return"
            else:
                action, event = self._center_refresh(currents)
                event["event"] = "post_second_pulse_exact_center_refresh"
                event_name = "center_refresh"
            if not event.get("passed"):
                raise ValueError(
                    "R8R51R4D4 action safety gate failed: "
                    + json.dumps(event, sort_keys=True)
                )
            trace = r4.r51.r6._trace_template(self.step, np.asarray(action, dtype=float))
        trace.update(
            {
                "action_norm_tsc": np.asarray(action, dtype=float).tolist(),
                "r3c3t13s24d1r14r8r51r4d4_controller_revision": CONTROLLER_REVISION,
                "r3c3t13s24d1r14r8r51r4d4_delegated_prefix": delegated,
                "r3c3t13s24d1r14r8r51r4d4_event": event_name,
                "r3c3t13s24d1r14r8r51r4d4_event_detail": copy.deepcopy(event),
                "r3c3t13s24d1r14r8r51r4d4_forbidden_input_used": False,
                "r3c3t13s24d1r14r8r51r4d4_pair_or_history_label_used": False,
                "r3c3t13s24d1r14r8r51r4d4_future_measurement_used": False,
                "r3c3t13s24d1r14r8r51r4d4_future_action_used": False,
                "r3c3t13s24d1r14r8r51r4d4_source_result_used": False,
                "r3c3t13s24d1r14r8r51r4d4_hidden_wire_used": False,
            }
        )
        return np.asarray(action, dtype=float), trace


class LocalWorker(r4.r51.LocalWorker):
    def evaluate(self, spec: dict[str, Any]) -> dict[str, Any]:
        started = time.time()
        failed = True
        trajectory: list[dict[str, Any]] = []
        trace: list[dict[str, Any]] = []
        result: dict[str, Any] = {
            "schema_version": 1, "stage": STAGE, "campaign_identity": IDENTITY,
            "controller_revision": CONTROLLER_REVISION,
            "experiment_id": spec["experiment_id"], "spec": copy.deepcopy(spec),
            "success": False, "completed": False, "failure_reason": "",
            "execution_failure_class": "", "trajectory": trajectory,
            "controller_trace": trace,
        }
        try:
            horizon = int(spec["horizon_steps"])
            if horizon != int(self.base.env.max_episode_steps) or horizon not in (35, 37):
                raise ValueError("R8R51R4D4 formal horizon changed")
            self.base.env.reset()
            zero = np.zeros(N_COILS, dtype=np.float32)
            record = r4.r51.r8r7.r8.d1r11.s21.s16.s9.t11.t1.r1._state_record_full
            trajectory.append(record(self.base.env, 0, zero))
            controller = TwoPulseController(
                self.base, self.bundle, spec, trajectory[0], self.lattice_cfg,
                self.calibration_cfg, self.dynamic_cfg, self.schedule_cfg,
                self.controller_cfg, spec=spec,
            )
            for step in range(horizon):
                current = trajectory[-1]
                finite = (
                    all(math.isfinite(float(current[key])) for key in ("R", "Z", "Ip"))
                    and np.all(np.isfinite(np.asarray(current["currents_a_tsc"], dtype=float)))
                )
                if not finite or bool(current.get("abnormal")):
                    result["execution_failure_class"] = "pre_action_visible_state_safety_failure"
                    raise ValueError("R8R51R4D4 pre-action state safety gate failed")
                try:
                    action, row = controller.action(current)
                except ValueError as exc:
                    if "safety gate failed" in str(exc):
                        result["execution_failure_class"] = "controller_action_safety_gate_failure"
                    raise
                _, _, terminated, truncated, info = self.base.env.step(action)
                next_state = record(self.base.env, step + 1, action)
                trajectory.append(next_state)
                trace.append(row)
                controller.advance(next_state)
                if terminated:
                    result["execution_failure_class"] = "plant_abnormal_termination"
                    raise RuntimeError(str(info.get("failure_reason", "environment terminated")))
                if truncated and step + 1 < horizon:
                    result["execution_failure_class"] = "plant_early_truncation"
                    raise RuntimeError("environment truncated before R8R51R4D4 horizon")
            names = [row.get("r3c3t13s24d1r14r8r51r4d4_event") for row in trace[PREFIX_END:]]
            expected = [
                "q0_exact_issue", "q0_observe_hold", "first_candidate_issue",
                "first_candidate_hold", "first_candidate_hold", "first_candidate_hold",
                "first_stored_center_return", "center_bridge_hold", "second_candidate_issue",
                "second_candidate_hold", "second_candidate_hold", "second_candidate_hold",
                "second_stored_center_return",
            ]
            success = bool(
                len(trajectory) == horizon + 1 and len(trace) == horizon
                and r4.r51.r8r7.r8.r4._calibration_exact(trace)
                and all(bool(row.get("r3c3t13s24d1r14r8r51r4d4_delegated_prefix")) for row in trace[:PREFIX_END])
                and names[:13] == expected
                and all(name == "center_refresh" for name in names[13:])
                and all(
                    bool((row.get("r3c3t13s24d1r14r8r51r4d4_event_detail") or {}).get("passed"))
                    for row in trace[PREFIX_END:]
                )
                and controller._active_issue is None
                and not any(bool(row.get("abnormal")) for row in trajectory)
            )
            result.update(
                {
                    "success": success, "completed": True,
                    "failure_reason": "" if success else "incomplete or invalid R8R51R4D4 rollout",
                    "execution_failure_class": "" if success else "controller_or_action_semantics_error",
                    "hidden_history_control_summary": {
                        "fresh_controller_actor": True, "fresh_tsc_process": True,
                        "full_tsc_hidden_state_loaded_from_sprsina": True,
                        "future_r17_controller_executed": False,
                        "stage_trajectory_allowed_in_expert_dataset": False,
                        "future_action_replay_used": False, "future_measurement_used": False,
                        "pair_or_history_label_used": False, "source_result_used": False,
                    },
                    "wall_time_s": time.time() - started,
                }
            )
            failed = not success
            return r4.r51.r8r7.r8.d1r11.s21.s16.s9.t11.t1._json_safe(result)
        except Exception as exc:
            result.update(
                {
                    "success": False, "completed": True, "failure_reason": repr(exc),
                    "execution_failure_class": str(result.get("execution_failure_class") or "runtime_or_controller_error"),
                    "trajectory": trajectory, "controller_trace": trace,
                    "traceback": traceback.format_exc(), "wall_time_s": time.time() - started,
                }
            )
            return r4.r51.r8r7.r8.d1r11.s21.s16.s9.t11.t1._json_safe(result)
        finally:
            runner = getattr(self.base.env, "runner", None)
            if runner is not None:
                runner.cleanup_episode_workspace(failed=failed, reason="stage4_2r3c3t13s24d1r14r8r51r4d4")


_RAY_ACTOR = None


def _ray_actor_class():
    global _RAY_ACTOR
    if _RAY_ACTOR is None:
        import ray

        @ray.remote(num_cpus=1, max_restarts=0)
        class R8R51R4D4Actor:
            def __init__(self, *args: Any):
                self.worker = LocalWorker(*args)

            def evaluate(self, spec: dict[str, Any]) -> dict[str, Any]:
                return self.worker.evaluate(spec)

            def close(self) -> bool:
                self.worker.close()
                return True

        _RAY_ACTOR = R8R51R4D4Actor
    return _RAY_ACTOR


def _result_complete(path: Path, spec: Mapping[str, Any], *, require_success: bool = True) -> bool:
    if not path.is_file():
        return False
    try:
        result = r4.r51.r8r7.r8._read_gz(path)
        horizon = int(spec["horizon_steps"])
        return bool(
            result.get("completed")
            and (result.get("success") or not require_success)
            and result.get("stage") == STAGE
            and result.get("campaign_identity") == IDENTITY
            and result.get("controller_revision") == CONTROLLER_REVISION
            and result.get("experiment_id") == spec["experiment_id"]
            and result.get("spec") == dict(spec)
            and (
                not require_success
                or (
                    len(result.get("trajectory") or []) == horizon + 1
                    and len(result.get("controller_trace") or []) == horizon
                )
            )
        )
    except Exception:
        return False


def evaluate_specs(ctx: Context, specs: Sequence[dict[str, Any]], *, backend: str, resume: bool) -> dict[str, Any]:
    pending = [
        spec for spec in specs
        if not (resume and _result_complete(ctx.paths.raw / f"{spec['experiment_id']}.json.gz", spec, require_success=False))
    ]
    payloads = {str(spec["experiment_id"]): _payload(ctx, spec) for spec in specs}
    execution = _execution_context(ctx)
    library, bundle, selector = r4.r51.r8r7.r8.d1r11._library_bundle_selector(execution.d1r11_ctx)
    lattice = execution.d1r11_ctx.base_ctx.base_ctx.cfg["lattice_probe"]
    calibration = execution.d1r11_ctx.base_ctx.base_ctx.cfg["active_calibration"]
    dynamic = execution.d1r11_ctx.base_ctx.cfg["causal_model"]
    schedule_cfg = execution.d1r11_ctx.cfg["schedule_contract"]
    controller_cfg = _controller_contract(ctx)

    def args_for(spec: Mapping[str, Any], index: int) -> tuple[Any, ...]:
        return (
            payloads[str(spec["experiment_id"])], library, bundle,
            f"stage42r8r51r4d4_{index:03d}", selector, lattice,
            calibration, dynamic, schedule_cfg, controller_cfg,
        )

    if backend == "serial":
        for index, spec in enumerate(pending):
            worker = LocalWorker(*args_for(spec, index))
            try:
                result = worker.evaluate(spec)
            finally:
                worker.close()
            r4.r51.r8r7.r8._write_gz(ctx.paths.raw / f"{spec['experiment_id']}.json.gz", result)
            print(f"[R8R51R4D4] {index + 1}/{len(pending)}", flush=True)
    elif backend == "ray" and pending:
        import ray

        plan = r4.r51.r8r7.r8.d1r11.s21.s16.ensure_ray_worker_plan(
            ray, requested_workers=int(ctx.cfg["parallel"]["n_workers"]),
            pending_tasks=len(pending),
            ray_tmpdir=os.environ.get("RAY_TMPDIR") or ctx.cfg["storage"]["ray_tmpdir"],
            log_prefix="[R8R51R4D4]",
        )
        Actor = _ray_actor_class()
        completed = 0
        for start in range(0, len(pending), plan.actor_count):
            batch = pending[start : start + plan.actor_count]
            actors, refs = [], {}
            for offset, spec in enumerate(batch):
                actor = Actor.remote(*args_for(spec, start + offset))
                actors.append(actor)
                refs[actor.evaluate.remote(spec)] = spec
            try:
                while refs:
                    ready, _ = ray.wait(list(refs), num_returns=1, timeout=30.0)
                    if not ready:
                        print(f"[R8R51R4D4] waiting {completed}/{len(pending)}", flush=True)
                        continue
                    ref = ready[0]
                    spec = refs.pop(ref)
                    try:
                        result = ray.get(ref)
                    except Exception as exc:
                        result = {
                            "schema_version": 1, "stage": STAGE,
                            "campaign_identity": IDENTITY,
                            "controller_revision": CONTROLLER_REVISION,
                            "experiment_id": spec["experiment_id"],
                            "spec": copy.deepcopy(spec), "success": False,
                            "completed": True, "failure_reason": repr(exc),
                            "execution_failure_class": "ray_actor_runtime_error",
                            "trajectory": [], "controller_trace": [],
                            "traceback": traceback.format_exc(),
                        }
                    r4.r51.r8r7.r8._write_gz(ctx.paths.raw / f"{spec['experiment_id']}.json.gz", result)
                    completed += 1
                    print(f"[R8R51R4D4] {completed}/{len(pending)}", flush=True)
            finally:
                close_refs = [actor.close.remote() for actor in actors]
                if close_refs:
                    ray.get(close_refs, timeout=float(ctx.cfg["storage"]["actor_close_timeout_s"]))
                for actor in actors:
                    ray.kill(actor, no_restart=True)
    elif backend not in {"serial", "ray"}:
        raise ValueError(f"unsupported R8R51R4D4 backend: {backend}")
    completed = sum(
        _result_complete(ctx.paths.raw / f"{spec['experiment_id']}.json.gz", spec, require_success=False)
        for spec in specs
    )
    successful = sum(
        _result_complete(ctx.paths.raw / f"{spec['experiment_id']}.json.gz", spec)
        for spec in specs
    )
    return {
        "expected": len(specs), "pending_at_start": len(pending),
        "completed": completed, "successful": successful,
        "passed": completed == len(specs),
    }


FORBIDDEN_KEYS = (
    "r3c3t13s24d1r14r8r51r4d4_forbidden_input_used",
    "r3c3t13s24d1r14r8r51r4d4_pair_or_history_label_used",
    "r3c3t13s24d1r14r8r51r4d4_future_measurement_used",
    "r3c3t13s24d1r14r8r51r4d4_future_action_used",
    "r3c3t13s24d1r14r8r51r4d4_source_result_used",
    "r3c3t13s24d1r14r8r51r4d4_hidden_wire_used",
)


def _semantic_event_equal(actual: Mapping[str, Any], expected: Mapping[str, Any]) -> bool:
    exact_keys = (
        "task_step", "event", "candidate_id", "requested_coordinate",
        "action_norm_tsc", "target_card15_fields", "stored_target_card15_fields",
        "q0_center_card15_fields", "stored_center_card15_fields",
        "issue_target_card15_fields", "center_card15_fields", "passed", "criteria",
    )
    return all(actual.get(key) == expected.get(key) for key in exact_keys)


def _nominal_current(event: Mapping[str, Any]) -> np.ndarray:
    key = (
        "nominal_issue_readback_current_a_tsc"
        if "nominal_issue_readback_current_a_tsc" in event
        else "nominal_readback_current_a_tsc"
    )
    return np.asarray(event.get(key) or [], dtype=float)


def _prefix_payload(result: Mapping[str, Any], state_count: int, trace_count: int) -> dict[str, Any]:
    return {
        "states": [
            r4.r51.r8r7.r8.r4._semantic_state(row)
            for row in (result.get("trajectory") or [])[:state_count]
        ],
        "trace": (result.get("controller_trace") or [])[:trace_count],
    }


def audit_raw_integrity(ctx: Context, *, write: bool = True) -> dict[str, Any]:
    specs = _saved_specs(ctx)
    offline = {
        str(row["experiment_id"]): row
        for row in _read(ctx.paths.analysis / "offline_construction.json")["rows"]
    }
    _, sources = r4.r51._source_baselines(ctx.r4_ctx.base_ctx)
    rows = []
    q0_prefixes: dict[tuple[str, str], list[str]] = defaultdict(list)
    first_prefixes: dict[tuple[str, str, str], list[str]] = defaultdict(list)
    contract = ctx.cfg["controller_contract"]
    expected_names = [
        "q0_exact_issue", "q0_observe_hold", "first_candidate_issue",
        "first_candidate_hold", "first_candidate_hold", "first_candidate_hold",
        "first_stored_center_return", "center_bridge_hold", "second_candidate_issue",
        "second_candidate_hold", "second_candidate_hold", "second_candidate_hold",
        "second_stored_center_return",
    ]
    for spec in specs:
        experiment_id = str(spec["experiment_id"])
        path = ctx.paths.raw / f"{experiment_id}.json.gz"
        result = r4.r51.r8r7.r8._read_gz(path) if _result_complete(path, spec, require_success=False) else {}
        trajectory = result.get("trajectory") or []
        trace = result.get("controller_trace") or []
        horizon = int(spec["horizon_steps"])
        full = len(trajectory) == horizon + 1 and len(trace) == horizon
        source = sources[str(spec["source_r8r7_baseline_experiment_id"])]
        restart = bool(
            full
            and r4.r51.r8r7.r8.r4._semantic_state(trajectory[0])
            == r4.r51.r8r7.r8.r4._semantic_state(source["trajectory"][0])
        )
        source_prefix_state = bool(
            full
            and all(
                r4.r51.r8r7.r8.r4._semantic_state(current)
                == r4.r51.r8r7.r8.r4._semantic_state(reference)
                for current, reference in zip(
                    trajectory[: PREFIX_END + 1], source["trajectory"][: PREFIX_END + 1]
                )
            )
        )
        source_prefix_trace = bool(
            full
            and all(
                r4.r51.r8r22._source_trace_semantic_projection(reference, current)
                for current, reference in zip(
                    trace[:PREFIX_END], source["controller_trace"][:PREFIX_END]
                )
            )
        )
        context_key = (str(spec["pair_id"]), str(spec["history_member"]))
        first_key = (*context_key, str(spec["first_candidate_id"]))
        q0_digest = _digest(_prefix_payload(result, 13, 12)) if full else ""
        first_digest = _digest(_prefix_payload(result, 19, 18)) if full else ""
        q0_prefixes[context_key].append(q0_digest)
        first_prefixes[first_key].append(first_digest)
        details = [
            trace[step].get("r3c3t13s24d1r14r8r51r4d4_event_detail") or {}
            for step in range(PREFIX_END, horizon)
        ] if full else []
        names = [
            trace[step].get("r3c3t13s24d1r14r8r51r4d4_event")
            for step in range(PREFIX_END, horizon)
        ] if full else []
        expected_events = offline[experiment_id]["events"]
        sequence = bool(
            names[:13] == expected_names
            and all(name == "center_refresh" for name in names[13:])
            and len(details) == len(expected_events) == horizon - PREFIX_END
        )
        event_gate = bool(
            sequence
            and all(
                detail.get("passed") is True
                and all(bool(value) for value in (detail.get("criteria") or {}).values())
                for detail in details
            )
        )
        semantic_offline = bool(
            sequence
            and all(_semantic_event_equal(detail, expected) for detail, expected in zip(details, expected_events))
        )
        action_exact = bool(
            sequence
            and all(
                list(detail.get("action_norm_tsc") or []) == list(trace[step]["action_norm_tsc"])
                and list(trace[step]["action_norm_tsc"]) == list(trajectory[step + 1]["action_norm_tsc"])
                for step, detail in zip(range(PREFIX_END, horizon), details)
            )
        )
        current_differences = []
        current_equivalent = sequence
        if sequence:
            for step, detail in zip(range(PREFIX_END, horizon), details):
                nominal = _nominal_current(detail)
                physical = np.asarray(trajectory[step + 1]["currents_a_tsc"], dtype=float)
                if nominal.shape != (N_COILS,) or physical.shape != (N_COILS,):
                    current_equivalent = False
                    continue
                difference = float(np.max(np.abs(physical - nominal)))
                current_differences.append(difference)
                current_equivalent = bool(
                    current_equivalent
                    and np.allclose(physical, nominal, rtol=0.0, atol=CURRENT_ATOL_A, equal_nan=False)
                )
        first_effect = bool(
            full
            and np.array_equal(
                np.asarray(trajectory[FIRST_ISSUE + 1]["action_norm_tsc"]),
                np.asarray(trace[FIRST_ISSUE]["action_norm_tsc"]),
            )
            and not np.array_equal(
                np.asarray(trajectory[FIRST_ISSUE + 1]["currents_a_tsc"]),
                np.asarray(trajectory[FIRST_ISSUE]["currents_a_tsc"]),
            )
        )
        second_effect = bool(
            full
            and np.array_equal(
                np.asarray(trajectory[SECOND_ISSUE + 1]["action_norm_tsc"]),
                np.asarray(trace[SECOND_ISSUE]["action_norm_tsc"]),
            )
            and not np.array_equal(
                np.asarray(trajectory[SECOND_ISSUE + 1]["currents_a_tsc"]),
                np.asarray(trajectory[SECOND_ISSUE]["currents_a_tsc"]),
            )
        )
        finite = bool(
            full
            and all(math.isfinite(float(row[key])) for row in trajectory for key in ("R", "Z", "Ip"))
            and all(np.all(np.isfinite(np.asarray(row["currents_a_tsc"], dtype=float))) for row in trajectory)
            and not any(bool(row.get("abnormal")) for row in trajectory)
        )
        actions = np.asarray([row.get("action_norm_tsc", []) for row in trace], dtype=float)
        currents = np.asarray([row.get("currents_a_tsc", []) for row in trajectory], dtype=float)
        payload = _read(ctx.paths.variants / f"payload_{experiment_id}.json")
        minimum, maximum = r4.r51.r8r7.r8.d1r11.s21.s13._current_limits_tsc(payload)
        center, half = 0.5 * (minimum + maximum), 0.5 * (maximum - minimum)
        utilization = (
            float(np.max(np.abs((currents - center) / half)))
            if currents.shape == (horizon + 1, N_COILS) else None
        )
        forbidden = sum(any(bool(row.get(key)) for key in FORBIDDEN_KEYS) for row in trace)
        limits = bool(
            actions.shape == (horizon, N_COILS)
            and np.max(np.abs(actions)) <= float(contract["maximum_total_normalized_action_abs"]) + 1e-12
            and all(
                float(detail.get("incremental_normalized_action_linf", math.inf))
                <= float(contract["maximum_incremental_normalized_action_linf"]) + 1e-12
                for detail in details
            )
            and utilization is not None
            and utilization <= float(contract["maximum_current_utilization"]) + 1e-12
        )
        passed = bool(
            result.get("success") and full and restart and source_prefix_state
            and source_prefix_trace and r4.r51.r8r7.r8.r4._calibration_exact(trace)
            and sequence and event_gate and semantic_offline and action_exact
            and current_equivalent and first_effect and second_effect and finite
            and forbidden == 0 and limits
        )
        rows.append(
            {
                "experiment_id": experiment_id,
                "context_index": int(spec["context_index"]),
                "pair_id": str(spec["pair_id"]),
                "history_member": str(spec["history_member"]),
                "first_candidate_id": str(spec["first_candidate_id"]),
                "second_candidate_id": str(spec["second_candidate_id"]),
                "runtime_success": bool(result.get("success")),
                "full_horizon": full, "authentic_restart": restart,
                "source_prefix_state_exact": source_prefix_state,
                "source_prefix_trace_exact": source_prefix_trace,
                "calibration_exact": bool(full and r4.r51.r8r7.r8.r4._calibration_exact(trace)),
                "event_sequence_exact": sequence, "event_gates_passed": event_gate,
                "offline_event_semantics_exact": semantic_offline,
                "event_action_detail_trace_effect_exact": action_exact,
                "event_nominal_currents_numerically_equivalent": current_equivalent,
                "maximum_event_nominal_current_difference_a": (
                    max(current_differences) if current_differences else None
                ),
                "first_effect_at_issue_plus_one": first_effect,
                "second_effect_at_issue_plus_one": second_effect,
                "finite": finite, "forbidden_trace_count": forbidden,
                "maximum_current_utilization": utilization,
                "q0_prefix_digest": q0_digest, "first_prefix_digest": first_digest,
                "event_stream_digest": _digest(details) if details else "",
                "execution_failure_class": str(result.get("execution_failure_class") or ""),
                "failure_reason": str(result.get("failure_reason") or ""),
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
    inventory = r4.r51.r8r7.r8._inventory(ctx.paths.raw)
    passed_count = sum(bool(row["passed"]) for row in rows)
    safety_stops = sum(row["execution_failure_class"] == "controller_action_safety_gate_failure" for row in rows)
    runtime_failures = sum(
        bool(row["execution_failure_class"])
        and row["execution_failure_class"] != "controller_action_safety_gate_failure"
        for row in rows
    )
    report = {
        "schema_version": 1, "stage": STAGE, "phase": "raw_integrity_primary",
        "raw_inventory": inventory, "expected_raw_count": 250,
        "strict_parse_count": len(rows),
        "runtime_success_count": sum(bool(row["runtime_success"]) for row in rows),
        "full_horizon_count": sum(bool(row["full_horizon"]) for row in rows),
        "authentic_restart_count": sum(bool(row["authentic_restart"]) for row in rows),
        "source_prefix_state_exact_count": sum(bool(row["source_prefix_state_exact"]) for row in rows),
        "source_prefix_trace_exact_count": sum(bool(row["source_prefix_trace_exact"]) for row in rows),
        "calibration_exact_count": sum(bool(row["calibration_exact"]) for row in rows),
        "event_sequence_exact_count": sum(bool(row["event_sequence_exact"]) for row in rows),
        "event_gates_passed_count": sum(bool(row["event_gates_passed"]) for row in rows),
        "offline_event_semantics_exact_count": sum(bool(row["offline_event_semantics_exact"]) for row in rows),
        "event_action_detail_trace_effect_exact_count": sum(bool(row["event_action_detail_trace_effect_exact"]) for row in rows),
        "event_nominal_currents_numerically_equivalent_count": sum(bool(row["event_nominal_currents_numerically_equivalent"]) for row in rows),
        "first_effect_at_issue_plus_one_count": sum(bool(row["first_effect_at_issue_plus_one"]) for row in rows),
        "second_effect_at_issue_plus_one_count": sum(bool(row["second_effect_at_issue_plus_one"]) for row in rows),
        "within_context_q0_prefix_exact_count": sum(bool(row["within_context_q0_prefix_exact"]) for row in rows),
        "within_first_candidate_prefix_exact_count": sum(bool(row["within_first_candidate_prefix_exact"]) for row in rows),
        "finite_count": sum(bool(row["finite"]) for row in rows),
        "causal_forbidden_pass_count": sum(int(row["forbidden_trace_count"]) == 0 for row in rows),
        "passed_count": passed_count, "safety_stop_count": safety_stops,
        "runtime_failure_count": runtime_failures,
        "forbidden_trace_count": sum(int(row["forbidden_trace_count"]) for row in rows),
        "maximum_event_nominal_current_difference_a": max(
            (
                float(row["maximum_event_nominal_current_difference_a"])
                for row in rows
                if row["maximum_event_nominal_current_difference_a"] is not None
            ),
            default=None,
        ),
        "maximum_current_utilization": max(
            (float(row["maximum_current_utilization"]) for row in rows if row["maximum_current_utilization"] is not None),
            default=None,
        ),
        "q0_prefix_digest": _digest(sorted(set(row["q0_prefix_digest"] for row in rows))),
        "first_prefix_digest": _digest(sorted(set(row["first_prefix_digest"] for row in rows))),
        "event_stream_digest": _digest([(row["experiment_id"], row["event_stream_digest"]) for row in rows]),
        "rows": rows,
        "route": ctx.cfg["routes"]["pass" if passed_count == 250 and inventory["count"] == 250 else "execution_fail"],
        "passed": passed_count == 250 and inventory["count"] == 250,
    }
    if write:
        _write(ctx.paths.analysis / "raw_integrity_primary.json", report)
    return report


def _formal_authority(ctx: Context) -> dict[str, Any]:
    specs = _saved_specs(ctx)
    integrity = _read(ctx.paths.analysis / "raw_integrity_primary.json")
    _, sources = r4.r51._source_baselines(ctx.r4_ctx.base_ctx)
    baseline_rows = []
    for baseline_id in ctx.cfg["matrix_contract"]["failed_source_baseline_ids"]:
        result = sources[str(baseline_id)]
        spec = result["spec"]
        baseline_rows.append(
            {
                "experiment_id": str(baseline_id), "partition": "baseline",
                "pair_id": str(spec["pair_id"]),
                "history_member": str(spec["history_member"]),
                "first_candidate_id": "baseline", "second_candidate_id": "baseline",
                **r4.r51r3.formal_metric(spec, result["trajectory"], ctx.cfg["formal_contract"]),
            }
        )
    valid = {str(row["experiment_id"]): row for row in integrity["rows"] if row["passed"]}
    candidate_rows = []
    for spec in specs:
        experiment_id = str(spec["experiment_id"])
        result = r4.r51.r8r7.r8._read_gz(ctx.paths.raw / f"{experiment_id}.json.gz")
        if (
            experiment_id not in valid
            or result.get("success") is not True
            or result.get("spec") != spec
            or len(result.get("trajectory") or []) != int(spec["horizon_steps"]) + 1
        ):
            raise ValueError(f"R8R51R4D4 formal row failed integrity: {experiment_id}")
        candidate_rows.append(
            {
                "experiment_id": experiment_id, "partition": "candidate",
                "pair_id": str(spec["pair_id"]),
                "history_member": str(spec["history_member"]),
                "first_candidate_id": str(spec["first_candidate_id"]),
                "second_candidate_id": str(spec["second_candidate_id"]),
                "first_candidate_index": int(spec["first_candidate_index"]),
                "second_candidate_index": int(spec["second_candidate_index"]),
                "source_baseline_experiment_id": str(spec["source_r8r7_baseline_experiment_id"]),
                **r4.r51r3.formal_metric(spec, result["trajectory"], ctx.cfg["formal_contract"]),
            }
        )
    rows = sorted(
        [*baseline_rows, *candidate_rows],
        key=lambda row: (
            row["pair_id"], row["history_member"],
            0 if row["partition"] == "baseline" else 1,
            int(row.get("first_candidate_index", -1)),
            int(row.get("second_candidate_index", -1)), row["experiment_id"],
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
        if len(baseline) != 1 or len(candidates) != 25:
            raise ValueError(f"R8R51R4D4 formal coverage changed: {key}")
        baseline_row = baseline[0]
        best = max(
            candidates,
            key=lambda row: (
                float(row["formal_minimum_signed_margin"]),
                float(row["formal_mean_signed_margin"]),
                -int(row["first_candidate_index"]),
                -int(row["second_candidate_index"]),
            ),
        )
        oracle = max(
            enumerate([baseline_row, *candidates]),
            key=lambda item: (
                float(item[1]["formal_minimum_signed_margin"]),
                float(item[1]["formal_mean_signed_margin"]), -item[0],
            ),
        )[1]
        gain = float(best["formal_minimum_signed_margin"]) - float(baseline_row["formal_minimum_signed_margin"])
        repaired = bool(
            not baseline_row["formal_contract_pass"]
            and any(bool(row["formal_contract_pass"]) for row in candidates)
        )
        context_rows.append(
            {
                "pair_id": key[0], "history_member": key[1],
                "baseline": baseline_row, "candidates": candidates,
                "best_first_candidate_id": str(best["first_candidate_id"]),
                "best_second_candidate_id": str(best["second_candidate_id"]),
                "best_candidate_minimum_margin_gain": gain,
                "best_candidate_strictly_improves_minimum_margin": gain > tolerance,
                "failed_baseline_repaired": repaired,
                "oracle_partition": str(oracle["partition"]),
                "oracle_first_candidate_id": str(oracle["first_candidate_id"]),
                "oracle_second_candidate_id": str(oracle["second_candidate_id"]),
                "oracle_formal_contract_pass": bool(oracle["formal_contract_pass"]),
            }
        )
    baseline_fail_pass = sum(bool(row["baseline"]["formal_contract_pass"]) for row in context_rows)
    repairs = sum(bool(row["failed_baseline_repaired"]) for row in context_rows)
    candidate_pass = sum(
        bool(candidate["formal_contract_pass"])
        for row in context_rows for candidate in row["candidates"]
    )
    candidate_context_pass = sum(
        any(bool(candidate["formal_contract_pass"]) for candidate in row["candidates"])
        for row in context_rows
    )
    gains = [float(row["best_candidate_minimum_margin_gain"]) for row in context_rows]
    measured_oracle = int(ctx.cfg["known_aggregate_contract"]["baseline_formal_pass_count"]) + repairs
    scientific = bool(
        repairs >= int(ctx.cfg["scientific_gate"]["minimum_repaired_failed_baseline_count"])
        and measured_oracle >= int(ctx.cfg["scientific_gate"]["minimum_measured_oracle_formal_pass_count"])
    )
    route = ctx.cfg["routes"]["pass" if scientific else "authority_insufficient"]
    return {
        "schema_version": 1, "stage": STAGE, "identity": IDENTITY,
        "phase": "formal_primary_detailed", "formal_rows": rows,
        "formal_metric_digest": _digest(rows), "context_rows": context_rows,
        "context_outcome_digest": _digest(context_rows),
        "strict_full_horizon_count": len(candidate_rows),
        "candidate_count": len(candidate_rows), "failed_context_count": len(context_rows),
        "known_all_context_baseline_formal_pass_count": int(ctx.cfg["known_aggregate_contract"]["baseline_formal_pass_count"]),
        "failed_context_baseline_formal_pass_count": baseline_fail_pass,
        "candidate_formal_pass_count": candidate_pass,
        "candidate_formal_pass_context_count": candidate_context_pass,
        "repaired_failed_baseline_count": repairs,
        "failed_baseline_strict_margin_improvement_count": sum(
            bool(row["best_candidate_strictly_improves_minimum_margin"]) for row in context_rows
        ),
        "measured_oracle_formal_pass_count": measured_oracle,
        "best_candidate_minimum_margin_gain_minimum": min(gains),
        "best_candidate_minimum_margin_gain_median": statistics.median(gains),
        "best_candidate_minimum_margin_gain_maximum": max(gains),
        "integrity_gate_passed": True, "scientific_gate_passed": scientific,
        "audit_passed": True, "route": route, "passed": scientific,
    }


def run_real(ctx: Context, *, backend: str, resume: bool) -> dict[str, Any]:
    state = _read(ctx.paths.state)
    if state.get("phase_status") != "real_authorized":
        raise ValueError("R8R51R4D4 real execution is not authorized")
    specs = _saved_specs(ctx)
    execution = evaluate_specs(ctx, specs, backend=backend, resume=resume)
    primary = audit_raw_integrity(ctx)
    passed = bool(primary["passed"])
    plant_steps = sum(
        min(
            len((r4.r51.r8r7.r8._read_gz(ctx.paths.raw / f"{spec['experiment_id']}.json.gz").get("controller_trace") or [])),
            int(spec["horizon_steps"]),
        )
        for spec in specs
        if (ctx.paths.raw / f"{spec['experiment_id']}.json.gz").is_file()
    )
    if plant_steps > int(ctx.cfg["known_aggregate_contract"]["maximum_successful_plant_steps"]):
        raise ValueError("R8R51R4D4 plant-step cap exceeded")
    _set_state(
        ctx,
        phase_status="raw_integrity_primary_ready" if passed else "real_execution_failed",
        finished=not passed, real_tsc_executed=True,
        plant_step_count=plant_steps, new_raw_count=primary["raw_inventory"]["count"],
        response_outcomes_opened=False,
        route=primary["route"], verdict={"route": primary["route"], "passed": passed},
        stop_reason="" if passed else "runtime_action_restart_raw_or_causality_gate_failed",
    )
    return {
        "stage": STAGE, "phase": "real", "execution": execution,
        "raw_integrity_primary_passed": passed,
        "formal_response_opened": False, "route": primary["route"],
    }


def finalize_primary(ctx: Context) -> dict[str, Any]:
    state = _read(ctx.paths.state)
    integrity = _read(ctx.paths.analysis / "raw_integrity_primary.json")
    independent = _read(ctx.paths.analysis / "raw_integrity_independent.json")
    if (
        state.get("phase_status") != "raw_integrity_primary_ready"
        or integrity.get("passed") is not True
        or independent.get("passed") is not True
        or independent.get("primary_agreement") is not True
    ):
        raise ValueError("R8R51R4D4 raw independent integrity gate incomplete")
    detailed = _formal_authority(ctx)
    _write(ctx.paths.analysis / "primary_detailed.json", detailed)
    keys = (
        "formal_metric_digest", "context_outcome_digest", "strict_full_horizon_count",
        "candidate_count", "failed_context_count",
        "known_all_context_baseline_formal_pass_count",
        "failed_context_baseline_formal_pass_count", "candidate_formal_pass_count",
        "candidate_formal_pass_context_count", "repaired_failed_baseline_count",
        "failed_baseline_strict_margin_improvement_count",
        "measured_oracle_formal_pass_count",
        "best_candidate_minimum_margin_gain_minimum",
        "best_candidate_minimum_margin_gain_median",
        "best_candidate_minimum_margin_gain_maximum",
        "integrity_gate_passed", "scientific_gate_passed", "audit_passed",
        "route", "passed",
    )
    summary = {
        "schema_version": 1, "stage": STAGE, "identity": IDENTITY,
        "phase": "formal_primary_summary", **{key: detailed[key] for key in keys},
        "raw_inventory": integrity["raw_inventory"],
        "raw_integrity_primary_sha256": _sha(ctx.paths.analysis / "raw_integrity_primary.json"),
        "raw_integrity_independent_sha256": _sha(ctx.paths.analysis / "raw_integrity_independent.json"),
        "primary_detailed_sha256": _sha(ctx.paths.analysis / "primary_detailed.json"),
        "new_tsc_count": 250, "new_raw_count": 250,
        "controller_execution_count": 250,
        "plant_step_count": int(state["plant_step_count"]),
        "model_fit_count": 0, "model_selection_count": 0,
        "optimization_count": 0, "snapshot_count": 0,
        "all_stage_trajectories_allowed_in_expert_dataset": False,
    }
    _write(ctx.paths.analysis / "primary_summary.json", summary)
    _set_state(
        ctx, phase_status="final_primary_ready", response_outcomes_opened=True,
        primary_detailed_sha256=summary["primary_detailed_sha256"],
        primary_summary_sha256=_sha(ctx.paths.analysis / "primary_summary.json"),
        route=summary["route"],
        verdict={"route": summary["route"], "passed": bool(summary["scientific_gate_passed"])},
    )
    return summary


def postprocess(ctx: Context) -> dict[str, Any]:
    state = _read(ctx.paths.state)
    summary = _read(ctx.paths.analysis / "primary_summary.json")
    independent = _read(ctx.paths.analysis / "formal_independent.json")
    if (
        state.get("phase_status") != "final_primary_ready"
        or independent.get("audit_passed") is not True
        or independent.get("primary_discrete_agreement") is not True
        or independent.get("primary_numerical_agreement") is not True
        or independent.get("primary_outcome_agreement") is not True
        or independent.get("route") != summary.get("route")
    ):
        raise ValueError("R8R51R4D4 final independent agreement failed")
    compact_keys = (
        "strict_full_horizon_count", "candidate_count", "failed_context_count",
        "known_all_context_baseline_formal_pass_count", "candidate_formal_pass_count",
        "candidate_formal_pass_context_count", "repaired_failed_baseline_count",
        "failed_baseline_strict_margin_improvement_count",
        "measured_oracle_formal_pass_count",
        "best_candidate_minimum_margin_gain_minimum",
        "best_candidate_minimum_margin_gain_median",
        "best_candidate_minimum_margin_gain_maximum",
        "integrity_gate_passed", "scientific_gate_passed", "route",
        "new_tsc_count", "new_raw_count", "controller_execution_count",
        "plant_step_count", "model_fit_count", "model_selection_count",
        "optimization_count", "snapshot_count",
        "all_stage_trajectories_allowed_in_expert_dataset",
    )
    compact = {
        "schema_version": 1, "stage": STAGE, "identity": IDENTITY,
        "phase": "compact_audit", **{key: summary[key] for key in compact_keys},
        "raw_inventory": summary["raw_inventory"],
        "formal_metric_digest": summary["formal_metric_digest"],
        "context_outcome_digest": summary["context_outcome_digest"],
        "primary_summary_sha256": _sha(ctx.paths.analysis / "primary_summary.json"),
        "primary_detailed_sha256": _sha(ctx.paths.analysis / "primary_detailed.json"),
        "raw_integrity_primary_sha256": summary["raw_integrity_primary_sha256"],
        "raw_integrity_independent_sha256": summary["raw_integrity_independent_sha256"],
        "formal_independent_sha256": _sha(ctx.paths.analysis / "formal_independent.json"),
        "primary_independent_maximum_numerical_difference": independent["maximum_primary_numerical_difference"],
        "audit_passed": True,
    }
    _write(ctx.paths.analysis / "compact_audit.json", compact)
    final = copy.deepcopy(summary)
    final.update(
        {
            "phase": "final", "independent_agreement": True,
            "compact_audit_sha256": _sha(ctx.paths.analysis / "compact_audit.json"),
            "formal_independent_sha256": compact["formal_independent_sha256"],
            "finished": True,
        }
    )
    _write(ctx.paths.analysis / "final_report.json", final)
    _set_state(
        ctx, phase_status="complete", finished=True, real_tsc_executed=True,
        response_outcomes_opened=True,
        final_report_sha256=_sha(ctx.paths.analysis / "final_report.json"),
        compact_audit_sha256=final["compact_audit_sha256"],
        formal_independent_sha256=final["formal_independent_sha256"],
        route=final["route"],
        verdict={"route": final["route"], "passed": bool(final["scientific_gate_passed"])},
        stop_reason="" if final["scientific_gate_passed"] else "measured_center_bridged_two_pulse_authority_gate_failed",
    )
    return final


def execute(ctx: Context, *, command: str, backend: str, resume: bool) -> dict[str, Any]:
    if command == "offline":
        return prepare_offline(ctx)
    if command == "authorize-real":
        return authorize_real(ctx)
    if command == "run":
        return run_real(ctx, backend=backend, resume=resume)
    if command == "finalize-primary":
        return finalize_primary(ctx)
    if command == "postprocess":
        return postprocess(ctx)
    raise ValueError(f"unsupported R8R51R4D4 command: {command}")


def _parser() -> argparse.ArgumentParser:
    parser = d3._parser()
    parser.description = __doc__
    parser.add_argument("--r51r4d3-run", type=Path, required=True)
    parser.add_argument("--failed-r51r4d4-run", type=Path, required=True)
    return parser


def main() -> None:
    args = _parser().parse_args()
    result = execute(
        load_context(args), command=args.command, backend=args.backend, resume=args.resume
    )
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
