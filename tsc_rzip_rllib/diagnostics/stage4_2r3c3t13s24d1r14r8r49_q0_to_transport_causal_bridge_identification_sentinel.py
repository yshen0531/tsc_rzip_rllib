#!/usr/bin/env python3
"""Execute the frozen R8R49 q0-to-transport causal bridge sentinel."""

from __future__ import annotations

import argparse
import copy
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import time
import traceback
from types import SimpleNamespace
from typing import Any, Mapping, Sequence

import numpy as np

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r6_direction0_replacement_sentinel as r6,
    stage4_2r3c3t13s24d1r14r8r7_fresh_multipulse_static_observer_interaction_campaign as r8r7,
    stage4_2r3c3t13s24d1r14r8r9_measured_multipulse_authority_audit as r8r9,
    stage4_2r3c3t13s24d1r14r8r22_bounded_continuous_multidirection_authority_sentinel as r8r22,
    stage4_2r3c3t13s24d1r14r8r31_aligned_explicit_four_coordinate_feedback_sentinel as r8r31,
    stage4_2r3c3t13s24d1r14r8r48_q0_to_transport_causal_bridge_support_audit as r8r48,
)


SCHEMA_VERSION = 1
STAGE = "Stage4.2R3c3T13S24D1R14R8R49"
IDENTITY = "q0_to_transport_causal_bridge_identification_sentinel_v1"
RUN_NAME = "stage4_2r3c3t13s24d1r14r8r49_q0_to_transport_causal_bridge_identification_sentinel"
CONTROLLER_REVISION = "q0_to_transport_causal_bridge_v42r3c3t13s24d1r14r8r49_v1"
N_COILS = 14
PREFIX_END = 10
Q0_STEP = 10
ISSUE_STEP = 12
FIRST_EFFECT_STATE = 13
SECOND_EFFECT_STATE = 14
RETURN_STEP = 14


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
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def _matrix_digest(value: Sequence[Sequence[float]]) -> str:
    return hashlib.sha256(
        np.ascontiguousarray(np.asarray(value, dtype="<f8")).tobytes(order="C")
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
    r8r48_ctx: r8r48.Context
    r8r48_stage: Path
    r8r22_ctx: Any
    source_ctx: r8r7.Context


def validate_config(cfg: Mapping[str, Any], *, project_root: Path) -> None:
    design = project_root / str(cfg.get("design_document", ""))
    source = project_root / str(cfg.get("source_r8r48_config", ""))
    matrix = cfg.get("matrix_contract", {})
    schedule = cfg.get("schedule_contract", {})
    controller = cfg.get("controller_contract", {})
    formal = cfg.get("formal_contract", {})
    scope = cfg.get("scientific_scope", {})
    expected_ids = (
        "q0", "d0m", "d0p", "d1p", "d2m", "d3m", "d3p", "u0p50",
        "u0p75", "u1p00", "u1p25", "u1p50", "v0p50", "v0p75",
        "v1p00", "v1p25", "v1p50",
    )
    expected_routes = {
        "source_blocked": "Q0_TO_TRANSPORT_BRIDGE_SENTINEL_BLOCKED_BY_SOURCE",
        "offline_fail": "Q0_TO_TRANSPORT_BRIDGE_SENTINEL_OFFLINE_FAIL_NO_REAL_TSC",
        "execution_fail": "Q0_TO_TRANSPORT_BRIDGE_SENTINEL_EXECUTION_FAIL_STOP",
        "safety_fail": "Q0_TO_TRANSPORT_BRIDGE_SENTINEL_SAFETY_FAIL_REDESIGN",
        "pass": "Q0_TO_TRANSPORT_BRIDGE_IDENTIFICATION_COMPLETE_MODEL_PREFLIGHT_REQUIRED",
    }
    invalid = (
        cfg.get("schema_version") != SCHEMA_VERSION
        or cfg.get("stage") != STAGE
        or cfg.get("identity") != IDENTITY
        or cfg.get("run_name") != RUN_NAME
        or cfg.get("controller_revision") != CONTROLLER_REVISION
        or not design.is_file()
        or _sha(design) != cfg.get("design_document_sha256")
        or not source.is_file()
        or _sha(source) != cfg.get("source_r8r48_config_sha256")
        or cfg.get("source_r8r48", {}).get("required_route")
        != "Q0_CALIBRATION_TO_TRANSPORT_CAUSAL_BRIDGE_SUPPORT_ABSENT_FRESH_SENTINEL_REQUIRED"
        or tuple(int(matrix.get(key, -1)) for key in (
            "context_count", "candidate_count", "nonzero_candidate_count", "trajectory_count"
        )) != (16, 17, 16, 256)
        or tuple(matrix.get("candidate_ids", ())) != expected_ids
        or matrix.get("canonical_matrix_float64_le_c_sha256")
        != "c8cd62c00c1f60b46312927789659657dc8cc35717533193433b0e398c1ec94c"
        or tuple(int(schedule.get(key, -1)) for key in (
            "prefix_end_task_step", "q0_issue_task_step", "candidate_issue_task_step",
            "candidate_first_effect_state_step", "candidate_second_effect_state_step",
            "stored_center_return_task_step", "dynamic_exact_search_radius",
            "require_exact_q0_prefix_through_state_step",
        )) != (10, 10, 12, 13, 14, 14, 16, 12)
        or schedule.get("require_exact_center_refresh_after_return") is not True
        or tuple(float(controller.get(key, -1.0)) for key in (
            "maximum_incremental_normalized_action_linf",
            "maximum_total_normalized_action_abs", "maximum_current_utilization",
            "minimum_desired_applied_current_cosine", "maximum_relative_off_basis_residual",
        )) != (0.25, 1.0, 0.55, 0.98, 0.10)
        or any(controller.get(key) is not True for key in (
            "require_exact_card15_issue", "require_exact_card15_refresh",
            "require_exact_stored_center_return", "require_first_effect_at_issue_plus_one",
            "safe_stop_before_failed_advance",
        ))
        or tuple(int(formal.get(key, -1)) for key in (
            "normal_arrival_deadline_step", "normal_hold_through_step",
            "weak_arrival_deadline_step", "weak_hold_through_step", "arrival_streak_steps",
        )) != (25, 35, 27, 37, 3)
        or tuple(float(formal.get(key, -1.0)) for key in (
            "position_tolerance_m", "speed_tolerance_m_per_s", "ip_tolerance_A"
        )) != (0.03, 0.1, 10000.0)
        or formal.get("arrival_deadline_expansion_allowed") is not False
        or formal.get("formal_tracking_diagnostic_only") is not True
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
        raise ValueError("R8R49 frozen design changed")


def load_context(args: argparse.Namespace) -> Context:
    config_path = args.config.expanduser().resolve()
    cfg = _read(config_path)
    validate_config(cfg, project_root=_root())
    source_args = SimpleNamespace(**vars(args))
    source_args.config = (_root() / str(cfg["source_r8r48_config"])).resolve()
    source_args.run_dir = args.r8r48_run.expanduser().resolve()
    source_ctx = r8r48.load_context(source_args)
    r8r22_ctx = source_ctx.source_ctx.r8r23_ctx.r8r22_ctx
    return Context(
        cfg=cfg,
        config_path=config_path,
        paths=_paths(args.run_dir),
        r8r48_ctx=source_ctx,
        r8r48_stage=source_ctx.paths.stage,
        r8r22_ctx=r8r22_ctx,
        source_ctx=r8r22_ctx.source_ctx,
    )


def _execution_context(ctx: Context) -> Any:
    return r8r7.r8.Context(
        cfg=ctx.source_ctx.r8_cfg,
        config_path=ctx.source_ctx.r8_config_path,
        d1r11_ctx=ctx.source_ctx.r8_ctx.d1r11_ctx,
        source_d1r11_run=ctx.source_ctx.r8_ctx.source_d1r11_run,
        source_response_runs=ctx.source_ctx.r8_ctx.source_response_runs,
        paths=ctx.paths,
    )


def _source_stage(ctx: Context) -> Path:
    return r8r22._source_stage(ctx.r8r22_ctx)


def _source_baselines(ctx: Context) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    specs, results = r8r22._source_baselines(ctx.r8r22_ctx)
    if len(specs) != 16 or len(results) != 16:
        raise SourceBlockedError("R8R49 source baseline coverage changed")
    return specs, results


def _r8r48_paths(stage: Path) -> dict[str, Path]:
    return {
        "primary_summary": stage / "analysis/primary_summary.json",
        "primary_detailed": stage / "analysis/primary_detailed.json",
        "independent": stage / "analysis/independent.json",
        "compact_audit": stage / "analysis/compact_audit.json",
        "final_report": stage / "analysis/final_report.json",
        "stage_state": stage / "stage_state.json",
        "stage_manifest": stage / "stage_manifest.json",
    }


def authenticate_sources(ctx: Context) -> dict[str, Any]:
    paths = _r8r48_paths(ctx.r8r48_stage)
    contract = ctx.cfg["source_r8r48"]
    if any(not path.is_file() for path in paths.values()):
        raise SourceBlockedError("R8R49 final R8R48 evidence incomplete")
    hashes = {name: _sha(path) for name, path in paths.items()}
    if any(hashes[name] != contract[f"{name}_sha256"] for name in hashes):
        raise SourceBlockedError("R8R49 final R8R48 hash changed")
    final = _read(paths["final_report"])
    state = _read(paths["stage_state"])
    if (
        final.get("route") != contract["required_route"]
        or state.get("route") != contract["required_route"]
        or final.get("passed") is not True
        or state.get("finished") is not True
        or not bool(final.get("independent_agreement"))
        or bool(final.get("real_tsc_executed"))
        or int(final.get("new_raw_count", -1)) != 0
    ):
        raise SourceBlockedError("R8R49 final R8R48 route changed")
    r8r31_cfg = ctx.r8r48_ctx.source_ctx.cfg
    candidates = r8r31._candidate_rows(r8r31_cfg)
    matrix = np.asarray(r8r31_cfg["candidate_contract"]["canonical_matrix_columns"], dtype=float)
    if (
        len(candidates) != 17
        or [row["id"] for row in candidates] != list(ctx.cfg["matrix_contract"]["candidate_ids"])
        or _matrix_digest(matrix) != ctx.cfg["matrix_contract"]["canonical_matrix_float64_le_c_sha256"]
    ):
        raise SourceBlockedError("R8R49 R8R31 candidate matrix changed")
    source_r8r7 = r8r9._authenticate_r8r7(_source_stage(ctx), ctx.r8r22_ctx.cfg)
    lineage = {
        "r8": r8r7._authenticate_r8(ctx.source_ctx),
        "r8r1": r8r7._authenticate_r8r1(ctx.source_ctx),
        "r8r6": r8r7._authenticate_r8r6(ctx.source_ctx),
    }
    return {
        "r8r48_hashes": hashes,
        "r8r48_route": contract["required_route"],
        "r8r7": source_r8r7,
        "lineage": lineage,
        "candidate_matrix_digest": _matrix_digest(matrix),
        "passed": True,
    }


def build_specs(ctx: Context) -> list[dict[str, Any]]:
    baselines, _ = _source_baselines(ctx)
    source_cfg = ctx.r8r48_ctx.source_ctx.cfg
    candidates = r8r31._candidate_rows(source_cfg)[1:]
    matrix = np.asarray(source_cfg["candidate_contract"]["canonical_matrix_columns"], dtype=float)
    rows: list[dict[str, Any]] = []
    for context_index, source in enumerate(baselines):
        for candidate in candidates:
            q = np.asarray(candidate["q"], dtype=float)
            requested = matrix @ q
            spec = copy.deepcopy(source)
            spec.update(
                {
                    "kind": "stage4_2r3c3t13s24d1r14r8r49_q0_transport_bridge",
                    "stage": STAGE,
                    "campaign_identity": IDENTITY,
                    "controller_revision": CONTROLLER_REVISION,
                    "experiment_id": f"r8r49_c{context_index:02d}_k{int(candidate['index']):02d}_{candidate['id']}",
                    "source_r8r7_baseline_experiment_id": str(source["experiment_id"]),
                    "r8r49_context_index": context_index,
                    "r8r49_candidate_index": int(candidate["index"]),
                    "r8r49_candidate_id": str(candidate["id"]),
                    "r8r49_candidate_q": q.tolist(),
                    "r8r49_requested_coordinate": requested.tolist(),
                    "r8r49_q0_issue_task_step": Q0_STEP,
                    "r8r49_candidate_issue_task_step": ISSUE_STEP,
                    "r8r49_first_effect_state_step": FIRST_EFFECT_STATE,
                    "r8r49_second_effect_state_step": SECOND_EFFECT_STATE,
                    "r8r49_return_task_step": RETURN_STEP,
                    "r8r49_allowed_in_expert_dataset": False,
                    "pair_or_history_label_available_to_controller": False,
                    "source_result_available_to_controller": False,
                    "future_measurement_count": 0,
                    "future_action_count": 0,
                    "formal_timing_unchanged": True,
                }
            )
            rows.append(spec)
    coverage = {
        (str(row["pair_id"]), str(row["history_member"]), int(row["r8r49_candidate_index"]))
        for row in rows
    }
    if len(rows) != 256 or len(coverage) != 256 or len({row["experiment_id"] for row in rows}) != 256:
        raise ValueError("R8R49 frozen specification matrix changed")
    return rows


def _payload(ctx: Context, spec: Mapping[str, Any]) -> dict[str, Any]:
    payload = r8r7.r8._payload(_execution_context(ctx), spec)
    experiment_id = str(spec["experiment_id"])
    payload.update(
        {
            "variant_id": f"stage4_2r3c3t13s24d1r14r8r49_{experiment_id}",
            "stage4_2r3c3t13s24d1r14r8r49_candidate_id": str(spec["r8r49_candidate_id"]),
            "stage4_2r3c3t13s24d1r14r8r49_pair_history_label_available_to_controller": False,
        }
    )
    _write(ctx.paths.variants / f"payload_{experiment_id}.json", payload)
    return payload


def _current_utilization(currents: Sequence[float], actuator: Any) -> float:
    minimum = np.asarray(actuator.minimum_current_a_tsc, dtype=float)
    maximum = np.asarray(actuator.maximum_current_a_tsc, dtype=float)
    center, half = 0.5 * (minimum + maximum), 0.5 * (maximum - minimum)
    return float(np.max(np.abs((np.asarray(currents, dtype=float) - center) / half)))


def _observe_event(*, task_step: int, currents: np.ndarray, target_fields: Sequence[str], actuator: Any, contract: Mapping[str, Any], event: str) -> dict[str, Any]:
    applied = actuator.apply(currents, np.zeros(N_COILS, dtype=float))
    utilization = _current_utilization(applied.nominal_readback_current_a_tsc, actuator)
    criteria = {
        "finite": bool(np.all(np.isfinite(currents))),
        "zero_action": True,
        "target_exact": list(applied.card15_fields) == list(map(str, target_fields)),
        "no_saturation": not any(applied.action_saturated),
        "no_current_clip": not any(applied.current_limit_clipped),
        "current_utilization": utilization <= float(contract["maximum_current_utilization"]) + 1e-12,
    }
    return {
        "event": event,
        "task_step": int(task_step),
        "stored_target_card15_fields": list(map(str, target_fields)),
        "action_norm_tsc": [0.0] * N_COILS,
        "nominal_readback_current_a_tsc": list(map(float, applied.nominal_readback_current_a_tsc)),
        "predicted_current_utilization": utilization,
        "incremental_normalized_action_linf": 0.0,
        "criteria": criteria,
        "passed": bool(all(criteria.values())),
    }


def _return_event(*, task_step: int, currents: np.ndarray, center_fields: Sequence[str], issue_event: Mapping[str, Any], field_basis: np.ndarray, actuator: Any, lattice: Mapping[str, Any], contract: Mapping[str, Any]) -> dict[str, Any]:
    event = r8r22._refresh_event(
        task_step=task_step,
        currents=currents,
        target_fields=center_fields,
        actuator=actuator,
        turns_tsc=actuator.turns_tsc,
        max_delta_a=actuator.max_slew_step_a,
        minimum_current=actuator.minimum_current_a_tsc,
        maximum_current=actuator.maximum_current_a_tsc,
        lattice_cfg=lattice,
        contract=contract,
    )
    returned = np.asarray(event["nominal_readback_current_a_tsc"], dtype=float)
    center_current = np.asarray(issue_event["center_nominal_readback_current_a_tsc"], dtype=float)
    desired = center_current - currents
    actual = returned - currents
    turns = np.asarray(actuator.turns_tsc, dtype=float)
    current_basis = np.asarray(field_basis, dtype=float) * 1000.0 / turns[:, None]
    coordinate = np.linalg.lstsq(current_basis, actual, rcond=None)[0]
    reconstructed = current_basis @ coordinate
    cosine = float(np.dot(desired, actual) / max(np.linalg.norm(desired) * np.linalg.norm(actual), 1e-300))
    off_basis = float(np.linalg.norm(actual - reconstructed) / max(np.linalg.norm(actual), 1e-300))
    event["event"] = "stored_pretransport_center_return"
    event["stored_center_card15_fields"] = list(map(str, center_fields))
    event["issue_target_card15_fields"] = list(issue_event["target_card15_fields"])
    event["desired_applied_current_cosine"] = cosine
    event["relative_off_basis_residual"] = off_basis
    event["criteria"].update(
        {
            "stored_center_reproduced": list(event["stored_target_card15_fields"]) == list(map(str, center_fields)),
            "cosine": cosine >= float(contract["minimum_desired_applied_current_cosine"]) - 1e-12,
            "off_basis": off_basis <= float(contract["maximum_relative_off_basis_residual"]) + 1e-12,
        }
    )
    event["passed"] = bool(all(event["criteria"].values()))
    return event


def _offline_construction(ctx: Context, specs: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    _, sources = _source_baselines(ctx)
    execution = _execution_context(ctx)
    lattice = execution.d1r11_ctx.base_ctx.base_ctx.cfg["lattice_probe"]
    contract = copy.deepcopy(ctx.cfg["controller_contract"])
    contract["dynamic_exact_search_radius"] = int(ctx.cfg["schedule_contract"]["dynamic_exact_search_radius"])
    rows = []
    for spec in specs:
        source = sources[str(spec["source_r8r7_baseline_experiment_id"])]
        payload = _read(ctx.paths.variants / f"payload_{spec['experiment_id']}.json")
        actuator = r8r22.mpc.actuator_from_payload(payload, lattice)
        field_basis = r8r22._fixed_basis(source)
        current = np.asarray(source["trajectory"][Q0_STEP]["currents_a_tsc"], dtype=float)
        center = actuator.apply(current, np.zeros(N_COILS, dtype=float))
        q0 = r8r22._refresh_event(
            task_step=Q0_STEP, currents=current, target_fields=center.card15_fields,
            actuator=actuator, turns_tsc=actuator.turns_tsc,
            max_delta_a=actuator.max_slew_step_a,
            minimum_current=actuator.minimum_current_a_tsc,
            maximum_current=actuator.maximum_current_a_tsc,
            lattice_cfg=lattice, contract=contract,
        )
        current = np.asarray(q0["nominal_readback_current_a_tsc"], dtype=float)
        observe_q0 = _observe_event(
            task_step=11, currents=current, target_fields=center.card15_fields,
            actuator=actuator, contract=contract, event="q0_observe_hold",
        )
        current = np.asarray(observe_q0["nominal_readback_current_a_tsc"], dtype=float)
        issue = r8r22._construct_coordinate_issue(
            task_step=ISSUE_STEP,
            currents_a_tsc=current,
            fixed_basis_delta_field_kat_tsc=field_basis.T,
            requested_coordinate=spec["r8r49_requested_coordinate"],
            candidate_id=str(spec["r8r49_candidate_id"]),
            actuator=actuator,
            controller_cfg=contract,
            lattice_cfg=lattice,
        )
        issue["center_nominal_readback_current_a_tsc"] = current.tolist()
        current = np.asarray(issue["nominal_issue_readback_current_a_tsc"], dtype=float)
        observe_candidate = _observe_event(
            task_step=13, currents=current, target_fields=issue["target_card15_fields"],
            actuator=actuator, contract=contract, event="candidate_observe_hold",
        )
        current = np.asarray(observe_candidate["nominal_readback_current_a_tsc"], dtype=float)
        returned = _return_event(
            task_step=RETURN_STEP, currents=current, center_fields=center.card15_fields,
            issue_event=issue, field_basis=field_basis, actuator=actuator,
            lattice=lattice, contract=contract,
        )
        current = np.asarray(returned["nominal_readback_current_a_tsc"], dtype=float)
        refresh_pass = True
        refresh_max = 0.0
        for step in range(RETURN_STEP + 1, int(spec["horizon_steps"])):
            refresh = r8r22._refresh_event(
                task_step=step, currents=current, target_fields=center.card15_fields,
                actuator=actuator, turns_tsc=actuator.turns_tsc,
                max_delta_a=actuator.max_slew_step_a,
                minimum_current=actuator.minimum_current_a_tsc,
                maximum_current=actuator.maximum_current_a_tsc,
                lattice_cfg=lattice, contract=contract,
            )
            refresh_pass = refresh_pass and bool(refresh["passed"])
            refresh_max = max(refresh_max, float(refresh["incremental_normalized_action_linf"]))
            current = np.asarray(refresh["nominal_readback_current_a_tsc"], dtype=float)
        criteria = {
            "q0": bool(q0["passed"]),
            "q0_observe": bool(observe_q0["passed"]),
            "candidate": bool(issue["passed"]),
            "candidate_observe": bool(observe_candidate["passed"]),
            "return": bool(returned["passed"]),
            "later_refresh": bool(refresh_pass),
            "candidate_identity": issue.get("candidate_id") == spec["r8r49_candidate_id"],
            "candidate_coordinate": bool(np.array_equal(
                np.asarray(issue.get("requested_coordinate"), dtype=float),
                np.asarray(spec["r8r49_requested_coordinate"], dtype=float),
            )),
        }
        rows.append(
            {
                "experiment_id": spec["experiment_id"],
                "pair_id": spec["pair_id"],
                "history_member": spec["history_member"],
                "candidate_index": spec["r8r49_candidate_index"],
                "candidate_id": spec["r8r49_candidate_id"],
                "issue_increment": issue["incremental_normalized_action_linf"],
                "return_increment": returned["incremental_normalized_action_linf"],
                "maximum_refresh_increment": refresh_max,
                "maximum_predicted_current_utilization": max(
                    float(q0["predicted_current_utilization"]),
                    float(issue["predicted_current_utilization"]),
                    float(returned["predicted_current_utilization"]),
                ),
                "criteria": criteria,
                "passed": bool(all(criteria.values())),
            }
        )
    return {
        "construction_count": len(rows),
        "construction_pass_count": sum(bool(row["passed"]) for row in rows),
        "maximum_issue_increment": max(float(row["issue_increment"]) for row in rows),
        "maximum_return_increment": max(float(row["return_increment"]) for row in rows),
        "maximum_refresh_increment": max(float(row["maximum_refresh_increment"]) for row in rows),
        "maximum_predicted_current_utilization": max(float(row["maximum_predicted_current_utilization"]) for row in rows),
        "rows": rows,
        "passed": len(rows) == 256 and all(bool(row["passed"]) for row in rows),
    }


def _set_state(ctx: Context, **updates: Any) -> dict[str, Any]:
    state = _read(ctx.paths.state)
    state.update(updates)
    _write(ctx.paths.state, state)
    return state


def prepare_offline(ctx: Context) -> dict[str, Any]:
    if ctx.paths.stage.exists():
        raise ValueError("R8R49 offline requires a fresh run identity")
    for path in (ctx.paths.stage, ctx.paths.variants, ctx.paths.specs, ctx.paths.source_reference, ctx.paths.raw, ctx.paths.analysis):
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
        package = r8r7._package_fingerprint()
        manifest = {
            "schema_version": 1,
            "stage": STAGE,
            "identity": IDENTITY,
            "controller_revision": CONTROLLER_REVISION,
            "package_revision": ctx.cfg["package_revision"],
            "config_sha256": _sha(ctx.config_path),
            "design_document_sha256": ctx.cfg["design_document_sha256"],
            "source_r8r48_run": str(ctx.r8r48_stage.parent),
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
            "schema_version": 1,
            "stage": STAGE,
            "phase_status": "offline_primary_ready" if passed else "offline_failed",
            "finished": not passed,
            "real_tsc_executed": False,
            "plant_step_count": 0,
            "new_raw_count": 0,
            "response_outcomes_opened": False,
            "spec_digest": manifest["spec_digest"],
            "package_digest": package["digest"],
            "route": route,
            "verdict": {"route": route, "passed": passed},
            "stop_reason": "" if passed else "offline_action_construction_failed",
        }
        _write(ctx.paths.state, state)
        report = {
            "schema_version": 1,
            "stage": STAGE,
            "phase": "offline_primary",
            "source_authenticated": True,
            "spec_count": len(specs),
            "construction_count": construction["construction_count"],
            "construction_pass_count": construction["construction_pass_count"],
            "maximum_issue_increment": construction["maximum_issue_increment"],
            "maximum_return_increment": construction["maximum_return_increment"],
            "maximum_predicted_current_utilization": construction["maximum_predicted_current_utilization"],
            "new_raw_count": 0,
            "plant_step_count": 0,
            "real_tsc_executed": False,
            "route": route,
            "passed": passed,
        }
    except SourceBlockedError as exc:
        route = ctx.cfg["routes"]["source_blocked"]
        report = {
            "schema_version": 1, "stage": STAGE, "phase": "offline_primary",
            "source_authenticated": False, "spec_count": 0, "construction_count": 0,
            "construction_pass_count": 0, "new_raw_count": 0, "plant_step_count": 0,
            "real_tsc_executed": False, "route": route, "passed": False,
            "failure_reason": repr(exc),
        }
        _write(ctx.paths.manifest, {"schema_version": 1, "stage": STAGE, "source_blocked": True})
        _write(ctx.paths.state, {
            "schema_version": 1, "stage": STAGE, "phase_status": "source_blocked",
            "finished": True, "real_tsc_executed": False, "plant_step_count": 0,
            "new_raw_count": 0, "route": route, "verdict": {"route": route, "passed": False},
            "stop_reason": "source_authentication_failed",
        })
    _write(ctx.paths.analysis / "offline_primary.json", report)
    return report


def _saved_specs(ctx: Context) -> list[dict[str, Any]]:
    specs = _read(ctx.paths.specs / "all_specs.json")
    manifest = _read(ctx.paths.manifest)
    if len(specs) != 256 or _digest(specs) != manifest.get("spec_digest") or _sha(ctx.config_path) != manifest.get("config_sha256"):
        raise ValueError("R8R49 saved specification identity changed")
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
        raise ValueError("R8R49 offline independent authorization gate failed")
    _set_state(
        ctx,
        phase_status="real_authorized",
        offline_independent_sha256=_sha(ctx.paths.analysis / "offline_independent.json"),
    )
    return {"stage": STAGE, "phase": "real_authorized", "passed": True}


class BridgeController(r6.d1r11.SequentialAmplitudeCodedProbeController):
    """Exact q0 hold, one fixed transport issue, exact center return, and hold."""

    def __init__(self, base: Any, bundle: Mapping[str, Any], source_spec: Mapping[str, Any], initial_state: Mapping[str, Any], lattice_cfg: Mapping[str, Any], calibration_cfg: Mapping[str, Any], dynamic_cfg: Mapping[str, Any], schedule_cfg: Mapping[str, Any], controller_cfg: Mapping[str, Any], *, spec: Mapping[str, Any]):
        matrix = np.asarray(controller_cfg["requested_coordinate_matrix_columns"], dtype=float)
        prepared = r6._controller_source_spec(source_spec, schedule_cfg)
        super().__init__(
            base, bundle, prepared, initial_state, lattice_cfg, calibration_cfg,
            dynamic_cfg, schedule_cfg,
        )
        if matrix.shape != (4, 4):
            raise ValueError("R8R49 canonical matrix shape changed")
        self.r8r49_candidate_id = str(spec["r8r49_candidate_id"])
        self.r8r49_requested_coordinate = np.asarray(spec["r8r49_requested_coordinate"], dtype=float)
        self.r8r49_contract = copy.deepcopy(dict(controller_cfg))
        self.r8r49_center_fields: list[str] | None = None
        self.r8r49_center_current: list[float] | None = None
        self.r8r49_issue_event: dict[str, Any] | None = None

    def _q0(self, currents: np.ndarray) -> tuple[np.ndarray, dict[str, Any]]:
        self._freeze_fixed_basis(currents, np.zeros(N_COILS, dtype=float))
        center = self.actuator.apply(currents, np.zeros(N_COILS, dtype=float))
        event = r8r22._refresh_event(
            task_step=self.step, currents=currents, target_fields=center.card15_fields,
            actuator=self.actuator, turns_tsc=self.turns_tsc,
            max_delta_a=float(self.base.max_delta_a), minimum_current=self.base.min_current,
            maximum_current=self.base.max_current, lattice_cfg=self.lattice_cfg,
            contract=self.r8r49_contract,
        )
        event["event"] = "q0_exact_current_target_issue"
        event["q0_center_card15_fields"] = list(center.card15_fields)
        event["criteria"]["q0_zero_target"] = bool(np.array_equal(np.asarray(event["action_norm_tsc"]), np.zeros(N_COILS)))
        event["passed"] = bool(all(event["criteria"].values()))
        if not event["passed"]:
            raise ValueError("R8R49 q0 action safety gate failed: " + json.dumps(event, sort_keys=True))
        self.r8r49_center_fields = list(center.card15_fields)
        self.r8r49_center_current = list(map(float, event["nominal_readback_current_a_tsc"]))
        return np.asarray(event["action_norm_tsc"], dtype=float), event

    def _issue_candidate(self, currents: np.ndarray) -> tuple[np.ndarray, dict[str, Any]]:
        field_basis, _ = self._basis_current()
        event = r8r22._construct_coordinate_issue(
            task_step=self.step, currents_a_tsc=currents,
            fixed_basis_delta_field_kat_tsc=field_basis.T,
            requested_coordinate=self.r8r49_requested_coordinate,
            candidate_id=self.r8r49_candidate_id, actuator=self.actuator,
            controller_cfg=self.r8r49_contract, lattice_cfg=self.lattice_cfg,
        )
        event["center_nominal_readback_current_a_tsc"] = list(self.r8r49_center_current or [])
        if not event["passed"]:
            raise ValueError("R8R49 candidate action safety gate failed: " + json.dumps(event, sort_keys=True))
        self.r8r49_issue_event = copy.deepcopy(event)
        self._active_issue = copy.deepcopy(event)
        return np.asarray(event["action_norm_tsc"], dtype=float), event

    def _return(self, currents: np.ndarray) -> tuple[np.ndarray, dict[str, Any]]:
        if self.r8r49_center_fields is None or self.r8r49_issue_event is None:
            raise ValueError("R8R49 return has no causal stored center/issue")
        field_basis, _ = self._basis_current()
        event = _return_event(
            task_step=self.step, currents=currents,
            center_fields=self.r8r49_center_fields, issue_event=self.r8r49_issue_event,
            field_basis=field_basis, actuator=self.actuator, lattice=self.lattice_cfg,
            contract=self.r8r49_contract,
        )
        if not event["passed"]:
            raise ValueError("R8R49 return action safety gate failed: " + json.dumps(event, sort_keys=True))
        self._active_issue = None
        return np.asarray(event["action_norm_tsc"], dtype=float), event

    def _center_refresh(self, currents: np.ndarray) -> tuple[np.ndarray, dict[str, Any]]:
        if self.r8r49_center_fields is None:
            raise ValueError("R8R49 center refresh has no stored center")
        event = r8r22._refresh_event(
            task_step=self.step, currents=currents, target_fields=self.r8r49_center_fields,
            actuator=self.actuator, turns_tsc=self.turns_tsc,
            max_delta_a=float(self.base.max_delta_a), minimum_current=self.base.min_current,
            maximum_current=self.base.max_current, lattice_cfg=self.lattice_cfg,
            contract=self.r8r49_contract,
        )
        event["event"] = "post_return_exact_center_refresh"
        if not event["passed"]:
            raise ValueError("R8R49 refresh action safety gate failed: " + json.dumps(event, sort_keys=True))
        return np.asarray(event["action_norm_tsc"], dtype=float), event

    def action(self, current_state: Mapping[str, Any]) -> tuple[np.ndarray, dict[str, Any]]:
        if int(current_state["step_index"]) != self.step:
            raise ValueError("R8R49 controller/current state index mismatch")
        if self.step < PREFIX_END:
            action, trace = super().action(current_state)
            event_name, event = "none", {}
            delegated = True
        else:
            currents = np.asarray(current_state["currents_a_tsc"], dtype=float)
            delegated = False
            if self.step == Q0_STEP:
                action, event = self._q0(currents)
                event_name = "q0_exact_issue"
            elif self.step == 11:
                event = _observe_event(
                    task_step=self.step, currents=currents,
                    target_fields=self.r8r49_center_fields or [], actuator=self.actuator,
                    contract=self.r8r49_contract, event="q0_observe_hold",
                )
                action, event_name = np.zeros(N_COILS), "q0_observe_hold"
            elif self.step == ISSUE_STEP:
                action, event = self._issue_candidate(currents)
                event_name = "candidate_issue"
            elif self.step == 13:
                if self.r8r49_issue_event is None:
                    raise ValueError("R8R49 candidate observation has no issue")
                event = _observe_event(
                    task_step=self.step, currents=currents,
                    target_fields=self.r8r49_issue_event["target_card15_fields"],
                    actuator=self.actuator, contract=self.r8r49_contract,
                    event="candidate_observe_hold",
                )
                action, event_name = np.zeros(N_COILS), "candidate_observe_hold"
            elif self.step == RETURN_STEP:
                action, event = self._return(currents)
                event_name = "stored_center_return"
            else:
                action, event = self._center_refresh(currents)
                event_name = "center_refresh"
            trace = r6._trace_template(self.step, np.asarray(action, dtype=float))
        trace.update(
            {
                "action_norm_tsc": np.asarray(action, dtype=float).tolist(),
                "r3c3t13s24d1r14r8r49_controller_revision": CONTROLLER_REVISION,
                "r3c3t13s24d1r14r8r49_delegated_prefix": delegated,
                "r3c3t13s24d1r14r8r49_event": event_name,
                "r3c3t13s24d1r14r8r49_event_detail": copy.deepcopy(event),
                "r3c3t13s24d1r14r8r49_forbidden_input_used": False,
                "r3c3t13s24d1r14r8r49_pair_or_history_label_used": False,
                "r3c3t13s24d1r14r8r49_future_measurement_used": False,
                "r3c3t13s24d1r14r8r49_future_action_used": False,
                "r3c3t13s24d1r14r8r49_source_result_used": False,
                "r3c3t13s24d1r14r8r49_hidden_wire_used": False,
            }
        )
        return np.asarray(action, dtype=float), trace


class LocalWorker:
    def __init__(self, payload: dict[str, Any], library: dict[str, Any], bundle: dict[str, Any], worker_id: str, selector: dict[str, Any], lattice_cfg: dict[str, Any], calibration_cfg: dict[str, Any], dynamic_cfg: dict[str, Any], schedule_cfg: dict[str, Any], controller_cfg: dict[str, Any]):
        self.plant = r8r7.r8.d1r11.s21.s16.s9.t11.t1.r1.LocalPlantReplayWorker(payload, library, bundle, worker_id, selector)
        self.base = self.plant.base_worker
        self.bundle = bundle
        self.lattice_cfg = lattice_cfg
        self.calibration_cfg = calibration_cfg
        self.dynamic_cfg = dynamic_cfg
        self.schedule_cfg = schedule_cfg
        self.controller_cfg = controller_cfg

    def close(self) -> None:
        self.plant.close()

    def evaluate(self, spec: dict[str, Any]) -> dict[str, Any]:
        started = time.time()
        failed = True
        trajectory: list[dict[str, Any]] = []
        trace: list[dict[str, Any]] = []
        result: dict[str, Any] = {
            "schema_version": 1, "stage": STAGE, "campaign_identity": IDENTITY,
            "controller_revision": CONTROLLER_REVISION, "experiment_id": spec["experiment_id"],
            "spec": copy.deepcopy(spec), "success": False, "completed": False,
            "failure_reason": "", "execution_failure_class": "",
            "trajectory": trajectory, "controller_trace": trace,
        }
        try:
            horizon = int(spec["horizon_steps"])
            if horizon != int(spec["formal_horizon_steps"]) or horizon != int(self.base.env.max_episode_steps) or horizon not in (35, 37):
                raise ValueError("R8R49 formal horizon changed")
            self.base.env.reset()
            zero = np.zeros(N_COILS, dtype=np.float32)
            trajectory.append(r8r7.r8.d1r11.s21.s16.s9.t11.t1.r1._state_record_full(self.base.env, 0, zero))
            controller = BridgeController(
                self.base, self.bundle, spec, trajectory[0], self.lattice_cfg,
                self.calibration_cfg, self.dynamic_cfg, self.schedule_cfg,
                self.controller_cfg, spec=spec,
            )
            for step in range(horizon):
                current = trajectory[-1]
                finite = all(math.isfinite(float(current[key])) for key in ("R", "Z", "Ip")) and np.all(np.isfinite(np.asarray(current["currents_a_tsc"], dtype=float)))
                if not finite or bool(current.get("abnormal")):
                    result["execution_failure_class"] = "pre_action_visible_state_safety_failure"
                    raise ValueError("R8R49 pre-action visible state safety gate failed")
                try:
                    action, row = controller.action(current)
                except ValueError as exc:
                    if "safety gate failed" in str(exc):
                        result["execution_failure_class"] = "controller_action_safety_gate_failure"
                    raise
                _, _, terminated, truncated, info = self.base.env.step(action)
                next_state = r8r7.r8.d1r11.s21.s16.s9.t11.t1.r1._state_record_full(self.base.env, step + 1, action)
                trajectory.append(next_state)
                trace.append(row)
                controller.advance(next_state)
                if terminated:
                    result["execution_failure_class"] = "plant_abnormal_termination"
                    raise RuntimeError(str(info.get("failure_reason", "environment terminated")))
                if truncated and step + 1 < horizon:
                    result["execution_failure_class"] = "plant_early_truncation"
                    raise RuntimeError("environment truncated before R8R49 horizon")
            names = [row.get("r3c3t13s24d1r14r8r49_event") for row in trace[PREFIX_END:]]
            event_pass = all(bool((row.get("r3c3t13s24d1r14r8r49_event_detail") or {}).get("passed")) for row in trace[PREFIX_END:])
            first_effect = bool(
                np.array_equal(np.asarray(trajectory[FIRST_EFFECT_STATE]["action_norm_tsc"]), np.asarray(trace[ISSUE_STEP]["action_norm_tsc"]))
                and not np.array_equal(np.asarray(trajectory[FIRST_EFFECT_STATE]["currents_a_tsc"]), np.asarray(trajectory[ISSUE_STEP]["currents_a_tsc"]))
            )
            success = bool(
                len(trajectory) == horizon + 1 and len(trace) == horizon
                and r8r7.r8.r4._calibration_exact(trace)
                and all(bool(row.get("r3c3t13s24d1r14r8r49_delegated_prefix")) for row in trace[:PREFIX_END])
                and names[:5] == ["q0_exact_issue", "q0_observe_hold", "candidate_issue", "candidate_observe_hold", "stored_center_return"]
                and all(name == "center_refresh" for name in names[5:])
                and event_pass and first_effect and controller._active_issue is None
                and not any(bool(row.get("abnormal")) for row in trajectory)
            )
            result.update(
                {
                    "success": success, "completed": True,
                    "failure_reason": "" if success else "incomplete or invalid R8R49 rollout",
                    "execution_failure_class": "" if success else "controller_or_action_semantics_error",
                    "hidden_history_control_summary": {
                        "fresh_controller_actor": True, "fresh_tsc_process": True,
                        "full_tsc_hidden_state_loaded_from_sprsina": True,
                        "future_r17_controller_executed": False,
                        "formal_tracking_diagnostic_only": True,
                        "stage_trajectory_allowed_in_expert_dataset": False,
                        "future_action_replay_used": False, "future_measurement_used": False,
                        "pair_or_history_label_used": False, "source_result_used": False,
                    },
                    "wall_time_s": time.time() - started,
                }
            )
            failed = not success
            return r8r7.r8.d1r11.s21.s16.s9.t11.t1._json_safe(result)
        except Exception as exc:
            result.update(
                {
                    "success": False, "completed": True, "failure_reason": repr(exc),
                    "execution_failure_class": str(result.get("execution_failure_class") or "runtime_or_controller_error"),
                    "trajectory": trajectory, "controller_trace": trace,
                    "traceback": traceback.format_exc(), "wall_time_s": time.time() - started,
                }
            )
            return r8r7.r8.d1r11.s21.s16.s9.t11.t1._json_safe(result)
        finally:
            runner = getattr(self.base.env, "runner", None)
            if runner is not None:
                runner.cleanup_episode_workspace(failed=failed, reason="stage4_2r3c3t13s24d1r14r8r49")


_RAY_ACTOR = None


def _ray_actor_class():
    global _RAY_ACTOR
    if _RAY_ACTOR is None:
        import ray

        @ray.remote(num_cpus=1, max_restarts=0)
        class R8R49Actor:
            def __init__(self, *args: Any):
                self.worker = LocalWorker(*args)

            def evaluate(self, spec: dict[str, Any]) -> dict[str, Any]:
                return self.worker.evaluate(spec)

            def close(self) -> bool:
                self.worker.close()
                return True

        _RAY_ACTOR = R8R49Actor
    return _RAY_ACTOR


def _result_complete(path: Path, spec: Mapping[str, Any], *, require_success: bool = True) -> bool:
    if not path.is_file():
        return False
    try:
        result = r8r7.r8._read_gz(path)
        horizon = int(spec["horizon_steps"])
        return bool(
            result.get("completed") and (result.get("success") or not require_success)
            and result.get("stage") == STAGE and result.get("campaign_identity") == IDENTITY
            and result.get("controller_revision") == CONTROLLER_REVISION
            and result.get("experiment_id") == spec["experiment_id"]
            and result.get("spec") == dict(spec)
            and (not require_success or (len(result.get("trajectory") or []) == horizon + 1 and len(result.get("controller_trace") or []) == horizon))
        )
    except Exception:
        return False


def evaluate_specs(ctx: Context, specs: Sequence[dict[str, Any]], *, backend: str, resume: bool) -> dict[str, Any]:
    pending = [spec for spec in specs if not (resume and _result_complete(ctx.paths.raw / f"{spec['experiment_id']}.json.gz", spec, require_success=False))]
    payloads = {str(spec["experiment_id"]): _payload(ctx, spec) for spec in specs}
    execution = _execution_context(ctx)
    library, bundle, selector = r8r7.r8.d1r11._library_bundle_selector(execution.d1r11_ctx)
    lattice = execution.d1r11_ctx.base_ctx.base_ctx.cfg["lattice_probe"]
    calibration = execution.d1r11_ctx.base_ctx.base_ctx.cfg["active_calibration"]
    dynamic = execution.d1r11_ctx.base_ctx.cfg["causal_model"]
    schedule_cfg = execution.d1r11_ctx.cfg["schedule_contract"]
    controller_cfg = copy.deepcopy(ctx.cfg["controller_contract"])
    source_cfg = ctx.r8r48_ctx.source_ctx.cfg
    controller_cfg.update(
        {
            "dynamic_exact_search_radius": int(ctx.cfg["schedule_contract"]["dynamic_exact_search_radius"]),
            "requested_coordinate_matrix_columns": copy.deepcopy(source_cfg["candidate_contract"]["canonical_matrix_columns"]),
            "requested_matrix_float64_le_c_sha256": str(source_cfg["candidate_contract"]["canonical_matrix_float64_le_c_sha256"]),
        }
    )

    def args_for(spec: Mapping[str, Any], index: int) -> tuple[Any, ...]:
        return (payloads[str(spec["experiment_id"])], library, bundle, f"stage42r8r49_{index:03d}", selector, lattice, calibration, dynamic, schedule_cfg, controller_cfg)

    if backend == "serial":
        for index, spec in enumerate(pending):
            worker = LocalWorker(*args_for(spec, index))
            try:
                result = worker.evaluate(spec)
            finally:
                worker.close()
            r8r7.r8._write_gz(ctx.paths.raw / f"{spec['experiment_id']}.json.gz", result)
            print(f"[R8R49] {index + 1}/{len(pending)}", flush=True)
    elif backend == "ray" and pending:
        import ray

        plan = r8r7.r8.d1r11.s21.s16.ensure_ray_worker_plan(
            ray, requested_workers=int(ctx.cfg["parallel"]["n_workers"]),
            pending_tasks=len(pending),
            ray_tmpdir=os.environ.get("RAY_TMPDIR") or ctx.cfg["storage"]["ray_tmpdir"],
            log_prefix="[R8R49]",
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
                        print(f"[R8R49] waiting {completed}/{len(pending)}", flush=True)
                        continue
                    ref = ready[0]
                    spec = refs.pop(ref)
                    try:
                        result = ray.get(ref)
                    except Exception as exc:
                        result = {
                            "schema_version": 1, "stage": STAGE, "campaign_identity": IDENTITY,
                            "controller_revision": CONTROLLER_REVISION, "experiment_id": spec["experiment_id"],
                            "spec": copy.deepcopy(spec), "success": False, "completed": True,
                            "failure_reason": repr(exc), "execution_failure_class": "ray_actor_runtime_error",
                            "trajectory": [], "controller_trace": [], "traceback": traceback.format_exc(),
                        }
                    r8r7.r8._write_gz(ctx.paths.raw / f"{spec['experiment_id']}.json.gz", result)
                    completed += 1
                    print(f"[R8R49] {completed}/{len(pending)}", flush=True)
            finally:
                close_refs = [actor.close.remote() for actor in actors]
                if close_refs:
                    ray.get(close_refs, timeout=float(ctx.cfg["storage"]["actor_close_timeout_s"]))
                for actor in actors:
                    ray.kill(actor, no_restart=True)
    elif backend not in {"serial", "ray"}:
        raise ValueError(f"unsupported R8R49 backend: {backend}")
    completed = sum(_result_complete(ctx.paths.raw / f"{spec['experiment_id']}.json.gz", spec, require_success=False) for spec in specs)
    successful = sum(_result_complete(ctx.paths.raw / f"{spec['experiment_id']}.json.gz", spec) for spec in specs)
    return {"expected": len(specs), "pending_at_start": len(pending), "completed": completed, "successful": successful, "passed": completed == len(specs)}


def _prefix_payload(result: Mapping[str, Any]) -> dict[str, Any]:
    trajectory = result["trajectory"]
    trace = result["controller_trace"]
    return {
        "states": [r8r7.r8.r4._semantic_state(row) for row in trajectory[:13]],
        "trace": trace[:12],
    }


FORBIDDEN_KEYS = (
    "r3c3t13s24d1r14r8r49_forbidden_input_used",
    "r3c3t13s24d1r14r8r49_pair_or_history_label_used",
    "r3c3t13s24d1r14r8r49_future_measurement_used",
    "r3c3t13s24d1r14r8r49_future_action_used",
    "r3c3t13s24d1r14r8r49_source_result_used",
    "r3c3t13s24d1r14r8r49_hidden_wire_used",
)


def audit_raw(ctx: Context, *, write: bool = True) -> dict[str, Any]:
    specs = _saved_specs(ctx)
    _, sources = _source_baselines(ctx)
    source_cfg = ctx.r8r48_ctx.source_ctx.cfg
    matrix = np.asarray(source_cfg["candidate_contract"]["canonical_matrix_columns"], dtype=float)
    rows = []
    prefix_by_context: dict[tuple[str, str], list[str]] = {}
    contract = ctx.cfg["controller_contract"]
    for spec in specs:
        path = ctx.paths.raw / f"{spec['experiment_id']}.json.gz"
        result = r8r7.r8._read_gz(path) if _result_complete(path, spec, require_success=False) else {}
        trajectory = result.get("trajectory") or []
        trace = result.get("controller_trace") or []
        horizon = int(spec["horizon_steps"])
        full = len(trajectory) == horizon + 1 and len(trace) == horizon
        source = sources[str(spec["source_r8r7_baseline_experiment_id"])]
        restart = bool(full and r8r7.r8.r4._semantic_state(trajectory[0]) == r8r7.r8.r4._semantic_state(source["trajectory"][0]))
        source_prefix_state = bool(full and all(r8r7.r8.r4._semantic_state(current) == r8r7.r8.r4._semantic_state(reference) for current, reference in zip(trajectory[: PREFIX_END + 1], source["trajectory"][: PREFIX_END + 1])))
        source_prefix_trace = bool(full and all(r8r7.r8.r4._source_trace_projection(reference, current) for current, reference in zip(trace[:PREFIX_END], source["controller_trace"][:PREFIX_END])))
        prefix_digest = _digest(_prefix_payload(result)) if full else ""
        prefix_by_context.setdefault((str(spec["pair_id"]), str(spec["history_member"])), []).append(prefix_digest)
        events = [trace[step].get("r3c3t13s24d1r14r8r49_event_detail") or {} for step in range(PREFIX_END, horizon)] if full else []
        names = [trace[step].get("r3c3t13s24d1r14r8r49_event") for step in range(PREFIX_END, horizon)] if full else []
        event_pass = bool(full and all(event.get("passed") is True and all(bool(value) for value in (event.get("criteria") or {}).values()) for event in events))
        q0 = events[0] if len(events) > 0 else {}
        issue = events[2] if len(events) > 2 else {}
        returned = events[4] if len(events) > 4 else {}
        expected_coordinate = matrix @ np.asarray(spec["r8r49_candidate_q"], dtype=float)
        candidate_exact = bool(
            issue.get("candidate_id") == spec["r8r49_candidate_id"]
            and np.array_equal(np.asarray(issue.get("requested_coordinate") or []), expected_coordinate)
            and np.array_equal(expected_coordinate, np.asarray(spec["r8r49_requested_coordinate"], dtype=float))
        )
        q0_exact = bool(
            q0.get("event") == "q0_exact_current_target_issue"
            and q0.get("passed") is True
            and list(q0.get("stored_target_card15_fields") or []) == list(q0.get("q0_center_card15_fields") or [])
        )
        return_exact = bool(
            returned.get("event") == "stored_pretransport_center_return"
            and returned.get("passed") is True
            and returned.get("stored_center_card15_fields") == issue.get("center_card15_fields")
            and returned.get("issue_target_card15_fields") == issue.get("target_card15_fields")
        )
        first_effect = bool(
            full
            and np.array_equal(np.asarray(trajectory[FIRST_EFFECT_STATE]["action_norm_tsc"]), np.asarray(trace[ISSUE_STEP]["action_norm_tsc"]))
            and not np.array_equal(np.asarray(trajectory[FIRST_EFFECT_STATE]["currents_a_tsc"]), np.asarray(trajectory[ISSUE_STEP]["currents_a_tsc"]))
            and np.array_equal(np.asarray(trajectory[ISSUE_STEP]["action_norm_tsc"]), np.asarray(trace[ISSUE_STEP - 1]["action_norm_tsc"]))
        )
        finite_response = bool(full and all(math.isfinite(float(trajectory[step][key])) for step in (FIRST_EFFECT_STATE, SECOND_EFFECT_STATE) for key in ("R", "Z", "Ip")) and all(np.all(np.isfinite(np.asarray(trajectory[step]["currents_a_tsc"]))) for step in (FIRST_EFFECT_STATE, SECOND_EFFECT_STATE)))
        actions = np.asarray([row.get("action_norm_tsc", []) for row in trace], dtype=float)
        currents = np.asarray([row.get("currents_a_tsc", []) for row in trajectory], dtype=float)
        finite = bool(full and actions.shape == (horizon, N_COILS) and currents.shape == (horizon + 1, N_COILS) and np.all(np.isfinite(actions)) and np.all(np.isfinite(currents)) and not any(bool(row.get("abnormal")) for row in trajectory))
        payload = _read(ctx.paths.variants / f"payload_{spec['experiment_id']}.json")
        minimum, maximum = r8r7.r8.d1r11.s21.s13._current_limits_tsc(payload)
        center, half = 0.5 * (minimum + maximum), 0.5 * (maximum - minimum)
        utilization = float(np.max(np.abs((currents - center) / half))) if currents.shape == (horizon + 1, N_COILS) else None
        forbidden = sum(any(bool(row.get(key)) for key in FORBIDDEN_KEYS) for row in trace)
        sequence_exact = bool(
            names[:5] == ["q0_exact_issue", "q0_observe_hold", "candidate_issue", "candidate_observe_hold", "stored_center_return"]
            and all(name == "center_refresh" for name in names[5:])
        )
        safety_limits = bool(
            event_pass
            and float(issue.get("incremental_normalized_action_linf", math.inf)) <= float(contract["maximum_incremental_normalized_action_linf"]) + 1e-12
            and float(returned.get("incremental_normalized_action_linf", math.inf)) <= float(contract["maximum_incremental_normalized_action_linf"]) + 1e-12
            and utilization is not None and utilization <= float(contract["maximum_current_utilization"]) + 1e-12
        )
        source_reference = source["trajectory"]
        response = {
            f"state{step}": {
                "R_Z_Ip": [float(trajectory[step][key]) - float(source_reference[step][key]) for key in ("R", "Z", "Ip")],
                "currents_a_tsc": (np.asarray(trajectory[step]["currents_a_tsc"]) - np.asarray(source_reference[step]["currents_a_tsc"])).tolist(),
            }
            for step in (FIRST_EFFECT_STATE, SECOND_EFFECT_STATE)
        } if finite_response else {}
        passed = bool(
            result.get("success") and full and restart and source_prefix_state and source_prefix_trace
            and r8r7.r8.r4._calibration_exact(trace) and sequence_exact and event_pass
            and q0_exact and candidate_exact and first_effect and finite_response and return_exact
            and finite and forbidden == 0 and safety_limits
        )
        rows.append(
            {
                "experiment_id": spec["experiment_id"], "pair_id": spec["pair_id"],
                "history_member": spec["history_member"],
                "candidate_index": spec["r8r49_candidate_index"],
                "candidate_id": spec["r8r49_candidate_id"],
                "runtime_success": bool(result.get("success")), "full_horizon": full,
                "authentic_restart": restart, "source_prefix_state_exact": source_prefix_state,
                "source_prefix_trace_exact": source_prefix_trace,
                "calibration_exact": bool(full and r8r7.r8.r4._calibration_exact(trace)),
                "q0_exact": q0_exact, "event_sequence_exact": sequence_exact,
                "event_gates_passed": event_pass, "candidate_exact": candidate_exact,
                "first_effect_at_issue_plus_one": first_effect,
                "finite_response": finite_response, "return_exact": return_exact,
                "finite": finite, "forbidden_trace_count": forbidden,
                "maximum_current_utilization": utilization,
                "prefix_digest": prefix_digest, "response": response,
                "execution_failure_class": str(result.get("execution_failure_class") or ""),
                "failure_reason": str(result.get("failure_reason") or ""),
                "passed": passed,
            }
        )
    prefix_exact = {
        key: len(values) == 16 and len(set(values)) == 1 and bool(values[0])
        for key, values in prefix_by_context.items()
    }
    for row in rows:
        row["within_context_q0_prefix_exact"] = bool(prefix_exact[(str(row["pair_id"]), str(row["history_member"]))])
        row["passed"] = bool(row["passed"] and row["within_context_q0_prefix_exact"])
    inventory = r8r7.r8._inventory(ctx.paths.raw)
    safety_stops = sum(row["execution_failure_class"] == "controller_action_safety_gate_failure" for row in rows)
    runtime_failures = sum(bool(row["execution_failure_class"]) and row["execution_failure_class"] != "controller_action_safety_gate_failure" for row in rows)
    passed_count = sum(bool(row["passed"]) for row in rows)
    coverage = len({(row["pair_id"], row["history_member"], row["candidate_index"]) for row in rows if row["passed"]})
    if passed_count == 256 and inventory["count"] == 256 and coverage == 256:
        route = ctx.cfg["routes"]["pass"]
    elif safety_stops > 0 and runtime_failures == 0:
        route = ctx.cfg["routes"]["safety_fail"]
    else:
        route = ctx.cfg["routes"]["execution_fail"]
    response_payload = [
        {"experiment_id": row["experiment_id"], "response": row["response"]}
        for row in rows
    ]
    report = {
        "schema_version": 1, "stage": STAGE, "phase": "raw_primary",
        "raw_inventory": inventory, "expected_raw_count": 256,
        "strict_parse_count": len(rows),
        "runtime_success_count": sum(bool(row["runtime_success"]) for row in rows),
        "full_horizon_count": sum(bool(row["full_horizon"]) for row in rows),
        "authentic_restart_count": sum(bool(row["authentic_restart"]) for row in rows),
        "causal_forbidden_pass_count": sum(int(row["forbidden_trace_count"]) == 0 for row in rows),
        "q0_exact_count": sum(bool(row["q0_exact"]) for row in rows),
        "within_context_q0_prefix_exact_count": sum(bool(row["within_context_q0_prefix_exact"]) for row in rows),
        "candidate_exact_count": sum(bool(row["candidate_exact"]) for row in rows),
        "candidate_issue_gate_pass_count": sum(bool(row["event_gates_passed"]) for row in rows),
        "first_effect_at_issue_plus_one_count": sum(bool(row["first_effect_at_issue_plus_one"]) for row in rows),
        "finite_response_count": sum(bool(row["finite_response"]) for row in rows),
        "stored_center_return_exact_count": sum(bool(row["return_exact"]) for row in rows),
        "bridge_coverage_count": coverage, "passed_count": passed_count,
        "safety_stop_count": safety_stops, "runtime_failure_count": runtime_failures,
        "forbidden_trace_count": sum(int(row["forbidden_trace_count"]) for row in rows),
        "maximum_current_utilization": max((float(row["maximum_current_utilization"]) for row in rows if row["maximum_current_utilization"] is not None), default=None),
        "prefix_digest": _digest(sorted(set(row["prefix_digest"] for row in rows))),
        "response_digest": _digest(response_payload),
        "rows": rows, "route": route,
        "passed": route == ctx.cfg["routes"]["pass"],
    }
    if write:
        _write(ctx.paths.analysis / "raw_primary.json", report)
    return report


def run_real(ctx: Context, *, backend: str, resume: bool) -> dict[str, Any]:
    state = _read(ctx.paths.state)
    if state.get("phase_status") != "real_authorized":
        raise ValueError("R8R49 real execution is not authorized")
    specs = _saved_specs(ctx)
    execution = evaluate_specs(ctx, specs, backend=backend, resume=resume)
    primary = audit_raw(ctx)
    finished = not bool(primary["passed"])
    _set_state(
        ctx,
        phase_status="raw_primary_ready" if primary["passed"] else "real_execution_failed",
        finished=finished,
        real_tsc_executed=True,
        plant_step_count=sum(min(len((r8r7.r8._read_gz(ctx.paths.raw / f"{spec['experiment_id']}.json.gz").get("controller_trace") or [])), int(spec["horizon_steps"])) for spec in specs if (ctx.paths.raw / f"{spec['experiment_id']}.json.gz").is_file()),
        new_raw_count=primary["raw_inventory"]["count"],
        response_outcomes_opened=True,
        route=primary["route"],
        verdict={"route": primary["route"], "passed": bool(primary["passed"])},
        stop_reason="" if primary["passed"] else ("hard_action_or_current_gate_failed" if primary["route"] == ctx.cfg["routes"]["safety_fail"] else "runtime_restart_causality_or_raw_gate_failed"),
    )
    return {"stage": STAGE, "phase": "real", "execution": execution, "raw_primary_passed": primary["passed"], "route": primary["route"]}


def finalize_primary(ctx: Context) -> dict[str, Any]:
    state = _read(ctx.paths.state)
    primary = _read(ctx.paths.analysis / "raw_primary.json")
    independent = _read(ctx.paths.analysis / "raw_independent.json")
    if (
        state.get("phase_status") != "raw_primary_ready"
        or primary.get("passed") is not True
        or independent.get("passed") is not True
        or independent.get("primary_agreement") is not True
    ):
        raise ValueError("R8R49 raw independent gate incomplete")
    detailed = copy.deepcopy(primary)
    detailed["phase"] = "final_primary_detailed"
    _write(ctx.paths.analysis / "primary_detailed.json", detailed)
    summary_keys = (
        "raw_inventory", "strict_parse_count", "runtime_success_count", "full_horizon_count",
        "authentic_restart_count", "causal_forbidden_pass_count", "q0_exact_count",
        "within_context_q0_prefix_exact_count", "candidate_exact_count",
        "candidate_issue_gate_pass_count", "first_effect_at_issue_plus_one_count",
        "finite_response_count", "stored_center_return_exact_count", "bridge_coverage_count",
        "passed_count", "safety_stop_count", "runtime_failure_count", "forbidden_trace_count",
        "maximum_current_utilization", "prefix_digest", "response_digest", "route", "passed",
    )
    summary = {"schema_version": 1, "stage": STAGE, "identity": IDENTITY, **{key: primary[key] for key in summary_keys}}
    summary.update(
        {
            "integrity_gate_passed": True,
            "scientific_gate_passed": True,
            "new_raw_count": 256,
            "real_tsc_executed": True,
            "model_fit_count": 0,
            "formal_tracking_diagnostic_only": True,
            "all_stage_trajectories_allowed_in_expert_dataset": False,
        }
    )
    _write(ctx.paths.analysis / "primary_summary.json", summary)
    _set_state(ctx, phase_status="final_primary_ready", primary_summary_sha256=_sha(ctx.paths.analysis / "primary_summary.json"))
    return summary


def postprocess(ctx: Context) -> dict[str, Any]:
    state = _read(ctx.paths.state)
    summary = _read(ctx.paths.analysis / "primary_summary.json")
    independent = _read(ctx.paths.analysis / "raw_independent.json")
    if state.get("phase_status") != "final_primary_ready" or independent.get("passed") is not True or independent.get("primary_agreement") is not True:
        raise ValueError("R8R49 final independent agreement failed")
    compact = {
        "schema_version": 1, "stage": STAGE, "identity": IDENTITY,
        "source_r8r48_route": ctx.cfg["source_r8r48"]["required_route"],
        "summary": summary,
        "independent_agreement": True,
        "primary_summary_sha256": _sha(ctx.paths.analysis / "primary_summary.json"),
        "primary_detailed_sha256": _sha(ctx.paths.analysis / "primary_detailed.json"),
        "raw_independent_sha256": _sha(ctx.paths.analysis / "raw_independent.json"),
        "stage_manifest_sha256": _sha(ctx.paths.manifest),
        "route": summary["route"], "passed": True,
    }
    _write(ctx.paths.analysis / "compact_audit.json", compact)
    final = copy.deepcopy(summary)
    final.update(
        {
            "phase": "final", "independent_agreement": True,
            "primary_summary_sha256": compact["primary_summary_sha256"],
            "primary_detailed_sha256": compact["primary_detailed_sha256"],
            "raw_independent_sha256": compact["raw_independent_sha256"],
            "compact_audit_sha256": _sha(ctx.paths.analysis / "compact_audit.json"),
            "stage_manifest_sha256": compact["stage_manifest_sha256"],
        }
    )
    _write(ctx.paths.analysis / "final_report.json", final)
    _set_state(
        ctx, phase_status="complete", finished=True, real_tsc_executed=True,
        new_raw_count=256, response_outcomes_opened=True,
        final_report_sha256=_sha(ctx.paths.analysis / "final_report.json"),
        raw_independent_sha256=compact["raw_independent_sha256"],
        compact_audit_sha256=final["compact_audit_sha256"],
        route=final["route"], verdict={"route": final["route"], "passed": True},
        stop_reason="",
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
    raise ValueError(f"unsupported R8R49 command: {command}")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    for name in (
        "r8r48-run", "r8r46-run", "r8r44-run", "r8r43-run", "r8r41-run",
        "r8r39-run", "r8r37-run", "r8r35-run", "r8r34-run", "r8r33-run",
        "r8r32-run", "r8r31-run", "r8r23-run", "r8r28-run", "r8r22-run",
        "r8r7-run", "r8r12-run", "r8r14-run", "r8r15-run", "r8r19-run",
        "r8r20-run", "r8r27-run", "r8-run", "r8r1-output", "r8r6-run",
        "source-d1r11-run", "source-r2-run", "source-r4-run", "source-r6-run",
        "source-s21-run", "source-s23r1-output", "source-s24-run", "source-d1r9-v1",
        "source-d1r9-v2", "source-d1r10-run", "source-d1r10-audit",
        "source-stage42r3b-run", "source-stage42r3c3-run",
        "source-stage42r3c3-bank-dir", "source-stage42r3c3t1-run",
        "source-stage42r3c3t1-audit-dir", "source-stage42r3c3t3-controller-bank",
        "q1-run", "q2-run", "q1-audit", "q2-audit", "r3b-server-audit",
        "r3b-snapshot-checks",
    ):
        parser.add_argument(f"--{name}", dest=name.replace("-", "_"), type=Path, required=True)
    parser.add_argument("--command", choices=("offline", "authorize-real", "run", "finalize-primary", "postprocess"), required=True)
    parser.add_argument("--backend", choices=("serial", "ray"), default="ray")
    parser.add_argument("--resume", action="store_true")
    return parser


def main() -> None:
    args = _parser().parse_args()
    ctx = load_context(args)
    result = execute(ctx, command=args.command, backend=args.backend, resume=args.resume)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
