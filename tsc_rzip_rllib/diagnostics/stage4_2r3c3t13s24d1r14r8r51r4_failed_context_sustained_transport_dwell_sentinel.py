#!/usr/bin/env python3
"""Execute the frozen R8R51R4 failed-context sustained-dwell sentinel."""

from __future__ import annotations

import argparse
import copy
from collections import defaultdict
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
    stage4_2r3c3t13s24d1r14r8r51r1_reduced_q0_transport_bridge_q0_gate_integration_sentinel
    as r51,
    stage4_2r3c3t13s24d1r14r8r51r3_single_transport_return_hold_formal_authority_audit
    as r51r3,
)


SCHEMA_VERSION = 1
STAGE = "Stage4.2R3c3T13S24D1R14R8R51R4"
IDENTITY = "failed_context_sustained_transport_dwell_sentinel_v1"
RUN_NAME = "stage4_2r3c3t13s24d1r14r8r51r4_failed_context_sustained_transport_dwell_sentinel"
CONTROLLER_REVISION = "failed_context_sustained_transport_dwell_v42r3c3t13s24d1r14r8r51r4_v1"
SELECTED_CANDIDATE_IDS = ("d0m", "d1p", "d2m", "d3p", "u1p50")
RETURN_STEPS = (16, 18)
PREFIX_END = 10
Q0_STEP = 10
ISSUE_STEP = 12
FIRST_EFFECT_STATE = 13
N_COILS = 14


class SourceBlockedError(RuntimeError):
    pass


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def _read(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
    )


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        + "\n",
        encoding="utf-8",
    )


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


@dataclass(frozen=True)
class Paths:
    run_dir: Path
    stage: Path
    variants: Path
    specs: Path
    source_reference: Path
    raw: Path
    analysis: Path
    state: Path
    manifest: Path


def _paths(run_dir: Path) -> Paths:
    root = run_dir.expanduser().resolve()
    stage = root / RUN_NAME
    return Paths(
        run_dir=root,
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
    base_ctx: r51.Context
    r51r1_stage: Path
    r51r3_stage: Path


def validate_config(cfg: Mapping[str, Any], *, project_root: Path) -> None:
    design = project_root / str(cfg.get("design_document", ""))
    source_config = project_root / str(cfg.get("source_r51r1_config", ""))
    source_implementation = project_root / (
        "tsc_rzip_rllib/diagnostics/"
        "stage4_2r3c3t13s24d1r14r8r51r1_reduced_q0_transport_bridge_"
        "q0_gate_integration_sentinel.py"
    )
    matrix = cfg.get("matrix_contract", {})
    schedule = cfg.get("schedule_contract", {})
    controller = cfg.get("controller_contract", {})
    formal = cfg.get("formal_contract", {})
    known = cfg.get("known_aggregate_contract", {})
    gate = cfg.get("scientific_gate", {})
    scope = cfg.get("scientific_scope", {})
    expected_routes = {
        "source_blocked": "REDUCED_Q0_TRANSPORT_BRIDGE_R51R4_SUSTAINED_DWELL_BLOCKED_BY_SOURCE",
        "offline_fail": "REDUCED_Q0_TRANSPORT_BRIDGE_R51R4_SUSTAINED_DWELL_OFFLINE_FAIL_NO_REAL_TSC",
        "execution_fail": "REDUCED_Q0_TRANSPORT_BRIDGE_R51R4_SUSTAINED_DWELL_EXECUTION_FAIL_STOP",
        "authority_insufficient": "REDUCED_Q0_TRANSPORT_BRIDGE_R51R4_SUSTAINED_DWELL_AUTHORITY_INSUFFICIENT_LONGER_SEQUENTIAL_REDESIGN_REQUIRED",
        "pass": "REDUCED_Q0_TRANSPORT_BRIDGE_R51R4_SUSTAINED_DWELL_AUTHORITY_PRESENT_R51R5_MODEL_PREFLIGHT_REQUIRED",
    }
    failed = tuple(matrix.get("failed_source_baseline_ids", ()))
    hash_contracts = (
        (cfg.get("source_r51r1", {}), (
            "raw_inventory_digest", "all_specs_sha256", "raw_primary_sha256",
            "final_report_sha256", "stage_state_sha256", "stage_manifest_sha256",
        )),
        (cfg.get("source_r51r3", {}), (
            "primary_detailed_sha256", "primary_summary_sha256", "independent_sha256",
            "compact_audit_sha256", "final_report_sha256", "stage_state_sha256",
            "stage_manifest_sha256", "server_final_evidence_sha256",
            "formal_metric_digest", "context_outcome_digest",
        )),
    )
    invalid = (
        cfg.get("schema_version") != SCHEMA_VERSION
        or cfg.get("stage") != STAGE
        or cfg.get("identity") != IDENTITY
        or cfg.get("run_name") != RUN_NAME
        or cfg.get("controller_revision") != CONTROLLER_REVISION
        or cfg.get("package_revision") != "r42r3c3t13s24d1r14r8r51r4_sustained_dwell_v1"
        or not design.is_file()
        or _sha(design) != cfg.get("design_document_sha256")
        or not source_config.is_file()
        or _sha(source_config) != cfg.get("source_r51r1_config_sha256")
        or not source_implementation.is_file()
        or _sha(source_implementation) != cfg.get("source_r51r1_implementation_sha256")
        or any(
            not isinstance(contract.get(key), str)
            or len(contract[key]) != 64
            or any(ch not in "0123456789abcdef" for ch in contract[key])
            for contract, keys in hash_contracts for key in keys
        )
        or cfg.get("source_r51r1", {}).get("run_name")
        != "stage4_2r3c3t13s24d1r14r8r51r1_reduced_q0_transport_bridge_q0_gate_integration_sentinel_20260809_1baf670_v1"
        or cfg.get("source_r51r1", {}).get("stage_directory")
        != "stage4_2r3c3t13s24d1r14r8r51r1_reduced_q0_transport_bridge_q0_gate_integration_sentinel"
        or cfg.get("source_r51r1", {}).get("required_route")
        != "REDUCED_Q0_TRANSPORT_BRIDGE_Q0_GATE_INTEGRATION_COMPLETE_R51R2_MODEL_PREFLIGHT_REQUIRED"
        or cfg.get("source_r51r3", {}).get("run_name")
        != "stage4_2r3c3t13s24d1r14r8r51r3_single_transport_return_hold_formal_authority_audit_20260810_06e4728_v1"
        or cfg.get("source_r51r3", {}).get("stage_directory")
        != "stage4_2r3c3t13s24d1r14r8r51r3_single_transport_return_hold_formal_authority_audit"
        or cfg.get("source_r51r3", {}).get("required_route")
        != "REDUCED_Q0_TRANSPORT_BRIDGE_R51R3_SINGLE_TRANSPORT_RETURN_HOLD_AUTHORITY_INSUFFICIENT_SEQUENTIAL_MODEL_REQUIRED"
        or tuple(int(matrix.get(key, -1)) for key in (
            "context_count", "candidate_count", "return_step_count", "trajectory_count"
        )) != (10, 5, 2, 100)
        or tuple(matrix.get("candidate_ids", ())) != SELECTED_CANDIDATE_IDS
        or tuple(map(int, matrix.get("return_task_steps", ()))) != RETURN_STEPS
        or failed != tuple(f"r8r7_baseline_{index:02d}" for index in (*range(8), 12, 13))
        or tuple(int(schedule.get(key, -1)) for key in (
            "prefix_end_task_step", "q0_issue_task_step", "candidate_issue_task_step",
            "candidate_first_effect_state_step", "dynamic_exact_search_radius",
            "require_exact_q0_prefix_through_state_step",
        )) != (10, 10, 12, 13, 16, 12)
        or tuple(map(int, schedule.get("stored_center_return_task_steps", ()))) != RETURN_STEPS
        or tuple(map(int, schedule.get("first_restored_center_state_steps", ()))) != (17, 19)
        or schedule.get("require_exact_candidate_current_hold") is not True
        or schedule.get("require_exact_center_refresh_after_return") is not True
        or tuple(float(controller.get(key, -1.0)) for key in (
            "maximum_incremental_normalized_action_linf",
            "maximum_total_normalized_action_abs", "maximum_current_utilization",
            "minimum_desired_applied_current_cosine", "maximum_relative_off_basis_residual",
        )) != (0.25, 1.0, 0.55, 0.98, 0.10)
        or float(controller.get("maximum_q0_integration_action_linf", -1.0)) != 1e-5
        or any(controller.get(key) is not True for key in (
            "require_exact_card15_issue", "require_exact_card15_refresh",
            "require_shared_q0_constructor_parity", "forbid_q0_zero_target_predicate",
            "require_exact_stored_center_return", "require_first_effect_at_issue_plus_one",
            "safe_stop_before_failed_advance",
        ))
        or tuple(map(float, formal.get("base_target_physical", ())))
        != (0.75, 0.0, 29779.724)
        or float(formal.get("dt_s", -1.0)) != 0.01
        or tuple(int(formal.get(key, -1)) for key in (
            "normal_arrival_first_step", "normal_arrival_deadline_step",
            "normal_hold_through_step", "weak_arrival_first_step",
            "weak_arrival_deadline_step", "weak_hold_through_step",
            "late_window_steps", "arrival_streak_steps",
        )) != (12, 25, 35, 12, 27, 37, 4, 3)
        or tuple(float(formal.get(key, -1.0)) for key in (
            "position_tolerance_m", "endpoint_speed_tolerance_m_per_s",
            "rms_speed_tolerance_m_per_s", "ip_safety_tolerance_A",
            "ip_terminal_abs_tolerance_A", "ip_hold_rms_tolerance_A",
            "ip_sustained_max_tolerance_A", "formal_pass_tolerance",
            "metric_equivalence_absolute_tolerance",
        )) != (0.03, 0.1, 0.1, 10000.0, 2000.0, 2400.0, 4000.0, 1e-12, 1e-12)
        or formal.get("arrival_deadline_expansion_allowed") is not False
        or tuple(int(known.get(key, -1)) for key in (
            "baseline_formal_pass_count", "failed_baseline_count", "trajectory_count",
            "candidate_count_per_failed_context",
        )) != (6, 10, 100, 10)
        or int(gate.get("minimum_repaired_failed_baseline_count", -1)) != 1
        or int(gate.get("minimum_measured_oracle_formal_pass_count", -1)) != 7
        or cfg.get("routes") != expected_routes
        or scope.get("identification_only") is not True
        or any(scope.get(key) is not False for key in (
            "model_fit_allowed", "real_mpc_executed", "gate_a_qualified",
            "expert_data_allowed", "bc_dagger_or_rl_allowed",
            "all_stage_trajectories_allowed_in_expert_dataset",
            "global_plant_reachability_claimed",
        ))
    )
    if invalid:
        raise ValueError("R8R51R4 frozen design changed")


def load_context(args: argparse.Namespace) -> Context:
    config_path = args.config.expanduser().resolve()
    cfg = _read(config_path)
    validate_config(cfg, project_root=_root())
    source_args = SimpleNamespace(**vars(args))
    source_args.config = (_root() / str(cfg["source_r51r1_config"])).resolve()
    source_args.run_dir = args.r51r1_run.expanduser().resolve()
    base_ctx = r51.load_context(source_args)
    r51r1_stage = base_ctx.paths.stage
    r51r3_stage = (
        args.r51r3_run.expanduser().resolve()
        / str(cfg["source_r51r3"]["stage_directory"])
    )
    if r51r1_stage.parent.name != cfg["source_r51r1"]["run_name"]:
        raise ValueError("R8R51R4 R51R1 source run identity changed")
    if r51r3_stage.parent.name != cfg["source_r51r3"]["run_name"]:
        raise ValueError("R8R51R4 R51R3 source run identity changed")
    return Context(cfg, config_path, _paths(args.run_dir), base_ctx, r51r1_stage, r51r3_stage)


def _artifact_hashes(stage: Path, names: Mapping[str, str], contract: Mapping[str, Any]) -> dict[str, str]:
    hashes = {}
    for name, relative in names.items():
        path = stage / relative
        if not path.is_file():
            raise SourceBlockedError(f"R8R51R4 source artifact missing: {name}")
        hashes[name] = _sha(path)
        if hashes[name] != contract[f"{name}_sha256"]:
            raise SourceBlockedError(f"R8R51R4 source artifact changed: {name}")
    return hashes


def _r51r3_server_evidence_authenticated(
    evidence: Mapping[str, Any], required_route: str
) -> bool:
    """Authenticate an integrity PASS whose preregistered science gate is FAIL."""

    return bool(
        evidence.get("integrity_gate_passed") is True
        and evidence.get("independent_audit_passed") is True
        and evidence.get("scientific_gate_passed") is False
        and evidence.get("passed") is False
        and evidence.get("route") == required_route
        and int(evidence.get("new_tsc_count", -1)) == 0
        and int(evidence.get("new_raw_count", -1)) == 0
        and int(evidence.get("plant_step_count", -1)) == 0
        and int(evidence.get("source_or_row_exclusion_count", -1)) == 0
    )


def authenticate_sources(ctx: Context) -> dict[str, Any]:
    inherited = r51.authenticate_sources(ctx.base_ctx)
    c1 = ctx.cfg["source_r51r1"]
    c3 = ctx.cfg["source_r51r3"]
    paths1 = {
        "all_specs": "specs/all_specs.json",
        "raw_primary": "analysis/raw_primary.json",
        "final_report": "analysis/q0_first_effect_reporting_hotfix_final_report.json",
        "stage_state": "stage_state.json",
        "stage_manifest": "stage_manifest.json",
    }
    paths3 = {
        "primary_detailed": "analysis/primary_detailed.json",
        "primary_summary": "analysis/primary_summary.json",
        "independent": "analysis/independent.json",
        "compact_audit": "analysis/compact_audit.json",
        "final_report": "analysis/final_report.json",
        "stage_state": "stage_state.json",
        "stage_manifest": "stage_manifest.json",
        "server_final_evidence": "analysis/server_final_evidence.json",
    }
    hashes1 = _artifact_hashes(ctx.r51r1_stage, paths1, c1)
    hashes3 = _artifact_hashes(ctx.r51r3_stage, paths3, c3)
    inventory = r51.r8r7.r8._inventory(ctx.r51r1_stage / "raw")
    if inventory != {
        "count": int(c1["raw_count"]), "bytes": int(c1["raw_bytes"]),
        "digest": c1["raw_inventory_digest"], "rows": inventory.get("rows", []),
    }:
        raise SourceBlockedError("R8R51R4 R51R1 raw inventory changed")
    final1 = _read(ctx.r51r1_stage / paths1["final_report"])
    detailed3 = _read(ctx.r51r3_stage / paths3["primary_detailed"])
    independent3 = _read(ctx.r51r3_stage / paths3["independent"])
    final3 = _read(ctx.r51r3_stage / paths3["final_report"])
    state3 = _read(ctx.r51r3_stage / paths3["stage_state"])
    evidence3 = _read(ctx.r51r3_stage / paths3["server_final_evidence"])
    failed_rows = [
        row for row in detailed3.get("context_rows", [])
        if not bool((row.get("baseline") or {}).get("formal_contract_pass"))
    ]
    failed_ids = tuple(str(row["baseline"]["experiment_id"]) for row in failed_rows)
    expected_failed = tuple(ctx.cfg["matrix_contract"]["failed_source_baseline_ids"])
    if (
        inherited.get("passed") is not True
        or final1.get("route") != c1["required_route"]
        or final1.get("passed") is not True
        or detailed3.get("route") != c3["required_route"]
        or detailed3.get("formal_metric_digest") != c3["formal_metric_digest"]
        or detailed3.get("context_outcome_digest") != c3["context_outcome_digest"]
        or int(detailed3.get("baseline_formal_pass_count", -1)) != 6
        or int(detailed3.get("repaired_failed_baseline_count", -1)) != 0
        or int(detailed3.get("measured_oracle_formal_pass_count", -1)) != 6
        or failed_ids != expected_failed
        or independent3.get("audit_passed") is not True
        or independent3.get("primary_discrete_agreement") is not True
        or independent3.get("primary_numerical_agreement") is not True
        or final3.get("route") != c3["required_route"]
        or state3.get("finished") is not True or state3.get("route") != c3["required_route"]
        or not _r51r3_server_evidence_authenticated(evidence3, c3["required_route"])
    ):
        raise SourceBlockedError("R8R51R4 R51R1/R51R3 source result changed")
    return {
        "r51r1_stage": str(ctx.r51r1_stage),
        "r51r3_stage": str(ctx.r51r3_stage),
        "r51r1_hashes": hashes1,
        "r51r3_hashes": hashes3,
        "r51r1_raw_inventory": inventory,
        "failed_contexts": [
            {
                "pair_id": str(row["pair_id"]),
                "history_member": str(row["history_member"]),
                "source_baseline_experiment_id": str(row["baseline"]["experiment_id"]),
                "baseline_formal_minimum_signed_margin": float(
                    row["baseline"]["formal_minimum_signed_margin"]
                ),
            }
            for row in failed_rows
        ],
        "inherited_source_authentication_digest": _digest(inherited),
        "passed": True,
    }


def build_specs(ctx: Context) -> list[dict[str, Any]]:
    baselines, _ = r51._source_baselines(ctx.base_ctx)
    baseline_by_id = {str(row["experiment_id"]): row for row in baselines}
    source_specs = _read(ctx.r51r1_stage / "specs/all_specs.json")
    candidate_by_key = {
        (str(row["source_r8r7_baseline_experiment_id"]), str(row["r8r51r1_candidate_id"])): row
        for row in source_specs
    }
    rows = []
    for context_index, baseline_id in enumerate(ctx.cfg["matrix_contract"]["failed_source_baseline_ids"]):
        baseline = baseline_by_id.get(str(baseline_id))
        if baseline is None:
            raise SourceBlockedError(f"R8R51R4 source baseline missing: {baseline_id}")
        for candidate_id in SELECTED_CANDIDATE_IDS:
            original = candidate_by_key.get((str(baseline_id), candidate_id))
            if original is None:
                raise SourceBlockedError(f"R8R51R4 original candidate missing: {baseline_id}/{candidate_id}")
            for return_step in RETURN_STEPS:
                spec = copy.deepcopy(baseline)
                candidate_index = int(original["r8r51r1_candidate_index"])
                spec.update(
                    {
                        "kind": "stage4_2r3c3t13s24d1r14r8r51r4_sustained_dwell",
                        "stage": STAGE,
                        "campaign_identity": IDENTITY,
                        "controller_revision": CONTROLLER_REVISION,
                        "experiment_id": (
                            f"r8r51r4_c{context_index:02d}_k{candidate_index:02d}_"
                            f"{candidate_id}_return{return_step:02d}"
                        ),
                        "source_r8r7_baseline_experiment_id": str(baseline_id),
                        "source_r51r1_experiment_id": str(original["experiment_id"]),
                        "r8r51r4_context_index": context_index,
                        "r8r51r4_candidate_index": candidate_index,
                        "r8r51r4_candidate_id": candidate_id,
                        "r8r51r4_candidate_q": copy.deepcopy(original["r8r51r1_candidate_q"]),
                        "r8r51r4_requested_coordinate": copy.deepcopy(
                            original["r8r51r1_requested_coordinate"]
                        ),
                        "r8r51r4_return_task_step": return_step,
                        "r8r51r4_first_restored_center_state_step": return_step + 1,
                        "r8r51r4_allowed_in_expert_dataset": False,
                        # Compatibility fields consumed only by the already authenticated
                        # R51R1 exact issue/return primitives.
                        "r8r51r1_candidate_index": candidate_index,
                        "r8r51r1_candidate_id": candidate_id,
                        "r8r51r1_candidate_q": copy.deepcopy(original["r8r51r1_candidate_q"]),
                        "r8r51r1_requested_coordinate": copy.deepcopy(
                            original["r8r51r1_requested_coordinate"]
                        ),
                        "pair_or_history_label_available_to_controller": False,
                        "source_result_available_to_controller": False,
                        "future_measurement_count": 0,
                        "future_action_count": 0,
                        "formal_timing_unchanged": True,
                    }
                )
                rows.append(spec)
    coverage = {
        (
            str(row["source_r8r7_baseline_experiment_id"]),
            str(row["r8r51r4_candidate_id"]), int(row["r8r51r4_return_task_step"]),
        )
        for row in rows
    }
    if len(rows) != 100 or len(coverage) != 100 or len({row["experiment_id"] for row in rows}) != 100:
        raise ValueError("R8R51R4 frozen specification matrix changed")
    return rows


def _execution_context(ctx: Context) -> Any:
    return r51._execution_context(ctx.base_ctx)


def _payload(ctx: Context, spec: Mapping[str, Any]) -> dict[str, Any]:
    payload = r51.r8r7.r8._payload(_execution_context(ctx), spec)
    experiment_id = str(spec["experiment_id"])
    payload.update(
        {
            "variant_id": f"stage4_2r3c3t13s24d1r14r8r51r4_{experiment_id}",
            "stage4_2r3c3t13s24d1r14r8r51r4_candidate_id": str(
                spec["r8r51r4_candidate_id"]
            ),
            "stage4_2r3c3t13s24d1r14r8r51r4_return_task_step": int(
                spec["r8r51r4_return_task_step"]
            ),
            "stage4_2r3c3t13s24d1r14r8r51r4_pair_history_label_available_to_controller": False,
        }
    )
    _write(ctx.paths.variants / f"payload_{experiment_id}.json", payload)
    return payload


def _controller_contract(ctx: Context) -> dict[str, Any]:
    contract = copy.deepcopy(ctx.cfg["controller_contract"])
    contract["dynamic_exact_search_radius"] = int(
        ctx.cfg["schedule_contract"]["dynamic_exact_search_radius"]
    )
    source_cfg = ctx.base_ctx.r8r48_ctx.source_ctx.cfg
    contract["requested_coordinate_matrix_columns"] = copy.deepcopy(
        source_cfg["candidate_contract"]["canonical_matrix_columns"]
    )
    contract["requested_matrix_float64_le_c_sha256"] = str(
        source_cfg["candidate_contract"]["canonical_matrix_float64_le_c_sha256"]
    )
    return contract


def construct_event_stream(
    ctx: Context, spec: Mapping[str, Any], *, include_events: bool = False
) -> dict[str, Any]:
    _, sources = r51._source_baselines(ctx.base_ctx)
    source = sources[str(spec["source_r8r7_baseline_experiment_id"])]
    execution = _execution_context(ctx)
    lattice = execution.d1r11_ctx.base_ctx.base_ctx.cfg["lattice_probe"]
    contract = _controller_contract(ctx)
    payload = _read(ctx.paths.variants / f"payload_{spec['experiment_id']}.json")
    actuator = r51.r8r22.mpc.actuator_from_payload(payload, lattice)
    field_basis = r51.r8r22._fixed_basis(source)
    current = np.asarray(source["trajectory"][Q0_STEP]["currents_a_tsc"], dtype=float)
    events = []
    q0 = r51._q0_event(
        task_step=Q0_STEP, currents=current, actuator=actuator,
        lattice=lattice, contract=contract,
    )
    events.append(q0)
    center_fields = list(q0["q0_center_card15_fields"])
    current = np.asarray(q0["nominal_readback_current_a_tsc"], dtype=float)
    q0_hold = r51._observe_event(
        task_step=11, currents=current, target_fields=center_fields,
        actuator=actuator, contract=contract, event="q0_observe_hold",
    )
    events.append(q0_hold)
    current = np.asarray(q0_hold["nominal_readback_current_a_tsc"], dtype=float)
    issue = r51.r8r22._construct_coordinate_issue(
        task_step=ISSUE_STEP, currents_a_tsc=current,
        fixed_basis_delta_field_kat_tsc=field_basis.T,
        requested_coordinate=spec["r8r51r4_requested_coordinate"],
        candidate_id=str(spec["r8r51r4_candidate_id"]), actuator=actuator,
        controller_cfg=contract, lattice_cfg=lattice,
    )
    issue["center_nominal_readback_current_a_tsc"] = current.tolist()
    events.append(issue)
    current = np.asarray(issue["nominal_issue_readback_current_a_tsc"], dtype=float)
    return_step = int(spec["r8r51r4_return_task_step"])
    for step in range(ISSUE_STEP + 1, return_step):
        hold = r51._observe_event(
            task_step=step, currents=current, target_fields=issue["target_card15_fields"],
            actuator=actuator, contract=contract, event="candidate_current_dwell_hold",
        )
        events.append(hold)
        current = np.asarray(hold["nominal_readback_current_a_tsc"], dtype=float)
    returned = r51._return_event(
        task_step=return_step, currents=current, center_fields=center_fields,
        issue_event=issue, field_basis=field_basis, actuator=actuator,
        lattice=lattice, contract=contract,
    )
    events.append(returned)
    current = np.asarray(returned["nominal_readback_current_a_tsc"], dtype=float)
    for step in range(return_step + 1, int(spec["horizon_steps"])):
        refresh = r51.r8r22._refresh_event(
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
    action_limits = all(
        float(event.get("incremental_normalized_action_linf", math.inf))
        <= float(contract["maximum_incremental_normalized_action_linf"]) + 1e-12
        for event in events
    )
    total_limits = all(
        max(map(abs, event.get("action_norm_tsc") or [math.inf]))
        <= float(contract["maximum_total_normalized_action_abs"]) + 1e-12
        for event in events
    )
    event_pass = all(
        event.get("passed") is True
        and all(bool(value) for value in (event.get("criteria") or {}).values())
        for event in events
    )
    dwell_events = events[3 : 3 + (return_step - ISSUE_STEP - 1)]
    criteria = {
        "q0_exact": bool(q0["passed"]),
        "q0_observe_exact": bool(q0_hold["passed"]),
        "candidate_exact": bool(issue["passed"]),
        "candidate_identity": issue.get("candidate_id") == spec["r8r51r4_candidate_id"],
        "candidate_coordinate": bool(np.array_equal(
            np.asarray(issue.get("requested_coordinate"), dtype=float),
            np.asarray(spec["r8r51r4_requested_coordinate"], dtype=float),
        )),
        "dwell_count": len(dwell_events) == return_step - ISSUE_STEP - 1,
        "dwell_exact": all(bool(event["passed"]) for event in dwell_events),
        "dwell_zero_increment": all(
            np.array_equal(np.asarray(event["action_norm_tsc"]), np.zeros(N_COILS))
            for event in dwell_events
        ),
        "dwell_target_exact": all(
            event["stored_target_card15_fields"] == issue["target_card15_fields"]
            for event in dwell_events
        ),
        "return_exact": bool(returned["passed"]),
        "later_refresh_exact": bool(event_pass),
        "incremental_action_limits": action_limits,
        "total_action_limits": total_limits,
    }
    row = {
        "experiment_id": str(spec["experiment_id"]),
        "source_baseline_experiment_id": str(spec["source_r8r7_baseline_experiment_id"]),
        "pair_id": str(spec["pair_id"]),
        "history_member": str(spec["history_member"]),
        "candidate_index": int(spec["r8r51r4_candidate_index"]),
        "candidate_id": str(spec["r8r51r4_candidate_id"]),
        "return_task_step": return_step,
        "q0_event_digest": _digest(q0),
        "q0_action_norm_tsc": list(q0["action_norm_tsc"]),
        "q0_criteria_keys": sorted(q0["criteria"]),
        "event_stream_digest": _digest(events),
        "event_count": len(events),
        "dwell_hold_count": len(dwell_events),
        "maximum_incremental_action_linf": max(
            float(event["incremental_normalized_action_linf"]) for event in events
        ),
        "maximum_predicted_current_utilization": max(
            float(event["predicted_current_utilization"]) for event in events
        ),
        "criteria": criteria,
        "passed": bool(all(criteria.values())),
    }
    if include_events:
        row["events"] = events
    return row


def _offline_construction(ctx: Context, specs: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    rows = [construct_event_stream(ctx, spec) for spec in specs]
    return {
        "construction_count": len(rows),
        "construction_pass_count": sum(bool(row["passed"]) for row in rows),
        "maximum_incremental_action_linf": max(
            float(row["maximum_incremental_action_linf"]) for row in rows
        ),
        "maximum_predicted_current_utilization": max(
            float(row["maximum_predicted_current_utilization"]) for row in rows
        ),
        "event_stream_digest": _digest([
            (row["experiment_id"], row["event_stream_digest"]) for row in rows
        ]),
        "rows": rows,
        "passed": len(rows) == 100 and all(bool(row["passed"]) for row in rows),
    }


def _set_state(ctx: Context, **updates: Any) -> dict[str, Any]:
    state = _read(ctx.paths.state)
    state.update(updates)
    _write(ctx.paths.state, state)
    return state


def prepare_offline(ctx: Context) -> dict[str, Any]:
    if ctx.paths.stage.exists():
        raise ValueError("R8R51R4 offline requires a fresh run identity")
    for path in (
        ctx.paths.stage, ctx.paths.variants, ctx.paths.specs,
        ctx.paths.source_reference, ctx.paths.raw, ctx.paths.analysis,
    ):
        path.mkdir(parents=True, exist_ok=True)
    try:
        source = authenticate_sources(ctx)
        specs = build_specs(ctx)
        for spec in specs:
            _payload(ctx, spec)
        construction = _offline_construction(ctx, specs)
        _write(ctx.paths.specs / "all_specs.json", specs)
        _write(ctx.paths.source_reference / "source_authentication.json", source)
        _write(ctx.paths.analysis / "offline_construction.json", construction)
        package = r51.r8r7._package_fingerprint()
        manifest = {
            "schema_version": 1,
            "stage": STAGE,
            "identity": IDENTITY,
            "controller_revision": CONTROLLER_REVISION,
            "package_revision": ctx.cfg["package_revision"],
            "config_sha256": _sha(ctx.config_path),
            "design_document_sha256": ctx.cfg["design_document_sha256"],
            "source_r51r1_run": str(ctx.r51r1_stage.parent),
            "source_r51r3_run": str(ctx.r51r3_stage.parent),
            "source_authentication_digest": _digest(source),
            "spec_count": len(specs),
            "spec_digest": _digest(specs),
            "offline_construction_digest": _digest(construction),
            "package_fingerprint": package,
            "all_stage_trajectories_allowed_in_expert_dataset": False,
        }
        _write(ctx.paths.manifest, manifest)
        passed = bool(construction["passed"])
        route = ctx.cfg["routes"]["pass" if passed else "offline_fail"]
        state = {
            "schema_version": 1, "stage": STAGE,
            "phase_status": "offline_primary_ready" if passed else "offline_failed",
            "finished": not passed, "real_tsc_executed": False,
            "plant_step_count": 0, "new_raw_count": 0,
            "response_outcomes_opened": False,
            "spec_digest": manifest["spec_digest"],
            "package_digest": package["digest"],
            "route": route, "verdict": {"route": route, "passed": passed},
            "stop_reason": "" if passed else "offline_action_construction_failed",
        }
        _write(ctx.paths.state, state)
        report = {
            "schema_version": 1, "stage": STAGE, "phase": "offline_primary",
            "source_authenticated": True, "spec_count": len(specs),
            "construction_count": construction["construction_count"],
            "construction_pass_count": construction["construction_pass_count"],
            "maximum_incremental_action_linf": construction["maximum_incremental_action_linf"],
            "maximum_predicted_current_utilization": construction["maximum_predicted_current_utilization"],
            "event_stream_digest": construction["event_stream_digest"],
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
        _write(ctx.paths.manifest, {
            "schema_version": 1, "stage": STAGE, "source_blocked": True,
        })
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
    if (
        len(specs) != 100
        or _digest(specs) != manifest.get("spec_digest")
        or _sha(ctx.config_path) != manifest.get("config_sha256")
    ):
        raise ValueError("R8R51R4 saved specification identity changed")
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
        or independent.get("source_route_authenticated") is not True
        or independent.get("design_authenticated") is not True
    ):
        raise ValueError("R8R51R4 offline independent authorization gate failed")
    _set_state(
        ctx, phase_status="real_authorized",
        offline_independent_sha256=_sha(ctx.paths.analysis / "offline_independent.json"),
    )
    return {"stage": STAGE, "phase": "real_authorized", "passed": True}


class SustainedDwellController(r51.BridgeController):
    """Exact R51R1 issue held at current, then returned at step 16 or 18."""

    def __init__(self, *args: Any, spec: Mapping[str, Any], **kwargs: Any):
        super().__init__(*args, spec=spec, **kwargs)
        self.r8r51r4_return_step = int(spec["r8r51r4_return_task_step"])
        if self.r8r51r4_return_step not in RETURN_STEPS:
            raise ValueError("R8R51R4 return step changed")

    def action(self, current_state: Mapping[str, Any]) -> tuple[np.ndarray, dict[str, Any]]:
        if int(current_state["step_index"]) != self.step:
            raise ValueError("R8R51R4 controller/current state index mismatch")
        if self.step < PREFIX_END:
            action, trace = super(r51.BridgeController, self).action(current_state)
            event_name, event, delegated = "none", {}, True
        else:
            currents = np.asarray(current_state["currents_a_tsc"], dtype=float)
            delegated = False
            if self.step == Q0_STEP:
                action, event = self._q0(currents)
                event_name = "q0_exact_issue"
            elif self.step == 11:
                event = r51._observe_event(
                    task_step=self.step, currents=currents,
                    target_fields=self.r8r51r1_center_fields or [],
                    actuator=self.actuator, contract=self.r8r51r1_contract,
                    event="q0_observe_hold",
                )
                action, event_name = np.zeros(N_COILS), "q0_observe_hold"
            elif self.step == ISSUE_STEP:
                action, event = self._issue_candidate(currents)
                event_name = "candidate_issue"
            elif ISSUE_STEP < self.step < self.r8r51r4_return_step:
                if self.r8r51r1_issue_event is None:
                    raise ValueError("R8R51R4 dwell has no causal issue")
                event = r51._observe_event(
                    task_step=self.step, currents=currents,
                    target_fields=self.r8r51r1_issue_event["target_card15_fields"],
                    actuator=self.actuator, contract=self.r8r51r1_contract,
                    event="candidate_current_dwell_hold",
                )
                action, event_name = np.zeros(N_COILS), "candidate_dwell_hold"
            elif self.step == self.r8r51r4_return_step:
                action, event = self._return(currents)
                event_name = "stored_center_return"
            else:
                action, event = self._center_refresh(currents)
                event_name = "center_refresh"
            if not event.get("passed"):
                raise ValueError(
                    "R8R51R4 action safety gate failed: "
                    + json.dumps(event, sort_keys=True)
                )
            trace = r51.r6._trace_template(self.step, np.asarray(action, dtype=float))
        trace.update(
            {
                "action_norm_tsc": np.asarray(action, dtype=float).tolist(),
                "r3c3t13s24d1r14r8r51r4_controller_revision": CONTROLLER_REVISION,
                "r3c3t13s24d1r14r8r51r4_delegated_prefix": delegated,
                "r3c3t13s24d1r14r8r51r4_event": event_name,
                "r3c3t13s24d1r14r8r51r4_event_detail": copy.deepcopy(event),
                "r3c3t13s24d1r14r8r51r4_forbidden_input_used": False,
                "r3c3t13s24d1r14r8r51r4_pair_or_history_label_used": False,
                "r3c3t13s24d1r14r8r51r4_future_measurement_used": False,
                "r3c3t13s24d1r14r8r51r4_future_action_used": False,
                "r3c3t13s24d1r14r8r51r4_source_result_used": False,
                "r3c3t13s24d1r14r8r51r4_hidden_wire_used": False,
            }
        )
        return np.asarray(action, dtype=float), trace


class LocalWorker(r51.LocalWorker):
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
            if (
                horizon != int(spec["formal_horizon_steps"])
                or horizon != int(self.base.env.max_episode_steps)
                or horizon not in (35, 37)
            ):
                raise ValueError("R8R51R4 formal horizon changed")
            self.base.env.reset()
            zero = np.zeros(N_COILS, dtype=np.float32)
            record = r51.r8r7.r8.d1r11.s21.s16.s9.t11.t1.r1._state_record_full
            trajectory.append(record(self.base.env, 0, zero))
            controller = SustainedDwellController(
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
                    raise ValueError("R8R51R4 pre-action visible state safety gate failed")
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
                    raise RuntimeError("environment truncated before R8R51R4 horizon")
            return_step = int(spec["r8r51r4_return_task_step"])
            names = [
                row.get("r3c3t13s24d1r14r8r51r4_event")
                for row in trace[PREFIX_END:]
            ]
            dwell_count = return_step - ISSUE_STEP - 1
            success = bool(
                len(trajectory) == horizon + 1 and len(trace) == horizon
                and r51.r8r7.r8.r4._calibration_exact(trace)
                and all(
                    bool(row.get("r3c3t13s24d1r14r8r51r4_delegated_prefix"))
                    for row in trace[:PREFIX_END]
                )
                and names[:3] == ["q0_exact_issue", "q0_observe_hold", "candidate_issue"]
                and names[3 : 3 + dwell_count] == ["candidate_dwell_hold"] * dwell_count
                and names[3 + dwell_count] == "stored_center_return"
                and all(name == "center_refresh" for name in names[4 + dwell_count :])
                and all(
                    bool((row.get("r3c3t13s24d1r14r8r51r4_event_detail") or {}).get("passed"))
                    for row in trace[PREFIX_END:]
                )
                and controller._active_issue is None
                and not any(bool(row.get("abnormal")) for row in trajectory)
            )
            result.update(
                {
                    "success": success, "completed": True,
                    "failure_reason": "" if success else "incomplete or invalid R8R51R4 rollout",
                    "execution_failure_class": "" if success else "controller_or_action_semantics_error",
                    "hidden_history_control_summary": {
                        "fresh_controller_actor": True, "fresh_tsc_process": True,
                        "full_tsc_hidden_state_loaded_from_sprsina": True,
                        "future_r17_controller_executed": False,
                        "formal_tracking_diagnostic_only": False,
                        "stage_trajectory_allowed_in_expert_dataset": False,
                        "future_action_replay_used": False, "future_measurement_used": False,
                        "pair_or_history_label_used": False, "source_result_used": False,
                    },
                    "wall_time_s": time.time() - started,
                }
            )
            failed = not success
            return r51.r8r7.r8.d1r11.s21.s16.s9.t11.t1._json_safe(result)
        except Exception as exc:
            result.update(
                {
                    "success": False, "completed": True, "failure_reason": repr(exc),
                    "execution_failure_class": str(
                        result.get("execution_failure_class") or "runtime_or_controller_error"
                    ),
                    "trajectory": trajectory, "controller_trace": trace,
                    "traceback": traceback.format_exc(), "wall_time_s": time.time() - started,
                }
            )
            return r51.r8r7.r8.d1r11.s21.s16.s9.t11.t1._json_safe(result)
        finally:
            runner = getattr(self.base.env, "runner", None)
            if runner is not None:
                runner.cleanup_episode_workspace(
                    failed=failed, reason="stage4_2r3c3t13s24d1r14r8r51r4"
                )


_RAY_ACTOR = None


def _ray_actor_class():
    global _RAY_ACTOR
    if _RAY_ACTOR is None:
        import ray

        @ray.remote(num_cpus=1, max_restarts=0)
        class R8R51R4Actor:
            def __init__(self, *args: Any):
                self.worker = LocalWorker(*args)

            def evaluate(self, spec: dict[str, Any]) -> dict[str, Any]:
                return self.worker.evaluate(spec)

            def close(self) -> bool:
                self.worker.close()
                return True

        _RAY_ACTOR = R8R51R4Actor
    return _RAY_ACTOR


def _result_complete(
    path: Path, spec: Mapping[str, Any], *, require_success: bool = True
) -> bool:
    if not path.is_file():
        return False
    try:
        result = r51.r8r7.r8._read_gz(path)
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


def evaluate_specs(
    ctx: Context, specs: Sequence[dict[str, Any]], *, backend: str, resume: bool
) -> dict[str, Any]:
    pending = [
        spec for spec in specs
        if not (
            resume
            and _result_complete(
                ctx.paths.raw / f"{spec['experiment_id']}.json.gz",
                spec, require_success=False,
            )
        )
    ]
    payloads = {str(spec["experiment_id"]): _payload(ctx, spec) for spec in specs}
    execution = _execution_context(ctx)
    library, bundle, selector = r51.r8r7.r8.d1r11._library_bundle_selector(
        execution.d1r11_ctx
    )
    lattice = execution.d1r11_ctx.base_ctx.base_ctx.cfg["lattice_probe"]
    calibration = execution.d1r11_ctx.base_ctx.base_ctx.cfg["active_calibration"]
    dynamic = execution.d1r11_ctx.base_ctx.cfg["causal_model"]
    schedule_cfg = execution.d1r11_ctx.cfg["schedule_contract"]
    controller_cfg = _controller_contract(ctx)

    def args_for(spec: Mapping[str, Any], index: int) -> tuple[Any, ...]:
        return (
            payloads[str(spec["experiment_id"])], library, bundle,
            f"stage42r8r51r4_{index:03d}", selector, lattice, calibration,
            dynamic, schedule_cfg, controller_cfg,
        )

    if backend == "serial":
        for index, spec in enumerate(pending):
            worker = LocalWorker(*args_for(spec, index))
            try:
                result = worker.evaluate(spec)
            finally:
                worker.close()
            r51.r8r7.r8._write_gz(
                ctx.paths.raw / f"{spec['experiment_id']}.json.gz", result
            )
            print(f"[R8R51R4] {index + 1}/{len(pending)}", flush=True)
    elif backend == "ray" and pending:
        import ray

        plan = r51.r8r7.r8.d1r11.s21.s16.ensure_ray_worker_plan(
            ray, requested_workers=int(ctx.cfg["parallel"]["n_workers"]),
            pending_tasks=len(pending),
            ray_tmpdir=os.environ.get("RAY_TMPDIR") or ctx.cfg["storage"]["ray_tmpdir"],
            log_prefix="[R8R51R4]",
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
                        print(f"[R8R51R4] waiting {completed}/{len(pending)}", flush=True)
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
                    r51.r8r7.r8._write_gz(
                        ctx.paths.raw / f"{spec['experiment_id']}.json.gz", result
                    )
                    completed += 1
                    print(f"[R8R51R4] {completed}/{len(pending)}", flush=True)
            finally:
                close_refs = [actor.close.remote() for actor in actors]
                if close_refs:
                    ray.get(
                        close_refs,
                        timeout=float(ctx.cfg["storage"]["actor_close_timeout_s"]),
                    )
                for actor in actors:
                    ray.kill(actor, no_restart=True)
    elif backend not in {"serial", "ray"}:
        raise ValueError(f"unsupported R8R51R4 backend: {backend}")
    completed = sum(
        _result_complete(
            ctx.paths.raw / f"{spec['experiment_id']}.json.gz",
            spec, require_success=False,
        )
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
    "r3c3t13s24d1r14r8r51r4_forbidden_input_used",
    "r3c3t13s24d1r14r8r51r4_pair_or_history_label_used",
    "r3c3t13s24d1r14r8r51r4_future_measurement_used",
    "r3c3t13s24d1r14r8r51r4_future_action_used",
    "r3c3t13s24d1r14r8r51r4_source_result_used",
    "r3c3t13s24d1r14r8r51r4_hidden_wire_used",
)


def _prefix_payload(result: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "states": [
            r51.r8r7.r8.r4._semantic_state(row)
            for row in (result.get("trajectory") or [])[:13]
        ],
        "trace": (result.get("controller_trace") or [])[:12],
    }


def audit_raw_integrity(ctx: Context, *, write: bool = True) -> dict[str, Any]:
    specs = _saved_specs(ctx)
    offline_rows = {
        str(row["experiment_id"]): row
        for row in _read(ctx.paths.analysis / "offline_construction.json")["rows"]
    }
    _, sources = r51._source_baselines(ctx.base_ctx)
    matrix = np.asarray(
        ctx.base_ctx.r8r48_ctx.source_ctx.cfg["candidate_contract"][
            "canonical_matrix_columns"
        ],
        dtype=float,
    )
    rows = []
    prefix_by_context: dict[tuple[str, str], list[str]] = defaultdict(list)
    contract = ctx.cfg["controller_contract"]
    for spec in specs:
        path = ctx.paths.raw / f"{spec['experiment_id']}.json.gz"
        result = (
            r51.r8r7.r8._read_gz(path)
            if _result_complete(path, spec, require_success=False) else {}
        )
        trajectory = result.get("trajectory") or []
        trace = result.get("controller_trace") or []
        horizon = int(spec["horizon_steps"])
        full = len(trajectory) == horizon + 1 and len(trace) == horizon
        source = sources[str(spec["source_r8r7_baseline_experiment_id"])]
        restart = bool(
            full
            and r51.r8r7.r8.r4._semantic_state(trajectory[0])
            == r51.r8r7.r8.r4._semantic_state(source["trajectory"][0])
        )
        source_prefix_state = bool(
            full and all(
                r51.r8r7.r8.r4._semantic_state(current)
                == r51.r8r7.r8.r4._semantic_state(reference)
                for current, reference in zip(
                    trajectory[: PREFIX_END + 1],
                    source["trajectory"][: PREFIX_END + 1],
                )
            )
        )
        source_prefix_trace = bool(
            full and all(
                r51.r8r22._source_trace_semantic_projection(reference, current)
                for current, reference in zip(
                    trace[:PREFIX_END], source["controller_trace"][:PREFIX_END]
                )
            )
        )
        wrapper_prefixes = (
            "r3c3t13s24d1r14r4_", "r3c3t13s24d1r14r8r7_",
            "r3c3t13s24d1r14r8r51r1_", "r3c3t13s24d1r14r8r51r4_",
        )
        trace_wrapper_only = bool(
            full and all(
                str(key).startswith(wrapper_prefixes)
                for current, reference in zip(
                    trace[:PREFIX_END], source["controller_trace"][:PREFIX_END]
                )
                for key in set(current) | set(reference)
                if current.get(key) != reference.get(key)
            )
        )
        prefix_digest = _digest(_prefix_payload(result)) if full else ""
        context_key = (str(spec["pair_id"]), str(spec["history_member"]))
        prefix_by_context[context_key].append(prefix_digest)
        events = [
            trace[step].get("r3c3t13s24d1r14r8r51r4_event_detail") or {}
            for step in range(PREFIX_END, horizon)
        ] if full else []
        names = [
            trace[step].get("r3c3t13s24d1r14r8r51r4_event")
            for step in range(PREFIX_END, horizon)
        ] if full else []
        return_step = int(spec["r8r51r4_return_task_step"])
        dwell_count = return_step - ISSUE_STEP - 1
        q0 = events[0] if len(events) > 0 else {}
        issue = events[2] if len(events) > 2 else {}
        dwell = events[3 : 3 + dwell_count]
        returned = events[3 + dwell_count] if len(events) > 3 + dwell_count else {}
        expected_coordinate = matrix @ np.asarray(spec["r8r51r4_candidate_q"], dtype=float)
        candidate_exact = bool(
            issue.get("candidate_id") == spec["r8r51r4_candidate_id"]
            and np.array_equal(
                np.asarray(issue.get("requested_coordinate") or []), expected_coordinate
            )
            and np.array_equal(
                expected_coordinate,
                np.asarray(spec["r8r51r4_requested_coordinate"], dtype=float),
            )
        )
        offline = offline_rows.get(str(spec["experiment_id"]), {})
        q0_exact = bool(
            q0.get("event") == "q0_exact_current_target_issue"
            and q0.get("q0_constructor_revision") == "shared_exact_card15_current_target_v1"
            and q0.get("passed") is True
            and set(q0.get("criteria") or {}) == r51.Q0_CRITERIA_KEYS
            and "q0_zero_target" not in (q0.get("criteria") or {})
            and list(q0.get("stored_target_card15_fields") or [])
            == list(q0.get("q0_center_card15_fields") or [])
            and float(q0.get("incremental_normalized_action_linf", math.inf))
            <= float(contract["maximum_q0_integration_action_linf"]) + 1e-12
        )
        q0_offline_parity = bool(
            q0_exact and _digest(q0) == offline.get("q0_event_digest")
            and list(q0.get("action_norm_tsc") or []) == offline.get("q0_action_norm_tsc")
            and sorted(q0.get("criteria") or {}) == offline.get("q0_criteria_keys")
        )
        q0_first_effect = bool(
            full
            and np.array_equal(
                np.asarray(trajectory[Q0_STEP + 1]["action_norm_tsc"]),
                np.asarray(trace[Q0_STEP]["action_norm_tsc"]),
            )
            and np.array_equal(
                np.asarray(trajectory[Q0_STEP + 1]["currents_a_tsc"]),
                np.asarray(q0.get("nominal_readback_current_a_tsc") or []),
            )
        )
        first_effect = bool(
            full
            and np.array_equal(
                np.asarray(trajectory[FIRST_EFFECT_STATE]["action_norm_tsc"]),
                np.asarray(trace[ISSUE_STEP]["action_norm_tsc"]),
            )
            and not np.array_equal(
                np.asarray(trajectory[FIRST_EFFECT_STATE]["currents_a_tsc"]),
                np.asarray(trajectory[ISSUE_STEP]["currents_a_tsc"]),
            )
        )
        dwell_exact = bool(
            len(dwell) == dwell_count
            and all(event.get("event") == "candidate_current_dwell_hold" for event in dwell)
            and all(event.get("passed") is True for event in dwell)
            and all(
                np.array_equal(np.asarray(event.get("action_norm_tsc") or []), np.zeros(N_COILS))
                for event in dwell
            )
            and all(
                event.get("stored_target_card15_fields") == issue.get("target_card15_fields")
                for event in dwell
            )
            and all(
                np.array_equal(
                    np.asarray(trajectory[step + 1]["currents_a_tsc"]),
                    np.asarray(issue.get("nominal_issue_readback_current_a_tsc") or []),
                )
                for step in range(ISSUE_STEP + 1, return_step)
            )
        )
        return_exact = bool(
            returned.get("event") == "stored_pretransport_center_return"
            and returned.get("passed") is True
            and returned.get("stored_center_card15_fields") == issue.get("center_card15_fields")
            and returned.get("issue_target_card15_fields") == issue.get("target_card15_fields")
        )
        sequence_exact = bool(
            names[:3] == ["q0_exact_issue", "q0_observe_hold", "candidate_issue"]
            and names[3 : 3 + dwell_count] == ["candidate_dwell_hold"] * dwell_count
            and names[3 + dwell_count] == "stored_center_return"
            and all(name == "center_refresh" for name in names[4 + dwell_count :])
        )
        event_pass = bool(
            full and all(
                event.get("passed") is True
                and all(bool(value) for value in (event.get("criteria") or {}).values())
                for event in events
            )
        )
        real_stream_digest = _digest(events)
        offline_parity = bool(real_stream_digest == offline.get("event_stream_digest"))
        actions = np.asarray([row.get("action_norm_tsc", []) for row in trace], dtype=float)
        currents = np.asarray(
            [row.get("currents_a_tsc", []) for row in trajectory], dtype=float
        )
        finite = bool(
            full and actions.shape == (horizon, N_COILS)
            and currents.shape == (horizon + 1, N_COILS)
            and np.all(np.isfinite(actions)) and np.all(np.isfinite(currents))
            and all(
                math.isfinite(float(row[key]))
                for row in trajectory for key in ("R", "Z", "Ip")
            )
            and not any(bool(row.get("abnormal")) for row in trajectory)
        )
        payload = _read(ctx.paths.variants / f"payload_{spec['experiment_id']}.json")
        minimum, maximum = r51.r8r7.r8.d1r11.s21.s13._current_limits_tsc(payload)
        center, half = 0.5 * (minimum + maximum), 0.5 * (maximum - minimum)
        utilization = (
            float(np.max(np.abs((currents - center) / half)))
            if currents.shape == (horizon + 1, N_COILS) else None
        )
        forbidden = sum(
            any(bool(row.get(key)) for key in FORBIDDEN_KEYS) for row in trace
        )
        passed = bool(
            result.get("success") and full and restart and source_prefix_state
            and source_prefix_trace and trace_wrapper_only
            and r51.r8r7.r8.r4._calibration_exact(trace)
            and q0_exact and q0_offline_parity and q0_first_effect
            and candidate_exact and first_effect and dwell_exact and return_exact
            and sequence_exact and event_pass and offline_parity and finite
            and forbidden == 0 and utilization is not None
            and utilization <= float(contract["maximum_current_utilization"]) + 1e-12
        )
        rows.append(
            {
                "experiment_id": str(spec["experiment_id"]),
                "source_baseline_experiment_id": str(
                    spec["source_r8r7_baseline_experiment_id"]
                ),
                "pair_id": str(spec["pair_id"]),
                "history_member": str(spec["history_member"]),
                "candidate_index": int(spec["r8r51r4_candidate_index"]),
                "candidate_id": str(spec["r8r51r4_candidate_id"]),
                "return_task_step": return_step,
                "runtime_success": bool(result.get("success")),
                "full_horizon": full, "authentic_restart": restart,
                "source_prefix_state_exact": source_prefix_state,
                "source_prefix_trace_exact": source_prefix_trace,
                "source_trace_difference_wrapper_only": trace_wrapper_only,
                "calibration_exact": bool(
                    full and r51.r8r7.r8.r4._calibration_exact(trace)
                ),
                "q0_exact": q0_exact, "q0_offline_parity": q0_offline_parity,
                "q0_first_effect_at_issue_plus_one": q0_first_effect,
                "candidate_exact": candidate_exact,
                "candidate_first_effect_at_issue_plus_one": first_effect,
                "dwell_exact": dwell_exact, "return_exact": return_exact,
                "event_sequence_exact": sequence_exact,
                "event_gates_passed": event_pass,
                "offline_event_stream_parity": offline_parity,
                "finite": finite, "forbidden_trace_count": forbidden,
                "maximum_current_utilization": utilization,
                "prefix_digest": prefix_digest,
                "event_stream_digest": real_stream_digest,
                "execution_failure_class": str(
                    result.get("execution_failure_class") or ""
                ),
                "failure_reason": str(result.get("failure_reason") or ""),
                "passed": passed,
            }
        )
    prefix_exact = {
        key: len(values) == 10 and len(set(values)) == 1 and bool(values[0])
        for key, values in prefix_by_context.items()
    }
    for row in rows:
        key = (str(row["pair_id"]), str(row["history_member"]))
        row["within_context_q0_prefix_exact"] = bool(prefix_exact.get(key))
        row["passed"] = bool(row["passed"] and row["within_context_q0_prefix_exact"])
    inventory = r51.r8r7.r8._inventory(ctx.paths.raw)
    passed_count = sum(bool(row["passed"]) for row in rows)
    safety_stops = sum(
        row["execution_failure_class"] == "controller_action_safety_gate_failure"
        for row in rows
    )
    runtime_failures = sum(
        bool(row["execution_failure_class"])
        and row["execution_failure_class"] != "controller_action_safety_gate_failure"
        for row in rows
    )
    report = {
        "schema_version": 1, "stage": STAGE, "phase": "raw_integrity_primary",
        "raw_inventory": inventory, "expected_raw_count": 100,
        "strict_parse_count": len(rows),
        "runtime_success_count": sum(bool(row["runtime_success"]) for row in rows),
        "full_horizon_count": sum(bool(row["full_horizon"]) for row in rows),
        "authentic_restart_count": sum(bool(row["authentic_restart"]) for row in rows),
        "source_prefix_state_exact_count": sum(
            bool(row["source_prefix_state_exact"]) for row in rows
        ),
        "source_prefix_trace_exact_count": sum(
            bool(row["source_prefix_trace_exact"]) for row in rows
        ),
        "source_trace_difference_wrapper_only_count": sum(
            bool(row["source_trace_difference_wrapper_only"]) for row in rows
        ),
        "calibration_exact_count": sum(bool(row["calibration_exact"]) for row in rows),
        "q0_exact_count": sum(bool(row["q0_exact"]) for row in rows),
        "q0_offline_parity_count": sum(bool(row["q0_offline_parity"]) for row in rows),
        "q0_first_effect_at_issue_plus_one_count": sum(
            bool(row["q0_first_effect_at_issue_plus_one"]) for row in rows
        ),
        "candidate_exact_count": sum(bool(row["candidate_exact"]) for row in rows),
        "candidate_first_effect_at_issue_plus_one_count": sum(
            bool(row["candidate_first_effect_at_issue_plus_one"]) for row in rows
        ),
        "dwell_exact_count": sum(bool(row["dwell_exact"]) for row in rows),
        "stored_center_return_exact_count": sum(bool(row["return_exact"]) for row in rows),
        "event_sequence_exact_count": sum(
            bool(row["event_sequence_exact"]) for row in rows
        ),
        "offline_event_stream_parity_count": sum(
            bool(row["offline_event_stream_parity"]) for row in rows
        ),
        "finite_count": sum(bool(row["finite"]) for row in rows),
        "causal_forbidden_pass_count": sum(
            int(row["forbidden_trace_count"]) == 0 for row in rows
        ),
        "within_context_q0_prefix_exact_count": sum(
            bool(row["within_context_q0_prefix_exact"]) for row in rows
        ),
        "passed_count": passed_count, "safety_stop_count": safety_stops,
        "runtime_failure_count": runtime_failures,
        "forbidden_trace_count": sum(int(row["forbidden_trace_count"]) for row in rows),
        "maximum_current_utilization": max(
            (float(row["maximum_current_utilization"]) for row in rows
             if row["maximum_current_utilization"] is not None),
            default=None,
        ),
        "prefix_digest": _digest(sorted(set(row["prefix_digest"] for row in rows))),
        "event_stream_digest": _digest([
            (row["experiment_id"], row["event_stream_digest"]) for row in rows
        ]),
        "rows": rows,
        "route": (
            ctx.cfg["routes"]["pass"] if passed_count == 100 and inventory["count"] == 100
            else ctx.cfg["routes"]["execution_fail"]
        ),
        "passed": passed_count == 100 and inventory["count"] == 100,
    }
    if write:
        _write(ctx.paths.analysis / "raw_integrity_primary.json", report)
    return report


def _formal_authority(ctx: Context) -> dict[str, Any]:
    specs = _saved_specs(ctx)
    integrity = _read(ctx.paths.analysis / "raw_integrity_primary.json")
    _, sources = r51._source_baselines(ctx.base_ctx)
    baseline_ids = tuple(ctx.cfg["matrix_contract"]["failed_source_baseline_ids"])
    baseline_rows = []
    for baseline_id in baseline_ids:
        result = sources[str(baseline_id)]
        spec = result["spec"]
        baseline_rows.append(
            {
                "experiment_id": str(baseline_id), "partition": "baseline",
                "pair_id": str(spec["pair_id"]),
                "history_member": str(spec["history_member"]),
                "candidate_index": -1, "candidate_id": "baseline",
                "return_task_step": -1,
                **r51r3.formal_metric(
                    spec, result["trajectory"], ctx.cfg["formal_contract"]
                ),
            }
        )
    valid = {
        str(row["experiment_id"]): row for row in integrity["rows"] if row["passed"]
    }
    candidate_rows = []
    for spec in specs:
        experiment_id = str(spec["experiment_id"])
        result = r51.r8r7.r8._read_gz(ctx.paths.raw / f"{experiment_id}.json.gz")
        if (
            experiment_id not in valid
            or result.get("success") is not True
            or result.get("spec") != spec
            or len(result.get("trajectory") or []) != int(spec["horizon_steps"]) + 1
        ):
            raise ValueError(f"R8R51R4 formal source row failed integrity: {experiment_id}")
        candidate_rows.append(
            {
                "experiment_id": experiment_id, "partition": "candidate",
                "pair_id": str(spec["pair_id"]),
                "history_member": str(spec["history_member"]),
                "candidate_index": int(spec["r8r51r4_candidate_index"]),
                "candidate_id": str(spec["r8r51r4_candidate_id"]),
                "return_task_step": int(spec["r8r51r4_return_task_step"]),
                "source_baseline_experiment_id": str(
                    spec["source_r8r7_baseline_experiment_id"]
                ),
                **r51r3.formal_metric(
                    spec, result["trajectory"], ctx.cfg["formal_contract"]
                ),
            }
        )
    rows = sorted(
        [*baseline_rows, *candidate_rows],
        key=lambda row: (
            row["pair_id"], row["history_member"],
            0 if row["partition"] == "baseline" else 1,
            int(row["candidate_index"]), int(row["return_task_step"]),
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
            raise ValueError(f"R8R51R4 formal context coverage changed: {key}")
        baseline_row = baseline[0]
        best = max(
            candidates,
            key=lambda row: (
                float(row["formal_minimum_signed_margin"]),
                float(row["formal_mean_signed_margin"]),
                -int(row["candidate_index"]), -int(row["return_task_step"]),
            ),
        )
        oracle = max(
            enumerate([baseline_row, *candidates]),
            key=lambda item: (
                float(item[1]["formal_minimum_signed_margin"]),
                float(item[1]["formal_mean_signed_margin"]), -item[0],
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
                "pair_id": key[0], "history_member": key[1],
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
        and measured_oracle
        >= int(ctx.cfg["scientific_gate"]["minimum_measured_oracle_formal_pass_count"])
    )
    route = ctx.cfg["routes"]["pass" if scientific else "authority_insufficient"]
    return {
        "schema_version": 1, "stage": STAGE, "identity": IDENTITY,
        "phase": "formal_primary_detailed", "formal_rows": rows,
        "formal_metric_digest": _digest(rows), "context_rows": context_rows,
        "context_outcome_digest": _digest(context_rows),
        "strict_full_horizon_count": len(candidate_rows),
        "candidate_count": len(candidate_rows), "failed_context_count": len(context_rows),
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
        "integrity_gate_passed": True, "scientific_gate_passed": scientific,
        "audit_passed": True, "route": route, "passed": scientific,
    }


def run_real(ctx: Context, *, backend: str, resume: bool) -> dict[str, Any]:
    state = _read(ctx.paths.state)
    if state.get("phase_status") != "real_authorized":
        raise ValueError("R8R51R4 real execution is not authorized")
    specs = _saved_specs(ctx)
    execution = evaluate_specs(ctx, specs, backend=backend, resume=resume)
    primary = audit_raw_integrity(ctx)
    passed = bool(primary["passed"])
    _set_state(
        ctx,
        phase_status="raw_integrity_primary_ready" if passed else "real_execution_failed",
        finished=not passed, real_tsc_executed=True,
        plant_step_count=sum(
            min(
                len((r51.r8r7.r8._read_gz(
                    ctx.paths.raw / f"{spec['experiment_id']}.json.gz"
                ).get("controller_trace") or [])),
                int(spec["horizon_steps"]),
            )
            for spec in specs
            if (ctx.paths.raw / f"{spec['experiment_id']}.json.gz").is_file()
        ),
        new_raw_count=primary["raw_inventory"]["count"],
        response_outcomes_opened=False,
        route=primary["route"], verdict={"route": primary["route"], "passed": passed},
        stop_reason="" if passed else "runtime_action_restart_raw_or_causality_gate_failed",
    )
    return {
        "stage": STAGE, "phase": "real", "execution": execution,
        "raw_integrity_primary_passed": passed, "formal_response_opened": False,
        "route": primary["route"],
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
        raise ValueError("R8R51R4 raw independent integrity gate incomplete")
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
        "raw_integrity_primary_sha256": _sha(
            ctx.paths.analysis / "raw_integrity_primary.json"
        ),
        "raw_integrity_independent_sha256": _sha(
            ctx.paths.analysis / "raw_integrity_independent.json"
        ),
        "primary_detailed_sha256": _sha(ctx.paths.analysis / "primary_detailed.json"),
        "new_tsc_count": 100, "new_raw_count": 100,
        "controller_execution_count": 100,
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
        raise ValueError("R8R51R4 final independent agreement failed")
    compact_keys = (
        "strict_full_horizon_count", "candidate_count", "failed_context_count",
        "known_all_context_baseline_formal_pass_count",
        "candidate_formal_pass_count", "candidate_formal_pass_context_count",
        "repaired_failed_baseline_count",
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
        "primary_independent_maximum_numerical_difference": independent[
            "maximum_primary_numerical_difference"
        ],
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
        stop_reason="" if final["scientific_gate_passed"] else "measured_sustained_dwell_authority_gate_failed",
    )
    return final


def execute(
    ctx: Context, *, command: str, backend: str, resume: bool
) -> dict[str, Any]:
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
    raise ValueError(f"unsupported R8R51R4 command: {command}")


def _parser() -> argparse.ArgumentParser:
    parser = r51._parser()
    parser.description = __doc__
    parser.add_argument("--r51r1-run", type=Path, required=True)
    parser.add_argument("--r51r3-run", type=Path, required=True)
    return parser


def main() -> None:
    args = _parser().parse_args()
    result = execute(
        load_context(args), command=args.command, backend=args.backend, resume=args.resume
    )
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
