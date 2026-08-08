#!/usr/bin/env python3
"""Execute the frozen R8R14 cumulative multidirection authority atlas."""

from __future__ import annotations

import argparse
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
from typing import Any, Mapping, Sequence

import numpy as np

from tsc_rzip_rllib.control import causal_discrete_pulse_mpc as mpc
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r6_direction0_replacement_sentinel as r6,
    stage4_2r3c3t13s24d1r14r8r7_fresh_multipulse_static_observer_interaction_campaign as r8r7,
    stage4_2r3c3t13s24d1r14r8r9_measured_multipulse_authority_audit as r8r9,
    stage4_2r3c3t13s24d1r14r8r11_sustained_exact_target_refresh_authority_sentinel as r8r11,
)


SCHEMA_VERSION = 1
STAGE = "Stage4.2R3c3T13S24D1R14R8R14"
IDENTITY = "cumulative_multidirection_staircase_authority_identification_v1"
RUN_NAME = "stage4_2r3c3t13s24d1r14r8r14_cumulative_multidirection_staircase_authority_identification"
CONTROLLER_REVISION = "cumulative_multidirection_staircase_v42r3c3t13s24d1r14r8r14_v1"
N_COILS = 14
PREFIX_END = 10
PHASES = ("safety", "qualification")
SOURCE_WRAPPER_METADATA_PREFIXES = (
    "r3c3t13s24d1r14r4_",
    "r3c3t13s24d1r14r8r7_",
)


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

    def phase_raw(self, phase: str) -> Path:
        if phase not in PHASES:
            raise ValueError(f"invalid R8R14 phase: {phase}")
        return self.raw / phase


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
    r8r7_run: Path
    r8r12_run: Path
    r8r13_run: Path
    source_ctx: r8r7.Context


def validate_config(cfg: Mapping[str, Any], *, project_root: Path) -> None:
    design = project_root / str(cfg["design_document"])
    contexts = cfg["context_contract"]
    schedule = cfg["schedule_contract"]
    controller = cfg["controller_contract"]
    formal = cfg["formal_contract"]
    gate = cfg["scientific_gate"]
    scope = cfg["scientific_scope"]
    matrix = schedule["canonical_matrix_columns"]
    if (
        int(cfg.get("schema_version", -1)) != SCHEMA_VERSION
        or cfg.get("stage") != STAGE
        or cfg.get("identity") != IDENTITY
        or cfg.get("run_name") != RUN_NAME
        or cfg.get("controller_revision") != CONTROLLER_REVISION
        or not design.is_file()
        or _sha(design) != str(cfg["design_document_sha256"])
        or tuple(contexts["histories"]) != ("minus_first", "plus_first")
        or len(contexts["ordered_pairs"]) != 8
        or tuple(contexts["safety_pairs"]) != tuple(contexts["ordered_pairs"][:2])
        or (
            int(contexts["context_count"]),
            int(contexts["safety_context_count"]),
            int(contexts["qualification_context_count"]),
        ) != (16, 4, 12)
        or tuple(map(int, schedule["decision_task_steps"])) != (10, 14, 18, 22)
        or tuple(map(int, schedule["directions"])) != (0, 1, 2, 3)
        or tuple(map(int, schedule["signs"])) != (-1, 1)
        or schedule["reused_candidate"] != {"direction_index": 2, "sign": 1}
        or tuple(tuple(map(int, row)) for row in schedule["new_candidates"])
        != ((0, -1), (0, 1), (1, -1), (1, 1), (2, -1), (3, -1), (3, 1))
        or float(schedule["canonical_scale"]) != 1.0
        or np.asarray(matrix, dtype=float).shape != (4, 4)
        or _matrix_digest(matrix) != str(schedule["canonical_matrix_float64_le_c_sha256"])
        or int(schedule["dynamic_exact_search_radius"]) != 16
        or (
            int(schedule["safety_spec_count"]),
            int(schedule["qualification_spec_count"]),
            int(schedule["total_spec_count"]),
            int(schedule["level_count_per_spec"]),
        ) != (28, 84, 112, 4)
        or int(schedule["final_atlas_spec_count"]) != 128
        or int(controller["delegated_last_task_step"]) != 9
        or float(controller["maximum_incremental_normalized_action_linf"]) != 0.25
        or float(controller["maximum_total_normalized_action_abs"]) != 1.0
        or float(controller["maximum_current_utilization"]) != 0.55
        or float(controller["minimum_desired_applied_current_cosine"]) != 0.98
        or float(controller["maximum_relative_off_basis_residual"]) != 0.10
        or not all(
            bool(controller[key])
            for key in (
                "require_exact_card15_issue",
                "require_exact_card15_refresh",
                "require_exact_source_prefix",
                "forbid_future_r17_controller_execution",
                "safe_stop_before_failed_advance",
            )
        )
        or (
            int(formal["normal_arrival_deadline_step"]),
            int(formal["normal_hold_through_step"]),
            int(formal["weak_arrival_deadline_step"]),
            int(formal["weak_hold_through_step"]),
        ) != (25, 35, 27, 37)
        or (
            float(formal["position_tolerance_m"]),
            float(formal["speed_tolerance_m_per_s"]),
            float(formal["ip_tolerance_A"]),
            int(formal["arrival_streak_steps"]),
        ) != (0.03, 0.1, 10000.0, 3)
        or float(formal["metric_equivalence_absolute_tolerance"]) != 1e-12
        or bool(formal["arrival_deadline_expansion_allowed"])
        or (
            int(gate["required_baseline_formal_pass_count"]),
            int(gate["required_failed_baseline_count"]),
            int(gate["minimum_repaired_failed_baseline_count"]),
            int(gate["minimum_held_oracle_formal_pass_count"]),
        ) != (6, 10, 1, 7)
        or not bool(gate["require_held_oracle_strictly_improves_baseline"])
        or any(
            bool(scope[key])
            for key in (
                "held_oracle_is_causal_selector",
                "real_mpc_executed",
                "gate_a_qualified",
                "all_stage_trajectories_allowed_in_expert_dataset",
                "expert_data_allowed",
                "bc_dagger_or_rl_allowed",
                "global_plant_reachability_claimed",
            )
        )
    ):
        raise ValueError("R8R14 frozen design changed")


def load_context(args: argparse.Namespace) -> Context:
    config_path = args.config.expanduser().resolve()
    cfg = _read(config_path)
    validate_config(cfg, project_root=_root())
    source_args = argparse.Namespace(**vars(args))
    source_args.config = (_root() / str(cfg["source_r8r7_config"])).resolve()
    source_args.run_dir = args.r8r7_run.expanduser().resolve()
    source_ctx = r8r7.load_context(source_args)
    return Context(
        cfg=cfg,
        config_path=config_path,
        paths=_paths(args.run_dir),
        r8r7_run=args.r8r7_run.expanduser().resolve(),
        r8r12_run=args.r8r12_run.expanduser().resolve(),
        r8r13_run=args.r8r13_run.expanduser().resolve(),
        source_ctx=source_ctx,
    )


def _source_stage(ctx: Context) -> Path:
    return ctx.r8r7_run / str(ctx.cfg["source_r8r7"]["stage_directory"])


def _r8r12_stage(ctx: Context) -> Path:
    return ctx.r8r12_run / str(ctx.cfg["source_r8r12"]["stage_directory"])


def _r8r13_stage(ctx: Context) -> Path:
    return ctx.r8r13_run / str(ctx.cfg["source_r8r13"]["stage_directory"])


def _execution_context(ctx: Context) -> Any:
    return r8r7.r8.Context(
        cfg=ctx.source_ctx.r8_cfg,
        config_path=ctx.source_ctx.r8_config_path,
        d1r11_ctx=ctx.source_ctx.r8_ctx.d1r11_ctx,
        source_d1r11_run=ctx.source_ctx.r8_ctx.source_d1r11_run,
        source_response_runs=ctx.source_ctx.r8_ctx.source_response_runs,
        paths=ctx.paths,  # compatible variants path
    )


def _source_baselines(
    ctx: Context,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    specs = [copy.deepcopy(row) for row in r8r7._phase_specs(ctx.source_ctx, "baseline")]
    ordered = tuple(map(str, ctx.cfg["context_contract"]["ordered_pairs"]))
    histories = tuple(map(str, ctx.cfg["context_contract"]["histories"]))
    order = {
        (pair, history): (pair_index, history_index)
        for pair_index, pair in enumerate(ordered)
        for history_index, history in enumerate(histories)
    }
    specs.sort(key=lambda row: order[(str(row["pair_id"]), str(row["history_member"]))])
    if len(specs) != 16 or {
        (str(row["pair_id"]), str(row["history_member"])) for row in specs
    } != set(order):
        raise ValueError("R8R14 source baseline coverage changed")
    results = {
        str(row["experiment_id"]): r8r7.r8._read_gz(
            _source_stage(ctx) / "raw" / "baseline" / f"{row['experiment_id']}.json.gz"
        )
        for row in specs
    }
    return specs, results


def _authenticate_r8r12(ctx: Context) -> dict[str, Any]:
    stage = _r8r12_stage(ctx)
    expected = ctx.cfg["source_r8r12"]
    paths = {
        "primary_detailed": stage / "analysis" / "primary_detailed.json",
        "primary_summary": stage / "analysis" / "primary_summary.json",
        "final_independent": stage / "analysis" / "final_independent.json",
        "final_report": stage / "analysis" / "final_report.json",
        "manifest": stage / "stage_manifest.json",
        "state": stage / "stage_state.json",
    }
    hashes = {
        name: _sha(path) if path.is_file() else "" for name, path in paths.items()
    }
    for name, key in (
        ("primary_detailed", "primary_detailed_sha256"),
        ("primary_summary", "primary_summary_sha256"),
        ("final_independent", "final_independent_sha256"),
        ("final_report", "final_report_sha256"),
        ("manifest", "stage_manifest_sha256"),
        ("state", "stage_state_sha256"),
    ):
        if hashes[name] != str(expected[key]):
            raise ValueError(f"R8R14 R8R12 source {name} changed")
    final = _read(paths["final_report"])
    state = _read(paths["state"])
    inventories = {
        phase: r8r7.r8._inventory(stage / "raw" / phase) for phase in PHASES
    }
    for phase in PHASES:
        inventory = inventories[phase]
        if (
            int(inventory["count"]) != int(expected[f"{phase}_raw_count"])
            or int(inventory["bytes"]) != int(expected[f"{phase}_raw_bytes"])
            or inventory["digest"] != str(expected[f"{phase}_raw_digest"])
        ):
            raise ValueError(f"R8R14 R8R12 {phase} raw inventory changed")
    if (
        final.get("route") != expected["required_route"]
        or final.get("passed") is not False
        or state.get("finished") is not True
        or (state.get("verdict") or {}).get("route") != expected["required_route"]
    ):
        raise ValueError("R8R14 R8R12 final route changed")
    return {
        "stage": str(stage),
        "hashes": hashes,
        "inventories": inventories,
        "required_route": expected["required_route"],
        "passed": True,
    }


def _authenticate_r8r13(ctx: Context) -> dict[str, Any]:
    stage = _r8r13_stage(ctx)
    expected = ctx.cfg["source_r8r13"]
    paths = {
        "primary_detailed": stage / "analysis/primary_detailed.json",
        "primary_summary": stage / "analysis/primary_summary.json",
        "final_independent": stage / "analysis/final_independent.json",
        "final_report": stage / "analysis/final_report.json",
        "manifest": stage / "stage_manifest.json",
        "state": stage / "stage_state.json",
    }
    hashes = {name: _sha(path) if path.is_file() else "" for name, path in paths.items()}
    for name, key in (
        ("primary_detailed", "primary_detailed_sha256"),
        ("primary_summary", "primary_summary_sha256"),
        ("final_independent", "final_independent_sha256"),
        ("final_report", "final_report_sha256"),
        ("manifest", "stage_manifest_sha256"),
        ("state", "stage_state_sha256"),
    ):
        if hashes[name] != str(expected[key]):
            raise ValueError(f"R8R14 R8R13 provenance {name} changed")
    final, state = _read(paths["final_report"]), _read(paths["state"])
    if (
        final.get("route") != expected["required_route"]
        or final.get("passed") is not False
        or state.get("finished") is not True
        or state.get("new_raw_count") != 0
        or state.get("real_tsc_executed") is not False
        or (state.get("verdict") or {}).get("route") != expected["required_route"]
    ):
        raise ValueError("R8R14 R8R13 final provenance changed")
    return {"stage": str(stage), "hashes": hashes, "required_route": expected["required_route"], "passed": True}


def _source_r8r12_candidates(
    ctx: Context,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    stage = _r8r12_stage(ctx)
    specs = _read(stage / "specs/all_specs.json")
    ordered = tuple(map(str, ctx.cfg["context_contract"]["ordered_pairs"]))
    histories = tuple(map(str, ctx.cfg["context_contract"]["histories"]))
    order = {
        (pair, history): (pair_index, history_index)
        for pair_index, pair in enumerate(ordered)
        for history_index, history in enumerate(histories)
    }
    specs.sort(key=lambda row: order[(str(row["pair_id"]), str(row["history_member"]))])
    if (
        len(specs) != 16
        or {(str(row["pair_id"]), str(row["history_member"])) for row in specs}
        != set(order)
        or any(
            int(row["r8r12_direction_index"]) != 2
            or int(row["r8r12_sign"]) != 1
            or float(row["r8r12_canonical_scale"]) != 1.0
            or tuple(map(int, row["r8r12_decision_task_steps"])) != (10, 14, 18, 22)
            for row in specs
        )
    ):
        raise ValueError("R8R14 source R8R12 candidate matrix changed")
    results = {
        str(row["experiment_id"]): r8r7.r8._read_gz(
            stage / "raw" / str(row["partition"]) / f"{row['experiment_id']}.json.gz"
        )
        for row in specs
    }
    return specs, results


def build_specs(ctx: Context) -> list[dict[str, Any]]:
    baselines, _ = _source_baselines(ctx)
    safety = set(map(str, ctx.cfg["context_contract"]["safety_pairs"]))
    schedule = ctx.cfg["schedule_contract"]
    output = []
    for index, source in enumerate(baselines):
        phase = "safety" if str(source["pair_id"]) in safety else "qualification"
        for direction, sign in schedule["new_candidates"]:
            direction, sign = int(direction), int(sign)
            requested = (
                np.asarray(schedule["canonical_matrix_columns"], dtype=float)[:, direction]
                * sign
            )
            spec = copy.deepcopy(source)
            spec.update(
                {
                    "kind": "stage4_2r3c3t13s24d1r14r8r14_cumulative_multidirection_staircase",
                    "stage": STAGE,
                    "campaign_identity": IDENTITY,
                    "controller_revision": CONTROLLER_REVISION,
                    "partition": phase,
                    "experiment_id": f"r8r14_{phase}_{index:02d}_d{direction}_{'p' if sign > 0 else 'm'}",
                    "source_r8r7_baseline_experiment_id": str(source["experiment_id"]),
                    "r8r14_role": "cumulative_multidirection_staircase",
                    "r8r14_direction_index": direction,
                    "r8r14_sign": sign,
                    "r8r14_canonical_scale": 1.0,
                    "r8r14_requested_coordinate": requested.tolist(),
                    "r8r14_matrix_digest": str(schedule["canonical_matrix_float64_le_c_sha256"]),
                    "r8r14_decision_task_steps": list(map(int, schedule["decision_task_steps"])),
                    "r8r14_allowed_in_expert_dataset": False,
                    "pair_or_history_label_available_to_controller": False,
                    "source_result_available_to_controller": False,
                    "future_measurement_count": 0,
                    "future_action_count": 0,
                    "formal_timing_unchanged": True,
                }
            )
            output.append(spec)
    counts = {phase: sum(row["partition"] == phase for row in output) for phase in PHASES}
    if counts != {"safety": 28, "qualification": 84} or len(output) != 112:
        raise ValueError("R8R14 frozen specification matrix changed")
    return output


def _payload(ctx: Context, spec: Mapping[str, Any]) -> dict[str, Any]:
    payload = r8r7.r8._payload(_execution_context(ctx), spec)
    experiment_id = str(spec["experiment_id"])
    payload.update(
        {
            "variant_id": f"stage4_2r3c3t13s24d1r14r8r14_{experiment_id}",
            "stage4_2r3c3t13s24d1r14r8r14_decision_task_steps": list(
                map(int, spec["r8r14_decision_task_steps"])
            ),
            "stage4_2r3c3t13s24d1r14r8r14_pair_history_label_available_to_controller": False,
        }
    )
    _write(ctx.paths.variants / f"payload_{experiment_id}.json", payload)
    return payload


def _fixed_basis(result: Mapping[str, Any]) -> np.ndarray:
    return r8r11._fixed_basis(result)


def _refresh_event(
    *,
    task_step: int,
    currents: Sequence[float],
    target_fields: Sequence[str],
    actuator: Any,
    turns_tsc: Sequence[float],
    max_delta_a: float,
    minimum_current: Sequence[float],
    maximum_current: Sequence[float],
    lattice_cfg: Mapping[str, Any],
    contract: Mapping[str, Any],
) -> dict[str, Any]:
    measured = np.asarray(currents, dtype=float).reshape(N_COILS)
    stored = tuple(map(str, target_fields))
    chosen = r8r7.r8.d1r11.s21.s16.s9.exact_stored_center_action(
        stored_fields=stored,
        measured_current_a_tsc=measured,
        baseline_action_norm_tsc=np.zeros(N_COILS),
        turns_tsc=turns_tsc,
        max_slew_step_a=float(max_delta_a),
        minimum_current_a_tsc=minimum_current,
        maximum_current_a_tsc=maximum_current,
        cfg=lattice_cfg,
    )
    applied = actuator.apply(measured, chosen["action_norm_tsc"])
    criteria = {
        "finite": bool(np.all(np.isfinite(measured))),
        "target_exact": list(applied.card15_fields) == list(stored),
        "exact_fields": all(len(field) == 10 for field in stored),
        "no_saturation": not any(applied.action_saturated),
        "no_current_clip": not any(applied.current_limit_clipped),
        "incremental_action": float(chosen["incremental_normalized_action_linf"])
        <= float(contract["maximum_incremental_normalized_action_linf"]) + 1e-12,
        "total_action": float(chosen["total_normalized_action_abs"])
        <= float(contract["maximum_total_normalized_action_abs"]) + 1e-12,
        "current_utilization": float(chosen["predicted_maximum_current_utilization"])
        <= float(contract["maximum_current_utilization"]) + 1e-12,
        "actuator_gate": bool(chosen["passed"]),
    }
    return {
        "event": "exact_target_refresh",
        "task_step": int(task_step),
        "stored_target_card15_fields": list(stored),
        "incremental_normalized_action_linf": float(
            chosen["incremental_normalized_action_linf"]
        ),
        "total_normalized_action_abs": float(chosen["total_normalized_action_abs"]),
        "predicted_current_utilization": float(
            chosen["predicted_maximum_current_utilization"]
        ),
        "action_norm_tsc": list(map(float, chosen["action_norm_tsc"])),
        "nominal_readback_current_a_tsc": list(applied.nominal_readback_current_a_tsc),
        "criteria": criteria,
        "passed": bool(all(criteria.values())),
        "actuator_prediction": copy.deepcopy(chosen),
    }


def _offline_construction(
    ctx: Context, specs: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    _, sources = _source_baselines(ctx)
    execution = _execution_context(ctx)
    lattice = execution.d1r11_ctx.base_ctx.base_ctx.cfg["lattice_probe"]
    controller_cfg = copy.deepcopy(ctx.cfg["controller_contract"])
    controller_cfg["dynamic_exact_search_radius"] = int(
        ctx.cfg["schedule_contract"]["dynamic_exact_search_radius"]
    )
    rows = []
    issue_count = refresh_count = 0
    for spec in specs:
        direction = int(spec["r8r14_direction_index"])
        sign = int(spec["r8r14_sign"])
        candidate = mpc.Candidate(
            f"direction{direction}_{'plus' if sign > 0 else 'minus'}",
            direction,
            sign,
            float(spec["r8r14_canonical_scale"]),
        )
        source = sources[str(spec["source_r8r7_baseline_experiment_id"])]
        payload = _read(ctx.paths.variants / f"payload_{spec['experiment_id']}.json")
        actuator = mpc.actuator_from_payload(payload, lattice)
        current = np.asarray(source["trajectory"][PREFIX_END]["currents_a_tsc"], dtype=float)
        basis = _fixed_basis(source).T
        levels = []
        horizon = int(spec["horizon_steps"])
        decisions = tuple(map(int, spec["r8r14_decision_task_steps"]))
        for level, decision in enumerate(decisions, start=1):
            issue = mpc.construct_issue(
                task_step=decision,
                currents_a_tsc=current,
                fixed_basis_delta_field_kat_tsc=basis,
                candidate=candidate,
                canonical_matrix_columns=ctx.cfg["schedule_contract"]["canonical_matrix_columns"],
                actuator=actuator,
                controller_cfg=controller_cfg,
                lattice_cfg=lattice,
            )
            issue_count += int(bool(issue["passed"]))
            current = np.asarray(issue["nominal_issue_readback_current_a_tsc"], dtype=float)
            next_decision = decisions[level] if level < len(decisions) else horizon
            refreshes = []
            for task_step in range(decision + 1, next_decision):
                refresh = _refresh_event(
                    task_step=task_step,
                    currents=current,
                    target_fields=issue["target_card15_fields"],
                    actuator=actuator,
                    turns_tsc=actuator.turns_tsc,
                    max_delta_a=actuator.max_slew_step_a,
                    minimum_current=actuator.minimum_current_a_tsc,
                    maximum_current=actuator.maximum_current_a_tsc,
                    lattice_cfg=lattice,
                    contract=ctx.cfg["controller_contract"],
                )
                refresh_count += int(bool(refresh["passed"]))
                current = np.asarray(refresh["nominal_readback_current_a_tsc"], dtype=float)
                refreshes.append(
                    {
                        "task_step": task_step,
                        "target_card15_fields": refresh["stored_target_card15_fields"],
                        "action_norm_tsc": refresh["action_norm_tsc"],
                        "incremental_normalized_action_linf": refresh[
                            "incremental_normalized_action_linf"
                        ],
                        "predicted_current_utilization": refresh[
                            "predicted_current_utilization"
                        ],
                        "criteria": refresh["criteria"],
                        "passed": refresh["passed"],
                    }
                )
            levels.append(
                {
                    "level": level,
                    "decision_task_step": decision,
                    "center_card15_fields": issue["center_card15_fields"],
                    "target_card15_fields": issue["target_card15_fields"],
                    "action_norm_tsc": issue["action_norm_tsc"],
                    "integer_grid_steps_tsc": issue["integer_grid_steps_tsc"],
                    "incremental_normalized_action_linf": issue[
                        "incremental_normalized_action_linf"
                    ],
                    "predicted_current_utilization": issue[
                        "predicted_current_utilization"
                    ],
                    "desired_applied_current_cosine": issue[
                        "desired_applied_current_cosine"
                    ],
                    "relative_off_basis_residual": issue[
                        "relative_off_basis_residual"
                    ],
                    "criteria": issue["criteria"],
                    "refreshes": refreshes,
                    "passed": bool(
                        issue["passed"] and all(row["passed"] for row in refreshes)
                    ),
                }
            )
        rows.append(
            {
                "experiment_id": spec["experiment_id"],
                "pair_id": spec["pair_id"],
                "history_member": spec["history_member"],
                "partition": spec["partition"],
                "levels": levels,
                "passed": all(row["passed"] for row in levels),
            }
        )
    return {
        "spec_count": len(rows),
        "level_construction_count": sum(len(row["levels"]) for row in rows),
        "level_construction_pass_count": issue_count,
        "refresh_construction_count": sum(
            len(level["refreshes"]) for row in rows for level in row["levels"]
        ),
        "refresh_construction_pass_count": refresh_count,
        "maximum_issue_increment": max(
            float(level["incremental_normalized_action_linf"])
            for row in rows
            for level in row["levels"]
        ),
        "maximum_refresh_increment": max(
            float(refresh["incremental_normalized_action_linf"])
            for row in rows
            for level in row["levels"]
            for refresh in level["refreshes"]
        ),
        "maximum_predicted_current_utilization": max(
            [
                float(level["predicted_current_utilization"])
                for row in rows
                for level in row["levels"]
            ]
            + [
                float(refresh["predicted_current_utilization"])
                for row in rows
                for level in row["levels"]
                for refresh in level["refreshes"]
            ]
        ),
        "rows": rows,
        "passed": bool(len(rows) == 112 and all(row["passed"] for row in rows)),
    }


def prepare_offline(ctx: Context) -> dict[str, Any]:
    if ctx.paths.stage.exists():
        raise ValueError("R8R14 offline requires a fresh run identity")
    source_r8r7 = r8r9._authenticate_r8r7(_source_stage(ctx), ctx.cfg)
    source_r8r12 = _authenticate_r8r12(ctx)
    source_r8r13 = _authenticate_r8r13(ctx)
    lineage = {
        "r8": r8r7._authenticate_r8(ctx.source_ctx),
        "r8r1": r8r7._authenticate_r8r1(ctx.source_ctx),
        "r8r6": r8r7._authenticate_r8r6(ctx.source_ctx),
    }
    specs = build_specs(ctx)
    for path in (
        ctx.paths.stage,
        ctx.paths.variants,
        ctx.paths.specs,
        ctx.paths.source_reference,
        ctx.paths.analysis,
    ):
        path.mkdir(parents=True, exist_ok=True)
    for phase in PHASES:
        ctx.paths.phase_raw(phase).mkdir(parents=True, exist_ok=True)
    for spec in specs:
        _payload(ctx, spec)
    preflight = _offline_construction(ctx, specs)
    if not preflight["passed"]:
        raise ValueError("R8R14 frozen cumulative construction preflight failed")
    _write(ctx.paths.specs / "all_specs.json", specs)
    for phase in PHASES:
        _write(
            ctx.paths.specs / f"{phase}_specs.json",
            [row for row in specs if row["partition"] == phase],
        )
    _write(ctx.paths.source_reference / "r8r7_authentication.json", source_r8r7)
    _write(ctx.paths.source_reference / "r8r12_authentication.json", source_r8r12)
    _write(ctx.paths.source_reference / "r8r13_authentication.json", source_r8r13)
    _write(ctx.paths.source_reference / "lineage_authentication.json", lineage)
    _write(ctx.paths.analysis / "offline_cumulative_preflight.json", preflight)
    package = r8r7._package_fingerprint()
    manifest = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "controller_revision": CONTROLLER_REVISION,
        "package_revision": ctx.cfg["package_revision"],
        "config_path": str(ctx.config_path),
        "config_sha256": _sha(ctx.config_path),
        "design_document_sha256": ctx.cfg["design_document_sha256"],
        "source_r8r7_run": str(ctx.r8r7_run),
        "source_r8r12_run": str(ctx.r8r12_run),
        "source_r8r13_run": str(ctx.r8r13_run),
        "source_r8r7_authenticated": True,
        "source_r8r12_authenticated": True,
        "source_r8r13_authenticated": True,
        "lineage_authenticated": True,
        "spec_count": len(specs),
        "spec_digest": _digest(specs),
        "offline_preflight_digest": _digest(preflight),
        "package_fingerprint": package,
        "formal_timing_unchanged": True,
        "all_stage_trajectories_allowed_in_expert_dataset": False,
    }
    _write(ctx.paths.manifest, manifest)
    _write(
        ctx.paths.state,
        {
            "schema_version": 1,
            "stage": STAGE,
            "phase_status": "offline_primary_ready",
            "finished": False,
            "real_tsc_executed": False,
            "new_raw_count": 0,
            "formal_outcomes_opened": False,
            "qualification_outcomes_opened": False,
            "spec_digest": manifest["spec_digest"],
            "package_digest": package["digest"],
            "stop_reason": "",
            "verdict": {},
        },
    )
    report = {
        "schema_version": 1,
        "stage": STAGE,
        "phase": "offline_primary",
        "source_r8r7_authenticated": True,
        "source_r8r12_authenticated": True,
        "source_r8r13_authenticated": True,
        "lineage_authenticated": True,
        "spec_count": 112,
        "safety_spec_count": 28,
        "qualification_spec_count": 84,
        "level_construction_count": preflight["level_construction_count"],
        "level_construction_pass_count": preflight["level_construction_pass_count"],
        "refresh_construction_count": preflight["refresh_construction_count"],
        "refresh_construction_pass_count": preflight[
            "refresh_construction_pass_count"
        ],
        "maximum_issue_increment": preflight["maximum_issue_increment"],
        "maximum_refresh_increment": preflight["maximum_refresh_increment"],
        "maximum_predicted_current_utilization": preflight[
            "maximum_predicted_current_utilization"
        ],
        "new_raw_count": 0,
        "real_tsc_executed": False,
        "passed": True,
    }
    _write(ctx.paths.analysis / "offline_primary.json", report)
    return report


def _saved_specs(ctx: Context) -> list[dict[str, Any]]:
    specs = _read(ctx.paths.specs / "all_specs.json")
    manifest = _read(ctx.paths.manifest)
    if (
        len(specs) != 112
        or _digest(specs) != manifest.get("spec_digest")
        or _sha(ctx.config_path) != manifest.get("config_sha256")
    ):
        raise ValueError("R8R14 saved identity or specifications changed")
    return specs


def _phase_specs(ctx: Context, phase: str) -> list[dict[str, Any]]:
    rows = [row for row in _saved_specs(ctx) if row["partition"] == phase]
    if len(rows) != {"safety": 28, "qualification": 84}[phase]:
        raise ValueError("R8R14 saved phase coverage changed")
    return rows


def _set_state(ctx: Context, **updates: Any) -> dict[str, Any]:
    state = _read(ctx.paths.state)
    state.update(updates)
    _write(ctx.paths.state, state)
    return state


class CumulativeMultidirectionStaircaseController(
    r6.MixedBasisSignedExcitationController
):
    """Four causal exact-target levels followed by continuous target refresh."""

    def __init__(
        self,
        base: Any,
        bundle: Mapping[str, Any],
        source_spec: Mapping[str, Any],
        initial_state: Mapping[str, Any],
        lattice_cfg: Mapping[str, Any],
        calibration_cfg: Mapping[str, Any],
        dynamic_cfg: Mapping[str, Any],
        schedule_cfg: Mapping[str, Any],
        controller_cfg: Mapping[str, Any],
        *,
        spec: Mapping[str, Any],
    ):
        requested = np.asarray(spec["r8r14_requested_coordinate"], dtype=float)
        direction = int(spec["r8r14_direction_index"])
        sign = int(spec["r8r14_sign"])
        super().__init__(
            base,
            bundle,
            source_spec,
            initial_state,
            lattice_cfg,
            calibration_cfg,
            dynamic_cfg,
            schedule_cfg,
            controller_cfg,
            role="signed_probe",
            direction_index=direction,
            sign=sign,
            requested_coordinate=requested,
            issue_step=14,
            cancel_step=15,
            zero_after_step=16,
        )
        self.r8r14_decisions = tuple(map(int, spec["r8r14_decision_task_steps"]))
        self.r8r14_direction = direction
        self.r8r14_contract = copy.deepcopy(dict(controller_cfg))
        self.r8r14_issue_count = 0
        self.r8r14_refresh_count = 0

    def _refresh(self, currents: np.ndarray) -> tuple[np.ndarray, dict[str, Any]]:
        if self._active_issue is None:
            raise ValueError("R8R14 refresh has no active exact target")
        event = _refresh_event(
            task_step=self.step,
            currents=currents,
            target_fields=self._active_issue["target_card15_fields"],
            actuator=self.actuator,
            turns_tsc=self.turns_tsc,
            max_delta_a=float(self.base.max_delta_a),
            minimum_current=self.base.min_current,
            maximum_current=self.base.max_current,
            lattice_cfg=self.lattice_cfg,
            contract=self.r8r14_contract,
        )
        if not event["passed"]:
            raise ValueError(
                "R8R14 exact target refresh action failed: "
                + json.dumps(event, sort_keys=True)
            )
        self.r8r14_refresh_count += 1
        return np.asarray(event["action_norm_tsc"], dtype=float), event

    def action(self, current_state: Mapping[str, Any]) -> tuple[np.ndarray, dict[str, Any]]:
        if int(current_state["step_index"]) != self.step:
            raise ValueError("R8R14 controller/current task-state index mismatch")
        if self.step < PREFIX_END:
            action, trace = super().action(current_state)
            trace.update(
                {
                    "r3c3t13s24d1r14r8r14_controller_revision": CONTROLLER_REVISION,
                    "r3c3t13s24d1r14r8r14_delegated_prefix": True,
                    "r3c3t13s24d1r14r8r14_event": "none",
                    "r3c3t13s24d1r14r8r14_event_detail": {},
                    "r3c3t13s24d1r14r8r14_forbidden_input_used": False,
                }
            )
            return np.asarray(action, dtype=float), trace
        currents = np.asarray(current_state["currents_a_tsc"], dtype=float)
        action = r6.zero_action(self.step)
        trace = r6._trace_template(self.step, action)
        if self.step in self.r8r14_decisions:
            action, event = self._issue(
                self.r8r14_direction, currents, np.zeros(N_COILS)
            )
            event_name = "staircase_issue"
            self.r8r14_issue_count += 1
        else:
            action, event = self._refresh(currents)
            event_name = "staircase_refresh"
        trace.update(
            {
                "action_norm_tsc": action.tolist(),
                "r3c3t13s24d1r14r8r14_controller_revision": CONTROLLER_REVISION,
                "r3c3t13s24d1r14r8r14_delegated_prefix": False,
                "r3c3t13s24d1r14r8r14_event": event_name,
                "r3c3t13s24d1r14r8r14_event_detail": copy.deepcopy(event),
                "r3c3t13s24d1r14r8r14_forbidden_input_used": False,
                "r3c3t13s24d1r14r8r14_pair_or_history_label_used": False,
                "r3c3t13s24d1r14r8r14_future_measurement_used": False,
                "r3c3t13s24d1r14r8r14_future_action_used": False,
                "r3c3t13s24d1r14r8r14_source_result_used": False,
                "r3c3t13s24d1r14r8r14_hidden_wire_used": False,
            }
        )
        return np.asarray(action, dtype=float), trace


class LocalWorker:
    def __init__(
        self,
        payload: dict[str, Any],
        library: dict[str, Any],
        bundle: dict[str, Any],
        worker_id: str,
        selector: dict[str, Any],
        lattice_cfg: dict[str, Any],
        calibration_cfg: dict[str, Any],
        dynamic_cfg: dict[str, Any],
        schedule_cfg: dict[str, Any],
        controller_cfg: dict[str, Any],
    ):
        self.plant = r8r7.r8.d1r11.s21.s16.s9.t11.t1.r1.LocalPlantReplayWorker(
            payload, library, bundle, worker_id, selector
        )
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
            "schema_version": 1,
            "stage": STAGE,
            "campaign_identity": IDENTITY,
            "controller_revision": CONTROLLER_REVISION,
            "experiment_id": spec["experiment_id"],
            "spec": copy.deepcopy(spec),
            "success": False,
            "completed": False,
            "failure_reason": "",
            "execution_failure_class": "",
            "trajectory": trajectory,
            "controller_trace": trace,
        }
        try:
            horizon = int(spec["horizon_steps"])
            if horizon != int(spec["formal_horizon_steps"]) or horizon != int(
                self.base.env.max_episode_steps
            ):
                raise ValueError("R8R14 formal horizon changed")
            self.base.env.reset()
            zero = np.zeros(N_COILS, dtype=np.float32)
            trajectory.append(
                r8r7.r8.d1r11.s21.s16.s9.t11.t1.r1._state_record_full(
                    self.base.env, 0, zero
                )
            )
            controller = CumulativeMultidirectionStaircaseController(
                self.base,
                self.bundle,
                spec,
                trajectory[0],
                self.lattice_cfg,
                self.calibration_cfg,
                self.dynamic_cfg,
                self.schedule_cfg,
                self.controller_cfg,
                spec=spec,
            )
            for step in range(horizon):
                current = trajectory[-1]
                finite = all(
                    math.isfinite(float(current[key])) for key in ("R", "Z", "Ip")
                ) and np.all(
                    np.isfinite(np.asarray(current["currents_a_tsc"], dtype=float))
                )
                if not finite or bool(current.get("abnormal")):
                    result["execution_failure_class"] = (
                        "pre_action_visible_state_safety_failure"
                    )
                    raise ValueError("R8R14 pre-action visible state safety gate failed")
                try:
                    action, row = controller.action(current)
                except ValueError as exc:
                    if "action failed" in str(exc):
                        result["execution_failure_class"] = (
                            "controller_action_safety_gate_failure"
                        )
                    raise
                _, _, terminated, truncated, info = self.base.env.step(action)
                next_state = r8r7.r8.d1r11.s21.s16.s9.t11.t1.r1._state_record_full(
                    self.base.env, step + 1, action
                )
                trajectory.append(next_state)
                trace.append(row)
                controller.advance(next_state)
                if terminated:
                    result["execution_failure_class"] = "plant_abnormal_termination"
                    raise RuntimeError(str(info.get("failure_reason", "environment terminated")))
                if truncated and step + 1 < horizon:
                    result["execution_failure_class"] = "plant_early_truncation"
                    raise RuntimeError("environment truncated before R8R14 horizon")
            calibration_events = [
                row.get("r3c3t13s16_lattice_event")
                for row in trace[:PREFIX_END]
                if row.get("r3c3t13s16_lattice_event") != "none"
            ]
            events = [
                row.get("r3c3t13s24d1r14r8r14_event")
                for row in trace[PREFIX_END:]
            ]
            success = bool(
                len(trajectory) == horizon + 1
                and len(trace) == horizon
                and calibration_events == r8r7.r4.EXPECTED_CALIBRATION
                and bool(trace[7].get("r3c3t13s21_exact_calibration_net_zero"))
                and all(
                    bool(row.get("r3c3t13s24d1r14r8r14_delegated_prefix"))
                    for row in trace[:PREFIX_END]
                )
                and all(
                    not bool(row.get("r3c3t13s24d1r14r8r14_delegated_prefix"))
                    for row in trace[PREFIX_END:]
                )
                and len(events) == horizon - PREFIX_END
                and events.count("staircase_issue") == 4
                and events.count("staircase_refresh") == horizon - PREFIX_END - 4
                and all(
                    bool(
                        (row.get("r3c3t13s24d1r14r8r14_event_detail") or {}).get(
                            "passed"
                        )
                    )
                    for row in trace[PREFIX_END:]
                )
                and controller.r8r14_issue_count == 4
                and controller.r8r14_refresh_count == horizon - PREFIX_END - 4
                and controller._active_issue is not None
                and not any(bool(row.get("abnormal")) for row in trajectory)
            )
            result.update(
                {
                    "success": success,
                    "completed": True,
                    "failure_reason": ""
                    if success
                    else "incomplete or invalid R8R14 rollout",
                    "execution_failure_class": ""
                    if success
                    else "controller_or_action_semantics_error",
                    "hidden_history_control_summary": {
                        "fresh_controller_actor": True,
                        "fresh_tsc_process": True,
                        "full_tsc_hidden_state_loaded_from_sprsina": True,
                        "future_r17_controller_executed": False,
                        "formal_tracking_diagnostic_only": False,
                        "stage_trajectory_allowed_in_expert_dataset": False,
                        "future_action_replay_used": False,
                        "future_measurement_used": False,
                        "pair_or_history_label_used": False,
                        "source_result_used": False,
                    },
                    "wall_time_s": time.time() - started,
                }
            )
            failed = not success
            return r8r7.r8.d1r11.s21.s16.s9.t11.t1._json_safe(result)
        except Exception as exc:
            result.update(
                {
                    "success": False,
                    "completed": True,
                    "failure_reason": repr(exc),
                    "execution_failure_class": str(
                        result.get("execution_failure_class")
                        or "runtime_or_controller_error"
                    ),
                    "trajectory": trajectory,
                    "controller_trace": trace,
                    "traceback": traceback.format_exc(),
                    "wall_time_s": time.time() - started,
                }
            )
            return r8r7.r8.d1r11.s21.s16.s9.t11.t1._json_safe(result)
        finally:
            runner = getattr(self.base.env, "runner", None)
            if runner is not None:
                runner.cleanup_episode_workspace(
                    failed=failed, reason="stage4_2r3c3t13s24d1r14r8r14"
                )


_RAY_ACTOR = None


def _ray_actor_class():
    global _RAY_ACTOR
    if _RAY_ACTOR is None:
        import ray

        @ray.remote(num_cpus=1, max_restarts=0)
        class R8R14Actor:
            def __init__(self, *args: Any):
                self.worker = LocalWorker(*args)

            def evaluate(self, spec: dict[str, Any]) -> dict[str, Any]:
                return self.worker.evaluate(spec)

            def close(self) -> bool:
                self.worker.close()
                return True

        _RAY_ACTOR = R8R14Actor
    return _RAY_ACTOR


def _result_complete(
    path: Path, spec: Mapping[str, Any], *, require_success: bool = True
) -> bool:
    if not path.is_file():
        return False
    try:
        result = r8r7.r8._read_gz(path)
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
    ctx: Context,
    specs: Sequence[dict[str, Any]],
    *,
    phase: str,
    backend: str,
    resume: bool,
) -> dict[str, Any]:
    raw_dir = ctx.paths.phase_raw(phase)
    pending = [
        spec
        for spec in specs
        if not (
            resume
            and _result_complete(raw_dir / f"{spec['experiment_id']}.json.gz", spec)
        )
    ]
    payloads = {str(spec["experiment_id"]): _payload(ctx, spec) for spec in specs}
    execution = _execution_context(ctx)
    library, bundle, selector = r8r7.r8.d1r11._library_bundle_selector(
        execution.d1r11_ctx
    )
    lattice = execution.d1r11_ctx.base_ctx.base_ctx.cfg["lattice_probe"]
    calibration = execution.d1r11_ctx.base_ctx.base_ctx.cfg["active_calibration"]
    dynamic = execution.d1r11_ctx.base_ctx.cfg["causal_model"]
    schedule_cfg = execution.d1r11_ctx.cfg["schedule_contract"]
    controller_cfg = copy.deepcopy(ctx.cfg["controller_contract"])
    controller_cfg.update(
        {
            "requested_coordinate_matrix_columns": copy.deepcopy(
                ctx.cfg["schedule_contract"]["canonical_matrix_columns"]
            ),
            "requested_matrix_float64_le_c_sha256": str(
                ctx.cfg["schedule_contract"]["canonical_matrix_float64_le_c_sha256"]
            ),
        }
    )

    def args_for(spec: Mapping[str, Any], index: int) -> tuple[Any, ...]:
        return (
            payloads[str(spec["experiment_id"])],
            library,
            bundle,
            f"stage42r8r14_{phase}_{index:03d}",
            selector,
            lattice,
            calibration,
            dynamic,
            schedule_cfg,
            controller_cfg,
        )

    if backend == "serial":
        for index, spec in enumerate(pending):
            worker = LocalWorker(*args_for(spec, index))
            try:
                result = worker.evaluate(spec)
            finally:
                worker.close()
            r8r7.r8._write_gz(raw_dir / f"{spec['experiment_id']}.json.gz", result)
            print(f"[R8R14 {phase}] {index + 1}/{len(pending)}", flush=True)
    elif backend == "ray" and pending:
        import ray

        plan = r8r7.r8.d1r11.s21.s16.ensure_ray_worker_plan(
            ray,
            requested_workers=int(ctx.cfg["parallel"]["n_workers"]),
            pending_tasks=len(pending),
            ray_tmpdir=os.environ.get("RAY_TMPDIR")
            or ctx.cfg["storage"]["ray_tmpdir"],
            log_prefix=f"[R8R14 {phase}]",
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
                        print(
                            f"[R8R14 {phase}] waiting {completed}/{len(pending)}",
                            flush=True,
                        )
                        continue
                    ref = ready[0]
                    spec = refs.pop(ref)
                    try:
                        result = ray.get(ref)
                    except Exception as exc:
                        result = {
                            "schema_version": 1,
                            "stage": STAGE,
                            "campaign_identity": IDENTITY,
                            "controller_revision": CONTROLLER_REVISION,
                            "experiment_id": spec["experiment_id"],
                            "spec": copy.deepcopy(spec),
                            "success": False,
                            "completed": True,
                            "failure_reason": repr(exc),
                            "execution_failure_class": "ray_actor_runtime_error",
                            "trajectory": [],
                            "controller_trace": [],
                            "traceback": traceback.format_exc(),
                        }
                    r8r7.r8._write_gz(
                        raw_dir / f"{spec['experiment_id']}.json.gz", result
                    )
                    completed += 1
                    print(f"[R8R14 {phase}] {completed}/{len(pending)}", flush=True)
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
        raise ValueError(f"unsupported R8R14 backend: {backend}")
    successful = sum(
        _result_complete(raw_dir / f"{spec['experiment_id']}.json.gz", spec)
        for spec in specs
    )
    return {
        "phase": phase,
        "expected": len(specs),
        "pending_at_start": len(pending),
        "successful": successful,
        "passed": successful == len(specs),
    }


def _source_trace_semantic_projection(
    source: Mapping[str, Any], current: Mapping[str, Any]
) -> bool:
    return all(
        current.get(key) == value
        for key, value in source.items()
        if not key.startswith(SOURCE_WRAPPER_METADATA_PREFIXES)
    )


def audit_raw_phase(ctx: Context, phase: str) -> dict[str, Any]:
    specs = _phase_specs(ctx, phase)
    _, sources = _source_baselines(ctx)
    rows = []
    contract = ctx.cfg["controller_contract"]
    decisions = set(map(int, ctx.cfg["schedule_contract"]["decision_task_steps"]))
    for spec in specs:
        path = ctx.paths.phase_raw(phase) / f"{spec['experiment_id']}.json.gz"
        result = (
            r8r7.r8._read_gz(path) if _result_complete(path, spec, require_success=False) else {}
        )
        trajectory = result.get("trajectory") or []
        trace = result.get("controller_trace") or []
        horizon = int(spec["horizon_steps"])
        full = len(trajectory) == horizon + 1 and len(trace) == horizon
        source = sources[str(spec["source_r8r7_baseline_experiment_id"])]
        prefix_state = bool(
            full
            and all(
                r8r7.r8.r4._semantic_state(current)
                == r8r7.r8.r4._semantic_state(reference)
                for current, reference in zip(
                    trajectory[: PREFIX_END + 1], source["trajectory"][: PREFIX_END + 1]
                )
            )
        )
        prefix_trace = bool(
            full
            and all(
                _source_trace_semantic_projection(reference, current)
                for current, reference in zip(
                    trace[:PREFIX_END], source["controller_trace"][:PREFIX_END]
                )
            )
        )
        calibration = bool(full and r8r7.r8.r4._calibration_exact(trace))
        events = [
            trace[step].get("r3c3t13s24d1r14r8r14_event_detail") or {}
            for step in range(PREFIX_END, horizon)
        ] if full else []
        event_names = [
            trace[step].get("r3c3t13s24d1r14r8r14_event")
            for step in range(PREFIX_END, horizon)
        ] if full else []
        event_exact = bool(
            full
            and len(events) == horizon - PREFIX_END
            and all(
                name == ("staircase_issue" if step in decisions else "staircase_refresh")
                and event.get("passed") is True
                and all(bool(value) for value in (event.get("criteria") or {}).values())
                for step, name, event in zip(
                    range(PREFIX_END, horizon), event_names, events
                )
            )
        )
        target_chain = True
        active_target: list[str] | None = None
        if event_exact:
            for step, name, event in zip(range(PREFIX_END, horizon), event_names, events):
                if name == "staircase_issue":
                    active_target = list(event.get("target_card15_fields") or [])
                elif list(event.get("stored_target_card15_fields") or []) != active_target:
                    target_chain = False
        else:
            target_chain = False
        actions = np.asarray(
            [row.get("action_norm_tsc", []) for row in trace], dtype=float
        )
        currents = np.asarray(
            [row.get("currents_a_tsc", []) for row in trajectory], dtype=float
        )
        finite = bool(
            full
            and actions.shape == (horizon, N_COILS)
            and currents.shape == (horizon + 1, N_COILS)
            and np.all(np.isfinite(actions))
            and np.all(np.isfinite(currents))
            and all(
                math.isfinite(float(row[key]))
                for row in trajectory
                for key in ("R", "Z", "Ip")
            )
            and all(
                np.all(np.isfinite(np.asarray(row.get("wire_currents_a", []), dtype=float)))
                for row in trajectory
            )
            and not any(bool(row.get("abnormal")) for row in trajectory)
        )
        forbidden = sum(
            any(
                bool(row.get(key))
                for key in (
                    "r3c3t13s24d1r14r8r14_forbidden_input_used",
                    "r3c3t13s24d1r14r8r14_pair_or_history_label_used",
                    "r3c3t13s24d1r14r8r14_future_measurement_used",
                    "r3c3t13s24d1r14r8r14_future_action_used",
                    "r3c3t13s24d1r14r8r14_source_result_used",
                    "r3c3t13s24d1r14r8r14_hidden_wire_used",
                )
            )
            for row in trace
        )
        payload = _read(ctx.paths.variants / f"payload_{spec['experiment_id']}.json")
        minimum, maximum = r8r7.r8.d1r11.s21.s13._current_limits_tsc(payload)
        center, half = 0.5 * (minimum + maximum), 0.5 * (maximum - minimum)
        utilization = (
            float(np.max(np.abs((currents - center) / half)))
            if currents.shape == (horizon + 1, N_COILS)
            else None
        )
        issue_events = [
            event for name, event in zip(event_names, events) if name == "staircase_issue"
        ]
        refresh_events = [
            event
            for name, event in zip(event_names, events)
            if name == "staircase_refresh"
        ]
        issue_increment = max(
            (float(event["incremental_normalized_action_linf"]) for event in issue_events),
            default=None,
        )
        refresh_increment = max(
            (
                float(event["incremental_normalized_action_linf"])
                for event in refresh_events
            ),
            default=None,
        )
        passed = bool(
            result.get("success")
            and full
            and prefix_state
            and prefix_trace
            and calibration
            and event_exact
            and target_chain
            and len(issue_events) == 4
            and len(refresh_events) == horizon - PREFIX_END - 4
            and finite
            and forbidden == 0
            and issue_increment is not None
            and issue_increment
            <= float(contract["maximum_incremental_normalized_action_linf"]) + 1e-12
            and refresh_increment is not None
            and refresh_increment
            <= float(contract["maximum_incremental_normalized_action_linf"]) + 1e-12
            and utilization is not None
            and utilization <= float(contract["maximum_current_utilization"]) + 1e-12
        )
        rows.append(
            {
                "experiment_id": spec["experiment_id"],
                "pair_id": spec["pair_id"],
                "history_member": spec["history_member"],
                "runtime_success": bool(result.get("success")),
                "full_horizon": full,
                "source_prefix_state_exact": prefix_state,
                "source_prefix_trace_exact": prefix_trace,
                "calibration_exact": calibration,
                "event_exact": event_exact,
                "target_chain_exact": target_chain,
                "issue_count": len(issue_events),
                "refresh_count": len(refresh_events),
                "finite": finite,
                "forbidden_trace_count": forbidden,
                "maximum_issue_increment": issue_increment,
                "maximum_refresh_increment": refresh_increment,
                "maximum_current_utilization": utilization,
                "failure_reason": str(result.get("failure_reason") or ""),
                "passed": passed,
            }
        )
    inventory = r8r7.r8._inventory(ctx.paths.phase_raw(phase))
    expected = {"safety": 28, "qualification": 84}[phase]
    report = {
        "schema_version": 1,
        "stage": STAGE,
        "phase": phase,
        "expected_raw_count": expected,
        "raw_inventory": inventory,
        "runtime_success_count": sum(bool(row["runtime_success"]) for row in rows),
        "full_horizon_count": sum(bool(row["full_horizon"]) for row in rows),
        "source_prefix_state_exact_count": sum(
            bool(row["source_prefix_state_exact"]) for row in rows
        ),
        "source_prefix_trace_exact_count": sum(
            bool(row["source_prefix_trace_exact"]) for row in rows
        ),
        "calibration_exact_count": sum(bool(row["calibration_exact"]) for row in rows),
        "event_exact_count": sum(bool(row["event_exact"]) for row in rows),
        "target_chain_exact_count": sum(bool(row["target_chain_exact"]) for row in rows),
        "issue_count": sum(int(row["issue_count"]) for row in rows),
        "refresh_count": sum(int(row["refresh_count"]) for row in rows),
        "finite_count": sum(bool(row["finite"]) for row in rows),
        "forbidden_trace_count": sum(int(row["forbidden_trace_count"]) for row in rows),
        "maximum_issue_increment": max(
            (
                float(row["maximum_issue_increment"])
                for row in rows
                if row["maximum_issue_increment"] is not None
            ),
            default=None,
        ),
        "maximum_refresh_increment": max(
            (
                float(row["maximum_refresh_increment"])
                for row in rows
                if row["maximum_refresh_increment"] is not None
            ),
            default=None,
        ),
        "maximum_current_utilization": max(
            (
                float(row["maximum_current_utilization"])
                for row in rows
                if row["maximum_current_utilization"] is not None
            ),
            default=None,
        ),
        "passed_count": sum(bool(row["passed"]) for row in rows),
        "rows": rows,
    }
    report["passed"] = bool(
        inventory["count"] == expected
        and len(rows) == expected
        and report["passed_count"] == expected
    )
    report["route"] = ctx.cfg["routes"][
        "pass" if report["passed"] else "execution_fail"
    ]
    _write(ctx.paths.analysis / f"{phase}_raw_primary.json", report)
    return report


def authorize_safety(ctx: Context) -> dict[str, Any]:
    state = _read(ctx.paths.state)
    independent = _read(ctx.paths.analysis / "offline_independent.json")
    if (
        state.get("phase_status") != "offline_primary_ready"
        or independent.get("passed") is not True
    ):
        raise ValueError("R8R14 offline independent gate failed")
    _set_state(
        ctx,
        phase_status="safety_authorized",
        offline_independent_sha256=_sha(ctx.paths.analysis / "offline_independent.json"),
    )
    return {"stage": STAGE, "phase": "safety_authorized", "passed": True}


def run_phase(
    ctx: Context, phase: str, *, backend: str, resume: bool
) -> dict[str, Any]:
    required = {"safety": "safety_authorized", "qualification": "qualification_authorized"}[
        phase
    ]
    state = _read(ctx.paths.state)
    if state.get("phase_status") != required:
        raise ValueError(f"R8R14 {phase} is not authorized")
    if phase == "safety" and any(ctx.paths.phase_raw("qualification").glob("*.json.gz")):
        raise ValueError("R8R14 qualification raw opened before safety authorization")
    specs = _phase_specs(ctx, phase)
    execution = evaluate_specs(ctx, specs, phase=phase, backend=backend, resume=resume)
    primary = audit_raw_phase(ctx, phase)
    total = sum(r8r7.r8._inventory(ctx.paths.phase_raw(name))["count"] for name in PHASES)
    if not execution["passed"] or not primary["passed"]:
        _set_state(
            ctx,
            phase_status=f"{phase}_execution_failed",
            finished=True,
            real_tsc_executed=total > 0,
            new_raw_count=total,
            qualification_outcomes_opened=phase == "qualification",
            formal_outcomes_opened=False,
            stop_reason="runtime_restart_action_current_or_raw_gate_failed",
            verdict={"route": ctx.cfg["routes"]["execution_fail"], "passed": False},
        )
    else:
        _set_state(
            ctx,
            phase_status=f"{phase}_primary_ready",
            real_tsc_executed=True,
            new_raw_count=total,
            qualification_outcomes_opened=phase == "qualification",
            formal_outcomes_opened=False,
        )
    return {
        "stage": STAGE,
        "phase": phase,
        "execution": execution,
        "primary_raw_audit_passed": primary["passed"],
        "route": primary["route"],
    }


def repair_safety_report(ctx: Context) -> dict[str, Any]:
    """Audit immutable structured failures without evaluating a controller."""

    state = _read(ctx.paths.state)
    specs = _phase_specs(ctx, "safety")
    inventory = r8r7.r8._inventory(ctx.paths.phase_raw("safety"))
    if (
        state.get("phase_status") != "safety_authorized"
        or inventory["count"] != len(specs)
        or any(ctx.paths.phase_raw("qualification").glob("*.json.gz"))
        or not all(
            _result_complete(
                ctx.paths.phase_raw("safety") / f"{spec['experiment_id']}.json.gz",
                spec,
                require_success=False,
            )
            for spec in specs
        )
    ):
        raise ValueError("R8R14 immutable safety reporting repair precondition failed")
    raw = [
        r8r7.r8._read_gz(
            ctx.paths.phase_raw("safety") / f"{spec['experiment_id']}.json.gz"
        )
        for spec in specs
    ]
    if any(result.get("success") for result in raw):
        raise ValueError("R8R14 safety reporting repair is only for structured failures")
    plant_advance_count = sum(
        max(0, len(result.get("trajectory") or []) - 1) for result in raw
    )
    controller_trace_count = sum(len(result.get("controller_trace") or []) for result in raw)
    primary = audit_raw_phase(ctx, "safety")
    _set_state(
        ctx,
        phase_status="safety_execution_failed",
        finished=True,
        real_tsc_executed=True,
        new_raw_count=len(raw),
        qualification_outcomes_opened=False,
        formal_outcomes_opened=False,
        plant_advance_count=plant_advance_count,
        physical_action_count=controller_trace_count,
        controller_initialization_failure_count=sum(
            "per-spec issue schedule changed" in str(result.get("failure_reason") or "")
            for result in raw
        ),
        stop_reason="controller_initialization_failed_before_plant_advance",
        verdict={"route": ctx.cfg["routes"]["execution_fail"], "passed": False},
    )
    return {
        "stage": STAGE,
        "phase": "safety_reporting_repaired",
        "raw_count": len(raw),
        "plant_advance_count": plant_advance_count,
        "physical_action_count": controller_trace_count,
        "primary_raw_audit_passed": primary["passed"],
        "route": primary["route"],
        "passed": True,
    }


def authorize_qualification(ctx: Context) -> dict[str, Any]:
    state = _read(ctx.paths.state)
    primary = _read(ctx.paths.analysis / "safety_raw_primary.json")
    independent = _read(ctx.paths.analysis / "safety_raw_independent.json")
    if (
        state.get("phase_status") != "safety_primary_ready"
        or primary.get("passed") is not True
        or independent.get("passed") is not True
        or independent.get("primary_agreement") is not True
    ):
        raise ValueError("R8R14 safety independent gate failed")
    _set_state(
        ctx,
        phase_status="qualification_authorized",
        safety_independent_sha256=_sha(ctx.paths.analysis / "safety_raw_independent.json"),
    )
    return {"stage": STAGE, "phase": "qualification_authorized", "passed": True}


def _formal_row(
    evaluator: Any, result: Mapping[str, Any], meta: Mapping[str, Any]
) -> dict[str, Any]:
    return r8r11._formal_row(evaluator, result, meta)


def compute_formal_authority(ctx: Context) -> dict[str, Any]:
    specs = _saved_specs(ctx)
    baseline_specs, baseline_results = _source_baselines(ctx)
    source_specs, source_results = _source_r8r12_candidates(ctx)
    evaluators, _ = r8r7.r8.d1r11._formal_callback(
        ctx.source_ctx.r8_ctx.d1r11_ctx, baseline_specs
    )
    evaluator_by_context = {
        (str(spec["pair_id"]), str(spec["history_member"])):
        evaluators[str(spec["experiment_id"])]
        for spec in baseline_specs
    }
    rows = []
    for spec in baseline_specs:
        rows.append(
            _formal_row(
                evaluators[str(spec["experiment_id"])],
                baseline_results[str(spec["experiment_id"])],
                {
                    "kind": "baseline",
                    "source": "R8R7",
                    "experiment_id": spec["experiment_id"],
                    "pair_id": spec["pair_id"],
                    "history_member": spec["history_member"],
                    "direction_index": -1,
                    "sign": 0,
                },
            )
        )
    for spec in source_specs:
        key = (str(spec["pair_id"]), str(spec["history_member"]))
        rows.append(
            _formal_row(
                evaluator_by_context[key],
                source_results[str(spec["experiment_id"])],
                {
                    "kind": "candidate",
                    "source": "R8R12",
                    "experiment_id": spec["experiment_id"],
                    "pair_id": key[0],
                    "history_member": key[1],
                    "direction_index": 2,
                    "sign": 1,
                },
            )
        )
    for spec in specs:
        result = r8r7.r8._read_gz(
            ctx.paths.phase_raw(str(spec["partition"]))
            / f"{spec['experiment_id']}.json.gz"
        )
        rows.append(
            _formal_row(
                evaluator_by_context[(str(spec["pair_id"]), str(spec["history_member"]))],
                result,
                {
                    "kind": "candidate",
                    "source": "R8R14",
                    "experiment_id": spec["experiment_id"],
                    "pair_id": spec["pair_id"],
                    "history_member": spec["history_member"],
                    "direction_index": int(spec["r8r14_direction_index"]),
                    "sign": int(spec["r8r14_sign"]),
                },
            )
        )
    tolerance = float(ctx.cfg["formal_contract"]["metric_equivalence_absolute_tolerance"])
    equivalence = bool(
        all(
            row["formal_contract_pass"] == row["existing_pass"]
            and row["formal_best_arrival_ms"] == row["existing_arrival_ms"]
            and float(row["maximum_margin_abs_difference"]) <= tolerance
            for row in rows
        )
    )
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault((str(row["pair_id"]), str(row["history_member"])), []).append(row)
    contexts = []
    for key, group in sorted(groups.items()):
        baseline = [row for row in group if row["kind"] == "baseline"]
        candidates = [row for row in group if row["kind"] == "candidate"]
        members = {(int(row["direction_index"]), int(row["sign"])) for row in candidates}
        if len(baseline) != 1 or len(candidates) != 8 or members != {
            (direction, sign) for direction in range(4) for sign in (-1, 1)
        }:
            raise ValueError("R8R14 formal context coverage changed")
        base = baseline[0]
        oracle = max(
            [base, *candidates],
            key=lambda row: (
                float(row["formal_minimum_signed_margin"]),
                float(row["formal_mean_signed_margin"]),
                row["kind"] == "baseline",
            ),
        )
        best_candidate = max(
            candidates,
            key=lambda row: (
                float(row["formal_minimum_signed_margin"]),
                float(row["formal_mean_signed_margin"]),
                -int(row["direction_index"]),
                -int(row["sign"]),
            ),
        )
        contexts.append(
            {
                "pair_id": key[0],
                "history_member": key[1],
                "baseline": base,
                "candidates": sorted(
                    candidates,
                    key=lambda row: (int(row["direction_index"]), int(row["sign"])),
                ),
                "best_candidate": best_candidate,
                "best_candidate_minimum_margin_gain": float(
                    best_candidate["formal_minimum_signed_margin"]
                )
                - float(base["formal_minimum_signed_margin"]),
                "failed_baseline_repaired": bool(
                    not base["formal_contract_pass"]
                    and any(row["formal_contract_pass"] for row in candidates)
                ),
                "held_oracle_formal_pass": bool(oracle["formal_contract_pass"]),
                "held_oracle_experiment_id": oracle["experiment_id"],
            }
        )
    baseline_pass = sum(bool(row["baseline"]["formal_contract_pass"]) for row in contexts)
    repairs = sum(bool(row["failed_baseline_repaired"]) for row in contexts)
    oracle_pass = sum(bool(row["held_oracle_formal_pass"]) for row in contexts)
    gains = [
        float(row["best_candidate_minimum_margin_gain"])
        for row in contexts
        if not row["baseline"]["formal_contract_pass"]
    ]
    gate = ctx.cfg["scientific_gate"]
    scientific = bool(
        baseline_pass == int(gate["required_baseline_formal_pass_count"])
        and len(contexts) - baseline_pass == int(gate["required_failed_baseline_count"])
        and repairs >= int(gate["minimum_repaired_failed_baseline_count"])
        and oracle_pass >= int(gate["minimum_held_oracle_formal_pass_count"])
        and oracle_pass > baseline_pass
    )
    candidate_summaries = []
    for direction in range(4):
        for sign in (-1, 1):
            selected = [
                row for row in rows
                if row["kind"] == "candidate"
                and int(row["direction_index"]) == direction
                and int(row["sign"]) == sign
            ]
            candidate_summaries.append(
                {
                    "direction_index": direction,
                    "sign": sign,
                    "source": selected[0]["source"] if selected else "",
                    "context_count": len(selected),
                    "formal_pass_count": sum(bool(row["formal_contract_pass"]) for row in selected),
                    "repaired_failed_baseline_count": sum(
                        not context["baseline"]["formal_contract_pass"]
                        and next(
                            row for row in context["candidates"]
                            if int(row["direction_index"]) == direction
                            and int(row["sign"]) == sign
                        )["formal_contract_pass"]
                        for context in contexts
                    ),
                    "baseline_pass_regression_count": sum(
                        context["baseline"]["formal_contract_pass"]
                        and not next(
                            row for row in context["candidates"]
                            if int(row["direction_index"]) == direction
                            and int(row["sign"]) == sign
                        )["formal_contract_pass"]
                        for context in contexts
                    ),
                }
            )
    return {
        "row_count": len(rows),
        "formal_metric_equivalence_passed": equivalence,
        "maximum_margin_abs_difference": max(
            float(row["maximum_margin_abs_difference"]) for row in rows
        ),
        "context_count": len(contexts),
        "baseline_formal_pass_count": baseline_pass,
        "failed_baseline_count": len(contexts) - baseline_pass,
        "source_r8r12_formal_pass_count": sum(
            bool(row["formal_contract_pass"])
            for row in rows if row["source"] == "R8R12"
        ),
        "new_candidate_formal_pass_count": sum(
            bool(row["formal_contract_pass"])
            for row in rows if row["source"] == "R8R14"
        ),
        "repaired_failed_baseline_count": repairs,
        "held_oracle_formal_pass_count": oracle_pass,
        "failed_baseline_best_candidate_margin_gain": {
            "minimum": min(gains),
            "median": statistics.median(gains),
            "maximum": max(gains),
        },
        "candidate_summaries": candidate_summaries,
        "context_rows": contexts,
        "rows": rows,
        "scientific_gate_passed": scientific,
    }


def finalize_primary(ctx: Context) -> dict[str, Any]:
    state = _read(ctx.paths.state)
    reports = [
        _read(ctx.paths.analysis / f"{phase}_raw_{kind}.json")
        for phase in PHASES
        for kind in ("primary", "independent")
    ]
    if (
        state.get("phase_status") != "qualification_primary_ready"
        or not all(report.get("passed") is True for report in reports)
        or not all(
            report.get("primary_agreement") is True
            for report in reports
            if report.get("audit_kind")
        )
    ):
        raise ValueError("R8R14 raw independent gates incomplete")
    formal = compute_formal_authority(ctx)
    integrity = bool(
        formal["formal_metric_equivalence_passed"]
        and formal["row_count"] == 144
        and formal["context_count"] == 16
        and formal["source_r8r12_formal_pass_count"]
        == int(ctx.cfg["source_r8r12"]["candidate_formal_pass_count"])
    )
    scientific = bool(integrity and formal["scientific_gate_passed"])
    route = ctx.cfg["routes"]["pass" if scientific else "authority_fail"]
    detailed = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "source_authenticated": True,
        "integrity_gate_passed": integrity,
        "scientific_gate_passed": scientific,
        "formal_authority": formal,
        "safety_raw_inventory": reports[0]["raw_inventory"],
        "qualification_raw_inventory": reports[2]["raw_inventory"],
        "new_raw_count": 112,
        "real_tsc_executed": True,
        "route": route,
        "passed": scientific,
    }
    _write(ctx.paths.analysis / "primary_detailed.json", detailed)
    summary = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "source_authenticated": True,
        "integrity_gate_passed": integrity,
        "scientific_gate_passed": scientific,
        "formal_metric_equivalence_passed": formal[
            "formal_metric_equivalence_passed"
        ],
        "maximum_margin_abs_difference": formal["maximum_margin_abs_difference"],
        "context_count": formal["context_count"],
        "baseline_formal_pass_count": formal["baseline_formal_pass_count"],
        "failed_baseline_count": formal["failed_baseline_count"],
        "source_r8r12_formal_pass_count": formal["source_r8r12_formal_pass_count"],
        "new_candidate_formal_pass_count": formal["new_candidate_formal_pass_count"],
        "candidate_summaries": formal["candidate_summaries"],
        "repaired_failed_baseline_count": formal["repaired_failed_baseline_count"],
        "held_oracle_formal_pass_count": formal["held_oracle_formal_pass_count"],
        "failed_baseline_best_candidate_margin_gain": formal[
            "failed_baseline_best_candidate_margin_gain"
        ],
        "new_raw_count": 112,
        "real_tsc_executed": True,
        "route": route,
        "passed": scientific,
    }
    _write(ctx.paths.analysis / "primary_summary.json", summary)
    _set_state(
        ctx,
        phase_status="final_primary_ready",
        formal_outcomes_opened=True,
        primary_route=route,
        primary_summary_sha256=_sha(ctx.paths.analysis / "primary_summary.json"),
    )
    return summary


def postprocess(ctx: Context) -> dict[str, Any]:
    state = _read(ctx.paths.state)
    primary = _read(ctx.paths.analysis / "primary_summary.json")
    independent = _read(ctx.paths.analysis / "final_independent.json")
    if (
        state.get("phase_status") != "final_primary_ready"
        or independent.get("passed") is not True
        or independent.get("primary_route_agreement") is not True
        or independent.get("primary_outcome_agreement") is not True
        or independent.get("primary_numerical_agreement") is not True
    ):
        raise ValueError("R8R14 final independent agreement failed")
    final = copy.deepcopy(primary)
    final.update(
        {
            "phase": "final",
            "primary_detailed_sha256": _sha(ctx.paths.analysis / "primary_detailed.json"),
            "primary_summary_sha256": _sha(ctx.paths.analysis / "primary_summary.json"),
            "independent_sha256": _sha(ctx.paths.analysis / "final_independent.json"),
            "stage_manifest_sha256": _sha(ctx.paths.manifest),
        }
    )
    _write(ctx.paths.analysis / "final_report.json", final)
    _set_state(
        ctx,
        phase_status="complete",
        finished=True,
        real_tsc_executed=True,
        new_raw_count=112,
        qualification_outcomes_opened=True,
        formal_outcomes_opened=True,
        final_report_sha256=_sha(ctx.paths.analysis / "final_report.json"),
        final_independent_sha256=_sha(ctx.paths.analysis / "final_independent.json"),
        stop_reason="" if final["passed"] else "formal_authority_gate_failed",
        verdict={"route": final["route"], "passed": bool(final["passed"])},
    )
    return final


def execute(
    ctx: Context, *, command: str, backend: str, resume: bool
) -> dict[str, Any]:
    if command == "offline":
        return prepare_offline(ctx)
    if command == "authorize-safety":
        return authorize_safety(ctx)
    if command in PHASES:
        return run_phase(ctx, command, backend=backend, resume=resume)
    if command == "repair-safety-report":
        return repair_safety_report(ctx)
    if command == "authorize-qualification":
        return authorize_qualification(ctx)
    if command == "finalize-primary":
        return finalize_primary(ctx)
    if command == "postprocess":
        return postprocess(ctx)
    raise ValueError(f"unsupported R8R14 command: {command}")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--r8r7-run", type=Path, required=True)
    parser.add_argument("--r8r12-run", type=Path, required=True)
    parser.add_argument("--r8r13-run", type=Path, required=True)
    parser.add_argument("--r8-run", type=Path, required=True)
    parser.add_argument("--r8r1-output", type=Path, required=True)
    parser.add_argument("--r8r6-run", type=Path, required=True)
    for name in (
        "source-d1r11-run",
        "source-r2-run",
        "source-r4-run",
        "source-r6-run",
        "source-s21-run",
        "source-s23r1-output",
        "source-s24-run",
        "source-d1r9-v1",
        "source-d1r9-v2",
        "source-d1r10-run",
        "source-d1r10-audit",
        "source-stage42r3b-run",
        "source-stage42r3c3-run",
        "source-stage42r3c3-bank-dir",
        "source-stage42r3c3t1-run",
        "source-stage42r3c3t1-audit-dir",
        "source-stage42r3c3t3-controller-bank",
        "q1-run",
        "q2-run",
        "q1-audit",
        "q2-audit",
        "r3b-server-audit",
        "r3b-snapshot-checks",
    ):
        parser.add_argument(
            f"--{name}", dest=name.replace("-", "_"), type=Path, required=True
        )
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument(
        "--command",
        choices=(
            "offline",
            "authorize-safety",
            "safety",
            "repair-safety-report",
            "authorize-qualification",
            "qualification",
            "finalize-primary",
            "postprocess",
        ),
        required=True,
    )
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
