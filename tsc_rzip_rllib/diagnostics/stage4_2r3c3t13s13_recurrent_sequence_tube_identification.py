#!/usr/bin/env python3
"""Stage4.2R3c3T13S13 recurrent causal sequence-tube identification."""

from __future__ import annotations

import argparse
import copy
from collections import defaultdict
from dataclasses import dataclass
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import time
import traceback
from types import SimpleNamespace
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

from tsc_rzip_rllib.core.coil_order import DISPLAY_TO_TSC_INDEX
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s9_unified_postqueue_q1_identification as s9,
)
from tsc_rzip_rllib.utils.ray_runtime import ensure_ray_worker_plan


SCHEMA_VERSION = 1
STAGE = "Stage4.2R3c3T13S13"
RUN_NAME = "stage4_2r3c3t13s13_recurrent_sequence_tube_identification"
CAMPAIGN_IDENTITY = "recurrent_causal_sequence_tube_identification_v1"
CONTROLLER_REVISION = "recurrent_sequence_lattice_probe_v42r3c3t13s13_v1"
PACKAGE_REVISION = "r42r3c3t13s13_recurrent_sequence_tube_v1"
PASS_ROUTE = "RECURRENT_CAUSAL_SEQUENCE_TUBE_HOLDOUT_PASS_MULTISTEP_AUDIT_REQUIRED"
FAIL_ROUTE = "RECURRENT_CAUSAL_SEQUENCE_TUBE_INSUFFICIENT_REDESIGN"
BASELINE_PROBE_ID = s9.BASELINE_PROBE_ID
WINDOWS = s9.WINDOWS
DIRECTIONS = s9.DIRECTIONS
SIGNS = s9.SIGNS
N_COILS = s9.N_COILS
RESPONSE_FLOOR = np.asarray([1e-9, 1e-9, 1e-7, 1e-7, 1e-4])
PHASES = (
    "offline_ready",
    "training_baseline_complete",
    "training_probe_complete",
    "training_model_frozen",
    "calibration_baseline_complete",
    "calibration_probe_complete",
    "calibration_tube_frozen",
    "holdout_baseline_complete",
    "holdout_probe_complete",
    "campaign_complete",
)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _digest(value: Any) -> str:
    return s9._canonical_digest(value)


def _read_json(path: Path) -> Any:
    return s9.t11.t1.r3c3.read_json(path)


def _write_json(path: Path, value: Any) -> None:
    s9.t11.t1.r3c3.atomic_write_json(path, value)


def _write_json_gz(path: Path, value: Any) -> None:
    s9.t11.t1.r3c3.atomic_write_json_gz(path, value)


def _formal_horizon(slew: float) -> int:
    return s9._formal_horizon(slew)


@dataclass(frozen=True)
class Paths:
    run_dir: Path
    control: Path
    raw: Path
    variants: Path
    source_reference: Path
    specs: Path
    model: Path
    analysis: Path
    manifest: Path
    state: Path


def _paths(run_dir: Path) -> Paths:
    root = run_dir.expanduser().resolve()
    control = root / RUN_NAME
    return Paths(
        run_dir=root,
        control=control,
        raw=control / "raw",
        variants=root / "stage4_2r3c3t13s13_environment_variants",
        source_reference=root / "stage4_2r3c3t13s13_source_reference",
        specs=root / "stage4_2r3c3t13s13_specs",
        model=root / "stage4_2r3c3t13s13_frozen_model",
        analysis=root / "stage4_2r3c3t13s13_analysis",
        manifest=root / "stage4_2r3c3t13s13_manifest.json",
        state=root / "stage4_2r3c3t13s13_state.json",
    )


@dataclass(frozen=True)
class Context:
    cfg: dict[str, Any]
    config_path: Path
    base_ctx: s9.Stage42R3C3T13S9Context
    q1_run: Path
    q2_run: Path
    q1_audit: Path
    q2_audit: Path
    r3b_server_audit: Path
    r3b_snapshot_checks: Path
    paths: Paths


def _validate_config(cfg: Mapping[str, Any]) -> None:
    split = cfg["split"]
    probe = cfg["lattice_probe"]
    observer = cfg["observer"]
    matrix = cfg["control_matrix"]
    if (
        int(cfg.get("schema_version", -1)) != SCHEMA_VERSION
        or cfg.get("stage") != STAGE
        or int(cfg.get("design_revision", -1)) != 1
        or cfg.get("run_name") != RUN_NAME
        or cfg.get("campaign_identity") != CAMPAIGN_IDENTITY
        or cfg.get("controller_revision") != CONTROLLER_REVISION
        or cfg.get("probe_primitive_revision") != s9.CONTROLLER_REVISION
        or cfg.get("package_revision") != PACKAGE_REVISION
    ):
        raise ValueError("T13S13 identity changed")
    if (
        int(split["expected_pairs"]) != 36
        or int(split["expected_contexts"]) != 72
        or int(split["expected_training_contexts"]) != 32
        or int(split["expected_calibration_contexts"]) != 20
        or int(split["expected_holdout_contexts"]) != 20
        or tuple(split["history_members"]) != ("plus_first", "minus_first")
        or not bool(split["forbid_outcome_based_selection"])
    ):
        raise ValueError("T13S13 split contract changed")
    regimes = {
        row["id"]: (row["target_id"], int(row["action_delay_steps"]), float(row["slew_scale"]))
        for row in split["regimes"]
    }
    if regimes != {
        "A": ("nominal", 0, 1.0),
        "B": ("nominal", 2, 0.9),
        "C": ("RZ_p10_m10", 0, 1.0),
        "D": ("RZ_p10_m10", 2, 0.9),
    }:
        raise ValueError("T13S13 regime contract changed")
    if (
        tuple(probe["probe_directions"]) != DIRECTIONS
        or tuple(map(int, probe["probe_signs"])) != SIGNS
        or tuple(probe["effect_windows"]) != WINDOWS
        or float(probe["maximum_incremental_normalized_action_linf"]) != 0.25
        or float(probe["maximum_total_normalized_action_abs"]) != 1.0
        or float(probe["maximum_current_utilization"]) != 0.55
        or float(probe["required_observed_odd_signal_radius_l2"]) != 4.0
        or float(probe["maximum_observed_even_to_odd_l2"]) != 0.1
        or float(probe["signal_floor_multiplier"]) != 10.0
        or float(probe["pre_effect_position_max_m"]) != 1e-9
        or float(probe["pre_effect_velocity_max_m_per_s"]) != 1e-7
        or float(probe["pre_effect_ip_max_A"]) != 1e-4
        or bool(probe["probe_trajectories_allowed_in_expert_dataset"])
        or bool(probe["post_effect_current_model_input_allowed"])
    ):
        raise ValueError("T13S13 probe contract changed")
    expected_schedules = {
        "0": {
            "transport": (2, 3, 3, 4),
            "braking": (16, 17, 17, 18),
        },
        "2": {
            "transport": (0, 1, 1, 2),
            "braking": (14, 15, 15, 16),
        },
    }
    for delay, windows in expected_schedules.items():
        for window, expected in windows.items():
            row = probe["schedule_by_delay"][delay][window]
            actual = tuple(int(row[key]) for key in (
                "issue_step", "cancel_step", "first_effect_state", "cancel_effect_state"
            ))
            if actual != expected:
                raise ValueError("T13S13 post-queue schedule changed")
    if (
        int(observer["seed"]) != 20260802
        or int(observer["reservoir_width"]) != 32
        or int(observer["feature_count_per_state"]) != 59
        or int(observer["maximum_sequence_states"]) != 17
        or list(map(float, observer["spectral_radii"])) != [0.35, 0.65, 0.85]
        or list(map(float, observer["leaks"])) != [0.5, 1.0]
        or list(map(int, observer["observer_ranks"])) != [4, 8, 12]
        or list(map(float, observer["ridge_values"])) != [1e-8, 1e-6, 1e-4]
        or int(observer["action_rank"]) != 4
        or float(observer["maximum_interaction_condition_number"]) != 30.0
        or float(observer["maximum_scaled_center_relative_error"]) != 0.1
        or float(observer["near_alias_linf_atol"]) != 1e-12
    ):
        raise ValueError("T13S13 observer contract changed")
    expected_counts = (1224, 136, 24, 384, 20, 320, 20, 320, 1088)
    actual_counts = tuple(int(matrix[key]) for key in (
        "expected_equivalent_rollouts", "expected_consumed_training_rollouts",
        "expected_new_training_baselines", "expected_new_training_probes",
        "expected_calibration_baselines", "expected_calibration_probes",
        "expected_holdout_baselines", "expected_holdout_probes",
        "expected_new_rollouts",
    ))
    if actual_counts != expected_counts:
        raise ValueError("T13S13 rollout count changed")
    if (
        bool(cfg["formal_timing_contract"]["arrival_deadline_expansion_allowed"])
        or not bool(cfg["identification_only"])
        or not bool(cfg["fresh_holdout_required"])
        or bool(cfg["bc_dagger_or_rl_allowed"])
    ):
        raise ValueError("T13S13 scientific route changed")


def load_config(
    config_path: Path,
    *,
    source_stage42r3b_run: Path,
    source_stage42r3c3_run: Path,
    source_stage42r3c3_bank_dir: Path,
    source_stage42r3c3t1_run: Path,
    source_stage42r3c3t1_audit_dir: Path,
    source_stage42r3c3t3_controller_bank: Path,
    q1_run: Path,
    q2_run: Path,
    q1_audit: Path,
    q2_audit: Path,
    r3b_server_audit: Path,
    r3b_snapshot_checks: Path,
    run_dir: Path,
) -> Context:
    config_path = config_path.expanduser().resolve()
    cfg = _read_json(config_path)
    _validate_config(cfg)
    base_path = (_project_root() / str(cfg["base_stage_config"])).resolve()
    if not base_path.is_file() or _sha256(base_path) != cfg["base_stage_config_sha256"]:
        raise ValueError("T13S13 base S9 config mismatch")
    base_ctx = s9.load_stage42r3c3t13s9_config(
        base_path,
        source_stage42r3b_run=source_stage42r3b_run,
        source_stage42r3c3_run=source_stage42r3c3_run,
        source_stage42r3c3_bank_dir=source_stage42r3c3_bank_dir,
        source_stage42r3c3t1_run=source_stage42r3c3t1_run,
        source_stage42r3c3t1_audit_dir=source_stage42r3c3t1_audit_dir,
        source_stage42r3c3t3_controller_bank=source_stage42r3c3t3_controller_bank,
        run_dir_override=run_dir,
    )
    return Context(
        cfg=cfg,
        config_path=config_path,
        base_ctx=base_ctx,
        q1_run=q1_run.expanduser().resolve(),
        q2_run=q2_run.expanduser().resolve(),
        q1_audit=q1_audit.expanduser().resolve(),
        q2_audit=q2_audit.expanduser().resolve(),
        r3b_server_audit=r3b_server_audit.expanduser().resolve(),
        r3b_snapshot_checks=r3b_snapshot_checks.expanduser().resolve(),
        paths=_paths(run_dir),
    )


def _source_paths(ctx: Context) -> dict[str, Path]:
    root = ctx.base_ctx.base_ctx.base_ctx.source_ctx.source_r3b_run
    return {
        "pair_results": root / "stage4_2r3b_pair_analysis" / "results.json",
        "state_specs": root / "stage4_2r3b_source_reference" / "state_generation_specs.json",
        "state_results": root / "stage4_2r3b_state_generation" / "results.json",
        "manifest": root / "stage4_2r3b_manifest.json",
        "server_audit": ctx.r3b_server_audit,
        "snapshot_checks": ctx.r3b_snapshot_checks,
    }


def _authenticate_sources(ctx: Context) -> dict[str, Any]:
    contract = ctx.cfg["source_contract"]
    paths = _source_paths(ctx)
    expected = {
        "pair_results": contract["r3b_pair_results_sha256"],
        "state_specs": contract["r3b_state_specs_sha256"],
        "state_results": contract["r3b_state_results_sha256"],
        "manifest": contract["r3b_manifest_sha256"],
        "server_audit": contract["r3b_server_audit_sha256"],
        "snapshot_checks": contract["r3b_snapshot_checks_sha256"],
    }
    rows = []
    for key, path in paths.items():
        if not path.is_file():
            raise FileNotFoundError(f"T13S13 source file missing: {path}")
        actual = _sha256(path)
        if actual != expected[key]:
            raise ValueError(f"T13S13 source {key} SHA-256 mismatch")
        rows.append({"source": key, "path": str(path), "sha256": actual})
    q1_raw = sorted((ctx.q1_run / "stage4_2r3c3t13s9_unified_postqueue_q1_identification" / "raw").glob("*.json.gz"))
    q2_raw = sorted((ctx.q2_run / "stage4_2r3c3t13s5_lattice_native_split_holdout" / "raw").glob("*.json.gz"))
    for label, files, count, digest in (
        ("q1", q1_raw, int(contract["q1_raw_count"]), contract["q1_raw_inventory_digest"]),
        ("q2", q2_raw, int(contract["q2_raw_count"]), contract["q2_raw_inventory_digest"]),
    ):
        inventory = [{"path": path.name, "size_bytes": path.stat().st_size, "sha256": _sha256(path)} for path in files]
        if len(files) != count or _digest(inventory) != digest:
            raise ValueError(f"T13S13 consumed {label} raw inventory mismatch")
    for label, path, expected_sha in (
        ("q1", ctx.q1_audit, contract["q1_server_audit_sha256"]),
        ("q2", ctx.q2_audit, contract["q2_server_audit_sha256"]),
    ):
        if not path.is_file() or _sha256(path) != expected_sha:
            raise ValueError(f"T13S13 consumed {label} audit mismatch")
        audit = _read_json(path)
        if not bool(
            int(audit.get("control_raw_expected", -1)) == 68
            and int(audit.get("control_raw_actual", -1)) == 68
            and audit.get("control_raw_identity_exact")
            and audit.get("reported_summary_exact_on_recomputation")
            and int(audit.get("runtime_or_environment_error_count", -1)) == 0
            and int(audit.get("plant_restart_fidelity_failure_count", -1)) == 0
            and int(audit.get("controller_causality_failure_count", -1)) == 0
            and int(audit.get("statistics_or_reporting_error_count", -1)) == 0
            and bool((audit.get("snapshot_integrity") or {}).get("passed"))
        ):
            raise ValueError(f"T13S13 consumed {label} evidence integrity failed")
    r3b_audit = _read_json(ctx.r3b_server_audit)
    snapshot_audit = _read_json(ctx.r3b_snapshot_checks)
    if not bool(
        r3b_audit.get("state_raw_parse_complete")
        and int(r3b_audit.get("state_raw_expected", -1)) == 72
        and int(r3b_audit.get("state_raw_actual", -1)) == 72
        and int(r3b_audit.get("snapshot_expected", -1)) == 72
        and int(r3b_audit.get("snapshot_valid_count", -1)) == 72
        and bool(r3b_audit.get("reporting_recomputation_completed"))
    ):
        raise ValueError("T13S13 authenticated R3b state/snapshot evidence is incomplete")
    if not (
        isinstance(snapshot_audit, list) and len(snapshot_audit) == 72
        and all(bool(row.get("valid")) for row in snapshot_audit)
    ):
        raise ValueError("T13S13 authenticated R3b snapshot checks are incomplete")
    return {"passed": True, "files": rows, "q1_raw_count": len(q1_raw), "q2_raw_count": len(q2_raw)}


def _parse_pair_id(pair_id: str) -> tuple[int, int, float, int]:
    import re
    match = re.fullmatch(r"p(5|9)_q(1|2)_a0p(600|750|900)_gap(2|3|4)_settle4", pair_id)
    if match is None:
        raise ValueError(f"T13S13 unexpected R3b pair id: {pair_id}")
    return int(match.group(1)), int(match.group(2)), int(match.group(3)) / 1000.0, int(match.group(4))


def build_context_table(ctx: Context) -> list[dict[str, Any]]:
    state_rows = _read_json(_source_paths(ctx)["state_results"])
    pair_rows = _read_json(_source_paths(ctx)["pair_results"])
    if len(state_rows) != 72 or len(pair_rows) != 36:
        raise ValueError("T13S13 R3b source coverage mismatch")
    states: dict[str, dict[str, Mapping[str, Any]]] = defaultdict(dict)
    for row in state_rows:
        if not bool(row["success"]):
            raise ValueError("T13S13 source state is not successful")
        states[str(row["pair_id"])][str(row["history_order"])] = row
    pair_ids = sorted(str(row["pair_id"]) for row in pair_rows)
    if set(pair_ids) != set(states) or any(set(states[pair]) != {"plus_first", "minus_first"} for pair in pair_ids):
        raise ValueError("T13S13 pair/member state coverage mismatch")
    consumed = set(map(str, ctx.cfg["split"]["consumed_training_pairs"]))
    regimes = {row["id"]: row for row in ctx.cfg["split"]["regimes"]}
    amplitude_groups: dict[float, list[str]] = defaultdict(list)
    parsed = {}
    for pair in pair_ids:
        parsed[pair] = _parse_pair_id(pair)
        amplitude_groups[parsed[pair][2]].append(pair)
    new_training = sorted(amplitude_groups[0.6])
    calibration = sorted(set(amplitude_groups[0.9]) - consumed)
    holdout = sorted(set(amplitude_groups[0.75]) - consumed)
    if len(new_training) != 12 or len(calibration) != 10 or len(holdout) != 10:
        raise ValueError("T13S13 pair partition mismatch")
    assignments: dict[str, tuple[str, str]] = {}
    for pair in consumed:
        assignments[pair] = ("training", "D" if pair.startswith("p5_") else "A")
    for partition, pairs, start in (
        ("training", new_training, 0),
        ("calibration", calibration, 0),
        ("holdout", holdout, 2),
    ):
        for index, pair in enumerate(pairs):
            assignments[pair] = (partition, "ABCD"[(start + index) % 4])
    if set(assignments) != set(pair_ids):
        raise ValueError("T13S13 split is not exhaustive")
    table = []
    for pair in pair_ids:
        prefix, direction, amplitude, gap = parsed[pair]
        partition, regime_id = assignments[pair]
        regime = regimes[regime_id]
        for member in ("plus_first", "minus_first"):
            state = states[pair][member]
            table.append({
                "pair_id": pair,
                "history_member": member,
                "partition": partition,
                "consumed_training": pair in consumed,
                "regime_id": regime_id,
                "target_id": regime["target_id"],
                "action_delay_steps": int(regime["action_delay_steps"]),
                "slew_scale": float(regime["slew_scale"]),
                "common_prefix_steps": prefix,
                "nullspace_direction_index": direction,
                "amplitude_fraction": amplitude,
                "gap_steps": gap,
                "state_generation_experiment_id": str(state["experiment_id"]),
                "restart_snapshot_dir": str(state["snapshot_dir"]),
                "restart_snapshot_manifest_digest": str(state["snapshot_manifest_digest"]),
            })
    counts = {name: sum(row["partition"] == name for row in table) for name in ("training", "calibration", "holdout")}
    if counts != {"training": 32, "calibration": 20, "holdout": 20}:
        raise ValueError("T13S13 context partition counts changed")
    return table


def _source_templates(ctx: Context) -> dict[tuple[str, int, float], dict[str, Any]]:
    selected_pairs = s9._selected_pairs(ctx.base_ctx)
    source = s9.t11.build_control_specs(ctx.base_ctx.base_ctx, selected_pairs)
    candidates: dict[tuple[str, int, float], list[dict[str, Any]]] = defaultdict(list)
    for spec in source:
        if str(spec["r3c3_probe_id"]) == s9.t11.BASELINE_PROBE_ID:
            key = (str(spec["target_id"]), int(spec["action_delay_steps"]), float(spec["slew_scale"]))
            candidates[key].append(spec)
    expected = {
        ("nominal", 0, 1.0), ("nominal", 2, 0.9),
        ("RZ_p10_m10", 0, 1.0), ("RZ_p10_m10", 2, 0.9),
    }
    if set(candidates) != expected or any(len(rows) != 8 for rows in candidates.values()):
        raise ValueError("T13S13 source template coverage mismatch")
    return {
        key: copy.deepcopy(sorted(rows, key=lambda row: str(row["experiment_id"]))[0])
        for key, rows in candidates.items()
    }


def build_new_specs(ctx: Context, table: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    templates = _source_templates(ctx)
    schedule_cfg = ctx.cfg["lattice_probe"]["schedule_by_delay"]
    specs: list[dict[str, Any]] = []
    for row in table:
        if bool(row["consumed_training"]):
            continue
        key = (str(row["target_id"]), int(row["action_delay_steps"]), float(row["slew_scale"]))
        template = templates[key]
        delay = key[1]
        horizon = _formal_horizon(key[2])
        members = [(BASELINE_PROBE_ID, "baseline", "", 0)]
        members.extend(
            (f"lattice_{window}_{direction}", window, direction, sign)
            for window in WINDOWS for direction in DIRECTIONS for sign in SIGNS
        )
        for probe_id, window, direction, sign in members:
            schedule = None if window == "baseline" else schedule_cfg[str(delay)][window]
            identity = {
                "stage": STAGE,
                "campaign_identity": CAMPAIGN_IDENTITY,
                "pair_id": row["pair_id"],
                "history_member": row["history_member"],
                "state_generation_experiment_id": row["state_generation_experiment_id"],
                "snapshot_manifest_digest": row["restart_snapshot_manifest_digest"],
                "target_id": row["target_id"],
                "delay": delay,
                "slew": key[2],
                "probe_id": probe_id,
                "probe_sign": sign,
                "controller_revision": CONTROLLER_REVISION,
            }
            experiment_id = s9.t11.t1.r3c3._scenario_digest(identity)
            spec = copy.deepcopy(template)
            spec.update({
                "kind": "stage4_2r3c3t13s13_recurrent_sequence_tube_identification",
                "stage": STAGE,
                "campaign_identity": CAMPAIGN_IDENTITY,
                "controller_revision": CONTROLLER_REVISION,
                "underlying_controller_revision": s9.t11.t1.r3c1.CONTROLLER_REVISION,
                "probe_primitive_revision": s9.CONTROLLER_REVISION,
                "experiment_id": experiment_id,
                "phase": "recurrent_sequence_response_identification",
                "category": "identification_only_partitioned_sequence_response",
                "pair_id": str(row["pair_id"]),
                "history_member": str(row["history_member"]),
                "state_generation_experiment_id": str(row["state_generation_experiment_id"]),
                "restart_snapshot_dir": str(row["restart_snapshot_dir"]),
                "restart_snapshot_manifest_digest": str(row["restart_snapshot_manifest_digest"]),
                "baseline_experiment_id": "",
                "environment_variant": f"stage4_2r3c3t13s13_{experiment_id}",
                "horizon_steps": horizon,
                "formal_horizon_steps": horizon,
                "identification_only": True,
                "r3c3_probe_id": probe_id,
                "r3c3_probe_window": window,
                "r3c3_probe_direction": direction,
                "r3c3_probe_sign": sign,
                "r3c3_probe_issue_step": -1 if schedule is None else int(schedule["issue_step"]),
                "r3c3_probe_cancel_step": -1 if schedule is None else int(schedule["cancel_step"]),
                "r3c3_probe_first_effect_state": -1 if schedule is None else int(schedule["first_effect_state"]),
                "r3c3_probe_cancel_effect_state": -1 if schedule is None else int(schedule["cancel_effect_state"]),
                "r3c3t13s9_schedule_contract": "lattice_native_split_return_first_hybrid_cancel_v1",
                "r3c3t13s9_offline_role": str(row["partition"]),
                "r3c3t13s9_stratum": "normal" if delay == 0 else "weak",
                "r3c3t13s9_source_r3c1_experiment_id": "",
                "probe_trajectory_allowed_in_expert_dataset": False,
                "pair_or_history_label_available_to_controller": False,
                "source_result_available_to_controller": False,
                "source_action_available_to_controller": False,
                "source_coil_current_available_to_controller": False,
                "source_wire_current_available_to_controller": False,
                "hidden_wire_current_available_to_controller": False,
                "future_action_count": 0,
                "future_measurement_count": 0,
                "online_action_computation_required": True,
                "task_clock_starts_at_zero": True,
                "formal_timing_unchanged": True,
            })
            specs.append(spec)
    if len(specs) != 1088 or len({str(row["experiment_id"]) for row in specs}) != 1088:
        raise ValueError("T13S13 new spec coverage mismatch")
    return specs


def _partition_specs(
    specs: Sequence[Mapping[str, Any]], table: Sequence[Mapping[str, Any]],
    partition: str, *, baseline: bool,
) -> list[dict[str, Any]]:
    keys = {
        (str(row["pair_id"]), str(row["history_member"]))
        for row in table
        if row["partition"] == partition and not bool(row["consumed_training"])
    }
    output = [
        copy.deepcopy(dict(spec)) for spec in specs
        if (str(spec["pair_id"]), str(spec["history_member"])) in keys
        and (str(spec["r3c3_probe_id"]) == BASELINE_PROBE_ID) == baseline
    ]
    expected_contexts = {"training": 24, "calibration": 20, "holdout": 20}[partition]
    expected = expected_contexts if baseline else expected_contexts * 16
    if len(output) != expected:
        raise ValueError("T13S13 phase specification count mismatch")
    return output


def _package_fingerprint(ctx: Context) -> dict[str, Any]:
    project = _project_root()
    manifest = _read_json(project / "PACKAGE_MANIFEST.json")
    paths = [project / str(relative) for relative in manifest["file_inventory"]]
    required = {
        project / "configs/stage4_2r3c3t13s13_recurrent_sequence_tube_identification_370ms.json",
        project / "tsc_rzip_rllib/diagnostics/stage4_2r3c3t13s13_recurrent_sequence_tube_identification.py",
        project / "scripts/stage4_2r3c3t13s13_recurrent_sequence_tube_identification.py",
        project / "scripts/stage4_2r3c3t13s13_server_postprocess.py",
        project / "scripts/stage4_2r3c3t13s13_shell_common.sh",
        project / "run_stage4_2r3c3t13s13_common.sh",
        project / "run_stage4_2r3c3t13s13_offline.sh",
        project / "run_stage4_2r3c3t13s13_native.sh",
        project / "run_stage4_2r3c3t13s13_nohup.sh",
        project / "run_stage4_2r3c3t13s13_self_test.sh",
        project / "run_stage4_2r3c3t13s13_server_postprocess.sh",
        project / "run_stage4_2r3c3t13s13_verify_package.sh",
        project / "run_stop_stage4_2r3c3t13s13_now.sh",
        project / "docs/codex/reports/STAGE4_2R3C3T13S13_RECURRENT_SEQUENCE_TUBE_IDENTIFICATION_DESIGN.md",
    }
    if not required <= set(paths):
        missing = sorted(str(path.relative_to(project)) for path in required - set(paths))
        raise ValueError(f"T13S13 package inventory missing: {missing}")
    rows = []
    for path in paths:
        if not path.is_file():
            raise FileNotFoundError(f"T13S13 package file missing: {path}")
        rows.append({
            "path": path.relative_to(project).as_posix(),
            "size_bytes": path.stat().st_size,
            "sha256": _sha256(path),
        })
    rows.sort(key=lambda row: row["path"])
    return {
        "contract": "r42r3c3t13s13_deployed_package_source_v1",
        "package_revision": PACKAGE_REVISION,
        "file_count": len(rows),
        "total_bytes": sum(row["size_bytes"] for row in rows),
        "digest": _digest(rows),
        "files": rows,
    }


def _reporting_hotfix_package_compatible(
    old: Mapping[str, Any], new: Mapping[str, Any],
) -> tuple[bool, list[dict[str, Any]]]:
    if (
        old.get("contract") != new.get("contract")
        or old.get("package_revision") != new.get("package_revision")
    ):
        return False, []
    old_files = {str(row["path"]): dict(row) for row in old.get("files") or []}
    new_files = {str(row["path"]): dict(row) for row in new.get("files") or []}
    if set(old_files) != set(new_files):
        return False, []
    changed = [
        {
            "path": path,
            "old_sha256": old_files[path]["sha256"],
            "new_sha256": new_files[path]["sha256"],
            "old_size_bytes": old_files[path]["size_bytes"],
            "new_size_bytes": new_files[path]["size_bytes"],
        }
        for path in sorted(old_files)
        if old_files[path] != new_files[path]
    ]
    allowed = {
        "tests/test_stage4_2r3c3t13s13_recurrent_sequence_tube_identification.py",
        "tsc_rzip_rllib/diagnostics/stage4_2r3c3t13s13_recurrent_sequence_tube_identification.py",
    }
    return bool(changed and {row["path"] for row in changed} <= allowed), changed


def _reporting_hotfix_manifest_compatible(
    old: Mapping[str, Any], new: Mapping[str, Any],
) -> tuple[bool, list[dict[str, Any]]]:
    package_ok, changed = _reporting_hotfix_package_compatible(
        old.get("deployed_package_fingerprint") or {},
        new.get("deployed_package_fingerprint") or {},
    )
    if not package_ok:
        return False, changed
    old_copy = copy.deepcopy(dict(old))
    new_copy = copy.deepcopy(dict(new))
    old_copy["deployed_package_fingerprint"] = copy.deepcopy(
        new_copy["deployed_package_fingerprint"]
    )
    return old_copy == new_copy, changed


def _validate_snapshots(table: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    rows = []
    for context in table:
        directory = Path(str(context["restart_snapshot_dir"])).expanduser().resolve()
        manifest_path = directory / "restart_snapshot_manifest.json"
        passed = False
        reason = ""
        try:
            manifest = _read_json(manifest_path)
            passed = bool(
                str(manifest.get("digest", ""))
                == str(context["restart_snapshot_manifest_digest"])
                and s9.t11.t1.r1._validate_snapshot_inventory(directory, manifest)
            )
            if not passed:
                reason = "snapshot inventory mismatch"
        except Exception as exc:
            reason = repr(exc)
        rows.append({
            "pair_id": context["pair_id"],
            "history_member": context["history_member"],
            "state_generation_experiment_id": context["state_generation_experiment_id"],
            "snapshot_dir": str(directory),
            "snapshot_manifest_sha256": str(context["restart_snapshot_manifest_digest"]),
            "passed": passed,
            "failure_reason": reason,
        })
    return {"expected": 72, "actual": len(rows), "pass_count": sum(row["passed"] for row in rows), "passed": len(rows) == 72 and all(row["passed"] for row in rows), "rows": rows}


def _prepare_dirs(paths: Paths) -> None:
    for path in (paths.run_dir, paths.control, paths.raw, paths.variants, paths.source_reference, paths.specs, paths.model, paths.analysis):
        path.mkdir(parents=True, exist_ok=True)


def prepare_offline(ctx: Context, *, resume: bool) -> dict[str, Any]:
    _prepare_dirs(ctx.paths)
    source = _authenticate_sources(ctx)
    table = build_context_table(ctx)
    specs = build_new_specs(ctx, table)
    snapshot = _validate_snapshots(table)
    package = _package_fingerprint(ctx)
    raw_before = sorted(ctx.paths.raw.glob("*.json.gz"))
    if raw_before and not resume:
        raise ValueError("T13S13 non-resume offline preflight found new-stage raw")
    context_digest = _digest(table)
    spec_digest = _digest(specs)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "campaign_identity": CAMPAIGN_IDENTITY,
        "controller_revision": CONTROLLER_REVISION,
        "probe_primitive_revision": s9.CONTROLLER_REVISION,
        "package_revision": PACKAGE_REVISION,
        "config_path": str(ctx.config_path),
        "config_sha256": _sha256(ctx.config_path),
        "source_authentication": source,
        "context_count": len(table),
        "context_table_digest": context_digest,
        "new_spec_count": len(specs),
        "new_spec_digest": spec_digest,
        "snapshot_audit": {key: value for key, value in snapshot.items() if key != "rows"},
        "deployed_package_fingerprint": package,
        "formal_timing_unchanged": True,
        "probe_trajectories_allowed_in_expert_dataset": False,
        "bc_dagger_or_rl_allowed": False,
    }
    reporting_hotfix = False
    reporting_hotfix_changes: list[dict[str, Any]] = []
    execution_package_digest = package["digest"]
    if ctx.paths.manifest.exists():
        old_manifest = _read_json(ctx.paths.manifest)
        execution_package_digest = old_manifest["deployed_package_fingerprint"]["digest"]
        if old_manifest != manifest:
            compatible, reporting_hotfix_changes = _reporting_hotfix_manifest_compatible(
                old_manifest, manifest
            )
            if not (resume and compatible):
                raise ValueError("T13S13 resume manifest mismatch")
            reporting_hotfix = True
    else:
        _write_json(ctx.paths.manifest, manifest)
    _write_json(ctx.paths.source_reference / "context_table.json", table)
    _write_json(ctx.paths.source_reference / "source_authentication.json", source)
    _write_json(ctx.paths.source_reference / "snapshot_audit.json", snapshot)
    if reporting_hotfix:
        _write_json(ctx.paths.analysis / "semantics_preserving_reporting_hotfix.json", {
            "schema_version": SCHEMA_VERSION,
            "stage": STAGE,
            "contract": "t13s13_execution_semantics_unchanged_reporting_hotfix_v1",
            "execution_package_digest": execution_package_digest,
            "reporting_package_digest": package["digest"],
            "changed_files": reporting_hotfix_changes,
            "raw_preserved_count": len(raw_before),
            "controller_revision_unchanged": True,
            "probe_primitive_revision_unchanged": True,
            "config_sha256_unchanged": True,
            "context_table_digest_unchanged": True,
            "new_spec_digest_unchanged": True,
            "formal_timing_unchanged": True,
            "physical_action_semantics_unchanged": True,
            "passed": True,
        })
    training_specs = _partition_specs(specs, table, "training", baseline=True) + _partition_specs(specs, table, "training", baseline=False)
    _write_json(ctx.paths.specs / "training_specs.json", training_specs)
    state = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "phase_status": "offline_ready",
        "finished": False,
        "primary_pass": False,
        "real_tsc_executed": bool(raw_before),
        "new_raw_count": len(raw_before),
        "context_table_digest": context_digest,
        "new_spec_digest": spec_digest,
        "package_digest": package["digest"],
        "model_sha256": "",
        "tube_sha256": "",
        "stop_reason": "",
    }
    if ctx.paths.state.exists():
        old = _read_json(ctx.paths.state)
        if old.get("phase_status") not in PHASES or old.get("context_table_digest") != context_digest or old.get("new_spec_digest") != spec_digest or old.get("package_digest") != execution_package_digest:
            raise ValueError("T13S13 resume state identity mismatch")
        state = old
    else:
        _write_json(ctx.paths.state, state)
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "phase": "zero_tsc_source_split_snapshot_preflight",
        "source_authentication": source,
        "context_counts": {name: sum(row["partition"] == name for row in table) for name in ("training", "calibration", "holdout")},
        "context_table_digest": context_digest,
        "new_spec_count": len(specs),
        "new_spec_digest": spec_digest,
        "snapshot_pass_count": snapshot["pass_count"],
        "snapshot_expected": 72,
        "new_raw_count": len(raw_before),
        "real_tsc_executed": bool(raw_before),
        "semantics_preserving_reporting_hotfix": reporting_hotfix,
        "execution_package_digest": execution_package_digest,
        "reporting_package_digest": package["digest"],
        "passed": bool(source["passed"] and snapshot["passed"] and (resume or not raw_before)),
    }


class LocalWorker(s9.LocalLatticeTransitionProbeWorker):
    """The frozen S9 physical primitive with a distinct S13 evidence identity."""

    def evaluate(self, spec: dict[str, Any]) -> dict[str, Any]:
        result = super().evaluate(spec)
        result.update({
            "schema_version": SCHEMA_VERSION,
            "stage": STAGE,
            "campaign_identity": CAMPAIGN_IDENTITY,
            "controller_revision": CONTROLLER_REVISION,
            "probe_primitive_revision": s9.CONTROLLER_REVISION,
        })
        for row in result.get("controller_trace", []):
            row["r3c3t13s13_identification_only"] = True
            row["post_effect_current_model_input_used"] = False
        summary = result.get("hidden_history_control_summary")
        if isinstance(summary, dict):
            summary["s13_recurrent_sequence_identification_only"] = True
            summary["probe_primitive_revision"] = s9.CONTROLLER_REVISION
            summary["post_effect_current_model_input_used"] = False
        return result


_RAY_ACTOR = None


def _ray_actor_class():
    global _RAY_ACTOR
    if _RAY_ACTOR is None:
        import ray

        @ray.remote(num_cpus=1, max_restarts=0)
        class Stage42R3C3T13S13Actor:
            def __init__(self, payload, library, bundle, worker_id, selector, lattice_cfg):
                self.worker = LocalWorker(payload, library, bundle, worker_id, selector, lattice_cfg)

            def evaluate(self, spec):
                return self.worker.evaluate(spec)

            def close(self):
                self.worker.close()
                return True

        _RAY_ACTOR = Stage42R3C3T13S13Actor
    return _RAY_ACTOR


def _payload(ctx: Context, spec: Mapping[str, Any]) -> dict[str, Any]:
    proxy = SimpleNamespace(base_ctx=ctx.base_ctx.base_ctx, paths=ctx.paths)
    payload = s9._control_payload(proxy, spec=spec)
    experiment_id = str(spec["experiment_id"])
    payload.update({
        "variant_id": f"stage4_2r3c3t13s13_{experiment_id}",
        "stage4_2r3c3t13s13_restart_snapshot_dir": str(spec["restart_snapshot_dir"]),
        "stage4_2r3c3t13s13_snapshot_manifest_digest": str(spec["restart_snapshot_manifest_digest"]),
        "stage4_2r3c3t13s13_partition_label_available_to_controller": False,
    })
    _write_json(ctx.paths.variants / f"payload_{experiment_id}.json", payload)
    return payload


def _library_bundle_selector(ctx: Context):
    r1_ctx = ctx.base_ctx.base_ctx.base_ctx.source_ctx.source_ctx.r1_ctx
    return s9.t11.t1.r1._library_bundle_selector(r1_ctx)


def _result_complete(path: Path, spec: Mapping[str, Any]) -> bool:
    if not path.is_file():
        return False
    try:
        result = s9.t11.t1.r3c3.read_json_gz(path)
        identity = bool(
            result.get("completed")
            and result.get("stage") == STAGE
            and result.get("campaign_identity") == CAMPAIGN_IDENTITY
            and result.get("controller_revision") == CONTROLLER_REVISION
            and result.get("probe_primitive_revision") == s9.CONTROLLER_REVISION
            and result.get("experiment_id") == spec["experiment_id"]
            and result.get("spec") == dict(spec)
            and isinstance(result.get("success"), bool)
            and isinstance(result.get("trajectory"), list)
            and isinstance(result.get("controller_trace"), list)
        )
        if not identity or not bool(result.get("success")):
            return identity
        trajectory = result["trajectory"]
        trace = result["controller_trace"]
        horizon = int(spec["horizon_steps"])
        return bool(
            len(trajectory) == horizon + 1 and len(trace) == horizon
            and all(
                isinstance(row, Mapping)
                and all(key in row for key in ("R", "Z", "Ip", "currents_a_tsc"))
                and len(row["currents_a_tsc"]) == N_COILS
                for row in trajectory
            )
            and all(
                isinstance(row, Mapping)
                and len(row.get("action_norm_tsc") or []) == N_COILS
                and isinstance(_prediction(row), Mapping)
                for row in trace
            )
            and isinstance(result.get("hidden_history_control_summary"), Mapping)
        )
    except Exception:
        return False


def _actor_failure(spec: Mapping[str, Any], exc: Exception) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "campaign_identity": CAMPAIGN_IDENTITY,
        "controller_revision": CONTROLLER_REVISION,
        "probe_primitive_revision": s9.CONTROLLER_REVISION,
        "experiment_id": str(spec["experiment_id"]),
        "spec": copy.deepcopy(dict(spec)),
        "success": False,
        "completed": True,
        "failure_reason": repr(exc),
        "traceback": traceback.format_exc(),
        "trajectory": [],
        "controller_trace": [],
    }


def evaluate_specs(
    ctx: Context, specs: Sequence[dict[str, Any]], *, backend: str, resume: bool,
) -> dict[str, Any]:
    ctx.paths.raw.mkdir(parents=True, exist_ok=True)
    pending = [
        spec for spec in specs
        if not (resume and _result_complete(ctx.paths.raw / f"{spec['experiment_id']}.json.gz", spec))
    ]
    payloads = {str(spec["experiment_id"]): _payload(ctx, spec) for spec in specs}
    library, bundle, selector = _library_bundle_selector(ctx)
    if backend == "serial":
        for index, spec in enumerate(pending):
            worker = LocalWorker(
                payloads[str(spec["experiment_id"])], library, bundle,
                f"stage42r3c3t13s13_serial_{index:04d}", selector,
                ctx.cfg["lattice_probe"],
            )
            try:
                result = worker.evaluate(spec)
            finally:
                worker.close()
            _write_json_gz(ctx.paths.raw / f"{spec['experiment_id']}.json.gz", result)
            print(f"[T13S13] {index + 1}/{len(pending)}", flush=True)
    elif backend == "ray" and pending:
        import ray

        plan = ensure_ray_worker_plan(
            ray,
            requested_workers=int(ctx.cfg["parallel"]["n_workers"]),
            pending_tasks=len(pending),
            ray_tmpdir=os.environ.get("RAY_TMPDIR") or ctx.cfg["storage"]["ray_tmpdir"],
            log_prefix="[T13S13]",
        )
        Actor = _ray_actor_class()
        completed = 0
        for batch_start in range(0, len(pending), plan.actor_count):
            batch = pending[batch_start:batch_start + plan.actor_count]
            actors = []
            refs = {}
            for offset, spec in enumerate(batch):
                actor = Actor.remote(
                    payloads[str(spec["experiment_id"])], library, bundle,
                    f"stage42r3c3t13s13_{batch_start + offset:04d}", selector,
                    ctx.cfg["lattice_probe"],
                )
                actors.append(actor)
                refs[actor.evaluate.remote(spec)] = spec
            try:
                while refs:
                    ready, _ = ray.wait(list(refs), num_returns=1, timeout=30.0)
                    if not ready:
                        print(f"[T13S13] waiting {completed}/{len(pending)}", flush=True)
                        continue
                    for ref in ready:
                        spec = refs.pop(ref)
                        try:
                            result = ray.get(ref)
                        except Exception as exc:
                            result = _actor_failure(spec, exc)
                        _write_json_gz(ctx.paths.raw / f"{spec['experiment_id']}.json.gz", result)
                        completed += 1
                        print(f"[T13S13] {completed}/{len(pending)}", flush=True)
            finally:
                close_refs = [actor.close.remote() for actor in actors]
                if close_refs:
                    ray.get(close_refs, timeout=float(ctx.cfg["storage"]["actor_close_timeout_s"]))
                for actor in actors:
                    ray.kill(actor, no_restart=True)
    elif backend not in {"serial", "ray"}:
        raise ValueError(f"T13S13 unknown backend: {backend}")
    complete = sum(_result_complete(ctx.paths.raw / f"{spec['experiment_id']}.json.gz", spec) for spec in specs)
    success = 0
    failures = []
    for spec in specs:
        path = ctx.paths.raw / f"{spec['experiment_id']}.json.gz"
        if not _result_complete(path, spec):
            continue
        result = s9.t11.t1.r3c3.read_json_gz(path)
        success += bool(result["success"])
        if not bool(result["success"]):
            failures.append({"experiment_id": spec["experiment_id"], "failure_reason": result.get("failure_reason", "")})
    return {
        "expected": len(specs), "pending_before_run": len(pending),
        "complete": complete, "success": success, "failures": failures,
        "passed": complete == success == len(specs),
    }


def _payload_for_result(ctx: Context, result: Mapping[str, Any]) -> Mapping[str, Any]:
    experiment_id = str(result["experiment_id"])
    path = ctx.paths.variants / f"payload_{experiment_id}.json"
    if path.is_file():
        return _read_json(path)
    for run, directory in (
        (ctx.q1_run, "stage4_2r3c3t13s9_environment_variants"),
        (ctx.q2_run, "stage4_2r3c3t13s5_environment_variants"),
    ):
        candidate = run / directory / f"payload_{experiment_id}.json"
        if candidate.is_file():
            return _read_json(candidate)
    raise FileNotFoundError(f"T13S13 payload missing for {experiment_id}")


def _current_scales(payload: Mapping[str, Any]) -> np.ndarray:
    env = payload["env_cfg"]
    minimum = np.asarray(env["min_current_a_display_order"], dtype=float)
    maximum = np.asarray(env["max_current_a_display_order"], dtype=float)
    display_to_tsc = np.asarray(DISPLAY_TO_TSC_INDEX)
    scales = 0.5 * (maximum[display_to_tsc] - minimum[display_to_tsc])
    if scales.shape != (N_COILS,) or not np.all(np.isfinite(scales)) or np.any(scales <= 0):
        raise ValueError("T13S13 invalid current half ranges")
    return scales


def _current_limits_tsc(payload: Mapping[str, Any]) -> tuple[np.ndarray, np.ndarray]:
    env = payload["env_cfg"]
    order = np.asarray(DISPLAY_TO_TSC_INDEX)
    minimum = np.asarray(env["min_current_a_display_order"], dtype=float)[order]
    maximum = np.asarray(env["max_current_a_display_order"], dtype=float)[order]
    if (
        minimum.shape != (N_COILS,) or maximum.shape != (N_COILS,)
        or not np.all(np.isfinite(minimum)) or not np.all(np.isfinite(maximum))
        or np.any(maximum <= minimum)
    ):
        raise ValueError("T13S13 invalid TSC-order current limits")
    return minimum, maximum


def _turns_tsc(payload: Mapping[str, Any]) -> np.ndarray:
    turns = np.asarray(payload["env_cfg"]["turns_display_order"], dtype=float)[
        np.asarray(DISPLAY_TO_TSC_INDEX)
    ]
    if turns.shape != (N_COILS,) or not np.all(np.isfinite(turns)) or np.any(turns <= 0):
        raise ValueError("T13S13 invalid TSC-order turn counts")
    return turns


def _source_state_map(ctx: Context) -> dict[str, Mapping[str, Any]]:
    public_rows = _read_json(_source_paths(ctx)["state_results"])
    source_root = ctx.base_ctx.base_ctx.base_ctx.source_ctx.source_r3b_run
    raw_paths = sorted(
        (source_root / "stage4_2r3b_state_generation" / "raw").glob("*.json.gz")
    )
    recomputed = [
        s9.t11.t1.r3b._state_row(s9.t11.t1.r3c3.read_json_gz(path))
        for path in raw_paths
    ]
    output = {str(row["experiment_id"]): row for row in recomputed}
    public_by_id = {str(row["experiment_id"]): row for row in public_rows}
    private = {"coil_currents_a", "action_norm_tsc", "wire_currents_a"}
    recomputed_public = {
        key: {name: value for name, value in row.items() if name not in private}
        for key, row in output.items()
    }
    if (
        len(raw_paths) != 72 or len(recomputed) != 72 or len(output) != 72
        or len(public_rows) != 72 or len(public_by_id) != 72
        or recomputed_public != public_by_id
        or not all(bool(row.get("success")) for row in recomputed)
    ):
        raise ValueError("T13S13 source state-result map mismatch")
    return output


def _execution_audit(
    ctx: Context, specs: Sequence[Mapping[str, Any]], *, baseline: bool,
) -> dict[str, Any]:
    rows = []
    state_map = _source_state_map(ctx)
    base_source_ctx = ctx.base_ctx.base_ctx.base_ctx.source_ctx.source_ctx
    forbidden_keys = (
        "future_measurement_used", "hidden_wire_used", "source_action_used",
        "source_coil_current_used", "source_wire_current_used",
        "current_run_future_used", "pair_or_history_label_used",
        "source_result_used", "future_probe_schedule_available_to_underlying_controller",
    )
    for spec in specs:
        path = ctx.paths.raw / f"{spec['experiment_id']}.json.gz"
        complete = _result_complete(path, spec)
        if complete:
            result = s9.t11.t1.r3c3.read_json_gz(path)
            trajectory = result["trajectory"]
            trace = result["controller_trace"]
            payload = _payload_for_result(ctx, result)
            currents = np.asarray([row["currents_a_tsc"] for row in trajectory], dtype=float)
            actions = np.asarray([row["action_norm_tsc"] for row in trace], dtype=float)
            forbidden = sum(any(bool(row.get(key)) for key in forbidden_keys) for row in trace)
            minimum, maximum = _current_limits_tsc(payload)
            center = 0.5 * (minimum + maximum)
            half = 0.5 * (maximum - minimum)
            current_utilization = (
                float(np.max(np.abs((currents - center) / half)))
                if currents.ndim == 2 and currents.shape[1] == N_COILS and len(currents)
                else math.inf
            )
            state_id = str(spec["state_generation_experiment_id"])
            if state_id not in state_map:
                raise ValueError(f"T13S13 missing source state result: {state_id}")
            restart = s9.t11.t1.r3b._control_row(
                base_source_ctx, result, state_map[state_id]
            )
            phase = s9.t11.t1.r3c1._phase_trace_valid(result)
            actuator = s9._actuator_execution(result, ctx.cfg["lattice_probe"])
            actual_events = [
                row.get("r3c3t13s9_lattice_event") for row in trace
                if row.get("r3c3t13s9_lattice_event") != "none"
            ]
            expected_events = [] if baseline else ["issue", "cancel"]
            cancellation = s9._cancellation_policy_trace(result, baseline=baseline)
            requested_zero = all(
                np.array_equal(
                    np.asarray(row.get("r3c3t13s9_requested_net_kAt_tsc"), dtype=float),
                    np.zeros(N_COILS),
                )
                for row in trace
            )
            summary = result.get("hidden_history_control_summary") or {}
            zero_net = bool(
                baseline or (
                    requested_zero
                    and bool(summary.get("requested_and_applied_zero_net"))
                    and bool(cancellation["cancellation_policy_pass"])
                )
            )
            runtime = bool(
                result["success"]
                and len(trajectory) == int(spec["horizon_steps"]) + 1
                and len(trace) == int(spec["horizon_steps"])
                and not any(bool(row.get("abnormal")) for row in trajectory)
                and currents.shape == (int(spec["horizon_steps"]) + 1, N_COILS)
                and actions.shape == (int(spec["horizon_steps"]), N_COILS)
                and np.all(np.isfinite(currents)) and np.all(np.isfinite(actions))
            )
            trace_pass = bool(
                all(bool(row.get("computed_online")) and bool(row.get("solver_success")) for row in trace)
                and actual_events == expected_events and forbidden == 0
                and bool(actions.size) and float(np.max(np.abs(actions))) <= 1.0 + 1e-12
                and bool(phase["passed"])
            )
            restart_pass = bool(
                restart.get("fresh_controller") and restart.get("fresh_tsc_process")
                and restart.get("initial_restart_exact") and restart.get("controller_trace_causal")
                and restart.get("online_action_computation")
                and not restart.get("hidden_wire_available_to_controller", True)
            )
            passed = bool(
                runtime and restart_pass and trace_pass and actuator["passed"] and zero_net
                and current_utilization <= float(ctx.cfg["lattice_probe"]["maximum_current_utilization"]) + 1e-12
            )
            if not runtime:
                failure_class = "runtime_or_environment_error"
            elif not restart["initial_restart_exact"]:
                failure_class = "plant_restart_fidelity_failure"
            elif not restart["fresh_controller"] or not restart["fresh_tsc_process"]:
                failure_class = "execution_isolation_failure"
            elif not restart["controller_trace_causal"] or not trace_pass:
                failure_class = "controller_causality_or_trace_failure"
            elif not actuator["passed"]:
                failure_class = "actuator_interval_or_card15_failure"
            elif not zero_net:
                failure_class = "probe_cancellation_or_zero_net_failure"
            elif current_utilization > float(ctx.cfg["lattice_probe"]["maximum_current_utilization"]) + 1e-12:
                failure_class = "current_utilization_failure"
            else:
                failure_class = ""
            reason = "" if passed else failure_class
        else:
            result = {}
            current_utilization = math.inf
            forbidden = 0
            restart = {}
            phase = {"passed": False}
            actuator = {"passed": False, "component_count": 0, "inside_interval_count": 0}
            actual_events = []
            cancellation = {"cancellation_policy_pass": False, "cancellation_method": ""}
            zero_net = False
            passed = False
            failure_class = "raw_missing_or_incompatible"
            reason = failure_class
        rows.append({
            "experiment_id": spec["experiment_id"],
            "pair_id": spec["pair_id"],
            "history_member": spec["history_member"],
            "complete": complete,
            "success": bool(result.get("success")),
            "fresh_controller": bool(restart.get("fresh_controller")),
            "fresh_tsc_process": bool(restart.get("fresh_tsc_process")),
            "initial_restart_exact": bool(restart.get("initial_restart_exact")),
            "controller_trace_causal": bool(restart.get("controller_trace_causal")),
            "phase_trace_valid": bool(phase["passed"]),
            "formal_contract_pass_diagnostic": bool(restart.get("formal_contract_pass")),
            "formal_minimum_signed_margin_diagnostic": restart.get("formal_minimum_signed_margin"),
            "formal_best_arrival_ms_diagnostic": restart.get("formal_best_arrival_ms"),
            "lattice_events": actual_events,
            "cancellation_method": cancellation["cancellation_method"],
            "cancellation_policy_pass": bool(cancellation["cancellation_policy_pass"]),
            "requested_and_applied_zero_net": zero_net,
            "actuator_execution_pass": bool(actuator["passed"]),
            "actuator_component_count": int(actuator.get("component_count", 0)),
            "actuator_inside_interval_count": int(actuator.get("inside_interval_count", 0)),
            "maximum_current_utilization": current_utilization,
            "forbidden_trace_count": forbidden,
            "passed": passed,
            "failure_class": failure_class,
            "failure_reason": reason or str(result.get("failure_reason", "")),
        })
    return {
        "expected": len(specs), "actual": len(rows),
        "pass_count": sum(row["passed"] for row in rows),
        "formal_tracking_pass_count_diagnostic_only": sum(
            row["formal_contract_pass_diagnostic"] for row in rows
        ),
        "formal_tracking_is_safety_gate": False,
        "passed": len(rows) == len(specs) and all(row["passed"] for row in rows),
        "rows": rows,
    }


def audit_baselines(ctx: Context, specs: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return _execution_audit(ctx, specs, baseline=True)


def audit_probes(ctx: Context, specs: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return _execution_audit(ctx, specs, baseline=False)


def audit_lattice_on_baselines(
    ctx: Context,
    baseline_specs: Sequence[Mapping[str, Any]],
    probe_specs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    probes_by_context: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for spec in probe_specs:
        probes_by_context[(str(spec["pair_id"]), str(spec["history_member"]))].append(spec)
    library, bundle, selector = _library_bundle_selector(ctx)
    rows = []
    for context_index, baseline_spec in enumerate(baseline_specs):
        key = (str(baseline_spec["pair_id"]), str(baseline_spec["history_member"]))
        result_path = ctx.paths.raw / f"{baseline_spec['experiment_id']}.json.gz"
        baseline = s9.t11.t1.r3c3.read_json_gz(result_path)
        trajectory = baseline["trajectory"]
        payload = _payload(ctx, baseline_spec)
        worker = s9.t11.t1.r1.LocalPlantReplayWorker(
            payload, library, bundle, f"stage42r3c3t13s13_lattice_{context_index:03d}", selector,
        )
        try:
            for spec in sorted(probes_by_context[key], key=lambda row: str(row["experiment_id"])):
                passed = True
                reason = ""
                events = []
                try:
                    initial = copy.deepcopy(dict(trajectory[0]))
                    initial["step_index"] = 0
                    controller = s9.LatticeTransitionProbeController(
                        worker.base_worker, bundle, s9._controller_spec(spec), initial,
                        ctx.cfg["lattice_probe"],
                    )
                    for step in range(int(spec["horizon_steps"])):
                        state = copy.deepcopy(dict(trajectory[step]))
                        state["step_index"] = step
                        action, trace = controller.action(state)
                        prediction = trace["r3c3t13s9_actuator_prediction"]
                        passed = bool(
                            passed
                            and np.all(np.isfinite(action))
                            and float(np.max(np.abs(action))) <= 1.0 + 1e-12
                            and not any(prediction["action_saturated"])
                            and not any(prediction["current_limit_clipped"])
                            and not any(bool(trace.get(name)) for name in (
                                "future_measurement_used", "hidden_wire_used",
                                "source_action_used", "source_result_used",
                                "pair_or_history_label_used", "current_run_future_used",
                            ))
                        )
                        if trace["r3c3t13s9_lattice_event"] != "none":
                            events.append(trace["r3c3t13s9_lattice_event"])
                        if step + 1 < len(trajectory):
                            next_state = copy.deepcopy(dict(trajectory[step + 1]))
                            next_state["step_index"] = step + 1
                            controller.advance(next_state)
                    passed = bool(passed and events == ["issue", "cancel"])
                except Exception as exc:
                    passed = False
                    reason = repr(exc)
                rows.append({
                    "experiment_id": spec["experiment_id"],
                    "pair_id": key[0], "history_member": key[1],
                    "probe_window": spec["r3c3_probe_window"],
                    "probe_direction": spec["r3c3_probe_direction"],
                    "probe_sign": spec["r3c3_probe_sign"],
                    "events": events, "passed": passed, "failure_reason": reason,
                })
        finally:
            worker.close()
    return {
        "expected": len(probe_specs), "actual": len(rows),
        "pass_count": sum(row["passed"] for row in rows),
        "plant_advance_count": 0, "real_tsc_executed": False,
        "passed": len(rows) == len(probe_specs) and all(row["passed"] for row in rows),
        "rows": rows,
    }


def _load_gz(path: Path) -> dict[str, Any]:
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        return json.load(stream)


def _raw_identity(spec: Mapping[str, Any]) -> tuple[str, str, str, str, int]:
    return (
        str(spec["pair_id"]), str(spec["history_member"]),
        str(spec["r3c3_probe_window"]), str(spec["r3c3_probe_direction"]),
        int(spec["r3c3_probe_sign"]),
    )


def _load_partition_raw(
    ctx: Context, table: Sequence[Mapping[str, Any]], specs: Sequence[Mapping[str, Any]],
    partition: str,
) -> list[dict[str, Any]]:
    contexts = {
        (str(row["pair_id"]), str(row["history_member"])): row
        for row in table if row["partition"] == partition
    }
    results = []
    if partition == "training":
        for run, subdir in (
            (ctx.q1_run, "stage4_2r3c3t13s9_unified_postqueue_q1_identification/raw"),
            (ctx.q2_run, "stage4_2r3c3t13s5_lattice_native_split_holdout/raw"),
        ):
            for path in sorted((run / subdir).glob("*.json.gz")):
                result = _load_gz(path)
                key = (str(result["spec"]["pair_id"]), str(result["spec"]["history_member"]))
                if key in contexts and bool(contexts[key]["consumed_training"]):
                    results.append(result)
    new_specs = [
        spec for spec in specs
        if (str(spec["pair_id"]), str(spec["history_member"])) in contexts
    ]
    for spec in new_specs:
        path = ctx.paths.raw / f"{spec['experiment_id']}.json.gz"
        if not _result_complete(path, spec):
            raise ValueError(f"T13S13 incomplete {partition} raw: {spec['experiment_id']}")
        results.append(s9.t11.t1.r3c3.read_json_gz(path))
    expected = len(contexts) * 17
    if len(results) != expected:
        raise ValueError(f"T13S13 {partition} raw coverage mismatch")
    grouped = defaultdict(set)
    for result in results:
        identity = _raw_identity(result["spec"])
        grouped[identity[:2]].add(identity[2:])
    expected_members = {("baseline", "", 0)} | {
        (window, direction, sign) for window in WINDOWS for direction in DIRECTIONS for sign in SIGNS
    }
    if set(grouped) != set(contexts) or any(members != expected_members for members in grouped.values()):
        raise ValueError(f"T13S13 {partition} member identity mismatch")
    return results


def _target(result: Mapping[str, Any], payload: Mapping[str, Any]) -> np.ndarray:
    spec = result["spec"]
    cfg_target = payload["cfg"]["target"]
    train_target = payload["train_cfg"]["target"]
    if any(abs(float(cfg_target[key]) - float(train_target[key])) > 1e-12 for key in ("R", "Z", "Ip")):
        raise ValueError("T13S13 payload target contract mismatch")
    target = np.asarray([
        float(cfg_target["R"]) + float(spec["target_R_offset_m"]),
        float(cfg_target["Z"]) + float(spec["target_Z_offset_m"]),
        float(cfg_target["Ip"]) + float(spec["target_Ip_offset_A"]),
    ])
    if not np.all(np.isfinite(target)):
        raise ValueError("T13S13 target is nonfinite")
    return target


def _history_sequence(
    baseline: Mapping[str, Any], payload: Mapping[str, Any], *, issue: int,
) -> tuple[np.ndarray, np.ndarray]:
    trajectory = baseline["trajectory"]
    trace = baseline["controller_trace"]
    if len(trajectory) <= issue or len(trace) < issue:
        raise ValueError("T13S13 history endpoint unavailable")
    scales = _current_scales(payload)
    target = _target(baseline, payload)
    base_target = np.asarray([float(payload["cfg"]["target"][key]) for key in ("R", "Z", "Ip")])
    delay = int(baseline["spec"]["action_delay_steps"])
    slew = float(baseline["spec"]["slew_scale"])
    rows = []
    for index in range(issue + 1):
        state = trajectory[index]
        currents = np.asarray(state["currents_a_tsc"], dtype=float)
        known = float(index > 0)
        if index:
            previous_state = trajectory[index - 1]
            velocity = np.asarray([
                (float(state["R"]) - float(previous_state["R"])) / 0.01,
                (float(state["Z"]) - float(previous_state["Z"])) / 0.01,
            ])
            current_delta = currents - np.asarray(previous_state["currents_a_tsc"], dtype=float)
            previous_trace = trace[index - 1]
            previous_action = np.asarray(previous_trace["action_norm_tsc"], dtype=float)
            previous_mode = np.asarray(previous_trace["issued_desired_physical_mode_coefficients"], dtype=float)
        else:
            velocity = np.zeros(2)
            current_delta = np.zeros(N_COILS)
            previous_action = np.zeros(N_COILS)
            previous_mode = np.zeros(3)
        row = np.asarray([
            (float(state["R"]) - target[0]) / 0.03,
            (float(state["Z"]) - target[1]) / 0.03,
            (float(state["Ip"]) - target[2]) / 10000.0,
            velocity[0] / 0.1, velocity[1] / 0.1, known,
            *(currents / scales), *(current_delta / scales), known,
            *previous_action, *previous_mode, known,
            index / 37.0, delay / 2.0, (slew - 0.95) / 0.05,
            (target[0] - base_target[0]) / 0.03,
            (target[1] - base_target[1]) / 0.03,
            (target[2] - base_target[2]) / 10000.0,
        ], dtype=float)
        if row.shape != (59,) or not np.all(np.isfinite(row)):
            raise ValueError("T13S13 causal history schema mismatch")
        rows.append(row)
    sequence = np.asarray(rows)
    padded = np.zeros((17, 60), dtype=float)
    padded[: len(sequence), :59] = sequence
    padded[: len(sequence), 59] = 1.0
    return sequence, padded.reshape(-1)


def _prediction(trace_row: Mapping[str, Any]) -> Mapping[str, Any]:
    for key in ("r3c3t13s9_actuator_prediction", "r3c3t13s5_actuator_prediction"):
        value = trace_row.get(key)
        if isinstance(value, Mapping):
            return value
    raise ValueError("T13S13 actuator prediction missing")


def _center_card15_fields(trace_row: Mapping[str, Any]) -> list[str]:
    for key in ("r3c3t13s9_center_card15_fields", "r3c3t13s5_center_card15_fields"):
        value = trace_row.get(key)
        if isinstance(value, list) and len(value) == N_COILS:
            return list(map(str, value))
    raise ValueError("T13S13 center Card15 fields missing")


def _response(
    result: Mapping[str, Any], baseline: Mapping[str, Any], payload: Mapping[str, Any],
) -> dict[str, Any]:
    spec = result["spec"]
    issue = int(spec["r3c3_probe_issue_step"])
    effect = int(spec["r3c3_probe_first_effect_state"])
    base_traj = baseline["trajectory"]
    probe_traj = result["trajectory"]
    if effect != issue + 1 or len(base_traj) <= effect or len(probe_traj) <= effect:
        raise ValueError("T13S13 post-queue effect contract mismatch")
    radius_a = float(s9.OUTPUT_GRID_KAT) * 1000.0 / _turns_tsc(payload)
    pre_position = 0.0
    pre_velocity = 0.0
    pre_ip = 0.0
    pre_current = 0.0
    pre_coil_radius = 0.0
    for index in range(issue + 1):
        for key in ("R", "Z"):
            pre_position = max(pre_position, abs(float(base_traj[index][key]) - float(probe_traj[index][key])))
        pre_ip = max(pre_ip, abs(float(base_traj[index]["Ip"]) - float(probe_traj[index]["Ip"])))
        current_difference = (
            np.asarray(probe_traj[index]["currents_a_tsc"], dtype=float)
            - np.asarray(base_traj[index]["currents_a_tsc"], dtype=float)
        )
        pre_current = max(pre_current, float(np.max(np.abs(current_difference))))
        pre_coil_radius = max(
            pre_coil_radius, float(np.max(np.abs(current_difference) / radius_a))
        )
        if index:
            for key in ("R", "Z"):
                baseline_velocity = (
                    float(base_traj[index][key]) - float(base_traj[index - 1][key])
                ) / 0.01
                probe_velocity = (
                    float(probe_traj[index][key]) - float(probe_traj[index - 1][key])
                ) / 0.01
                pre_velocity = max(pre_velocity, abs(probe_velocity - baseline_velocity))
    base_state = base_traj[effect]
    probe_state = probe_traj[effect]
    base_prev = base_traj[effect - 1]
    probe_prev = probe_traj[effect - 1]
    output = np.asarray([
        float(probe_state["R"]) - float(base_state["R"]),
        float(probe_state["Z"]) - float(base_state["Z"]),
        ((float(probe_state["R"]) - float(probe_prev["R"])) - (float(base_state["R"]) - float(base_prev["R"]))) / 0.01,
        ((float(probe_state["Z"]) - float(probe_prev["Z"])) - (float(base_state["Z"]) - float(base_prev["Z"]))) / 0.01,
        float(probe_state["Ip"]) - float(base_state["Ip"]),
    ])
    base_prediction = _prediction(baseline["controller_trace"][issue])
    probe_prediction = _prediction(result["controller_trace"][issue])
    scales = _current_scales(payload)
    base_nominal = np.asarray(base_prediction["nominal_readback_current_a_tsc"], dtype=float)
    probe_nominal = np.asarray(probe_prediction["nominal_readback_current_a_tsc"], dtype=float)
    u_center = (probe_nominal - base_nominal) / scales
    base_radius = 0.5 * (np.asarray(base_prediction["readback_upper_a_tsc"]) - np.asarray(base_prediction["readback_lower_a_tsc"]))
    probe_radius = 0.5 * (np.asarray(probe_prediction["readback_upper_a_tsc"]) - np.asarray(probe_prediction["readback_lower_a_tsc"]))
    u_radius = (base_radius + probe_radius) / scales
    actual_current = (
        np.asarray(probe_state["currents_a_tsc"], dtype=float)
        - np.asarray(base_state["currents_a_tsc"], dtype=float)
    ) / scales
    actual_current_a = actual_current * scales
    input_box = bool(np.all(np.abs(actual_current - u_center) <= u_radius + 1e-12))
    probe_issue_trace = result["controller_trace"][issue]
    return {
        "u_center": u_center, "u_radius": u_radius,
        "actual_current": actual_current, "actual_current_A": actual_current_a,
        "target_card15_fields": list(probe_prediction["card15_fields"]),
        "center_card15_fields": _center_card15_fields(probe_issue_trace),
        "lattice_radius_A": radius_a,
        "output": output,
        "pre_effect_position_max_m": pre_position,
        "pre_effect_velocity_max_m_per_s": pre_velocity,
        "pre_effect_ip_max_A": pre_ip,
        "pre_effect_current_max_A": pre_current,
        "pre_effect_coil_radius_units": pre_coil_radius,
        "pre_effect_causality_pass": bool(
            pre_position <= 1e-9 and pre_velocity <= 1e-7 and pre_ip <= 1e-4
            and pre_coil_radius <= 1.0 + 1e-12
        ),
        "actuator_input_box_containment_pass": input_box,
        "post_effect_current_model_input_used": False,
    }


def extract_rows(
    ctx: Context, table: Sequence[Mapping[str, Any]], raw: Sequence[Mapping[str, Any]],
    partition: str,
) -> tuple[list[dict[str, Any]], dict[tuple[str, str, str], np.ndarray]]:
    table_by_key = {(str(row["pair_id"]), str(row["history_member"])): row for row in table if row["partition"] == partition}
    grouped: dict[tuple[str, str], dict[tuple[str, str, int], Mapping[str, Any]]] = defaultdict(dict)
    for result in raw:
        spec = result["spec"]
        key = (str(spec["pair_id"]), str(spec["history_member"]))
        grouped[key][(str(spec["r3c3_probe_window"]), str(spec["r3c3_probe_direction"]), int(spec["r3c3_probe_sign"]))] = result
    rows = []
    histories = {}
    for key, members in grouped.items():
        context = table_by_key[key]
        baseline = members[("baseline", "", 0)]
        payload = _payload_for_result(ctx, baseline)
        for window in WINDOWS:
            exemplar = members[(window, DIRECTIONS[0], -1)]
            issue = int(exemplar["spec"]["r3c3_probe_issue_step"])
            sequence, padded = _history_sequence(baseline, payload, issue=issue)
            histories[(key[0], key[1], window)] = padded
            for direction in DIRECTIONS:
                for sign in SIGNS:
                    result = members[(window, direction, sign)]
                    response = _response(result, baseline, payload)
                    rows.append({
                        "pair_id": key[0], "history_member": key[1],
                        "partition": partition, "window": window,
                        "direction": direction, "sign": sign,
                        "delay": int(context["action_delay_steps"]),
                        "sequence": sequence, "padded_history": padded,
                        **response,
                    })
    expected = len(table_by_key) * 16
    if len(rows) != expected or len(histories) != len(table_by_key) * 2:
        raise ValueError("T13S13 extracted response coverage mismatch")
    return rows, histories


def _reservoir_weights(seed: int, width: int) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.Generator(np.random.PCG64(seed))
    recurrent = rng.standard_normal((width, width))
    eigenvalues = np.linalg.eigvals(recurrent)
    radius = float(np.max(np.abs(eigenvalues)))
    if not math.isfinite(radius) or radius <= 0:
        raise ValueError("T13S13 reservoir spectral radius is invalid")
    recurrent /= radius
    inputs = rng.standard_normal((width, 60))
    return recurrent, inputs


def _encode_sequence(
    sequence: np.ndarray, recurrent: np.ndarray, inputs: np.ndarray,
    *, rho: float, leak: float, input_scale: float,
) -> np.ndarray:
    state = np.zeros(recurrent.shape[0], dtype=float)
    for row in np.asarray(sequence, dtype=float):
        candidate = np.tanh(rho * (recurrent @ state) + input_scale * (inputs @ np.concatenate(([1.0], row))))
        state = (1.0 - leak) * state + leak * candidate
    if not np.all(np.isfinite(state)):
        raise ValueError("T13S13 reservoir state is nonfinite")
    return state


def _unique_history_rows(rows: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    output = {}
    for row in rows:
        key = (str(row["pair_id"]), str(row["history_member"]), str(row["window"]))
        output.setdefault(key, row)
    return [output[key] for key in sorted(output)]


def _rms(values: np.ndarray, minimum: float) -> tuple[np.ndarray, bool]:
    rms = np.sqrt(np.mean(np.square(values), axis=0))
    passed = bool(np.all(np.isfinite(rms)) and np.all(rms > minimum))
    return np.where(rms > minimum, rms, 1.0), passed


def _fit_model(
    rows: Sequence[Mapping[str, Any]], hyper: Mapping[str, Any], observer_cfg: Mapping[str, Any],
) -> dict[str, Any]:
    width = int(observer_cfg["reservoir_width"])
    recurrent, inputs = _reservoir_weights(int(observer_cfg["seed"]), width)
    rho = float(hyper["rho"])
    leak = float(hyper["leak"])
    rank = int(hyper["observer_rank"])
    minimum = float(observer_cfg["minimum_whitening_rms"])
    unique = _unique_history_rows(rows)
    encoded_by_key = {}
    for row in unique:
        key = (str(row["pair_id"]), str(row["history_member"]), str(row["window"]))
        encoded_by_key[key] = _encode_sequence(
            np.asarray(row["sequence"]), recurrent, inputs,
            rho=rho, leak=leak, input_scale=float(observer_cfg["input_scale"]),
        )
    encoded = np.asarray([encoded_by_key[(str(row["pair_id"]), str(row["history_member"]), str(row["window"]))] for row in unique])
    history_mean = np.mean(encoded, axis=0)
    centered = encoded - history_mean
    history_rank = int(np.linalg.matrix_rank(centered))
    _, _, history_vt = np.linalg.svd(centered, full_matrices=False)
    if history_rank < rank:
        return {"eligible": False, "failure_reason": "observer rank unavailable", "history_rank": history_rank}
    history_basis = history_vt[:rank]
    history_scores_all = centered @ history_basis.T
    history_rms, history_whitening = _rms(history_scores_all, minimum)
    actions = np.asarray([row["u_center"] for row in rows], dtype=float)
    action_rank = int(np.linalg.matrix_rank(actions))
    _, _, action_vt = np.linalg.svd(actions, full_matrices=False)
    action_basis = action_vt[:4]
    action_scores_all = actions @ action_basis.T
    action_rms, action_whitening = _rms(action_scores_all, minimum)
    design = []
    response = []
    for row, action_scores in zip(rows, action_scores_all):
        key = (str(row["pair_id"]), str(row["history_member"]), str(row["window"]))
        history_scores = ((encoded_by_key[key] - history_mean) @ history_basis.T) / history_rms
        action_scores = action_scores / action_rms
        design.append(np.kron(np.concatenate(([1.0], history_scores)), action_scores))
        response.append(np.asarray(row["output"], dtype=float) / np.asarray(observer_cfg["response_scales"], dtype=float))
    design = np.asarray(design)
    response = np.asarray(response)
    column_rms, design_whitening = _rms(design, minimum)
    whitened = design / column_rms
    interaction_rank = int(np.linalg.matrix_rank(whitened))
    condition = float(np.linalg.cond(whitened))
    expected_columns = (rank + 1) * 4
    ridge = float(hyper["ridge"])
    matrix = whitened.T @ whitened + ridge * np.eye(expected_columns)
    coefficients_whitened = np.linalg.solve(matrix, whitened.T @ response)
    coefficients = coefficients_whitened / column_rms[:, None]
    eligible = bool(
        history_whitening and action_whitening and design_whitening
        and action_rank == 4 and interaction_rank == expected_columns
        and math.isfinite(condition)
        and condition <= float(observer_cfg["maximum_interaction_condition_number"])
        and np.all(np.isfinite(coefficients))
    )
    return {
        "eligible": eligible,
        "failure_reason": "" if eligible else "rank/whitening/condition/model gate failed",
        "hyper": dict(hyper),
        "history_rank": history_rank,
        "history_mean": history_mean.tolist(),
        "history_basis": history_basis.tolist(),
        "history_rms": history_rms.tolist(),
        "action_rank": action_rank,
        "action_basis": action_basis.tolist(),
        "action_rms": action_rms.tolist(),
        "interaction_rank": interaction_rank,
        "interaction_expected_columns": expected_columns,
        "interaction_condition": condition,
        "coefficients": coefficients.tolist(),
    }


def _model_coordinates(
    row: Mapping[str, Any], model: Mapping[str, Any], observer_cfg: Mapping[str, Any],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    recurrent, inputs = _reservoir_weights(int(observer_cfg["seed"]), int(observer_cfg["reservoir_width"]))
    hyper = model["hyper"]
    encoded = _encode_sequence(
        np.asarray(row["sequence"]), recurrent, inputs,
        rho=float(hyper["rho"]), leak=float(hyper["leak"]),
        input_scale=float(observer_cfg["input_scale"]),
    )
    history = ((encoded - np.asarray(model["history_mean"])) @ np.asarray(model["history_basis"]).T) / np.asarray(model["history_rms"])
    action_transform = np.asarray(model["action_basis"]).T / np.asarray(model["action_rms"])
    action = np.asarray(row["u_center"]) @ action_transform
    phi = np.concatenate(([1.0], history))
    return phi, action, action_transform


def _predict(
    row: Mapping[str, Any], model: Mapping[str, Any], observer_cfg: Mapping[str, Any],
) -> tuple[np.ndarray, np.ndarray]:
    phi, action, action_transform = _model_coordinates(row, model, observer_cfg)
    coefficients = np.asarray(model["coefficients"])
    scaled = np.kron(phi, action) @ coefficients
    scales = np.asarray(observer_cfg["response_scales"], dtype=float)
    predicted = scaled * scales
    block = coefficients.reshape(len(phi), 4, 5)
    action_to_scaled_response = np.tensordot(phi, block, axes=(0, 0))
    raw_to_unscaled_response = action_transform @ action_to_scaled_response * scales
    return predicted, raw_to_unscaled_response


def _scaled_relative(actual: np.ndarray, predicted: np.ndarray, scales: np.ndarray) -> float:
    floor = float(np.linalg.norm(RESPONSE_FLOOR / scales))
    return float(np.linalg.norm((actual - predicted) / scales) / max(np.linalg.norm(actual / scales), floor))


def _history_support_contract(rows: Sequence[Mapping[str, Any]], observer_cfg: Mapping[str, Any]) -> dict[str, Any]:
    unique = _unique_history_rows(rows)
    distances = []
    for held in unique:
        candidates = [
            row for row in unique
            if row["pair_id"] != held["pair_id"]
            and row["window"] == held["window"] and int(row["delay"]) == int(held["delay"])
        ]
        if not candidates:
            distance = math.inf
        else:
            left = np.asarray(held["padded_history"])
            distance = min(float(np.linalg.norm(left - np.asarray(row["padded_history"])) / math.sqrt(left.size)) for row in candidates)
        distances.append({
            "pair_id": held["pair_id"], "history_member": held["history_member"],
            "window": held["window"], "delay": held["delay"], "distance": distance,
        })
    maximum = max(float(row["distance"]) for row in distances)
    uncapped = float(observer_cfg["history_support_multiplier"]) * maximum
    cap = float(observer_cfg["maximum_history_support_distance"])
    radius = min(uncapped, cap)
    passed = bool(math.isfinite(maximum) and maximum <= radius + 1e-15)
    references = [
        {
            "pair_id": row["pair_id"], "history_member": row["history_member"],
            "window": row["window"], "delay": int(row["delay"]),
            "padded_history": np.asarray(row["padded_history"]).tolist(),
        }
        for row in unique
    ]
    return {
        "radius": radius, "uncapped_radius": uncapped, "maximum_training_lopo_distance": maximum,
        "training_lopo_pass": passed, "distances": distances, "references": references,
    }


def _history_support(row: Mapping[str, Any], contract: Mapping[str, Any]) -> tuple[float, bool]:
    references = [
        ref for ref in contract["references"]
        if ref["pair_id"] != row["pair_id"] and ref["window"] == row["window"] and int(ref["delay"]) == int(row["delay"])
    ]
    if not references:
        return math.inf, False
    value = np.asarray(row["padded_history"])
    distance = min(float(np.linalg.norm(value - np.asarray(ref["padded_history"])) / math.sqrt(value.size)) for ref in references)
    return distance, bool(distance <= float(contract["radius"]) + 1e-15)


def _action_support_contract(rows: Sequence[Mapping[str, Any]], model: Mapping[str, Any], observer_cfg: Mapping[str, Any]) -> dict[str, Any]:
    basis = np.asarray(model["action_basis"])
    rms = np.asarray(model["action_rms"])
    actions = np.asarray([row["u_center"] for row in rows])
    projections = (actions @ basis.T) @ basis
    residuals = np.linalg.norm(actions - projections, axis=1) / np.maximum(np.linalg.norm(actions, axis=1), 1e-300)
    coordinates = (actions @ basis.T) / rms
    minimum = np.min(coordinates, axis=0)
    maximum = np.max(coordinates, axis=0)
    expansion = float(observer_cfg["action_coordinate_expansion_fraction"]) * np.maximum(maximum - minimum, 1e-12)
    return {
        "maximum_training_projection_residual": float(np.max(residuals)),
        "projection_residual_limit": float(observer_cfg["maximum_action_projection_residual"]),
        "coordinate_minimum": (minimum - expansion).tolist(),
        "coordinate_maximum": (maximum + expansion).tolist(),
        "passed": bool(float(np.max(residuals)) <= float(observer_cfg["maximum_action_projection_residual"])),
    }


def _action_support(row: Mapping[str, Any], model: Mapping[str, Any], contract: Mapping[str, Any]) -> tuple[float, bool]:
    value = np.asarray(row["u_center"])
    basis = np.asarray(model["action_basis"])
    projection = (value @ basis.T) @ basis
    residual = float(np.linalg.norm(value - projection) / max(np.linalg.norm(value), 1e-300))
    coordinate = (value @ basis.T) / np.asarray(model["action_rms"])
    passed = bool(
        residual <= float(contract["projection_residual_limit"]) + 1e-15
        and np.all(coordinate >= np.asarray(contract["coordinate_minimum"]) - 1e-15)
        and np.all(coordinate <= np.asarray(contract["coordinate_maximum"]) + 1e-15)
    )
    return residual, passed


def _candidate_grid(observer_cfg: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        {"rho": rho, "leak": leak, "observer_rank": rank, "ridge": ridge}
        for rho in map(float, observer_cfg["spectral_radii"])
        for leak in map(float, observer_cfg["leaks"])
        for rank in map(int, observer_cfg["observer_ranks"])
        for ridge in map(float, observer_cfg["ridge_values"])
    ]


def _cross_validate(rows: Sequence[Mapping[str, Any]], hyper: Mapping[str, Any], observer_cfg: Mapping[str, Any]) -> dict[str, Any]:
    pairs = sorted({str(row["pair_id"]) for row in rows})
    errors = []
    fold_conditions = []
    eligible = True
    for held_pair in pairs:
        training = [row for row in rows if row["pair_id"] != held_pair]
        held = [row for row in rows if row["pair_id"] == held_pair]
        model = _fit_model(training, hyper, observer_cfg)
        if not bool(model.get("eligible")):
            eligible = False
            break
        fold_conditions.append(float(model["interaction_condition"]))
        for row in held:
            predicted, _ = _predict(row, model, observer_cfg)
            errors.append(_scaled_relative(np.asarray(row["output"]), predicted, np.asarray(observer_cfg["response_scales"])))
    maximum = max(errors, default=math.inf)
    mean = float(np.mean(errors)) if errors else math.inf
    eligible = bool(
        eligible and len(errors) == len(rows)
        and math.isfinite(maximum) and math.isfinite(mean)
    )
    return {
        "hyper": dict(hyper), "eligible": eligible, "held_row_count": len(errors),
        "maximum_error": maximum, "mean_error": mean,
        "maximum_condition": max(fold_conditions, default=math.inf),
    }


def _identification_gates(rows: Sequence[Mapping[str, Any]], cfg: Mapping[str, Any]) -> dict[str, Any]:
    grouped: dict[tuple[str, str, str, str], dict[int, Mapping[str, Any]]] = defaultdict(dict)
    for row in rows:
        grouped[(str(row["pair_id"]), str(row["history_member"]), str(row["window"]), str(row["direction"]))][int(row["sign"])] = row
    details = []
    for key, signed in sorted(grouped.items()):
        if set(signed) != {-1, 1}:
            raise ValueError("T13S13 signed group incomplete")
        plus_fields = list(signed[1]["target_card15_fields"])
        minus_fields = list(signed[-1]["target_card15_fields"])
        plus_center = list(signed[1]["center_card15_fields"])
        minus_center = list(signed[-1]["center_card15_fields"])
        target_symmetry = bool(
            plus_center == minus_center
            and all(
                s9._decimal_field(plus) - s9._decimal_field(center)
                == s9._decimal_field(center) - s9._decimal_field(minus)
                for plus, center, minus in zip(plus_fields, plus_center, minus_fields)
            )
        )
        plus_current = np.asarray(signed[1]["actual_current_A"], dtype=float)
        minus_current = np.asarray(signed[-1]["actual_current_A"], dtype=float)
        odd_current = 0.5 * (plus_current - minus_current)
        even_current = 0.5 * (plus_current + minus_current)
        odd_current_norm = float(np.linalg.norm(odd_current))
        even_current_norm = float(np.linalg.norm(even_current))
        radius_a = np.asarray(signed[1]["lattice_radius_A"], dtype=float)
        required_current_norm = float(
            cfg["lattice_probe"]["required_observed_odd_signal_radius_l2"]
        ) * float(np.linalg.norm(radius_a))
        signal = bool(odd_current_norm >= required_current_norm)
        current_symmetry_ratio = even_current_norm / max(odd_current_norm, 1e-300)
        current_symmetry = bool(
            target_symmetry and signal
            and current_symmetry_ratio
            <= float(cfg["lattice_probe"]["maximum_observed_even_to_odd_l2"])
        )
        plus = np.asarray(signed[1]["output"])
        minus = np.asarray(signed[-1]["output"])
        odd = 0.5 * (plus - minus)
        even = 0.5 * (plus + minus)
        response_scales = np.asarray(cfg["observer"]["response_scales"], dtype=float)
        response_symmetry = float(
            np.linalg.norm(even / response_scales)
            / max(np.linalg.norm(odd / response_scales), 1e-300)
        )
        floor_scaled = float(np.linalg.norm(RESPONSE_FLOOR / response_scales))
        odd_response_norm = float(np.linalg.norm(odd / response_scales))
        development_signal = bool(
            np.isfinite(odd_response_norm)
            and odd_response_norm
            >= float(cfg["lattice_probe"]["signal_floor_multiplier"]) * floor_scaled
        )
        passed = bool(
            target_symmetry and signal and current_symmetry and development_signal
            and all(bool(row["pre_effect_causality_pass"]) and bool(row["actuator_input_box_containment_pass"]) for row in signed.values())
        )
        details.append({
            "pair_id": key[0], "history_member": key[1], "window": key[2], "direction": key[3],
            "target_field_central_symmetry_exact": target_symmetry,
            "observed_current_odd_l2_A": odd_current_norm,
            "observed_current_required_l2_A": required_current_norm,
            "observed_current_signal_pass": signal,
            "observed_current_even_l2_A": even_current_norm,
            "observed_current_even_to_odd_l2": current_symmetry_ratio,
            "observed_current_symmetry_pass": current_symmetry,
            "scaled_odd_response_l2": odd_response_norm,
            "scaled_even_to_odd_response_l2_diagnostic": response_symmetry,
            "development_signal_pass": development_signal,
            "passed": passed,
        })
    return {
        "expected_groups": len(rows) // 2, "actual_groups": len(details),
        "pass_count": sum(row["passed"] for row in details),
        "target_field_central_symmetry_exact_count": sum(
            row["target_field_central_symmetry_exact"] for row in details
        ),
        "observed_current_signal_pass_count": sum(
            row["observed_current_signal_pass"] for row in details
        ),
        "observed_current_symmetry_pass_count": sum(
            row["observed_current_symmetry_pass"] for row in details
        ),
        "development_signal_pass_count": sum(
            row["development_signal_pass"] for row in details
        ),
        "pre_effect_pass_count": sum(bool(row["pre_effect_causality_pass"]) for row in rows),
        "input_box_pass_count": sum(bool(row["actuator_input_box_containment_pass"]) for row in rows),
        "passed": len(details) == len(rows) // 2 and all(row["passed"] for row in details),
        "rows": details,
    }


def _alias_audit(
    rows: Sequence[Mapping[str, Any]], observer_cfg: Mapping[str, Any],
) -> dict[str, Any]:
    vectors = [
        np.concatenate((
            np.asarray(row["padded_history"], dtype=float),
            np.asarray(row["u_center"], dtype=float),
        ))
        for row in rows
    ]
    tolerance = float(observer_cfg["near_alias_linf_atol"])
    exact = 0
    near_nonexact = 0
    minimum_disjoint_linf = math.inf
    examples = []
    for left in range(len(rows)):
        for right in range(left + 1, len(rows)):
            if str(rows[left]["pair_id"]) == str(rows[right]["pair_id"]):
                continue
            distance = float(np.max(np.abs(vectors[left] - vectors[right])))
            minimum_disjoint_linf = min(minimum_disjoint_linf, distance)
            is_exact = bool(distance == 0.0)
            is_near = bool(not is_exact and distance <= tolerance)
            exact += is_exact
            near_nonexact += is_near
            if (is_exact or is_near) and len(examples) < 20:
                examples.append({
                    "left_pair_id": rows[left]["pair_id"],
                    "right_pair_id": rows[right]["pair_id"],
                    "linf_distance": distance,
                })
    return {
        "near_alias_linf_atol": tolerance,
        "minimum_disjoint_history_action_linf": minimum_disjoint_linf,
        "disjoint_exact_alias_pair_count": exact,
        "disjoint_near_nonexact_alias_pair_count": near_nonexact,
        "violation_count": exact + near_nonexact,
        "passed": exact + near_nonexact == 0,
        "examples": examples,
    }


def fit_training_model(
    ctx: Context, table: Sequence[Mapping[str, Any]], specs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    raw = _load_partition_raw(ctx, table, specs, "training")
    rows, _ = extract_rows(ctx, table, raw, "training")
    observer_cfg = ctx.cfg["observer"]
    identification = _identification_gates(rows, ctx.cfg)
    history_support = _history_support_contract(rows, observer_cfg)
    candidates = [_cross_validate(rows, hyper, observer_cfg) for hyper in _candidate_grid(observer_cfg)]
    eligible = [row for row in candidates if row["eligible"]]
    if eligible:
        selected = min(eligible, key=lambda row: (
            float(row["maximum_error"]), float(row["mean_error"]),
            int(row["hyper"]["observer_rank"]), float(row["hyper"]["rho"]),
            float(row["hyper"]["leak"]), float(row["hyper"]["ridge"]),
        ))
        model = _fit_model(rows, selected["hyper"], observer_cfg)
    else:
        selected = None
        model = {"eligible": False, "failure_reason": "no training-CV-eligible candidate"}
    validation = []
    base_radius = np.full(5, math.inf)
    training_max_abs_residual = np.full(5, math.inf)
    action_support = {"passed": False}
    if bool(model.get("eligible")):
        action_support = _action_support_contract(rows, model, observer_cfg)
        residuals = []
        temporary = []
        scales = np.asarray(observer_cfg["response_scales"], dtype=float)
        for row in rows:
            predicted, derivative = _predict(row, model, observer_cfg)
            residual = np.asarray(row["output"]) - predicted
            residuals.append(residual)
            history_distance, history_pass = _history_support(row, history_support)
            action_residual, action_pass = _action_support(row, model, action_support)
            temporary.append((row, predicted, derivative, residual, history_distance, history_pass, action_residual, action_pass))
        residuals_array = np.asarray(residuals)
        training_max_abs_residual = np.max(np.abs(residuals_array), axis=0)
        base_radius = RESPONSE_FLOOR + float(observer_cfg["training_tube_multiplier"]) * training_max_abs_residual
        caps = np.asarray(observer_cfg["tube_caps_unscaled"], dtype=float)
        for row, predicted, derivative, residual, history_distance, history_pass, action_residual, action_pass in temporary:
            total_radius = base_radius + np.abs(derivative).T @ np.asarray(row["u_radius"])
            contained = bool(np.all(np.abs(residual) <= total_radius + 1e-15))
            error = _scaled_relative(np.asarray(row["output"]), predicted, scales)
            passed = bool(
                history_pass and action_pass and contained
                and np.all(total_radius <= caps + 1e-15)
                and error <= float(observer_cfg["maximum_scaled_center_relative_error"])
                and row["pre_effect_causality_pass"] and row["actuator_input_box_containment_pass"]
            )
            validation.append({
                "pair_id": row["pair_id"], "history_member": row["history_member"],
                "window": row["window"], "direction": row["direction"], "sign": row["sign"],
                "history_support_distance": history_distance, "history_support_pass": history_pass,
                "action_support_residual": action_residual, "action_support_pass": action_pass,
                "componentwise_contained": contained,
                "scaled_center_relative_error": error,
                "scaled_center_relative_error_pass": error <= float(observer_cfg["maximum_scaled_center_relative_error"]),
                "total_radius": total_radius.tolist(), "passed": passed,
            })
    alias = _alias_audit(rows, observer_cfg)
    passed = bool(
        len(rows) == 512
        and identification["passed"]
        and history_support["training_lopo_pass"]
        and eligible and bool(model.get("eligible"))
        and bool(action_support.get("passed"))
        and len(validation) == 512 and all(row["passed"] for row in validation)
        and alias["passed"]
    )
    compact_candidates = sorted(candidates, key=lambda row: (
        not bool(row["eligible"]), float(row["maximum_error"]), float(row["mean_error"]),
        int(row["hyper"]["observer_rank"]), float(row["hyper"]["rho"]),
        float(row["hyper"]["leak"]), float(row["hyper"]["ridge"]),
    ))
    audit = {
        "schema_version": SCHEMA_VERSION, "stage": STAGE,
        "phase": "training_model_selection_and_freeze",
        "training_raw_count": len(raw), "training_context_count": 32,
        "training_response_row_count": len(rows),
        "identification_gates": identification,
        "history_support": {key: value for key, value in history_support.items() if key != "references"},
        "candidate_count": len(candidates), "eligible_candidate_count": len(eligible),
        "candidate_results": compact_candidates,
        "selected_candidate": selected,
        "model_eligible": bool(model.get("eligible")),
        "interaction_condition": model.get("interaction_condition", math.inf),
        "action_support": action_support,
        "provisional_base_radius": base_radius.tolist(),
        "validation_pass_count": sum(row["passed"] for row in validation),
        "maximum_validation_error": max((row["scaled_center_relative_error"] for row in validation), default=math.inf),
        "history_action_alias_audit": alias,
        "post_effect_current_model_input_count": 0,
        "passed": passed,
        "route": "TRAINING_MODEL_FROZEN_CALIBRATION_REQUIRED" if passed else FAIL_ROUTE,
        "validation": validation,
    }
    _write_json(ctx.paths.analysis / "training_model_audit.json", audit)
    if passed:
        artifact = {
            "schema_version": SCHEMA_VERSION, "stage": STAGE,
            "artifact": "training_center_model_v1",
            "config_sha256": _sha256(ctx.config_path),
            "context_table_digest": _digest(table),
            "training_raw_count": len(raw), "training_response_row_count": len(rows),
            "model": model,
            "history_support": history_support,
            "action_support": action_support,
            "training_base_radius": base_radius.tolist(),
            "training_max_abs_residual": training_max_abs_residual.tolist(),
            "selected_cv": selected,
            "post_effect_current_model_input_allowed": False,
        }
        path = ctx.paths.model / "training_center_model.json"
        _write_json(path, artifact)
        audit["model_path"] = str(path)
        audit["model_sha256"] = _sha256(path)
        _write_json(ctx.paths.analysis / "training_model_audit.json", audit)
    return audit


def calibrate_tube(
    ctx: Context, table: Sequence[Mapping[str, Any]], specs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    model_path = ctx.paths.model / "training_center_model.json"
    if not model_path.is_file():
        raise ValueError("T13S13 calibration requested before model freeze")
    artifact = _read_json(model_path)
    model = artifact["model"]
    raw = _load_partition_raw(ctx, table, specs, "calibration")
    rows, _ = extract_rows(ctx, table, raw, "calibration")
    training_raw = _load_partition_raw(ctx, table, specs, "training")
    training_rows, _ = extract_rows(ctx, table, training_raw, "training")
    observer_cfg = ctx.cfg["observer"]
    identification = _identification_gates(rows, ctx.cfg)
    residuals = []
    temporary = []
    scales = np.asarray(observer_cfg["response_scales"], dtype=float)
    for row in rows:
        predicted, derivative = _predict(row, model, observer_cfg)
        residual = np.asarray(row["output"]) - predicted
        residuals.append(residual)
        history_distance, history_pass = _history_support(row, artifact["history_support"])
        action_residual, action_pass = _action_support(row, model, artifact["action_support"])
        temporary.append((row, predicted, derivative, residual, history_distance, history_pass, action_residual, action_pass))
    maximum_residual = np.maximum(
        np.asarray(artifact["training_max_abs_residual"]),
        np.max(np.abs(np.asarray(residuals)), axis=0),
    )
    base_radius = RESPONSE_FLOOR + float(observer_cfg["calibration_tube_multiplier"]) * maximum_residual
    caps = np.asarray(observer_cfg["tube_caps_unscaled"], dtype=float)
    validation = []
    for row, predicted, derivative, residual, history_distance, history_pass, action_residual, action_pass in temporary:
        total_radius = base_radius + np.abs(derivative).T @ np.asarray(row["u_radius"])
        contained = bool(np.all(np.abs(residual) <= total_radius + 1e-15))
        error = _scaled_relative(np.asarray(row["output"]), predicted, scales)
        passed = bool(
            history_pass and action_pass and contained and np.all(total_radius <= caps + 1e-15)
            and error <= float(observer_cfg["maximum_scaled_center_relative_error"])
            and row["pre_effect_causality_pass"] and row["actuator_input_box_containment_pass"]
        )
        validation.append({
            "pair_id": row["pair_id"], "history_member": row["history_member"],
            "window": row["window"], "direction": row["direction"], "sign": row["sign"],
            "history_support_distance": history_distance, "history_support_pass": history_pass,
            "action_support_residual": action_residual, "action_support_pass": action_pass,
            "componentwise_contained": contained,
            "scaled_center_relative_error": error,
            "scaled_center_relative_error_pass": error <= float(observer_cfg["maximum_scaled_center_relative_error"]),
            "total_radius": total_radius.tolist(), "passed": passed,
        })
    alias = _alias_audit([*training_rows, *rows], observer_cfg)
    passed = bool(
        len(rows) == 320 and identification["passed"]
        and len(validation) == 320 and all(row["passed"] for row in validation)
        and alias["passed"]
    )
    audit = {
        "schema_version": SCHEMA_VERSION, "stage": STAGE,
        "phase": "calibration_tube_freeze",
        "model_sha256": _sha256(model_path),
        "calibration_raw_count": len(raw), "calibration_context_count": 20,
        "calibration_response_row_count": len(rows),
        "identification_gates": identification,
        "final_base_radius": base_radius.tolist(),
        "validation_pass_count": sum(row["passed"] for row in validation),
        "maximum_validation_error": max(row["scaled_center_relative_error"] for row in validation),
        "history_action_alias_audit_all_opened_partitions": alias,
        "post_effect_current_model_input_count": 0,
        "passed": passed,
        "route": "CALIBRATION_TUBE_FROZEN_FRESH_HOLDOUT_REQUIRED" if passed else FAIL_ROUTE,
        "validation": validation,
    }
    _write_json(ctx.paths.analysis / "calibration_tube_audit.json", audit)
    if passed:
        tube = {
            "schema_version": SCHEMA_VERSION, "stage": STAGE,
            "artifact": "calibrated_sequence_tube_v1",
            "model_sha256": _sha256(model_path),
            "context_table_digest": _digest(table),
            "final_base_radius": base_radius.tolist(),
            "tube_caps_unscaled": list(observer_cfg["tube_caps_unscaled"]),
            "calibration_raw_count": len(raw),
            "calibration_response_row_count": len(rows),
            "post_effect_current_model_input_allowed": False,
        }
        tube_path = ctx.paths.model / "calibrated_sequence_tube.json"
        _write_json(tube_path, tube)
        audit["tube_path"] = str(tube_path)
        audit["tube_sha256"] = _sha256(tube_path)
        _write_json(ctx.paths.analysis / "calibration_tube_audit.json", audit)
    return audit


def evaluate_holdout(
    ctx: Context, table: Sequence[Mapping[str, Any]], specs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    model_path = ctx.paths.model / "training_center_model.json"
    tube_path = ctx.paths.model / "calibrated_sequence_tube.json"
    if not model_path.is_file() or not tube_path.is_file():
        raise ValueError("T13S13 holdout requested before model/tube freeze")
    artifact = _read_json(model_path)
    tube = _read_json(tube_path)
    if tube["model_sha256"] != _sha256(model_path):
        raise ValueError("T13S13 model/tube identity mismatch")
    raw = _load_partition_raw(ctx, table, specs, "holdout")
    rows, _ = extract_rows(ctx, table, raw, "holdout")
    training_raw = _load_partition_raw(ctx, table, specs, "training")
    calibration_raw = _load_partition_raw(ctx, table, specs, "calibration")
    training_rows, _ = extract_rows(ctx, table, training_raw, "training")
    calibration_rows, _ = extract_rows(ctx, table, calibration_raw, "calibration")
    observer_cfg = ctx.cfg["observer"]
    identification = _identification_gates(rows, ctx.cfg)
    model = artifact["model"]
    base_radius = np.asarray(tube["final_base_radius"], dtype=float)
    caps = np.asarray(tube["tube_caps_unscaled"], dtype=float)
    scales = np.asarray(observer_cfg["response_scales"], dtype=float)
    validation = []
    for row in rows:
        predicted, derivative = _predict(row, model, observer_cfg)
        residual = np.asarray(row["output"]) - predicted
        history_distance, history_pass = _history_support(row, artifact["history_support"])
        action_residual, action_pass = _action_support(row, model, artifact["action_support"])
        total_radius = base_radius + np.abs(derivative).T @ np.asarray(row["u_radius"])
        contained = bool(np.all(np.abs(residual) <= total_radius + 1e-15))
        error = _scaled_relative(np.asarray(row["output"]), predicted, scales)
        passed = bool(
            history_pass and action_pass and contained and np.all(total_radius <= caps + 1e-15)
            and error <= float(observer_cfg["maximum_scaled_center_relative_error"])
            and row["pre_effect_causality_pass"] and row["actuator_input_box_containment_pass"]
        )
        validation.append({
            "pair_id": row["pair_id"], "history_member": row["history_member"],
            "window": row["window"], "direction": row["direction"], "sign": row["sign"],
            "history_support_distance": history_distance, "history_support_pass": history_pass,
            "action_support_residual": action_residual, "action_support_pass": action_pass,
            "componentwise_contained": contained,
            "scaled_center_relative_error": error,
            "scaled_center_relative_error_pass": error <= float(observer_cfg["maximum_scaled_center_relative_error"]),
            "total_radius": total_radius.tolist(), "passed": passed,
        })
    alias = _alias_audit([*training_rows, *calibration_rows, *rows], observer_cfg)
    passed = bool(
        len(raw) == 340 and len(rows) == 320 and identification["passed"]
        and len(validation) == 320 and all(row["passed"] for row in validation)
        and alias["passed"]
    )
    audit = {
        "schema_version": SCHEMA_VERSION, "stage": STAGE,
        "phase": "fresh_holdout_final_audit",
        "model_sha256": _sha256(model_path), "tube_sha256": _sha256(tube_path),
        "holdout_raw_count": len(raw), "holdout_context_count": 20,
        "holdout_response_row_count": len(rows),
        "identification_gates": identification,
        "history_support_pass_count": sum(row["history_support_pass"] for row in validation),
        "action_support_pass_count": sum(row["action_support_pass"] for row in validation),
        "componentwise_containment_pass_count": sum(row["componentwise_contained"] for row in validation),
        "center_error_pass_count": sum(row["scaled_center_relative_error_pass"] for row in validation),
        "both_response_gates_pass_count": sum(row["passed"] for row in validation),
        "maximum_scaled_center_relative_error": max(row["scaled_center_relative_error"] for row in validation),
        "history_action_alias_audit_all_opened_partitions": alias,
        "post_effect_current_model_input_count": 0,
        "passed": passed, "route": PASS_ROUTE if passed else FAIL_ROUTE,
        "formal_timing_unchanged": True,
        "probe_trajectories_allowed_in_expert_dataset": False,
        "bc_dagger_or_rl_allowed": False,
        "validation": validation,
    }
    _write_json(ctx.paths.analysis / "stage4_2r3c3t13s13_final_audit.json", audit)
    return audit


def _state(ctx: Context) -> dict[str, Any]:
    if not ctx.paths.state.is_file():
        raise ValueError("T13S13 state file missing; run offline preflight first")
    return _read_json(ctx.paths.state)


def _set_state(ctx: Context, **updates: Any) -> dict[str, Any]:
    state = _state(ctx)
    state.update(updates)
    state["updated_utc"] = s9.t11.t1.r3c3.utc_timestamp()
    _write_json(ctx.paths.state, state)
    return state


def _require_phase(ctx: Context, expected: str) -> dict[str, Any]:
    state = _state(ctx)
    if bool(state.get("finished")) and state.get("phase_status") != "campaign_complete":
        raise ValueError(
            f"T13S13 campaign is fail-closed: {state.get('stop_reason', 'unspecified failure')}"
        )
    if state.get("phase_status") != expected:
        raise ValueError(f"T13S13 phase order violation: expected {expected}, found {state.get('phase_status')}")
    return state


def _phase_specs(
    ctx: Context, table: Sequence[Mapping[str, Any]], all_specs: Sequence[Mapping[str, Any]],
    partition: str, baseline: bool,
) -> list[dict[str, Any]]:
    specs = _partition_specs(all_specs, table, partition, baseline=baseline)
    path = ctx.paths.specs / f"{partition}_{'baseline' if baseline else 'probe'}_specs.json"
    if path.exists():
        if _read_json(path) != specs:
            raise ValueError("T13S13 existing phase spec mismatch")
    else:
        _write_json(path, specs)
    return specs


def run_baseline_phase(
    ctx: Context, table: Sequence[Mapping[str, Any]], all_specs: Sequence[Mapping[str, Any]],
    partition: str, *, backend: str, resume: bool,
) -> dict[str, Any]:
    expected_phase = {
        "training": "offline_ready",
        "calibration": "training_model_frozen",
        "holdout": "calibration_tube_frozen",
    }[partition]
    next_phase = f"{partition}_baseline_complete"
    state = _require_phase(ctx, expected_phase)
    if partition == "calibration":
        model_path = ctx.paths.model / "training_center_model.json"
        if not model_path.is_file() or _sha256(model_path) != state.get("model_sha256"):
            raise ValueError("T13S13 calibration opened before exact model freeze")
    if partition == "holdout":
        model_path = ctx.paths.model / "training_center_model.json"
        tube_path = ctx.paths.model / "calibrated_sequence_tube.json"
        if (
            not model_path.is_file() or not tube_path.is_file()
            or _sha256(model_path) != state.get("model_sha256")
            or _sha256(tube_path) != state.get("tube_sha256")
        ):
            raise ValueError("T13S13 holdout opened before exact model/tube freeze")
    baselines = _phase_specs(ctx, table, all_specs, partition, True)
    probes = _partition_specs(all_specs, table, partition, baseline=False)
    execution = evaluate_specs(ctx, baselines, backend=backend, resume=resume)
    audit = audit_baselines(ctx, baselines)
    lattice = audit_lattice_on_baselines(ctx, baselines, probes) if audit["passed"] else {
        "expected": len(probes), "actual": 0, "pass_count": 0,
        "plant_advance_count": 0, "real_tsc_executed": False, "passed": False,
        "rows": [],
    }
    output = {
        "schema_version": SCHEMA_VERSION, "stage": STAGE,
        "phase": f"{partition}_baseline_safety_and_lattice_gate",
        "execution": execution, "baseline_audit": audit,
        "dynamic_lattice_audit": lattice,
        "formal_tracking_is_diagnostic_only": True,
        "passed": bool(execution["passed"] and audit["passed"] and lattice["passed"]),
    }
    _write_json(ctx.paths.analysis / f"{partition}_baseline_gate.json", output)
    if output["passed"]:
        _set_state(ctx, phase_status=next_phase, real_tsc_executed=True, new_raw_count=len(list(ctx.paths.raw.glob("*.json.gz"))), stop_reason="")
    else:
        _set_state(ctx, finished=True, primary_pass=False, stop_reason=f"{partition}_baseline_or_lattice_gate_failed", real_tsc_executed=True, new_raw_count=len(list(ctx.paths.raw.glob("*.json.gz"))))
    return output


def run_probe_phase(
    ctx: Context, table: Sequence[Mapping[str, Any]], all_specs: Sequence[Mapping[str, Any]],
    partition: str, *, backend: str, resume: bool,
) -> dict[str, Any]:
    _require_phase(ctx, f"{partition}_baseline_complete")
    specs = _phase_specs(ctx, table, all_specs, partition, False)
    execution = evaluate_specs(ctx, specs, backend=backend, resume=resume)
    audit = audit_probes(ctx, specs)
    output = {
        "schema_version": SCHEMA_VERSION, "stage": STAGE,
        "phase": f"{partition}_signed_probe_execution",
        "execution": execution, "probe_evidence_audit": audit,
        "passed": bool(execution["passed"] and audit["passed"]),
    }
    _write_json(ctx.paths.analysis / f"{partition}_probe_execution.json", output)
    if output["passed"]:
        _set_state(ctx, phase_status=f"{partition}_probe_complete", real_tsc_executed=True, new_raw_count=len(list(ctx.paths.raw.glob("*.json.gz"))), stop_reason="")
    else:
        _set_state(ctx, finished=True, primary_pass=False, stop_reason=f"{partition}_probe_runtime_gate_failed", real_tsc_executed=True, new_raw_count=len(list(ctx.paths.raw.glob("*.json.gz"))))
    return output


def run_training_freeze(ctx: Context, table: Sequence[Mapping[str, Any]], all_specs: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    _require_phase(ctx, "training_probe_complete")
    audit = fit_training_model(ctx, table, all_specs)
    if audit["passed"]:
        _set_state(ctx, phase_status="training_model_frozen", model_sha256=audit["model_sha256"], stop_reason="")
    else:
        _set_state(ctx, finished=True, primary_pass=False, stop_reason="training_model_gate_failed")
    return audit


def run_calibration_freeze(ctx: Context, table: Sequence[Mapping[str, Any]], all_specs: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    state = _require_phase(ctx, "calibration_probe_complete")
    model_path = ctx.paths.model / "training_center_model.json"
    if not model_path.is_file() or _sha256(model_path) != state.get("model_sha256"):
        raise ValueError("T13S13 calibration fit saw a changed model")
    audit = calibrate_tube(ctx, table, all_specs)
    if audit["passed"]:
        _set_state(ctx, phase_status="calibration_tube_frozen", tube_sha256=audit["tube_sha256"], stop_reason="")
    else:
        _set_state(ctx, finished=True, primary_pass=False, stop_reason="calibration_tube_gate_failed")
    return audit


def run_final(ctx: Context, table: Sequence[Mapping[str, Any]], all_specs: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    _require_phase(ctx, "holdout_probe_complete")
    audit = evaluate_holdout(ctx, table, all_specs)
    _set_state(
        ctx, phase_status="campaign_complete", finished=True,
        primary_pass=bool(audit["passed"]), stop_reason="" if audit["passed"] else "fresh_holdout_gate_failed",
        verdict={"route": audit["route"], "passed": audit["passed"]},
    )
    return audit


def execute(ctx: Context, *, command: str, backend: str, resume: bool) -> dict[str, Any]:
    offline = prepare_offline(ctx, resume=resume)
    if not offline["passed"]:
        return offline
    if command == "offline":
        return offline
    table = build_context_table(ctx)
    specs = build_new_specs(ctx, table)
    dispatch = {
        "training-baseline": lambda: run_baseline_phase(ctx, table, specs, "training", backend=backend, resume=resume),
        "training-probe": lambda: run_probe_phase(ctx, table, specs, "training", backend=backend, resume=resume),
        "fit-training": lambda: run_training_freeze(ctx, table, specs),
        "calibration-baseline": lambda: run_baseline_phase(ctx, table, specs, "calibration", backend=backend, resume=resume),
        "calibration-probe": lambda: run_probe_phase(ctx, table, specs, "calibration", backend=backend, resume=resume),
        "calibrate": lambda: run_calibration_freeze(ctx, table, specs),
        "holdout-baseline": lambda: run_baseline_phase(ctx, table, specs, "holdout", backend=backend, resume=resume),
        "holdout-probe": lambda: run_probe_phase(ctx, table, specs, "holdout", backend=backend, resume=resume),
        "finalize": lambda: run_final(ctx, table, specs),
    }
    return dispatch[command]()


def self_test() -> dict[str, Any]:
    cfg = _read_json(_project_root() / "configs/stage4_2r3c3t13s13_recurrent_sequence_tube_identification_370ms.json")
    _validate_config(cfg)
    recurrent, inputs = _reservoir_weights(20260802, 32)
    sequence = np.zeros((17, 59), dtype=float)
    a = _encode_sequence(sequence, recurrent, inputs, rho=0.65, leak=0.5, input_scale=0.25)
    b = _encode_sequence(sequence, recurrent, inputs, rho=0.65, leak=0.5, input_scale=0.25)
    lattice = s9.self_test()
    passed = bool(
        np.array_equal(a, b) and a.shape == (32,) and np.all(np.isfinite(a))
        and lattice["passed"]
        and int(cfg["control_matrix"]["expected_new_rollouts"]) == 1088
        and sum((24, 20, 20)) * 17 == 1088
    )
    return {
        "schema_version": SCHEMA_VERSION, "stage": STAGE,
        "reservoir_deterministic": bool(np.array_equal(a, b)),
        "lattice_primitive_self_test": bool(lattice["passed"]),
        "expected_contexts": 72, "expected_new_rollouts": 1088,
        "real_tsc_executed": False, "formal_timing_unchanged": True,
        "bc_dagger_or_rl_allowed": False, "passed": passed,
    }


def _context_from_args(args: argparse.Namespace) -> Context:
    required = (
        "config", "source_stage4_2r3b_run", "source_stage4_2r3c3_run",
        "source_stage4_2r3c3_bank_dir", "source_stage4_2r3c3t1_run",
        "source_stage4_2r3c3t1_audit_dir", "source_stage4_2r3c3t3_controller_bank",
        "q1_run", "q2_run", "q1_audit", "q2_audit", "r3b_server_audit",
        "r3b_snapshot_checks", "run_dir",
    )
    if any(getattr(args, name) is None for name in required):
        raise ValueError("T13S13 execution requires every declared source path")
    return load_config(
        args.config,
        source_stage42r3b_run=args.source_stage4_2r3b_run,
        source_stage42r3c3_run=args.source_stage4_2r3c3_run,
        source_stage42r3c3_bank_dir=args.source_stage4_2r3c3_bank_dir,
        source_stage42r3c3t1_run=args.source_stage4_2r3c3t1_run,
        source_stage42r3c3t1_audit_dir=args.source_stage4_2r3c3t1_audit_dir,
        source_stage42r3c3t3_controller_bank=args.source_stage4_2r3c3t3_controller_bank,
        q1_run=args.q1_run, q2_run=args.q2_run,
        q1_audit=args.q1_audit, q2_audit=args.q2_audit,
        r3b_server_audit=args.r3b_server_audit,
        r3b_snapshot_checks=args.r3b_snapshot_checks,
        run_dir=args.run_dir,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage4.2R3c3T13S13 recurrent sequence-tube identification")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--source-stage4-2r3b-run", type=Path)
    parser.add_argument("--source-stage4-2r3c3-run", type=Path)
    parser.add_argument("--source-stage4-2r3c3-bank-dir", type=Path)
    parser.add_argument("--source-stage4-2r3c3t1-run", type=Path)
    parser.add_argument("--source-stage4-2r3c3t1-audit-dir", type=Path)
    parser.add_argument("--source-stage4-2r3c3t3-controller-bank", type=Path)
    parser.add_argument("--q1-run", type=Path)
    parser.add_argument("--q2-run", type=Path)
    parser.add_argument("--q1-audit", type=Path)
    parser.add_argument("--q2-audit", type=Path)
    parser.add_argument("--r3b-server-audit", type=Path)
    parser.add_argument("--r3b-snapshot-checks", type=Path)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument(
        "--command",
        choices=(
            "offline", "training-baseline", "training-probe", "fit-training",
            "calibration-baseline", "calibration-probe", "calibrate",
            "holdout-baseline", "holdout-probe", "finalize",
        ),
        default="offline",
    )
    parser.add_argument("--backend", choices=("serial", "ray"), default="ray")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        print(json.dumps(self_test(), indent=2, sort_keys=True))
        return
    result = execute(_context_from_args(args), command=args.command, backend=args.backend, resume=args.resume)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
