#!/usr/bin/env python3
"""Zero-TSC deterministic geometry-restoring amplitude search for S24D1R1."""

from __future__ import annotations

import argparse
import copy
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import numpy as np

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1_contracted_amplitude_preflight as d1,
)


r1 = d1.r1
STAGE = "Stage4.2R3c3T13S24D1R1"
IDENTITY = "minimum_geometry_restoring_amplitude_search_v1"
PATTERNS = ("++--", "+--+")


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


def _grid(cfg: Mapping[str, Any]) -> tuple[Decimal, ...]:
    search = cfg["search_contract"]
    start = Decimal(search["grid_start_decimal"])
    stop = Decimal(search["grid_stop_decimal"])
    step = Decimal(search["grid_step_decimal"])
    values = tuple(start + step * index for index in range(int(search["grid_count"])))
    if not values or values[-1] != stop:
        raise ValueError("S24D1R1 Decimal grid endpoints changed")
    return values


def _validate_design(cfg: Mapping[str, Any]) -> None:
    source = cfg["source_contract"]
    search = cfg["search_contract"]
    schedule = cfg["schedule_contract"]
    formal = cfg["formal_contract"]
    gate = cfg["primary_gate"]
    sentinel = cfg["sentinel_contract"]
    execution = cfg["execution_contract"]
    scope = cfg["scientific_scope"]
    if (
        int(cfg.get("schema_version", -1)) != 1
        or cfg.get("stage") != STAGE
        or cfg.get("identity") != IDENTITY
        or cfg.get("package_revision")
        != "r42r3c3t13s24d1r1_geometry_restoring_amplitude_search_v1"
        or cfg.get("selection_status")
        != "frozen_after_d1_failure_before_r1_implementation_or_candidate_evaluation"
        or cfg.get("design_document_sha256")
        != "e6a9fd89397aabd1ac2017448b1d9cea278b67e3af198508b037ecdcb2c44407"
        or source["required_d1_route"]
        != "CONTRACTED_AMPLITUDE_PREFLIGHT_FAIL_REDESIGN_REQUIRED"
        or not bool(source["required_d1_source_applicability"])
        or tuple(int(source[key]) for key in (
            "required_d1_issue_pass", "required_d1_cancellation_pass",
            "required_d1_event_rows", "required_d1_selected_sentinel_specs",
            "required_d1_new_raw",
        )) != (1920, 3840, 3840, 0, 0)
        or search["fixed_pattern_amplitudes"] != {"++++": "0.250", "+-+-": "0.250"}
        or tuple(search["searched_patterns_in_order"]) != PATTERNS
        or search["grid_start_decimal"] != "0.225"
        or search["grid_stop_decimal"] != "0.500"
        or search["grid_step_decimal"] != "0.005"
        or int(search["grid_count"]) != 56
        or search["selection_rule"]
        != "first_grid_amplitude_passing_all_960_pattern_occurrences"
        or int(search["expected_occurrences_per_pattern"]) != 960
        or any(bool(search[key]) for key in (
            "adaptive_grid_refinement_allowed", "continuous_optimization_allowed",
            "amplitude_outside_grid_allowed",
        ))
        or tuple(schedule["ordered_directions"]) != r1.DIRECTIONS
        or tuple(map(int, schedule["issue_task_steps"])) != r1.ISSUE_STEPS
        or tuple(map(int, schedule["cancel_task_steps"])) != r1.CANCEL_STEPS
        or tuple(int(schedule[key]) for key in (
            "hadamard_order", "primary_sequence_rows", "central_sign_primary_rows",
            "central_sign_sentinel_rows", "total_sequence_rows",
            "dynamic_exact_search_radius",
        )) != (16, 16, 8, 8, 24, 16)
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
        or not all(bool(schedule[key]) for key in (
            "require_decimal_exact_central_target_symmetry",
            "require_exact_stored_center_cancellation",
            "require_exact_zero_target_jump_net",
        ))
        or tuple(int(formal[key]) for key in (
            "normal_arrival_deadline_step", "normal_hold_through_step",
            "weak_arrival_deadline_step", "weak_hold_through_step",
            "arrival_streak_steps",
        )) != (25, 35, 27, 37, 3)
        or float(formal["position_tolerance_m"]) != 0.03
        or float(formal["speed_tolerance_m_per_s"]) != 0.1
        or float(formal["ip_tolerance_A"]) != 10000.0
        or bool(formal["arrival_deadline_expansion_allowed"])
        or tuple(int(gate[key]) for key in (
            "source_raw_authentication_required", "baseline_authentication_required",
            "probe_authentication_required", "fixed_basis_contexts_required",
            "finite_constructions_required", "issue_gate_pass_required",
            "cancellation_gate_pass_required", "central_sign_gate_pass_required",
            "global_rank_condition_contexts_required",
            "slot_rank_condition_blocks_required", "late_novelty_contexts_required",
            "selected_sentinel_specs_required",
        )) != (360, 40, 320, 40, 7680, 3840, 3840, 1280, 40, 160, 40, 54)
        or sentinel["next_stage"] != "Stage4.2R3c3T13S24D1R2"
        or sentinel["campaign_identity"]
        != "geometry_restored_amplitude_safety_sentinel_v1"
        or float(sentinel["maximum_online_cancel_incremental_normalized_action_linf"])
        != 0.24
        or float(sentinel["formal_maximum_incremental_normalized_action_linf"])
        != 0.25
        or not all(bool(sentinel[key]) for key in (
            "select_every_allowed_s24_failure", "fresh_tsc_process_required",
            "fresh_controller_required", "full_horizon_required",
        ))
        or bool(sentinel["source_outcome_available_to_controller"])
        or not bool(execution["server_side_only_for_large_raw"])
        or not bool(execution["read_raw_in_place"])
        or int(execution["new_raw_count"]) != 0
        or any(bool(execution[key]) for key in (
            "ray_executed", "gotsc_executed", "tsc_executed",
            "controller_executed", "snapshot_creation_allowed",
        ))
        or int(execution["plant_steps_executed"]) != 0
        or not bool(scope["fixed_grid_only"])
        or bool(scope["plant_response_simulated"])
        or bool(scope["real_mpc_executed"])
        or not bool(scope["pass_authorizes_safety_sentinel_only"])
        or bool(scope["pass_authorizes_full_campaign"])
        or bool(scope["probe_trajectories_are_demonstrations"])
        or bool(scope["bc_dagger_or_rl_allowed"])
    ):
        raise ValueError("T13S24D1R1 frozen design changed")
    _grid(cfg)


def _canonical_pattern(signs: Sequence[int]) -> str:
    block = np.asarray(signs, dtype=int).reshape(4)
    if set(map(int, block)) - {-1, 1}:
        raise ValueError("S24D1R1 pattern block is not signed")
    canonical = int(block[0]) * block
    return "".join("+" if value == 1 else "-" for value in canonical)


def _authenticate_d1(
    output: Path, config_path: Path, implementation_path: Path,
    cfg: Mapping[str, Any],
) -> tuple[dict[str, Any], Mapping[str, Any]]:
    source = cfg["source_contract"]
    paths = {
        "detailed": output / "stage4_2r3c3t13s24d1_contracted_amplitude_preflight_v1.json",
        "summary": output / "stage4_2r3c3t13s24d1_summary_v1.json",
        "sentinel_specs": output / "stage4_2r3c3t13s24d1_selected_sentinel_specs_v1.json",
        "manifest": output / "stage4_2r3c3t13s24d1_manifest_v1.json",
    }
    hashes = {name: _sha256(path) for name, path in paths.items()}
    expected = {
        "detailed": source["d1_detailed_sha256"],
        "summary": source["d1_summary_sha256"],
        "sentinel_specs": source["d1_sentinel_specs_sha256"],
        "manifest": source["d1_manifest_sha256"],
    }
    detailed = _read_json(paths["detailed"])
    summary = _read_json(paths["summary"])
    sentinel = _read_json(paths["sentinel_specs"])
    manifest = _read_json(paths["manifest"])
    if (
        output.name != source["d1_output_name"]
        or _sha256(config_path) != source["d1_config_sha256"]
        or _sha256(implementation_path) != source["d1_implementation_sha256"]
        or hashes != expected
        or detailed.get("route") != source["required_d1_route"]
        or summary.get("route") != source["required_d1_route"]
        or not bool(summary.get("source_applicability_passed"))
        or bool(summary.get("static_replay_passed"))
        or int(summary.get("issue_gate_pass", -1)) != 1920
        or int(summary.get("cancellation_gate_pass", -1)) != 3840
        or int(summary.get("event_row_count", -1)) != 3840
        or int(sentinel.get("selected_spec_count", -1)) != 0
        or int(manifest.get("new_raw_files_created", -1)) != 0
        or bool(manifest.get("ray_gotsc_tsc_plant_or_controller_executed"))
    ):
        raise ValueError("immutable S24D1 source changed")
    return {"paths": {k: str(v) for k, v in paths.items()}, "hashes": hashes}, detailed


def _replay_config(
    s23r1_cfg: Mapping[str, Any], cfg: Mapping[str, Any],
    amplitudes: Mapping[str, Decimal | float | str],
) -> dict[str, Any]:
    replay = copy.deepcopy(s23r1_cfg)
    replay["schedule_contract"].update(copy.deepcopy(cfg["schedule_contract"]))
    replay["schedule_contract"]["canonical_pattern_amplitudes"] = {
        pattern: float(value) for pattern, value in amplitudes.items()
    }
    return replay


def _prepare_issue_contexts(ctx: Any, contexts: Mapping[Any, Any]) -> list[dict[str, Any]]:
    output = []
    for key in sorted(contexts):
        baseline = contexts[key]["baseline"]
        field_basis, turns, minimum, maximum, max_delta, actuator, basis_audit = (
            r1.s23._basis_and_actuator(ctx, baseline)
        )
        output.append({
            "key": key, "baseline": baseline, "field_basis": field_basis,
            "turns": turns, "minimum": minimum, "maximum": maximum,
            "max_delta": max_delta, "actuator": actuator,
            "basis_audit": basis_audit,
        })
    return output


def _evaluate_pattern_amplitude(
    ctx: Any, prepared: Sequence[Mapping[str, Any]], pattern: str,
    amplitude: Decimal, replay_cfg: Mapping[str, Any],
) -> dict[str, Any]:
    sequence = r1.s23._sequence_matrix()
    rows = []
    adapter_cfg = {"search_contract": replay_cfg["schedule_contract"]}
    for item in prepared:
        for sequence_index in range(24):
            for slot in range(4):
                signs = sequence[sequence_index, 4 * slot:4 * slot + 4]
                if _canonical_pattern(signs) != pattern:
                    continue
                desired = float(amplitude) * signs.astype(float)
                issue = r1.d1._issue_construction(
                    ctx=ctx, baseline=item["baseline"],
                    issue_step=r1.ISSUE_STEPS[slot], desired_coordinate=desired,
                    field_basis=item["field_basis"], turns=item["turns"],
                    minimum=item["minimum"], maximum=item["maximum"],
                    max_delta=item["max_delta"], actuator=item["actuator"],
                    cfg=adapter_cfg,
                )
                rows.append(issue)
    criteria_failures: dict[str, int] = {}
    for row in rows:
        for name, passed in row["criteria"].items():
            if not bool(passed):
                criteria_failures[name] = criteria_failures.get(name, 0) + 1
    return {
        "pattern": pattern,
        "amplitude_decimal": format(amplitude, ".3f"),
        "occurrence_count": len(rows),
        "issue_gate_pass_count": sum(bool(row["passed"]) for row in rows),
        "criteria_failure_counts": dict(sorted(criteria_failures.items())),
        "minimum_active_absolute_coordinate": min(
            float(row["minimum_active_absolute_coordinate"]) for row in rows
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
        "maximum_incremental_normalized_action_linf": max(
            float(row["incremental_normalized_action_linf"]) for row in rows
        ),
        "maximum_total_normalized_action_abs": max(
            float(row["total_normalized_action_abs"]) for row in rows
        ),
        "maximum_predicted_current_utilization": max(
            float(row["predicted_current_utilization"]) for row in rows
        ),
        "passed": bool(rows and all(bool(row["passed"]) for row in rows)),
    }


def _select_first_feasible(
    pattern: str, grid: Sequence[Decimal],
    evaluate: Callable[[str, Decimal], Mapping[str, Any]],
) -> tuple[Decimal | None, list[Mapping[str, Any]]]:
    audit = []
    selected = None
    for amplitude in grid:
        row = dict(evaluate(pattern, amplitude))
        audit.append(row)
        if bool(row.get("passed")):
            selected = amplitude
            break
    return selected, audit


def _full_replay(
    ctx: Any, contexts: Mapping[Any, Any], replay_cfg: Mapping[str, Any],
    source_count: int, reproduction: Mapping[str, int],
) -> tuple[bool, list[dict[str, Any]], list[dict[str, Any]], dict[str, int]]:
    context_rows = []
    event_rows = []
    for key in sorted(contexts):
        context, events = r1._context_replay(ctx, contexts[key]["baseline"], replay_cfg)
        context_rows.append(context)
        event_rows.extend(events)
    primary = r1._primary_counts(context_rows)
    passed, _ = r1._route(source_count, reproduction, primary, replay_cfg)
    return passed, context_rows, event_rows, primary


def run_audit(args: argparse.Namespace) -> dict[str, Any]:
    config_path = args.config.expanduser().resolve()
    cfg = _read_json(config_path)
    _validate_design(cfg)
    design_path = args.design_document.expanduser().resolve()
    if _sha256(design_path) != cfg["design_document_sha256"]:
        raise ValueError("S24D1R1 design-document hash mismatch")
    output = args.output.expanduser().resolve()
    if output.exists():
        raise ValueError("S24D1R1 output directory must be new")

    d1_config_path = args.source_d1_config.expanduser().resolve()
    d1_cfg = _read_json(d1_config_path)
    d1._validate_design(d1_cfg)
    d1_auth, _ = _authenticate_d1(
        args.source_d1_output.expanduser().resolve(), d1_config_path,
        args.source_d1_implementation.expanduser().resolve(), cfg,
    )
    s23r1_config_path = args.source_s23r1_config.expanduser().resolve()
    s23r1_cfg = _read_json(s23r1_config_path)
    s23r1_auth, s23r1_detailed = d1._authenticate_s23r1(
        args.source_s23r1_output.expanduser().resolve(), s23r1_config_path,
        args.source_s23r1_implementation.expanduser().resolve(), d1_cfg,
    )
    s24_auth, s24_rows, sequence_specs = d1._authenticate_s24(
        args, d1_cfg, s23r1_detailed
    )
    source_pass = bool(s24_auth["source_applicability_passed"])
    if not source_pass:
        raise ValueError(cfg["routes"]["source_stop"])

    r1.s23.s22._load_s21_module()
    s21 = r1.s23.s22.s21
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
        run_dir=args.source_s21_run.expanduser().resolve(),
    )
    authenticated = r1.s23.s22._authenticate_source(ctx, s23r1_config_path, s23r1_cfg)
    contexts, reproduction = r1.s23.s22._load_and_authenticate_raw(
        ctx, authenticated["phase_formal_map"]
    )
    source_count = int(authenticated["raw_inventory"]["count"])
    prepared = _prepare_issue_contexts(ctx, contexts)
    base_amplitudes: dict[str, Decimal] = {
        pattern: Decimal(value)
        for pattern, value in cfg["search_contract"]["fixed_pattern_amplitudes"].items()
    }
    search_rows: dict[str, list[Mapping[str, Any]]] = {}
    selected: dict[str, Decimal] = {}
    grid = _grid(cfg)
    base_replay = _replay_config(
        s23r1_cfg, cfg,
        {**base_amplitudes, "++--": grid[0], "+--+": grid[0]},
    )
    for pattern in PATTERNS:
        amplitude, audit = _select_first_feasible(
            pattern, grid,
            lambda current_pattern, current_amplitude: _evaluate_pattern_amplitude(
                ctx, prepared, current_pattern, current_amplitude, base_replay
            ),
        )
        search_rows[pattern] = audit
        if amplitude is not None:
            selected[pattern] = amplitude
    candidate_found = len(selected) == len(PATTERNS)
    amplitudes = {**base_amplitudes, **selected}
    context_rows: list[dict[str, Any]] = []
    event_rows: list[dict[str, Any]] = []
    primary: dict[str, int] = {}
    full_pass = False
    requested = None
    replay_cfg = None
    if candidate_found:
        replay_cfg = _replay_config(s23r1_cfg, cfg, amplitudes)
        requested = r1._requested_matrix(replay_cfg)
        full_pass, context_rows, event_rows, primary = _full_replay(
            ctx, contexts, replay_cfg, source_count, reproduction
        )
    failure_rows = [
        row for row in s24_rows if row.get("failure_class") == d1.ALLOWED_FAILURE
    ]
    sentinel_rows = d1._sentinel_rows(
        failure_rows, sequence_specs, replay_cfg, cfg, _sha256(config_path)
    ) if candidate_found and full_pass and replay_cfg is not None else []
    primary_pass = bool(
        candidate_found and full_pass
        and len(sentinel_rows) == int(cfg["primary_gate"]["selected_sentinel_specs_required"])
    )
    route = cfg["routes"]["pass" if primary_pass else "fail"]
    matrix_metrics = r1.s23._matrix_metrics(requested, replay_cfg) if requested is not None else {}
    provenance = {
        "stage": STAGE,
        "identity": IDENTITY,
        "config_sha256": _sha256(config_path),
        "design_document_sha256": _sha256(design_path),
        "d1_source": d1_auth,
        "s23r1_source": s23r1_auth,
        "s24_run_dir": s24_auth["run_dir"],
        "s24_active_raw_inventory_digest": s24_auth["active_raw"]["inventory"]["digest"],
        "s21_raw_inventory_digest": authenticated["raw_inventory"]["digest"],
        "search_grid_decimal": [format(value, ".3f") for value in grid],
        "formal_timing_changed": False,
    }
    detailed = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "classification": "zero_tsc_minimum_geometry_restoring_amplitude_search",
        "provenance": provenance,
        "provenance_digest": _digest(provenance),
        "search_rows": search_rows,
        "selected_pattern_amplitudes": {
            pattern: format(value, ".3f") for pattern, value in selected.items()
        },
        "candidate_found": candidate_found,
        "requested_matrix": requested.tolist() if requested is not None else [],
        "requested_matrix_metrics": matrix_metrics,
        "s21_reproduction": reproduction,
        "full_replay_primary_gate_counts": primary,
        "context_rows": context_rows,
        "event_rows": event_rows,
        "selected_sentinel_spec_count": len(sentinel_rows),
        "full_replay_passed": full_pass,
        "primary_pass": primary_pass,
        "route": route,
        "execution": cfg["execution_contract"],
        "scientific_scope": cfg["scientific_scope"],
        "audit_complete": True,
    }
    summary = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "provenance_digest": detailed["provenance_digest"],
        "source_raw_authentication_count": source_count,
        **reproduction,
        "searched_pattern_order": list(PATTERNS),
        "evaluated_amplitude_count_by_pattern": {
            pattern: len(search_rows[pattern]) for pattern in PATTERNS
        },
        "selected_pattern_amplitudes": detailed["selected_pattern_amplitudes"],
        "candidate_found": candidate_found,
        **primary,
        "context_count": len(context_rows),
        "event_row_count": len(event_rows),
        "requested_global_rank": matrix_metrics.get("global_rank"),
        "requested_global_normalized_condition": matrix_metrics.get(
            "global_normalized_condition"
        ),
        "requested_maximum_slot_normalized_condition": max(
            (float(row["normalized_condition"]) for row in matrix_metrics.get("slot_rows", [])),
            default=None,
        ),
        "selected_sentinel_spec_count": len(sentinel_rows),
        "full_replay_passed": full_pass,
        "primary_pass": primary_pass,
        "route": route,
        "scientific_classification": {
            "runtime_or_environment_error": False,
            "raw_or_snapshot_corruption": False,
            "statistics_or_reporting_error": False,
            "static_schedule_search_result": "pass" if primary_pass else "fail",
            "real_tsc_or_plant_executed": False,
            "real_controller_or_mpc_executed": False,
            "real_closed_loop_conclusion": "not_tested",
            "full_campaign_authorized": False,
            "safety_sentinel_authorized": primary_pass,
        },
    }
    output.mkdir(parents=True, exist_ok=False)
    detailed_path = output / "stage4_2r3c3t13s24d1r1_geometry_restoring_search_v1.json"
    summary_path = output / "stage4_2r3c3t13s24d1r1_summary_v1.json"
    sentinel_path = output / "stage4_2r3c3t13s24d1r1_selected_sentinel_specs_v1.json"
    _write_json(detailed_path, detailed)
    _write_json(summary_path, summary)
    _write_json(sentinel_path, {
        "schema_version": 1,
        "stage": STAGE,
        "next_stage": cfg["sentinel_contract"]["next_stage"],
        "source_outcomes_available_to_controller": False,
        "selected_pattern_amplitudes": detailed["selected_pattern_amplitudes"],
        "selected_spec_count": len(sentinel_rows),
        "spec_rows": sentinel_rows,
    })
    manifest = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "provenance_digest": detailed["provenance_digest"],
        "output_files": [
            {"path": path.name, "size_bytes": path.stat().st_size, "sha256": _sha256(path)}
            for path in (detailed_path, summary_path, sentinel_path)
        ],
        "source_raw_files_copied_or_modified": 0,
        "new_raw_files_created": 0,
        "ray_gotsc_tsc_plant_or_controller_executed": False,
        "pass_authorizes_safety_sentinel_only": True,
        "pass_authorizes_full_campaign": False,
    }
    manifest_path = output / "stage4_2r3c3t13s24d1r1_manifest_v1.json"
    _write_json(manifest_path, manifest)
    return {
        "output": str(output),
        "detailed_sha256": _sha256(detailed_path),
        "summary_sha256": _sha256(summary_path),
        "sentinel_specs_sha256": _sha256(sentinel_path),
        "manifest_sha256": _sha256(manifest_path),
        **summary,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--design-document", type=Path, required=True)
    parser.add_argument("--source-d1-config", type=Path, required=True)
    parser.add_argument("--source-d1-implementation", type=Path, required=True)
    parser.add_argument("--source-d1-output", type=Path, required=True)
    parser.add_argument("--source-s23r1-config", type=Path, required=True)
    parser.add_argument("--source-s23r1-implementation", type=Path, required=True)
    parser.add_argument("--source-s23r1-output", type=Path, required=True)
    parser.add_argument("--source-s24-run", type=Path, required=True)
    parser.add_argument("--source-s24-config", type=Path, required=True)
    parser.add_argument("--source-s24-implementation", type=Path, required=True)
    parser.add_argument("--source-s24-hotfix-config", type=Path, required=True)
    parser.add_argument("--source-s24-hotfix-audit-tool", type=Path, required=True)
    parser.add_argument("--source-s24-forensic-tool", type=Path, required=True)
    parser.add_argument("--source-s24-forensics", type=Path, required=True)
    parser.add_argument("--source-s24-log", type=Path, required=True)
    parser.add_argument("--source-s21-config", type=Path, required=True)
    parser.add_argument("--source-s21-run", type=Path, required=True)
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
    print(json.dumps(run_audit(_parser().parse_args()), indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
