#!/usr/bin/env python3
"""Zero-TSC replay of the fixed S23R1 amplitude-coded H16 schedule."""

from __future__ import annotations

import argparse
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from docs.codex.audit_tools import (
    stage4_2r3c3t13s23d1_bounded_schedule_redesign_search as d1,
)


s23 = d1.s23
STAGE = "Stage4.2R3c3T13S23R1"
IDENTITY = "amplitude_coded_h16_exact_card15_preflight_v1"
ISSUE_STEPS = (10, 13, 15, 17)
CANCEL_STEPS = (11, 14, 16, 18)
DIRECTIONS = s23.DIRECTIONS


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _digest(value: Any) -> str:
    text = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False,
    )
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        + "\n",
        encoding="utf-8",
    )


def _validate_design(cfg: Mapping[str, Any]) -> None:
    source = cfg["source_contract"]
    schedule = cfg["schedule_contract"]
    formal = cfg["formal_contract"]
    gate = cfg["primary_gate"]
    execution = cfg["execution_contract"]
    scope = cfg["scientific_scope"]
    if (
        int(cfg.get("schema_version", -1)) != 1
        or cfg.get("stage") != STAGE
        or cfg.get("identity") != IDENTITY
        or cfg.get("package_revision")
        != "r42r3c3t13s23r1_amplitude_coded_hadamard_preflight_v1"
        or cfg.get("selection_status")
        != "frozen_after_s23d1_forensics_before_s23r1_implementation_or_actual_coordinate_replay"
        or cfg.get("design_document_sha256")
        != "1661c1356c2e31899f8163e6861e97d2d5f8d62dd77263a1b14ef520275ca0f4"
        or str(source["s21_package_commit"]) != "98dc353"
        or int(source["s21_raw_count"]) != 360
        or int(source["s21_raw_total_bytes"]) != 21083271
        or int(source["expected_baseline_formal_pass_count"]) != 16
        or int(source["expected_probe_formal_pass_count"]) != 99
        or source["required_s22_route"]
        != "AFFINE_STATE10_AUTHORITY_FAIL_SEQUENTIAL_MODEL_REQUIRED"
        or source["required_s23_route"]
        != "SEQUENTIAL_HADAMARD_LATTICE_PREFLIGHT_FAIL_SCHEDULE_REDESIGN"
        or int(source["required_s23_issue_pass"]) != 1920
        or int(source["required_s23_cancel_pass"]) != 3720
        or source["required_s23d1_route"]
        != "BOUNDED_TERNARY_SCHEDULE_SEARCH_FAIL_NEW_EXCITATION_ARCHITECTURE_REQUIRED"
        or int(source["required_s23d1_feasible_pairs_per_step"]) != 103
        or int(source["required_s23d1_tested_schedules"]) != 100000
        or tuple(schedule["context_key_fields"]) != ("pair_id", "history_member")
        or int(schedule["expected_context_count"]) != 40
        or schedule["baseline_probe_id"] != "lattice_baseline"
        or tuple(schedule["ordered_directions"]) != DIRECTIONS
        or tuple(map(int, schedule["issue_task_steps"])) != ISSUE_STEPS
        or tuple(map(int, schedule["cancel_task_steps"])) != CANCEL_STEPS
        or tuple(map(int, schedule["issue_effect_states"])) != (11, 14, 16, 18)
        or tuple(map(int, schedule["cancel_effect_states"])) != (12, 15, 17, 19)
        or int(schedule["adjacent_cancel_offset"]) != 1
        or int(schedule["hadamard_order"]) != 16
        or schedule["hadamard_construction"]
        != "unpermuted_sylvester_h2_kronecker_power_4"
        or schedule["column_assignment"] != "4_times_slot_plus_direction"
        or schedule["canonical_pattern_amplitudes"]
        != {"++++": 0.25, "+-+-": 0.25, "++--": 0.5, "+--+": 0.5}
        or tuple(
            int(schedule[key]) for key in (
                "primary_sequence_rows", "central_sign_primary_rows",
                "central_sign_sentinel_rows", "total_sequence_rows",
            )
        ) != (16, 8, 8, 24)
        or int(schedule["dynamic_exact_search_radius"]) != 16
        or float(schedule["maximum_absolute_coordinate_error"]) != 0.07
        or float(schedule["maximum_inactive_coordinate_abs"]) != 0.07
        or float(schedule["minimum_active_absolute_coordinate"]) != 0.18
        or float(schedule["minimum_desired_applied_current_cosine"]) != 0.98
        or float(schedule["maximum_relative_off_basis_residual"]) != 0.10
        or float(schedule["maximum_incremental_normalized_action_linf"]) != 0.25
        or float(schedule["maximum_total_normalized_action_abs"]) != 1.0
        or float(schedule["maximum_current_utilization"]) != 0.55
        or int(schedule["required_global_rank"]) != 16
        or float(schedule["maximum_global_normalized_condition"]) != 3.0
        or int(schedule["required_slot_rank"]) != 4
        or float(schedule["maximum_slot_normalized_condition"]) != 3.0
        or float(schedule["minimum_late_column_residual_outside_slot0_span"]) != 0.5
        or not bool(schedule["require_decimal_exact_central_target_symmetry"])
        or not bool(schedule["require_exact_stored_center_cancellation"])
        or not bool(schedule["require_exact_zero_target_jump_net"])
        or tuple(
            int(formal[key]) for key in (
                "normal_arrival_deadline_step", "normal_hold_through_step",
                "weak_arrival_deadline_step", "weak_hold_through_step",
                "arrival_streak_steps",
            )
        ) != (25, 35, 27, 37, 3)
        or float(formal["position_tolerance_m"]) != 0.03
        or float(formal["speed_tolerance_m_per_s"]) != 0.1
        or float(formal["ip_tolerance_A"]) != 10000.0
        or bool(formal["arrival_deadline_expansion_allowed"])
        or tuple(
            int(gate[key]) for key in (
                "source_raw_authentication_required", "baseline_authentication_required",
                "probe_authentication_required", "fixed_basis_contexts_required",
                "finite_constructions_required", "issue_gate_pass_required",
                "cancellation_gate_pass_required", "central_sign_gate_pass_required",
                "global_rank_condition_contexts_required",
                "slot_rank_condition_blocks_required", "late_novelty_contexts_required",
            )
        ) != (360, 40, 320, 40, 7680, 3840, 3840, 1280, 40, 160, 40)
        or not bool(execution["server_side_only_for_large_raw"])
        or not bool(execution["read_raw_in_place"])
        or int(execution["new_raw_count"]) != 0
        or any(bool(execution[key]) for key in (
            "ray_executed", "gotsc_executed", "tsc_executed",
            "controller_executed", "snapshot_creation_allowed",
        ))
        or int(execution["plant_steps_executed"]) != 0
        or not bool(scope["adaptive_to_d1_catalog"])
        or not bool(scope["fixed_candidate_only"])
        or bool(scope["plant_response_simulated"])
        or bool(scope["real_mpc_executed"])
        or bool(scope["global_plant_reachability_claimed"])
        or bool(scope["hidden_history_robustness_claimed"])
        or not bool(scope["pass_authorizes_s24_design_only"])
        or bool(scope["probe_trajectories_are_demonstrations"])
        or bool(scope["bc_dagger_or_rl_allowed"])
    ):
        raise ValueError("T13S23R1 frozen design changed")


def _coded_coordinate(signs: Sequence[int], cfg: Mapping[str, Any]) -> np.ndarray:
    block = np.asarray(signs, dtype=int).reshape(4)
    if set(map(int, block)) - {-1, 1}:
        raise ValueError("S23R1 block must contain only signs")
    orientation = int(block[0])
    canonical = orientation * block
    pattern = "".join("+" if value == 1 else "-" for value in canonical)
    amplitudes = cfg["schedule_contract"]["canonical_pattern_amplitudes"]
    if pattern not in amplitudes:
        raise ValueError(f"S23R1 unexpected H16 block pattern: {pattern}")
    return float(amplitudes[pattern]) * block.astype(float)


def _requested_matrix(cfg: Mapping[str, Any]) -> np.ndarray:
    sequence = s23._sequence_matrix()
    matrix = np.zeros((24, 16), dtype=float)
    for row in range(24):
        for slot in range(4):
            matrix[row, 4 * slot:4 * slot + 4] = _coded_coordinate(
                sequence[row, 4 * slot:4 * slot + 4], cfg
            )
    metrics = s23._matrix_metrics(matrix, cfg)
    if (
        not metrics["global_pass"]
        or int(metrics["slot_pass_count"]) != 4
        or not metrics["late_novelty_pass"]
        or not np.array_equal(matrix[16:], -matrix[:8])
    ):
        raise ValueError("S23R1 requested matrix lost frozen geometry")
    return matrix


def _authenticate_d1(
    output: Path, config_path: Path, implementation_path: Path,
    cfg: Mapping[str, Any],
) -> dict[str, Any]:
    source = cfg["source_contract"]
    if output.name != str(source["s23d1_output_name"]):
        raise ValueError("immutable S23D1 output name mismatch")
    paths = {
        "detailed": output / "stage4_2r3c3t13s23d1_bounded_schedule_search_v1.json",
        "summary": output / "stage4_2r3c3t13s23d1_summary_v1.json",
        "manifest": output / "stage4_2r3c3t13s23d1_manifest_v1.json",
    }
    expected = {
        "detailed": source["s23d1_detailed_sha256"],
        "summary": source["s23d1_summary_sha256"],
        "manifest": source["s23d1_manifest_sha256"],
    }
    hashes = {name: _sha256(path) for name, path in paths.items()}
    if (
        _sha256(config_path) != str(source["s23d1_config_sha256"])
        or _sha256(implementation_path) != str(source["s23d1_implementation_sha256"])
        or any(hashes[name] != str(expected[name]) for name in expected)
    ):
        raise ValueError("immutable S23D1 source hash mismatch")
    detailed = _read_json(paths["detailed"])
    summary = _read_json(paths["summary"])
    manifest = _read_json(paths["manifest"])
    feasible = summary.get("feasible_sign_pairs_by_issue_step") or {}
    if (
        detailed.get("route") != source["required_s23d1_route"]
        or summary.get("route") != source["required_s23d1_route"]
        or bool(summary.get("candidate_found"))
        or int(summary.get("total_tested_schedules", -1))
        != int(source["required_s23d1_tested_schedules"])
        or set(map(int, feasible.values()))
        != {int(source["required_s23d1_feasible_pairs_per_step"])}
        or int(summary.get("source_raw_authentication_count", -1)) != 360
        or bool(manifest.get("ray_gotsc_tsc_plant_or_controller_executed"))
        or int(manifest.get("new_raw_files_created", -1)) != 0
    ):
        raise ValueError("immutable S23D1 result changed")
    return {
        "paths": {name: str(path) for name, path in paths.items()},
        "hashes": hashes,
        "route": summary["route"],
        "feasible_pairs_per_step": feasible,
        "total_tested_schedules": int(summary["total_tested_schedules"]),
    }


def _context_replay(
    ctx: Any, baseline: Mapping[str, Any], cfg: Mapping[str, Any]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    sequence = s23._sequence_matrix()
    requested = _requested_matrix(cfg)
    (
        field_basis, turns, minimum, maximum, max_delta, actuator, basis_audit,
    ) = s23._basis_and_actuator(ctx, baseline)
    adapter_cfg = {"search_contract": cfg["schedule_contract"]}
    cancel_cache = {
        slot: d1._cancel_construction(
            ctx=ctx, baseline=baseline, issue_step=ISSUE_STEPS[slot],
            turns=turns, minimum=minimum, maximum=maximum,
            max_delta=max_delta, actuator=actuator, cfg=adapter_cfg,
        )
        for slot in range(4)
    }
    actual = np.zeros((24, 16), dtype=float)
    rows = []
    by_sequence_slot: dict[tuple[int, int], dict[str, Any]] = {}
    for row_index in range(24):
        for slot in range(4):
            desired = requested[row_index, 4 * slot:4 * slot + 4]
            issue = d1._issue_construction(
                ctx=ctx, baseline=baseline, issue_step=ISSUE_STEPS[slot],
                desired_coordinate=desired, field_basis=field_basis,
                turns=turns, minimum=minimum, maximum=maximum,
                max_delta=max_delta, actuator=actuator, cfg=adapter_cfg,
            )
            cancel = cancel_cache[slot]
            centers = tuple(
                s23.s22.s21.s16.s9._decimal_field(value)
                for value in issue["center_fields"]
            )
            targets = tuple(
                s23.s22.s21.s16.s9._decimal_field(value)
                for value in issue["target_fields"]
            )
            zero_net = all(
                (target - center) + (center - target) == Decimal(0)
                for center, target in zip(centers, targets)
            )
            finite = bool(
                issue["criteria"]["finite"]
                and all(math.isfinite(float(cancel[key])) for key in (
                    "incremental_normalized_action_linf",
                    "total_normalized_action_abs", "predicted_current_utilization",
                ))
            )
            event = {
                "sequence_index": row_index,
                "slot": slot,
                "schedule_signs": sequence[
                    row_index, 4 * slot:4 * slot + 4
                ].astype(int).tolist(),
                "issue_task_step": ISSUE_STEPS[slot],
                "cancel_task_step": CANCEL_STEPS[slot],
                "desired_coordinate": desired.tolist(),
                "actual_coordinate": issue["coordinate"].tolist(),
                "maximum_absolute_coordinate_error": float(
                    issue["maximum_absolute_coordinate_error"]
                ),
                "minimum_active_absolute_coordinate": float(
                    issue["minimum_active_absolute_coordinate"]
                ),
                "desired_applied_current_cosine": float(
                    issue["desired_applied_current_cosine"]
                ),
                "relative_off_basis_residual": float(
                    issue["relative_off_basis_residual"]
                ),
                "issue_incremental_normalized_action_linf": float(
                    issue["incremental_normalized_action_linf"]
                ),
                "issue_total_normalized_action_abs": float(
                    issue["total_normalized_action_abs"]
                ),
                "issue_predicted_current_utilization": float(
                    issue["predicted_current_utilization"]
                ),
                "issue_center_fields": list(issue["center_fields"]),
                "issue_target_fields": list(issue["target_fields"]),
                "issue_criteria": issue["criteria"],
                "issue_gate_pass": bool(issue["passed"]),
                "cancel_incremental_normalized_action_linf": float(
                    cancel["incremental_normalized_action_linf"]
                ),
                "cancel_total_normalized_action_abs": float(
                    cancel["total_normalized_action_abs"]
                ),
                "cancel_predicted_current_utilization": float(
                    cancel["predicted_current_utilization"]
                ),
                "cancel_criteria": cancel["criteria"],
                "cancellation_target_exact": bool(cancel["criteria"]["target_exact"]),
                "exact_zero_target_jump_net": zero_net,
                "cancellation_gate_pass": bool(cancel["passed"] and zero_net),
                "finite_issue_and_cancellation": finite,
            }
            rows.append(event)
            by_sequence_slot[(row_index, slot)] = event
            actual[row_index, 4 * slot:4 * slot + 4] = issue["coordinate"]
    matrix = s23._matrix_metrics(actual, cfg)
    central_rows = []
    for primary in range(8):
        sentinel = 16 + primary
        for slot in range(4):
            plus = by_sequence_slot[(primary, slot)]
            minus = by_sequence_slot[(sentinel, slot)]
            center = tuple(
                s23.s22.s21.s16.s9._decimal_field(value)
                for value in plus["issue_center_fields"]
            )
            plus_target = tuple(
                s23.s22.s21.s16.s9._decimal_field(value)
                for value in plus["issue_target_fields"]
            )
            minus_target = tuple(
                s23.s22.s21.s16.s9._decimal_field(value)
                for value in minus["issue_target_fields"]
            )
            passed = bool(
                plus["issue_center_fields"] == minus["issue_center_fields"]
                and all(p + m == 2 * c for p, m, c in zip(
                    plus_target, minus_target, center
                ))
            )
            central_rows.append({
                "primary_sequence": primary,
                "sentinel_sequence": sentinel,
                "slot": slot,
                "decimal_exact_target_symmetry": passed,
            })
    spec = baseline["spec"]
    basis_pass = bool(
        int(basis_audit["fixed_basis_rank"]) == 4
        and bool(basis_audit["fixed_basis_constant_through_state20"])
        and float(basis_audit["fixed_basis_normalized_condition"])
        <= float(ctx.base_ctx.cfg["lattice_probe"]["maximum_fixed_field_basis_condition"])
        + 1e-12
    )
    context = {
        "pair_id": str(spec["pair_id"]),
        "history_member": str(spec["history_member"]),
        "partition": str(spec["partition"]),
        "baseline_experiment_id": str(baseline["experiment_id"]),
        "baseline_raw_sha256": str(baseline["_s22_raw_sha256"]),
        "basis_audit": basis_audit,
        "basis_pass": basis_pass,
        "finite_construction_count": 2 * sum(
            bool(row["finite_issue_and_cancellation"]) for row in rows
        ),
        "issue_gate_pass_count": sum(bool(row["issue_gate_pass"]) for row in rows),
        "cancellation_gate_pass_count": sum(
            bool(row["cancellation_gate_pass"]) for row in rows
        ),
        "central_sign_gate_pass_count": sum(
            bool(row["decimal_exact_target_symmetry"]) for row in central_rows
        ),
        "central_sign_rows": central_rows,
        "matrix_metrics": matrix,
        "maximum_issue_incremental_normalized_action_linf": max(
            float(row["issue_incremental_normalized_action_linf"]) for row in rows
        ),
        "maximum_cancel_incremental_normalized_action_linf": max(
            float(row["cancel_incremental_normalized_action_linf"]) for row in rows
        ),
        "maximum_total_normalized_action_abs": max(
            max(float(row["issue_total_normalized_action_abs"]),
                float(row["cancel_total_normalized_action_abs"])) for row in rows
        ),
        "maximum_predicted_current_utilization": max(
            max(float(row["issue_predicted_current_utilization"]),
                float(row["cancel_predicted_current_utilization"])) for row in rows
        ),
        "maximum_absolute_coordinate_error": max(
            float(row["maximum_absolute_coordinate_error"]) for row in rows
        ),
        "minimum_desired_applied_current_cosine": min(
            float(row["desired_applied_current_cosine"]) for row in rows
        ),
        "maximum_relative_off_basis_residual": max(
            float(row["relative_off_basis_residual"]) for row in rows
        ),
    }
    for row in rows:
        row.update({
            "pair_id": context["pair_id"],
            "history_member": context["history_member"],
            "baseline_experiment_id": context["baseline_experiment_id"],
        })
    return context, rows


def _primary_counts(contexts: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    return {
        "fixed_basis_contexts": sum(bool(row["basis_pass"]) for row in contexts),
        "finite_constructions": sum(int(row["finite_construction_count"]) for row in contexts),
        "issue_gate_pass": sum(int(row["issue_gate_pass_count"]) for row in contexts),
        "cancellation_gate_pass": sum(
            int(row["cancellation_gate_pass_count"]) for row in contexts
        ),
        "central_sign_gate_pass": sum(
            int(row["central_sign_gate_pass_count"]) for row in contexts
        ),
        "global_rank_condition_contexts": sum(
            bool(row["matrix_metrics"]["global_pass"]) for row in contexts
        ),
        "slot_rank_condition_blocks": sum(
            int(row["matrix_metrics"]["slot_pass_count"]) for row in contexts
        ),
        "late_novelty_contexts": sum(
            bool(row["matrix_metrics"]["late_novelty_pass"]) for row in contexts
        ),
    }


def _route(
    source_count: int, reproduction: Mapping[str, int], primary: Mapping[str, int],
    cfg: Mapping[str, Any],
) -> tuple[bool, str]:
    gate = cfg["primary_gate"]
    pairs = (
        (source_count, "source_raw_authentication_required"),
        (reproduction["baseline_formal_reproduction_count"], "baseline_authentication_required"),
        (reproduction["measured_probe_formal_reproduction_count"], "probe_authentication_required"),
        (primary["fixed_basis_contexts"], "fixed_basis_contexts_required"),
        (primary["finite_constructions"], "finite_constructions_required"),
        (primary["issue_gate_pass"], "issue_gate_pass_required"),
        (primary["cancellation_gate_pass"], "cancellation_gate_pass_required"),
        (primary["central_sign_gate_pass"], "central_sign_gate_pass_required"),
        (primary["global_rank_condition_contexts"], "global_rank_condition_contexts_required"),
        (primary["slot_rank_condition_blocks"], "slot_rank_condition_blocks_required"),
        (primary["late_novelty_contexts"], "late_novelty_contexts_required"),
    )
    passed = all(int(value) == int(gate[name]) for value, name in pairs)
    return passed, str(cfg["routes"]["pass" if passed else "fail"])


def run_audit(args: argparse.Namespace) -> dict[str, Any]:
    config_path = args.config.expanduser().resolve()
    cfg = _read_json(config_path)
    _validate_design(cfg)
    design_path = args.design_document.expanduser().resolve()
    if _sha256(design_path) != str(cfg["design_document_sha256"]):
        raise ValueError("S23R1 design-document hash mismatch")
    source_run = args.source_s21_run.expanduser().resolve()
    source_s22 = args.source_s22_output.expanduser().resolve()
    source_s23 = args.source_s23_output.expanduser().resolve()
    source_d1 = args.source_s23d1_output.expanduser().resolve()
    output = args.output.expanduser().resolve()
    if output.exists():
        raise ValueError("S23R1 output directory must be new")
    if any(output == source or source in output.parents for source in (
        source_run, source_s22, source_s23, source_d1
    )):
        raise ValueError("S23R1 output must remain outside immutable sources")

    s23.s22._load_s21_module()
    s21 = s23.s22.s21
    ctx = s21.load_config(
        args.source_s21_config.expanduser().resolve(),
        source_stage42r3b_run=args.source_stage42r3b_run,
        source_stage42r3c3_run=args.source_stage42r3c3_run,
        source_stage42r3c3_bank_dir=args.source_stage42r3c3_bank_dir,
        source_stage42r3c3t1_run=args.source_stage42r3c3t1_run,
        source_stage42r3c3t1_audit_dir=args.source_stage42r3c3t1_audit_dir,
        source_stage42r3c3t3_controller_bank=args.source_stage42r3c3t3_controller_bank,
        q1_run=args.q1_run, q2_run=args.q2_run,
        q1_audit=args.q1_audit, q2_audit=args.q2_audit,
        r3b_server_audit=args.r3b_server_audit,
        r3b_snapshot_checks=args.r3b_snapshot_checks,
        run_dir=source_run,
    )
    authenticated = s23.s22._authenticate_source(ctx, config_path, cfg)
    contexts, reproduction = s23.s22._load_and_authenticate_raw(
        ctx, authenticated["phase_formal_map"]
    )
    if (
        len(contexts) != 40
        or reproduction["baseline_formal_pass_count"] != 16
        or reproduction["measured_probe_formal_pass_count"] != 99
    ):
        raise ValueError("S21 frozen context or formal counts changed")
    s22_auth = s23._authenticate_s22(source_s22, cfg)
    s23_auth = d1._authenticate_s23(
        source_s23,
        args.source_s23_config.expanduser().resolve(),
        args.source_s23_implementation.expanduser().resolve(), cfg,
    )
    d1_auth = _authenticate_d1(
        source_d1,
        args.source_s23d1_config.expanduser().resolve(),
        args.source_s23d1_implementation.expanduser().resolve(), cfg,
    )
    context_rows = []
    event_rows = []
    for key in sorted(contexts):
        context, events = _context_replay(ctx, contexts[key]["baseline"], cfg)
        context_rows.append(context)
        event_rows.extend(events)
    primary = _primary_counts(context_rows)
    source_count = int(authenticated["raw_inventory"]["count"])
    primary_pass, route = _route(source_count, reproduction, primary, cfg)
    requested = _requested_matrix(cfg)
    provenance = {
        "stage": STAGE,
        "identity": IDENTITY,
        "design_config_sha256": _sha256(config_path),
        "design_document_sha256": _sha256(design_path),
        "source_s21_run": str(source_run),
        "source_s21_raw_inventory_digest": authenticated["raw_inventory"]["digest"],
        "source_s22_output": str(source_s22),
        "source_s22_hashes": s22_auth["hashes"],
        "source_s23_output": str(source_s23),
        "source_s23_hashes": s23_auth["hashes"],
        "source_s23d1_output": str(source_d1),
        "source_s23d1_hashes": d1_auth["hashes"],
        "requested_matrix_digest": _digest(requested.tolist()),
        "formal_timing_changed": False,
    }
    provenance_digest = _digest(provenance)
    detailed = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "classification": "zero_tsc_fixed_amplitude_coded_hadamard_preflight",
        "provenance": provenance,
        "provenance_digest": provenance_digest,
        "source_authentication": {
            "s21_raw_count": source_count,
            "s21_reproduction": reproduction,
            "s22": s22_auth, "s23": s23_auth, "s23d1": d1_auth,
        },
        "requested_matrix": requested.tolist(),
        "requested_matrix_metrics": s23._matrix_metrics(requested, cfg),
        "primary_gate_counts": primary,
        "context_rows": context_rows,
        "event_rows": event_rows,
        "primary_pass": primary_pass,
        "route": route,
        "scientific_guardrails": cfg["scientific_scope"],
        "execution": cfg["execution_contract"],
        "audit_complete": True,
    }
    summary = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "provenance_digest": provenance_digest,
        "source_raw_authentication_count": source_count,
        **reproduction, **primary,
        "context_count": len(context_rows),
        "event_row_count": len(event_rows),
        "maximum_global_normalized_condition": max(
            float(row["matrix_metrics"]["global_normalized_condition"])
            for row in context_rows
        ),
        "maximum_slot_normalized_condition": max(
            float(slot["normalized_condition"])
            for row in context_rows for slot in row["matrix_metrics"]["slot_rows"]
        ),
        "minimum_late_column_residual": min(
            min(map(float, row["matrix_metrics"]["late_column_residuals"]))
            for row in context_rows
        ),
        "maximum_incremental_normalized_action_linf": max(
            max(float(row["maximum_issue_incremental_normalized_action_linf"]),
                float(row["maximum_cancel_incremental_normalized_action_linf"]))
            for row in context_rows
        ),
        "maximum_total_normalized_action_abs": max(
            float(row["maximum_total_normalized_action_abs"]) for row in context_rows
        ),
        "maximum_predicted_current_utilization": max(
            float(row["maximum_predicted_current_utilization"]) for row in context_rows
        ),
        "maximum_absolute_coordinate_error": max(
            float(row["maximum_absolute_coordinate_error"]) for row in context_rows
        ),
        "minimum_desired_applied_current_cosine": min(
            float(row["minimum_desired_applied_current_cosine"]) for row in context_rows
        ),
        "maximum_relative_off_basis_residual": max(
            float(row["maximum_relative_off_basis_residual"]) for row in context_rows
        ),
        "primary_pass": primary_pass,
        "route": route,
        "scientific_classification": {
            "runtime_or_environment_error": False,
            "raw_or_snapshot_corruption": False,
            "statistics_or_reporting_error": False,
            "action_schedule_preflight_result": "pass" if primary_pass else "fail",
            "real_tsc_or_plant_executed": False,
            "real_controller_or_mpc_executed": False,
            "real_closed_loop_conclusion": "not_tested",
            "real_campaign_authorized": False,
        },
    }
    output.mkdir(parents=True, exist_ok=False)
    detailed_path = output / "stage4_2r3c3t13s23r1_amplitude_coded_preflight_v1.json"
    summary_path = output / "stage4_2r3c3t13s23r1_summary_v1.json"
    _write_json(detailed_path, detailed)
    _write_json(summary_path, summary)
    manifest = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "provenance_digest": provenance_digest,
        "output_files": [
            {"path": path.name, "size_bytes": path.stat().st_size, "sha256": _sha256(path)}
            for path in (detailed_path, summary_path)
        ],
        "source_raw_files_copied_or_modified": 0,
        "new_raw_files_created": 0,
        "ray_gotsc_tsc_plant_or_controller_executed": False,
        "pass_authorizes_s24_design_only": True,
    }
    manifest_path = output / "stage4_2r3c3t13s23r1_manifest_v1.json"
    _write_json(manifest_path, manifest)
    return {
        "output": str(output),
        "detailed_sha256": _sha256(detailed_path),
        "summary_sha256": _sha256(summary_path),
        "manifest_sha256": _sha256(manifest_path),
        **summary,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--design-document", type=Path, required=True)
    parser.add_argument("--source-s21-config", type=Path, required=True)
    parser.add_argument("--source-s21-run", type=Path, required=True)
    parser.add_argument("--source-s22-output", type=Path, required=True)
    parser.add_argument("--source-s23-config", type=Path, required=True)
    parser.add_argument("--source-s23-implementation", type=Path, required=True)
    parser.add_argument("--source-s23-output", type=Path, required=True)
    parser.add_argument("--source-s23d1-config", type=Path, required=True)
    parser.add_argument("--source-s23d1-implementation", type=Path, required=True)
    parser.add_argument("--source-s23d1-output", type=Path, required=True)
    for name in (
        "source-stage42r3b-run", "source-stage42r3c3-run",
        "source-stage42r3c3-bank-dir", "source-stage42r3c3t1-run",
        "source-stage42r3c3t1-audit-dir", "source-stage42r3c3t3-controller-bank",
        "q1-run", "q2-run", "q1-audit", "q2-audit",
        "r3b-server-audit", "r3b-snapshot-checks",
    ):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main() -> None:
    result = run_audit(_parser().parse_args())
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
