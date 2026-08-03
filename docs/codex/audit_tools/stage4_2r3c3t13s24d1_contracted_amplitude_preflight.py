#!/usr/bin/env python3
"""Zero-TSC S24D1 contracted-amplitude replay and sentinel-spec construction."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from docs.codex.audit_tools import (
    stage4_2r3c3t13s23r1_amplitude_coded_hadamard_preflight as r1,
)
from docs.codex.audit_tools import (
    stage4_2r3c3t13s24_training_sequence_forensics as s24f,
)


STAGE = "Stage4.2R3c3T13S24D1"
IDENTITY = "contracted_amplitude_exact_card15_preflight_v1"
S24_RUN_NAME = s24f.RUN_NAME
ALLOWED_FAILURE = "sequential_cancel_incremental_action_gate"


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
    sentinel = cfg["sentinel_contract"]
    execution = cfg["execution_contract"]
    scope = cfg["scientific_scope"]
    if (
        int(cfg.get("schema_version", -1)) != 1
        or cfg.get("stage") != STAGE
        or cfg.get("identity") != IDENTITY
        or cfg.get("package_revision")
        != "r42r3c3t13s24d1_contracted_amplitude_preflight_v1"
        or cfg.get("selection_status")
        != "frozen_before_s24_final_wave_completed_and_before_d1_implementation"
        or cfg.get("design_document_sha256")
        != "e2020a6c9a62e3f4de386d7d5abd4169bd13a43999d3df4142442d781085534b"
        or source["required_s23r1_route"]
        != "AMPLITUDE_CODED_HADAMARD_PREFLIGHT_PASS_FREEZE_S24_REQUIRED"
        or source["required_s24_phase_status"] != "training_sequence_failed"
        or source["required_s24_route"] != "SEQUENTIAL_IDENTIFICATION_RUNTIME_FAIL"
        or tuple(int(source[key]) for key in (
            "active_raw_count", "active_raw_total_bytes",
            "active_baseline_success_count", "active_sequence_success_count",
            "active_sequence_failure_count", "passed_cancel_events_at_0p25",
            "passed_cancel_events_at_0p50", "failed_cancel_events_at_0p50",
            "archived_pre_hotfix_raw_count", "archived_pre_hotfix_raw_total_bytes",
        )) != (600, 34003877, 24, 522, 54, 1152, 1026, 54, 576, 13706096)
        or source["required_failure_class"] != ALLOWED_FAILURE
        or float(source["maximum_cancel_increment_at_0p25"])
        != 0.23606572488943792
        or float(source["maximum_cancel_increment_at_0p50"])
        != 0.3506501714388529
        or tuple(schedule["ordered_directions"]) != r1.DIRECTIONS
        or tuple(map(int, schedule["issue_task_steps"])) != r1.ISSUE_STEPS
        or tuple(map(int, schedule["cancel_task_steps"])) != r1.CANCEL_STEPS
        or schedule["canonical_pattern_amplitudes"]
        != {"++++": 0.25, "+-+-": 0.25, "++--": 0.225, "+--+": 0.225}
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
        or not bool(schedule["require_decimal_exact_central_target_symmetry"])
        or not bool(schedule["require_exact_stored_center_cancellation"])
        or not bool(schedule["require_exact_zero_target_jump_net"])
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
        or sentinel["next_stage"] != "Stage4.2R3c3T13S24D2"
        or sentinel["campaign_identity"] != "contracted_amplitude_safety_sentinel_v1"
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
        or not bool(scope["fixed_candidate_only"])
        or bool(scope["amplitude_search_executed"])
        or bool(scope["plant_response_simulated"])
        or bool(scope["real_mpc_executed"])
        or not bool(scope["pass_authorizes_safety_sentinel_only"])
        or bool(scope["pass_authorizes_full_campaign"])
        or bool(scope["probe_trajectories_are_demonstrations"])
        or bool(scope["bc_dagger_or_rl_allowed"])
    ):
        raise ValueError("T13S24D1 frozen design changed")


def _replay_config(s23r1_cfg: Mapping[str, Any], cfg: Mapping[str, Any]) -> dict[str, Any]:
    replay = copy.deepcopy(s23r1_cfg)
    replay["schedule_contract"].update(copy.deepcopy(cfg["schedule_contract"]))
    return replay


def _source_applicability(active: Mapping[str, Any], cfg: Mapping[str, Any]) -> bool:
    source = cfg["source_contract"]
    return bool(
        int(active["strict_parse_count"]) == 600
        and not active["parse_errors"]
        and not active["unexpected_ids"]
        and not active["missing_ids"]
        and int(active["inventory"]["count"]) == int(source["active_raw_count"])
        and int(active["inventory"]["total_bytes"]) == int(source["active_raw_total_bytes"])
        and active["inventory"]["digest"] == source["active_raw_inventory_digest"]
        and int(active["baseline_complete_success_count"])
        == int(source["active_baseline_success_count"])
        and int(active["sequence_complete_success_count"])
        == int(source["active_sequence_success_count"])
        and int(active["sequence_failure_count"])
        == int(source["active_sequence_failure_count"])
        and active["failure_classes"] == {ALLOWED_FAILURE: 54}
        and int(active["forensic_integrity_pass_count"]) == 600
        and int(active["identity_and_spec_exact_count"]) == 600
        and int(active["restart_exact_count"]) == 600
        and int(active["causal_trace_pass_count"]) == 600
        and int(active["runtime_prefix_pass_count"]) == 600
        and int(active["calibration_pass_count"]) == 600
        and int(active["event_prefix_pass_count"]) == 600
        and active["cancellation_event_counts_by_amplitude"] == {
            "failed@0.5": 54, "passed@0.25": 1152, "passed@0.5": 1026,
        }
        and active["maximum_cancel_increment_by_amplitude"] == {
            "0.25": 0.23606572488943792, "0.5": 0.3506501714388529,
        }
        and int(active["cancellation_failure_static_match_count"]) == 54
    )


def _authenticate_s23r1(
    output: Path, config_path: Path, implementation_path: Path,
    cfg: Mapping[str, Any],
) -> tuple[dict[str, Any], Mapping[str, Any]]:
    source = cfg["source_contract"]
    paths = {
        "detailed": output / "stage4_2r3c3t13s23r1_amplitude_coded_preflight_v1.json",
        "summary": output / "stage4_2r3c3t13s23r1_summary_v1.json",
        "manifest": output / "stage4_2r3c3t13s23r1_manifest_v1.json",
    }
    hashes = {name: _sha256(path) for name, path in paths.items()}
    expected = {
        "detailed": source["s23r1_detailed_sha256"],
        "summary": source["s23r1_summary_sha256"],
        "manifest": source["s23r1_manifest_sha256"],
    }
    detailed = _read_json(paths["detailed"])
    summary = _read_json(paths["summary"])
    manifest = _read_json(paths["manifest"])
    if (
        output.name != source["s23r1_output_name"]
        or _sha256(config_path) != source["s23r1_config_sha256"]
        or _sha256(implementation_path) != source["s23r1_implementation_sha256"]
        or hashes != expected
        or detailed.get("route") != source["required_s23r1_route"]
        or summary.get("route") != source["required_s23r1_route"]
        or not bool(detailed.get("primary_pass"))
        or not bool(summary.get("primary_pass"))
        or int(summary.get("source_raw_authentication_count", -1)) != 360
        or int(summary.get("event_row_count", -1)) != 3840
        or bool(manifest.get("ray_gotsc_tsc_plant_or_controller_executed"))
        or int(manifest.get("new_raw_files_created", -1)) != 0
    ):
        raise ValueError("immutable S23R1 source changed")
    return {"paths": {k: str(v) for k, v in paths.items()}, "hashes": hashes}, detailed


def _authenticate_s24(args: argparse.Namespace, cfg: Mapping[str, Any], s23r1: Mapping[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    source = cfg["source_contract"]
    run_dir = args.source_s24_run.expanduser().resolve()
    stage_dir = run_dir / S24_RUN_NAME
    paths = {
        "state": stage_dir / "stage_state.json",
        "manifest": stage_dir / "stage_manifest.json",
        "gate": stage_dir / "analysis" / "training_sequence_gate.json",
        "forensics": args.source_s24_forensics.expanduser().resolve(),
        "baseline_specs": stage_dir / "specs" / "training_baseline_specs.json",
        "sequence_specs": stage_dir / "specs" / "training_sequence_specs.json",
        "all_specs": stage_dir / "specs" / "all_specs.json",
        "log": args.source_s24_log.expanduser().resolve(),
    }
    expected_hashes = {
        "state": source["s24_state_sha256"],
        "manifest": source["s24_manifest_sha256"],
        "gate": source["s24_training_gate_sha256"],
        "forensics": source["s24_independent_forensics_sha256"],
        "baseline_specs": source["s24_training_baseline_specs_sha256"],
        "sequence_specs": source["s24_training_sequence_specs_sha256"],
        "all_specs": source["s24_all_specs_sha256"],
        "log": source["s24_log_sha256"],
    }
    hashes = {name: _sha256(path) for name, path in paths.items()}
    if (
        run_dir.name != source["s24_run_name"]
        or hashes != expected_hashes
        or _sha256(args.source_s24_config.expanduser().resolve())
        != source["s24_config_sha256"]
        or _sha256(args.source_s24_implementation.expanduser().resolve())
        != source["s24_implementation_sha256"]
        or _sha256(args.source_s24_hotfix_config.expanduser().resolve())
        != source["s24_hotfix_config_sha256"]
        or _sha256(args.source_s24_hotfix_audit_tool.expanduser().resolve())
        != source["s24_hotfix_audit_tool_sha256"]
        or _sha256(args.source_s24_forensic_tool.expanduser().resolve())
        != source["s24_forensic_tool_sha256"]
    ):
        raise ValueError("immutable S24 source hash changed")
    state = _read_json(paths["state"])
    manifest = _read_json(paths["manifest"])
    gate = _read_json(paths["gate"])
    prior_forensics = _read_json(paths["forensics"])
    active, rows = s24f._audit_active_raw(stage_dir, s23r1)
    archived_dirs = [
        path for path in run_dir.rglob("runtime_hotfix_attempt1_failed_sequence_raw")
        if path.is_dir()
    ]
    archived = s24f._inventory(archived_dirs[0].glob("*.json.gz")) if len(archived_dirs) == 1 else {}
    log_text = paths["log"].read_text(encoding="utf-8", errors="replace")
    applicable = _source_applicability(active, cfg)
    applicable = bool(
        applicable
        and state.get("finished")
        and state.get("phase_status") == source["required_s24_phase_status"]
        and (state.get("verdict") or {}).get("route") == source["required_s24_route"]
        and not bool(state.get("heldout_outcomes_opened"))
        and not bool(gate.get("passed"))
        and manifest.get("config_sha256") == source["s24_config_sha256"]
        and manifest.get("semantics_preserving_runtime_hotfix", {}).get(
            "hotfixed_package_digest"
        ) == state.get("package_digest")
        and prior_forensics.get("forensic_recomputation_passed") is True
        and prior_forensics.get("statistics_or_reporting_error_found") is False
        and (prior_forensics.get("active_raw") or {}).get("inventory", {}).get("digest")
        == active["inventory"]["digest"]
        and archived.get("count") == source["archived_pre_hotfix_raw_count"]
        and archived.get("total_bytes") == source["archived_pre_hotfix_raw_total_bytes"]
        and archived.get("digest") == source["archived_pre_hotfix_raw_inventory_digest"]
        and "actors=128" in log_text and "pending=576" in log_text
        and "576/576" in log_text
    )
    specs = _read_json(paths["sequence_specs"])
    return {
        "run_dir": str(run_dir),
        "paths": {name: str(path) for name, path in paths.items()},
        "hashes": hashes,
        "active_raw": active,
        "archived_raw": archived,
        "source_applicability_passed": applicable,
    }, rows, specs


def _sentinel_rows(
    failure_rows: Sequence[Mapping[str, Any]], sequence_specs: Sequence[Mapping[str, Any]],
    replay_cfg: Mapping[str, Any], cfg: Mapping[str, Any], config_sha256: str,
) -> list[dict[str, Any]]:
    spec_by_id = {str(row["experiment_id"]): row for row in sequence_specs}
    selected = sorted(
        (row for row in failure_rows if row.get("failure_class") == ALLOWED_FAILURE),
        key=lambda row: (
            str(row["pair_id"]), str(row["history_member"]),
            int(row["sequence_index"]), str(row["experiment_id"]),
        ),
    )
    matrix = r1._requested_matrix(replay_cfg)
    schedule_digest = _digest(matrix.tolist())
    output = []
    for index, row in enumerate(selected):
        source_spec = spec_by_id[str(row["experiment_id"])]
        sequence_index = int(source_spec["s24_sequence_index"])
        requested_row = matrix[sequence_index]
        action_by_step: dict[str, list[float]] = {}
        for slot, (issue, cancel) in enumerate(zip(r1.ISSUE_STEPS, r1.CANCEL_STEPS)):
            values = requested_row[4 * slot:4 * slot + 4].astype(float).tolist()
            action_by_step[str(issue)] = values
            action_by_step[str(cancel)] = (-np.asarray(values)).tolist()
        identity_seed = {
            "stage": cfg["sentinel_contract"]["next_stage"],
            "source_snapshot": source_spec["restart_snapshot_dir"],
            "pair_id": source_spec["pair_id"],
            "history_member": source_spec["history_member"],
            "sequence_index": sequence_index,
            "schedule_digest": schedule_digest,
            "config_sha256": config_sha256,
        }
        experiment_id = "s42r3c3t13s24d2_" + _digest(identity_seed)[:20]
        sentinel_spec = copy.deepcopy(source_spec)
        sentinel_spec.update({
            "stage": cfg["sentinel_contract"]["next_stage"],
            "campaign_identity": cfg["sentinel_contract"]["campaign_identity"],
            "controller_revision": cfg["sentinel_contract"]["controller_revision"],
            "experiment_id": experiment_id,
            "environment_variant": "stage4_2r3c3t13s24d2_" + experiment_id,
            "kind": "stage4_2r3c3t13s24d2_contracted_amplitude_safety_sentinel",
            "phase": "prospective_contracted_amplitude_safety_sentinel",
            "partition": "safety_sentinel",
            "r3c3t13s9_offline_role": "safety_sentinel",
            "baseline_experiment_id": "",
            "candidate_preflight_sha256": config_sha256,
            "s24_requested_action_by_task_step": action_by_step,
            "s24_requested_matrix_row": requested_row.astype(float).tolist(),
            "s24_schedule_digest": schedule_digest,
            "s24d2_online_cancel_margin_gate": 0.24,
            "fresh_tsc_process_required": True,
            "fresh_controller_required": True,
            "source_result_available_to_controller": False,
            "source_action_available_to_controller": False,
            "source_coil_current_available_to_controller": False,
            "source_wire_current_available_to_controller": False,
            "pair_or_history_label_available_to_controller": False,
            "partition_label_available_to_controller": False,
            "probe_trajectory_allowed_in_expert_dataset": False,
        })
        output.append({
            "selection_index": index,
            "selection": {
                "source_s24_experiment_id": row["experiment_id"],
                "source_failure_class": ALLOWED_FAILURE,
                "pair_id": row["pair_id"],
                "history_member": row["history_member"],
                "sequence_index": sequence_index,
            },
            "fresh_identities": {
                "stage": cfg["sentinel_contract"]["next_stage"],
                "campaign": cfg["sentinel_contract"]["campaign_identity"],
                "controller": cfg["sentinel_contract"]["controller_revision"],
                "experiment": experiment_id,
                "environment": sentinel_spec["environment_variant"],
                "run_family": "stage4_2r3c3t13s24d2_runs",
                "raw_family": "stage4_2r3c3t13s24d2_contracted_amplitude_safety_sentinel/raw",
                "state": "stage4_2r3c3t13s24d2_stage_state.json",
                "manifest": "stage4_2r3c3t13s24d2_stage_manifest.json",
                "log_family": "logs/nohup/stage4_2r3c3t13s24d2_",
                "ray_session_prefix": "stage4_2r3c3t13s24d2_",
                "package_revision": "r42r3c3t13s24d2_contracted_amplitude_safety_sentinel_v1",
            },
            "sentinel_spec": sentinel_spec,
        })
    if len({row["sentinel_spec"]["experiment_id"] for row in output}) != len(output):
        raise ValueError("S24D1 sentinel experiment identities collided")
    return output


def _static_pass(
    source_count: int, reproduction: Mapping[str, int], primary: Mapping[str, int],
    contexts: Sequence[Mapping[str, Any]], requested: np.ndarray,
    replay_cfg: Mapping[str, Any], cfg: Mapping[str, Any],
) -> bool:
    passed, _ = r1._route(source_count, reproduction, primary, replay_cfg)
    metrics = r1.s23._matrix_metrics(requested, replay_cfg)
    maximum_slot = max(float(row["normalized_condition"]) for row in metrics["slot_rows"])
    return bool(
        passed and len(contexts) == 40
        and int(metrics["global_rank"]) == 16
        and abs(float(metrics["global_normalized_condition"])
                - float(cfg["schedule_contract"]["expected_requested_global_normalized_condition"]))
        <= 1e-12
        and abs(maximum_slot
                - float(cfg["schedule_contract"]["expected_requested_maximum_slot_normalized_condition"]))
        <= 1e-12
        and np.array_equal(requested[16:], -requested[:8])
    )


def run_audit(args: argparse.Namespace) -> dict[str, Any]:
    config_path = args.config.expanduser().resolve()
    cfg = _read_json(config_path)
    _validate_design(cfg)
    design_path = args.design_document.expanduser().resolve()
    if _sha256(design_path) != cfg["design_document_sha256"]:
        raise ValueError("S24D1 design-document hash mismatch")
    output = args.output.expanduser().resolve()
    if output.exists():
        raise ValueError("S24D1 output directory must be new")
    s23r1_config_path = args.source_s23r1_config.expanduser().resolve()
    s23r1_cfg = _read_json(s23r1_config_path)
    s23r1_auth, s23r1_detailed = _authenticate_s23r1(
        args.source_s23r1_output.expanduser().resolve(), s23r1_config_path,
        args.source_s23r1_implementation.expanduser().resolve(), cfg,
    )
    s24_auth, s24_rows, sequence_specs = _authenticate_s24(args, cfg, s23r1_detailed)
    source_pass = bool(s24_auth["source_applicability_passed"])

    replay_cfg = _replay_config(s23r1_cfg, cfg)
    context_rows: list[dict[str, Any]] = []
    event_rows: list[dict[str, Any]] = []
    reproduction: dict[str, int] = {}
    primary: dict[str, int] = {}
    source_count = 0
    requested = r1._requested_matrix(replay_cfg)
    static_pass = False
    if source_pass:
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
        for key in sorted(contexts):
            context, events = r1._context_replay(ctx, contexts[key]["baseline"], replay_cfg)
            context_rows.append(context)
            event_rows.extend(events)
        primary = r1._primary_counts(context_rows)
        static_pass = _static_pass(
            source_count, reproduction, primary, context_rows, requested, replay_cfg, cfg
        )

    failure_rows = [row for row in s24_rows if row.get("failure_class") == ALLOWED_FAILURE]
    sentinel_rows = _sentinel_rows(
        failure_rows, sequence_specs, replay_cfg, cfg, _sha256(config_path)
    ) if source_pass and static_pass else []
    if not source_pass:
        route = cfg["routes"]["source_stop"]
    elif not static_pass or len(sentinel_rows) != int(cfg["primary_gate"]["selected_sentinel_specs_required"]):
        route = cfg["routes"]["static_fail"]
    else:
        route = cfg["routes"]["pass"]
    primary_pass = route == cfg["routes"]["pass"]
    matrix_metrics = r1.s23._matrix_metrics(requested, replay_cfg)
    provenance = {
        "stage": STAGE,
        "identity": IDENTITY,
        "config_sha256": _sha256(config_path),
        "design_document_sha256": _sha256(design_path),
        "s23r1": s23r1_auth,
        "s24_run_dir": s24_auth["run_dir"],
        "s24_hashes": s24_auth["hashes"],
        "s24_active_raw_inventory_digest": s24_auth["active_raw"]["inventory"]["digest"],
        "s21_source_raw_count": source_count,
        "requested_matrix_digest": _digest(requested.tolist()),
        "formal_timing_changed": False,
    }
    detailed = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "classification": "zero_tsc_contracted_amplitude_preflight",
        "provenance": provenance,
        "provenance_digest": _digest(provenance),
        "s24_source_authentication": s24_auth,
        "source_failure_rows": failure_rows,
        "s21_reproduction": reproduction,
        "static_primary_gate_counts": primary,
        "requested_matrix": requested.tolist(),
        "requested_matrix_metrics": matrix_metrics,
        "context_rows": context_rows,
        "event_rows": event_rows,
        "selected_sentinel_spec_count": len(sentinel_rows),
        "source_applicability_passed": source_pass,
        "static_replay_passed": static_pass,
        "primary_pass": primary_pass,
        "route": route,
        "execution": cfg["execution_contract"],
        "scientific_scope": cfg["scientific_scope"],
        "audit_complete": True,
    }
    maximum_slot = max(float(row["normalized_condition"]) for row in matrix_metrics["slot_rows"])
    summary = {
        "schema_version": 1,
        "stage": STAGE,
        "identity": IDENTITY,
        "provenance_digest": detailed["provenance_digest"],
        "s24_active_raw_count": s24_auth["active_raw"]["inventory"]["count"],
        "s24_sequence_success_count": s24_auth["active_raw"]["sequence_complete_success_count"],
        "s24_allowed_failure_count": len(failure_rows),
        "s24_cancel_event_counts_by_amplitude": s24_auth["active_raw"]["cancellation_event_counts_by_amplitude"],
        "s24_maximum_cancel_increment_by_amplitude": s24_auth["active_raw"]["maximum_cancel_increment_by_amplitude"],
        "source_applicability_passed": source_pass,
        "source_raw_authentication_count": source_count,
        **reproduction,
        **primary,
        "context_count": len(context_rows),
        "event_row_count": len(event_rows),
        "requested_global_rank": int(matrix_metrics["global_rank"]),
        "requested_global_normalized_condition": float(matrix_metrics["global_normalized_condition"]),
        "requested_maximum_slot_normalized_condition": maximum_slot,
        "selected_sentinel_spec_count": len(sentinel_rows),
        "static_replay_passed": static_pass,
        "primary_pass": primary_pass,
        "route": route,
        "scientific_classification": {
            "runtime_or_environment_error": False,
            "raw_or_snapshot_corruption": False,
            "statistics_or_reporting_error": False,
            "s24_action_schedule_design_failure": True,
            "real_tsc_or_plant_executed_by_d1": False,
            "real_controller_or_mpc_executed_by_d1": False,
            "real_closed_loop_conclusion_from_d1": "not_tested",
            "full_campaign_authorized": False,
            "safety_sentinel_authorized": primary_pass,
        },
    }
    output.mkdir(parents=True, exist_ok=False)
    detailed_path = output / "stage4_2r3c3t13s24d1_contracted_amplitude_preflight_v1.json"
    summary_path = output / "stage4_2r3c3t13s24d1_summary_v1.json"
    sentinel_path = output / "stage4_2r3c3t13s24d1_selected_sentinel_specs_v1.json"
    _write_json(detailed_path, detailed)
    _write_json(summary_path, summary)
    _write_json(sentinel_path, {
        "schema_version": 1,
        "stage": STAGE,
        "next_stage": cfg["sentinel_contract"]["next_stage"],
        "source_outcomes_available_to_controller": False,
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
    manifest_path = output / "stage4_2r3c3t13s24d1_manifest_v1.json"
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
