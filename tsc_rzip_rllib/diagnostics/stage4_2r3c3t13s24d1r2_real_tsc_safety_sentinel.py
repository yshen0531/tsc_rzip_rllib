"""Stage4.2R3c3T13S24D1R2 authentic real-TSC safety sentinel."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import time
import traceback
from collections import Counter
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping, Sequence

import numpy as np

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24_sequential_transition_identification as s24,
)


SCHEMA_VERSION = 1
STAGE = "Stage4.2R3c3T13S24D1R2"
RUN_NAME = "stage4_2r3c3t13s24d1r2_geometry_restored_amplitude_safety_sentinel"
CAMPAIGN_IDENTITY = "geometry_restored_amplitude_safety_sentinel_v1"
CONTROLLER_REVISION = "sequential_amplitude_coded_card15_probe_v42r3c3t13s24d1r2_v1"
PACKAGE_REVISION = "r42r3c3t13s24d1r2_geometry_restored_amplitude_safety_sentinel_v2"
N_COILS = 14


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
    ).hexdigest()


def _read_json(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
    )


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _write_json_gz(path: Path, value: Any) -> None:
    s24._write_json_gz(path, value)


@dataclass(frozen=True)
class Paths:
    run_dir: Path
    stage_dir: Path
    variants: Path
    specs: Path
    source_reference: Path
    raw: Path
    analysis: Path
    state: Path
    manifest: Path
    final: Path


def _paths(run_dir: Path) -> Paths:
    root = run_dir.expanduser().resolve()
    stage = root / RUN_NAME
    return Paths(
        run_dir=root,
        stage_dir=stage,
        variants=stage / "variants",
        specs=stage / "specs",
        source_reference=stage / "source_reference",
        raw=stage / "raw",
        analysis=stage / "analysis",
        state=stage / "stage_state.json",
        manifest=stage / "stage_manifest.json",
        final=stage / "final_result.json",
    )


@dataclass(frozen=True)
class Context:
    cfg: dict[str, Any]
    config_path: Path
    base_s24_ctx: Any
    source_d1r1_output: Path
    source_d1r1_log: Path
    paths: Paths


def _package_path(cfg: Mapping[str, Any], key: str) -> Path:
    root = _project_root()
    path = (root / str(cfg[key])).resolve()
    if path != root and root not in path.parents:
        raise ValueError(f"D1R2 {key} is outside package")
    return path


def _validate_config(cfg: Mapping[str, Any], config_path: Path) -> None:
    exact = {
        "schema_version": 1,
        "stage": STAGE,
        "run_name": RUN_NAME,
        "campaign_identity": CAMPAIGN_IDENTITY,
        "controller_revision": CONTROLLER_REVISION,
        "package_revision": PACKAGE_REVISION,
        "selection_status": "frozen_after_d1r1_pass_before_d1r2_implementation_or_tsc",
    }
    for key, expected in exact.items():
        if cfg.get(key) != expected:
            raise ValueError(f"D1R2 frozen {key} changed")
    for key in ("design_document", "base_s24_config", "base_s24_implementation"):
        path = _package_path(cfg, key)
        if not path.is_file() or _sha256(path) != str(cfg[f"{key}_sha256"]):
            raise ValueError(f"D1R2 frozen {key} hash changed")
    expected_config = (
        _project_root()
        / "configs/stage4_2r3c3t13s24d1r2_real_tsc_safety_sentinel_370ms.json"
    ).resolve()
    if config_path.resolve() != expected_config:
        raise ValueError("D1R2 config path changed")
    source = cfg["source_contract"]
    if (
        source["d1r1_output_name"]
        != "stage4_2r3c3t13s24d1r1_geometry_restoring_search_20260803_145327"
        or source["required_d1r1_route"]
        != "GEOMETRY_RESTORING_AMPLITUDE_SEARCH_PASS_REAL_SENTINEL_REQUIRED"
        or source["required_selected_amplitudes"]
        != {"++++": "0.250", "+-+-": "0.250", "++--": "0.290", "+--+": "0.360"}
        or tuple(
            int(source[key])
            for key in (
                "required_issue_gate_pass",
                "required_cancellation_gate_pass",
                "required_finite_constructions",
                "required_selected_spec_count",
            )
        )
        != (3840, 3840, 7680, 54)
        or any(
            len(str(value)) != 64
            for key, value in source.items()
            if key.endswith("sha256") or key.endswith("digest")
        )
    ):
        raise ValueError("D1R2 immutable source contract changed")
    normalization = cfg["identity_normalization"]
    if (
        normalization["allowed_changed_spec_paths"]
        != [
            "experiment_id",
            "environment_variant",
            "kind",
            "phase",
            "s24d2_online_cancel_margin_gate->s24d1r2_online_cancel_margin_gate",
        ]
        or normalization["old_experiment_prefix"] != "s42r3c3t13s24d2_"
        or normalization["new_experiment_prefix"] != "s42r3c3t13s24d1r2_"
        or normalization["old_environment_prefix"] != "stage4_2r3c3t13s24d2_"
        or normalization["new_environment_prefix"] != "stage4_2r3c3t13s24d1r2_"
        or normalization["old_kind"]
        != "stage4_2r3c3t13s24d2_contracted_amplitude_safety_sentinel"
        or normalization["new_kind"]
        != "stage4_2r3c3t13s24d1r2_geometry_restored_amplitude_safety_sentinel"
        or normalization["old_phase"]
        != "prospective_contracted_amplitude_safety_sentinel"
        or normalization["new_phase"]
        != "prospective_geometry_restored_amplitude_safety_sentinel"
        or normalization["normalized_ordered_spec_digest"]
        != "50832fadb244bbd338bd7c5cd5f9ff136eedce498d920f416458516d7655648f"
    ):
        raise ValueError("D1R2 identity normalization changed")
    specs = cfg["spec_contract"]
    if (
        tuple(int(specs[key]) for key in (
            "expected_specs", "expected_contexts", "expected_pairs", "expected_snapshots"
        )) != (54, 18, 9, 18)
        or specs["expected_horizon_counts"] != {"35": 20, "37": 34}
        or specs["expected_sequence_index_counts"]
        != {"6": 12, "10": 14, "14": 6, "18": 16, "22": 6}
        or not all(bool(specs[key]) for key in (
            "fresh_tsc_process_required", "fresh_controller_required", "full_horizon_required"
        ))
        or bool(specs["source_outcome_available_to_controller"])
        or bool(specs["pair_history_partition_label_available_to_controller"])
    ):
        raise ValueError("D1R2 spec contract changed")
    schedule = cfg["schedule_contract"]
    if (
        list(map(int, schedule["issue_task_steps"])) != [10, 13, 15, 17]
        or list(map(int, schedule["cancel_task_steps"])) != [11, 14, 16, 18]
        or list(map(int, schedule["issue_effect_states"])) != [11, 14, 16, 18]
        or list(map(int, schedule["cancel_effect_states"])) != [12, 15, 17, 19]
        or int(schedule["dynamic_exact_search_radius"]) != 16
        or float(schedule["maximum_absolute_coordinate_error"]) != 0.07
        or float(schedule["minimum_active_absolute_coordinate"]) != 0.18
        or float(schedule["minimum_desired_applied_current_cosine"]) != 0.98
        or float(schedule["maximum_relative_off_basis_residual"]) != 0.10
        or float(schedule["maximum_incremental_normalized_action_linf"]) != 0.25
        or float(schedule["maximum_online_cancel_incremental_normalized_action_linf"])
        != 0.24
        or float(schedule["maximum_total_normalized_action_abs"]) != 1.0
        or float(schedule["maximum_current_utilization"]) != 0.55
        or not bool(schedule["require_exact_stored_center_cancellation"])
        or not bool(schedule["require_exact_zero_target_jump_net"])
        or schedule["requested_matrix_digest"]
        != "023a6c9212bf52f38b1d4268d2be406964b5c1d1c64e43ffad85f0af689a3ce6"
    ):
        raise ValueError("D1R2 action schedule or gates changed")
    formal = cfg["formal_timing_contract"]
    if (
        formal["normal"] != {"arrival_deadline_step": 25, "hold_through_step": 35}
        or formal["weak"] != {"arrival_deadline_step": 27, "hold_through_step": 37}
        or float(formal["position_tolerance_m"]) != 0.03
        or float(formal["speed_tolerance_m_per_s"]) != 0.1
        or float(formal["ip_tolerance_A"]) != 10000.0
        or int(formal["arrival_streak_steps"]) != 3
        or bool(formal["arrival_deadline_expansion_allowed"])
    ):
        raise ValueError("D1R2 formal timing changed")
    gate = cfg["execution_gate"]
    if tuple(int(gate[key]) for key in (
        "raw_files_required", "fresh_actor_tsc_controller_required",
        "issue_events_required", "cancel_events_required", "strict_parse_required",
        "restart_required", "causality_required", "calibration_required",
        "full_horizon_required", "forbidden_use_count_required",
    )) != (54, 54, 216, 216, 54, 54, 54, 54, 54, 0):
        raise ValueError("D1R2 execution gate changed")
    if cfg["routes"] != {
        "offline_fail": "GEOMETRY_RESTORED_SENTINEL_PREFLIGHT_FAIL_NO_TSC",
        "runtime_fail": "GEOMETRY_RESTORED_SENTINEL_RUNTIME_FAIL_STOP",
        "action_fail": "GEOMETRY_RESTORED_SENTINEL_ACTION_MARGIN_FAIL_REDESIGN_REQUIRED",
        "pass": "GEOMETRY_RESTORED_SENTINEL_PASS_FULL_REPLACEMENT_IDENTIFICATION_REQUIRED",
    }:
        raise ValueError("D1R2 routes changed")
    if int(cfg["parallel"]["n_workers"]) != 54:
        raise ValueError("D1R2 Ray capacity changed")
    scope = cfg["scientific_scope"]
    if (
        not bool(scope["development_set_safety_sentinel_only"])
        or bool(scope["model_fit_executed"])
        or bool(scope["real_mpc_executed"])
        or not bool(scope["pass_authorizes_full_replacement_identification_only"])
        or bool(scope["pass_authorizes_mpc"])
        or bool(scope["probe_trajectories_allowed_in_expert_dataset"])
        or bool(scope["independent_long_hold_validated"])
        or bool(scope["bc_dagger_or_rl_allowed"])
    ):
        raise ValueError("D1R2 scientific scope changed")


def load_config(
    config_path: Path,
    *,
    source_d1r1_output: Path,
    source_d1r1_log: Path,
    source_s21_run: Path,
    source_s23r1_output: Path,
    run_dir: Path,
    **source_kwargs: Path,
) -> Context:
    config_path = config_path.expanduser().resolve()
    cfg = _read_json(config_path)
    _validate_config(cfg, config_path)
    base_s24_ctx = s24.load_config(
        _package_path(cfg, "base_s24_config"),
        source_s21_run=source_s21_run,
        source_s23r1_output=source_s23r1_output,
        run_dir=run_dir,
        **source_kwargs,
    )
    return Context(
        cfg=cfg,
        config_path=config_path,
        base_s24_ctx=base_s24_ctx,
        source_d1r1_output=source_d1r1_output.expanduser().resolve(),
        source_d1r1_log=source_d1r1_log.expanduser().resolve(),
        paths=_paths(run_dir),
    )


def _normalise_spec(source_spec: Mapping[str, Any], cfg: Mapping[str, Any]) -> dict[str, Any]:
    contract = cfg["identity_normalization"]
    spec = copy.deepcopy(dict(source_spec))
    old_id = str(spec["experiment_id"])
    old_prefix = str(contract["old_experiment_prefix"])
    if not old_id.startswith(old_prefix):
        raise ValueError("D1R2 source experiment identity prefix changed")
    suffix = old_id[len(old_prefix):]
    new_id = str(contract["new_experiment_prefix"]) + suffix
    expected_environment = str(contract["old_environment_prefix"]) + old_id
    if spec.get("environment_variant") != expected_environment:
        raise ValueError("D1R2 source environment identity changed")
    if spec.get("kind") != contract["old_kind"] or spec.get("phase") != contract["old_phase"]:
        raise ValueError("D1R2 source kind/phase changed")
    if float(spec.pop("s24d2_online_cancel_margin_gate")) != 0.24:
        raise ValueError("D1R2 source online margin changed")
    spec.update(
        {
            "experiment_id": new_id,
            "environment_variant": str(contract["new_environment_prefix"]) + new_id,
            "kind": str(contract["new_kind"]),
            "phase": str(contract["new_phase"]),
            "s24d1r2_online_cancel_margin_gate": 0.24,
        }
    )
    return spec


def _reverse_normalisation(spec: Mapping[str, Any], cfg: Mapping[str, Any]) -> dict[str, Any]:
    contract = cfg["identity_normalization"]
    restored = copy.deepcopy(dict(spec))
    new_id = str(restored["experiment_id"])
    new_prefix = str(contract["new_experiment_prefix"])
    if not new_id.startswith(new_prefix):
        raise ValueError("D1R2 normalized experiment identity prefix changed")
    old_id = str(contract["old_experiment_prefix"]) + new_id[len(new_prefix):]
    if restored.get("environment_variant") != str(contract["new_environment_prefix"]) + new_id:
        raise ValueError("D1R2 normalized environment identity changed")
    if restored.get("kind") != contract["new_kind"] or restored.get("phase") != contract["new_phase"]:
        raise ValueError("D1R2 normalized kind/phase changed")
    if float(restored.pop("s24d1r2_online_cancel_margin_gate")) != 0.24:
        raise ValueError("D1R2 normalized online margin changed")
    restored.update(
        {
            "experiment_id": old_id,
            "environment_variant": str(contract["old_environment_prefix"]) + old_id,
            "kind": str(contract["old_kind"]),
            "phase": str(contract["old_phase"]),
            "s24d2_online_cancel_margin_gate": 0.24,
        }
    )
    return restored


def _authenticate_d1r1(ctx: Context) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    source = ctx.cfg["source_contract"]
    root = ctx.source_d1r1_output
    if root.name != source["d1r1_output_name"]:
        raise ValueError("D1R2 exact D1R1 source directory changed")
    package_sources = {
        "config": (
            _project_root()
            / "configs/stage4_2r3c3t13s24d1r1_geometry_restoring_amplitude_search_v1.json",
            "d1r1_config_sha256",
        ),
        "implementation": (
            _project_root()
            / "docs/codex/audit_tools/stage4_2r3c3t13s24d1r1_geometry_restoring_amplitude_search.py",
            "d1r1_implementation_sha256",
        ),
        "design": (
            _project_root()
            / "docs/codex/reports/STAGE4_2R3C3T13S24D1R1_GEOMETRY_RESTORING_AMPLITUDE_SEARCH_DESIGN.md",
            "d1r1_design_sha256",
        ),
        "forensic_report": (
            _project_root()
            / "docs/codex/reports/STAGE4_2R3C3T13S24D1R1_FORENSIC_REPORT.md",
            "d1r1_forensic_report_sha256",
        ),
    }
    source_hashes = {}
    for name, (path, key) in package_sources.items():
        if not path.is_file() or _sha256(path) != str(source[key]):
            raise ValueError(f"D1R2 immutable D1R1 {name} changed")
        source_hashes[name] = _sha256(path)
    outputs = {
        "detailed": (
            root / "stage4_2r3c3t13s24d1r1_geometry_restoring_search_v1.json",
            "d1r1_detailed_sha256",
        ),
        "summary": (
            root / "stage4_2r3c3t13s24d1r1_summary_v1.json",
            "d1r1_summary_sha256",
        ),
        "selected_specs": (
            root / "stage4_2r3c3t13s24d1r1_selected_sentinel_specs_v1.json",
            "d1r1_selected_specs_sha256",
        ),
        "manifest": (
            root / "stage4_2r3c3t13s24d1r1_manifest_v1.json",
            "d1r1_manifest_sha256",
        ),
        "complete_log": (ctx.source_d1r1_log, "d1r1_complete_log_sha256"),
    }
    output_hashes = {}
    for name, (path, key) in outputs.items():
        if not path.is_file() or _sha256(path) != str(source[key]):
            raise ValueError(f"D1R2 immutable D1R1 {name} changed")
        output_hashes[name] = _sha256(path)
    if outputs["selected_specs"][0].stat().st_size != int(
        source["d1r1_selected_specs_size_bytes"]
    ):
        raise ValueError("D1R2 D1R1 selected-spec size changed")
    detailed = _read_json(outputs["detailed"][0])
    summary = _read_json(outputs["summary"][0])
    selected = _read_json(outputs["selected_specs"][0])
    manifest = _read_json(outputs["manifest"][0])
    primary = detailed.get("full_replay_primary_gate_counts") or {}
    if not (
        detailed.get("primary_pass")
        and detailed.get("full_replay_passed")
        and summary.get("primary_pass")
        and detailed.get("route") == source["required_d1r1_route"]
        and summary.get("route") == source["required_d1r1_route"]
        and detailed.get("selected_pattern_amplitudes")
        == {"++--": "0.290", "+--+": "0.360"}
        and int(primary.get("issue_gate_pass", -1))
        == int(source["required_issue_gate_pass"])
        and int(primary.get("cancellation_gate_pass", -1))
        == int(source["required_cancellation_gate_pass"])
        and int(primary.get("finite_constructions", -1))
        == int(source["required_finite_constructions"])
        and int(selected.get("selected_spec_count", -1))
        == int(source["required_selected_spec_count"])
        and selected.get("next_stage") == STAGE
        and selected.get("source_outcomes_available_to_controller") is False
        and int(manifest.get("new_raw_files_created", -1)) == 0
        and not bool(manifest.get("ray_gotsc_tsc_plant_or_controller_executed"))
        and detailed["provenance"]["s24_active_raw_inventory_digest"]
        == source["s24_active_raw_inventory_digest"]
        and detailed["provenance"]["s21_raw_inventory_digest"]
        == source["s21_raw_inventory_digest"]
    ):
        raise ValueError("D1R2 D1R1 scientific source contract changed")
    rows = list(selected.get("spec_rows") or [])
    if [int(row.get("selection_index", -1)) for row in rows] != list(range(54)):
        raise ValueError("D1R2 selected source order changed")
    specs: list[dict[str, Any]] = []
    for row in rows:
        selection = row.get("selection") or {}
        if selection.get("source_failure_class") != "sequential_cancel_incremental_action_gate":
            raise ValueError("D1R2 selected source failure class changed")
        source_spec = row.get("sentinel_spec") or {}
        normalized = _normalise_spec(source_spec, ctx.cfg)
        if _reverse_normalisation(normalized, ctx.cfg) != source_spec:
            raise ValueError("D1R2 normalization changed a scientific field")
        if (
            normalized.get("stage") != STAGE
            or normalized.get("campaign_identity") != CAMPAIGN_IDENTITY
            or normalized.get("controller_revision") != CONTROLLER_REVISION
            or normalized.get("pair_id") != selection.get("pair_id")
            or normalized.get("history_member") != selection.get("history_member")
            or int(normalized.get("s24_sequence_index", -1))
            != int(selection.get("sequence_index", -2))
            or normalized.get("s24_schedule_digest")
            != ctx.cfg["schedule_contract"]["requested_matrix_digest"]
            or normalized.get("s24_role") != "sequential_response"
            or normalized.get("partition") != "safety_sentinel"
            or bool(normalized.get("source_result_available_to_controller"))
            or bool(normalized.get("source_action_available_to_controller"))
            or bool(normalized.get("source_coil_current_available_to_controller"))
            or bool(normalized.get("source_wire_current_available_to_controller"))
            or bool(normalized.get("pair_or_history_label_available_to_controller"))
            or bool(normalized.get("partition_label_available_to_controller"))
            or not bool(normalized.get("fresh_tsc_process_required"))
            or not bool(normalized.get("fresh_controller_required"))
            or bool(normalized.get("probe_trajectory_allowed_in_expert_dataset"))
        ):
            raise ValueError("D1R2 normalized spec contract changed")
        specs.append(normalized)
    contract = ctx.cfg["spec_contract"]
    contexts = {(row["pair_id"], row["history_member"]) for row in specs}
    if (
        _digest(specs)
        != ctx.cfg["identity_normalization"]["normalized_ordered_spec_digest"]
        or len(specs) != int(contract["expected_specs"])
        or len({row["experiment_id"] for row in specs}) != len(specs)
        or len({row["environment_variant"] for row in specs}) != len(specs)
        or len(contexts) != int(contract["expected_contexts"])
        or len({row["pair_id"] for row in specs}) != int(contract["expected_pairs"])
        or len({row["restart_snapshot_dir"] for row in specs})
        != int(contract["expected_snapshots"])
        or Counter(str(row["horizon_steps"]) for row in specs)
        != Counter(contract["expected_horizon_counts"])
        or Counter(str(row["s24_sequence_index"]) for row in specs)
        != Counter(contract["expected_sequence_index_counts"])
    ):
        raise ValueError("D1R2 normalized spec inventory changed")
    return (
        {
            "source_dir": str(root),
            "package_source_hashes": source_hashes,
            "output_hashes": output_hashes,
            "source_route": str(summary["route"]),
            "source_provenance_digest": str(detailed["provenance_digest"]),
            "source_spec_count": len(rows),
            "normalized_spec_count": len(specs),
            "normalized_spec_digest": _digest(specs),
            "passed": True,
        },
        specs,
    )


def _selected_context_table(specs: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    by_key = {}
    for spec in specs:
        key = (str(spec["pair_id"]), str(spec["history_member"]))
        by_key.setdefault(
            key,
            {
                "pair_id": key[0],
                "history_member": key[1],
                "state_generation_experiment_id": spec["state_generation_experiment_id"],
                "restart_snapshot_manifest_digest": spec["restart_snapshot_manifest_digest"],
                "restart_snapshot_dir": spec["restart_snapshot_dir"],
                "target_id": spec["target_id"],
                "action_delay_steps": spec["action_delay_steps"],
                "slew_scale": spec["slew_scale"],
                "regime_id": spec["regime_id"],
                "partition": "safety_sentinel",
            },
        )
    return [by_key[key] for key in sorted(by_key)]


def _selected_snapshot_audit(
    contexts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Re-aggregate the inherited source audit for D1R2's selected subset."""
    source_audit = s24.s21._snapshot_audit(contexts)
    rows = list(source_audit.get("rows") or [])
    pass_count = sum(bool(row.get("passed")) for row in rows)
    expected = 18
    passed = bool(
        len(contexts) == expected
        and len(rows) == expected
        and pass_count == expected
        and all(bool(row.get("passed")) for row in rows)
    )
    return {
        "expected": expected,
        "actual": len(rows),
        "pass_count": pass_count,
        "passed": passed,
        "rows": rows,
        "source_helper_expected": source_audit.get("expected"),
        "source_helper_actual": source_audit.get("actual"),
        "source_helper_pass_count": source_audit.get("pass_count"),
        "source_helper_passed": source_audit.get("passed"),
    }


def _prepare_dirs(paths: Paths) -> None:
    for path in (
        paths.run_dir,
        paths.stage_dir,
        paths.variants,
        paths.specs,
        paths.source_reference,
        paths.raw,
        paths.analysis,
    ):
        path.mkdir(parents=True, exist_ok=True)


def prepare_offline(ctx: Context) -> dict[str, Any]:
    if ctx.paths.run_dir.exists() and any(ctx.paths.run_dir.iterdir()):
        raise ValueError("D1R2 offline requires a fresh empty run identity")
    auth, specs = _authenticate_d1r1(ctx)
    contexts = _selected_context_table(specs)
    snapshots = _selected_snapshot_audit(contexts)
    if not snapshots.get("passed") or int(snapshots.get("pass_count", -1)) != 18:
        raise ValueError(ctx.cfg["routes"]["offline_fail"])
    package = s24.s21._package_fingerprint()
    _prepare_dirs(ctx.paths)
    manifest = {
        "schema_version": 1,
        "stage": STAGE,
        "campaign_identity": CAMPAIGN_IDENTITY,
        "controller_revision": CONTROLLER_REVISION,
        "package_revision": PACKAGE_REVISION,
        "config_path": str(ctx.config_path),
        "config_sha256": _sha256(ctx.config_path),
        "design_document_sha256": ctx.cfg["design_document_sha256"],
        "base_s24_config_sha256": ctx.cfg["base_s24_config_sha256"],
        "base_s24_implementation_sha256": ctx.cfg["base_s24_implementation_sha256"],
        "d1r1_authentication": auth,
        "spec_count": len(specs),
        "spec_digest": _digest(specs),
        "context_count": len(contexts),
        "context_digest": _digest(contexts),
        "snapshot_pass_count": int(snapshots["pass_count"]),
        "package_fingerprint": package,
        "formal_timing_unchanged": True,
        "probe_trajectories_allowed_in_expert_dataset": False,
        "bc_dagger_or_rl_allowed": False,
    }
    state = {
        "schema_version": 1,
        "stage": STAGE,
        "phase_status": "offline_ready",
        "finished": False,
        "primary_pass": False,
        "real_tsc_executed": False,
        "new_raw_count": 0,
        "spec_digest": _digest(specs),
        "package_digest": package["digest"],
        "stop_reason": "",
        "verdict": {},
    }
    _write_json(ctx.paths.manifest, manifest)
    _write_json(ctx.paths.state, state)
    _write_json(ctx.paths.source_reference / "d1r1_authentication.json", auth)
    _write_json(ctx.paths.source_reference / "selected_contexts.json", contexts)
    _write_json(ctx.paths.source_reference / "snapshot_audit.json", snapshots)
    _write_json(ctx.paths.specs / "normalized_sentinel_specs.json", specs)
    output = {
        "schema_version": 1,
        "stage": STAGE,
        "phase": "zero_plant_offline_preflight",
        "source_authentication_passed": True,
        "identity_only_normalization_passed": True,
        "spec_count": len(specs),
        "context_count": len(contexts),
        "snapshot_pass_count": int(snapshots["pass_count"]),
        "new_raw_count": 0,
        "real_tsc_executed": False,
        "passed": True,
    }
    _write_json(ctx.paths.analysis / "offline_preflight.json", output)
    return output


def _saved_specs(ctx: Context) -> list[dict[str, Any]]:
    saved = _read_json(ctx.paths.specs / "normalized_sentinel_specs.json")
    _, rebuilt = _authenticate_d1r1(ctx)
    if saved != rebuilt:
        raise ValueError("D1R2 frozen normalized specs changed")
    manifest = _read_json(ctx.paths.manifest)
    if _digest(saved) != manifest.get("spec_digest"):
        raise ValueError("D1R2 frozen normalized spec digest changed")
    return saved


def _payload(ctx: Context, spec: Mapping[str, Any]) -> dict[str, Any]:
    s21_ctx = ctx.base_s24_ctx.base_ctx
    proxy = SimpleNamespace(
        base_ctx=s21_ctx.base_ctx,
        paths=ctx.paths,
        cfg=s21_ctx.cfg,
    )
    payload = s24.s21._payload(proxy, spec)
    experiment_id = str(spec["experiment_id"])
    payload.update(
        {
            "variant_id": f"stage4_2r3c3t13s24d1r2_{experiment_id}",
            "stage4_2r3c3t13s24d1r2_restart_snapshot_dir": str(
                spec["restart_snapshot_dir"]
            ),
            "stage4_2r3c3t13s24d1r2_snapshot_manifest_digest": str(
                spec["restart_snapshot_manifest_digest"]
            ),
            "stage4_2r3c3t13s24d1r2_selection_label_available_to_controller": False,
        }
    )
    _write_json(ctx.paths.variants / f"payload_{experiment_id}.json", payload)
    return payload


def _structured_event_from_exception(exc: Exception) -> dict[str, Any] | None:
    text = str(exc)
    marker = ": {"
    if marker not in text:
        return None
    try:
        value = json.loads("{" + text.split(marker, 1)[1])
        return value if isinstance(value, dict) else None
    except Exception:
        return None


class GeometryRestoredSafetySentinelController(
    s24.SequentialAmplitudeCodedProbeController
):
    """Exact S24 controller plus the preregistered cancellation margin."""

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self._last_failed_event: dict[str, Any] | None = None

    def _issue(
        self, slot: int, currents: np.ndarray, baseline_action: np.ndarray
    ) -> tuple[np.ndarray, dict[str, Any]]:
        try:
            return super()._issue(slot, currents, baseline_action)
        except Exception as exc:
            self._last_failed_event = _structured_event_from_exception(exc)
            raise

    def _cancel(
        self, slot: int, currents: np.ndarray, baseline_action: np.ndarray
    ) -> tuple[np.ndarray, dict[str, Any]]:
        if self._active_issue is None or int(self._active_issue["slot"]) != slot:
            raise ValueError("D1R2 cancellation has no matching causal issue")
        stored_fields = tuple(map(str, self._active_issue["center_card15_fields"]))
        issue_target = tuple(map(str, self._active_issue["target_card15_fields"]))
        chosen = s24.s21.s16.s9.exact_stored_center_action(
            stored_fields=stored_fields,
            measured_current_a_tsc=currents,
            baseline_action_norm_tsc=baseline_action,
            turns_tsc=self.turns_tsc,
            max_slew_step_a=float(self.base.max_delta_a),
            minimum_current_a_tsc=self.base.min_current,
            maximum_current_a_tsc=self.base.max_current,
            cfg=self.lattice_cfg,
        )
        cancelled = self.actuator.apply(currents, chosen["action_norm_tsc"])
        exact_zero = all(
            (
                s24.s21.s16.s9._decimal_field(target)
                - s24.s21.s16.s9._decimal_field(center)
            )
            + (
                s24.s21.s16.s9._decimal_field(center)
                - s24.s21.s16.s9._decimal_field(target)
            )
            == 0
            for center, target in zip(stored_fields, issue_target)
        )
        increment = float(chosen["incremental_normalized_action_linf"])
        criteria = {
            "target_exact": list(cancelled.card15_fields) == list(stored_fields),
            "exact_fields": all(len(field) == 10 for field in stored_fields),
            "exact_zero_target_jump_net": exact_zero,
            "no_saturation": not any(cancelled.action_saturated),
            "no_current_clip": not any(cancelled.current_limit_clipped),
            "incremental_action": increment
            <= float(self.schedule_cfg["maximum_incremental_normalized_action_linf"])
            + 1e-12,
            "online_cancel_margin": increment
            <= float(
                self.schedule_cfg[
                    "maximum_online_cancel_incremental_normalized_action_linf"
                ]
            )
            + 1e-12,
            "total_action": float(chosen["total_normalized_action_abs"])
            <= float(self.schedule_cfg["maximum_total_normalized_action_abs"])
            + 1e-12,
            "current_utilization": float(
                chosen["predicted_maximum_current_utilization"]
            )
            <= float(self.schedule_cfg["maximum_current_utilization"]) + 1e-12,
            "actuator_gate": bool(chosen["passed"]),
        }
        event = {
            "event": "sequential_cancel",
            "stage": STAGE,
            "controller_revision": CONTROLLER_REVISION,
            "slot": slot,
            "task_step": self.step,
            "requested_coordinate": self.requested_by_step[
                self.cancel_steps[slot]
            ].tolist(),
            "stored_center_card15_fields": list(stored_fields),
            "issue_target_card15_fields": list(issue_target),
            "incremental_normalized_action_linf": increment,
            "online_cancel_margin": float(
                self.schedule_cfg[
                    "maximum_online_cancel_incremental_normalized_action_linf"
                ]
            ),
            "total_normalized_action_abs": float(
                chosen["total_normalized_action_abs"]
            ),
            "predicted_current_utilization": float(
                chosen["predicted_maximum_current_utilization"]
            ),
            "criteria": criteria,
            "passed": bool(all(criteria.values())),
            "actuator_prediction": copy.deepcopy(chosen),
        }
        if not event["passed"]:
            self._last_failed_event = copy.deepcopy(event)
            raise ValueError(
                "D1R2 sequential cancel action failed: "
                + json.dumps(event, sort_keys=True)
            )
        self._active_issue = None
        return np.asarray(chosen["action_norm_tsc"], dtype=float), event

    def action(
        self, current_state: Mapping[str, Any]
    ) -> tuple[np.ndarray, dict[str, Any]]:
        action, trace = super().action(current_state)
        event = trace.get("r3c3t13s24_event_detail") or {}
        trace.update(
            {
                "r3c3t13s24d1r2_identification_only": True,
                "r3c3t13s24d1r2_safety_sentinel_only": True,
                "r3c3t13s24d1r2_controller_revision": CONTROLLER_REVISION,
                "r3c3t13s24d1r2_event": trace.get("r3c3t13s24_event", "none"),
                "r3c3t13s24d1r2_event_detail": copy.deepcopy(event),
                "r3c3t13s24d1r2_source_selection_label_used": False,
                "r3c3t13s24d1r2_pair_history_partition_label_used": False,
                "r3c3t13s24d1r2_source_outcome_used": False,
                "r3c3t13s24d1r2_future_measurement_used": False,
                "r3c3t13s24d1r2_future_executed_action_used": False,
                "r3c3t13s24d1r2_hidden_wire_current_used": False,
                "r3c3t13s24d1r2_schedule_available_to_underlying_controller": False,
            }
        )
        return action, trace


class LocalWorker:
    """One fresh authentic TSC process and D1R2 controller per rollout."""

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
    ):
        self.plant = s24.s21.s16.s9.t11.t1.r1.LocalPlantReplayWorker(
            payload, library, bundle, worker_id, selector
        )
        self.base = self.plant.base_worker
        self.bundle = bundle
        self.lattice_cfg = lattice_cfg
        self.calibration_cfg = calibration_cfg
        self.dynamic_cfg = dynamic_cfg
        self.schedule_cfg = schedule_cfg

    def close(self) -> None:
        self.plant.close()

    def evaluate(self, spec: dict[str, Any]) -> dict[str, Any]:
        started = time.time()
        failed = True
        trajectory: list[dict[str, Any]] = []
        trace: list[dict[str, Any]] = []
        controller: GeometryRestoredSafetySentinelController | None = None
        result: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "stage": STAGE,
            "campaign_identity": CAMPAIGN_IDENTITY,
            "controller_revision": CONTROLLER_REVISION,
            "underlying_controller_revision": (
                s24.s21.s16.s9.t11.t1.r3c1.CONTROLLER_REVISION
            ),
            "probe_primitive_revision": CONTROLLER_REVISION,
            "base_s24_controller_revision": s24.CONTROLLER_REVISION,
            "experiment_id": str(spec["experiment_id"]),
            "spec": copy.deepcopy(spec),
            "success": False,
            "completed": False,
            "failure_class": "",
            "failure_reason": "",
            "trajectory": trajectory,
            "controller_trace": trace,
        }
        try:
            horizon = int(spec["horizon_steps"])
            if (
                horizon != s24.s21.s13._formal_horizon(float(spec["slew_scale"]))
                or horizon != int(spec["formal_horizon_steps"])
                or horizon != int(self.base.env.max_episode_steps)
            ):
                raise ValueError("D1R2 formal horizon changed")
            self.base.env.reset()
            zero = np.zeros(N_COILS, dtype=np.float32)
            trajectory.append(
                s24.s21.s16.s9.t11.t1.r1._state_record_full(
                    self.base.env, 0, zero
                )
            )
            controller = GeometryRestoredSafetySentinelController(
                self.base,
                self.bundle,
                s24.s21.s16.s9._controller_spec(spec),
                trajectory[0],
                self.lattice_cfg,
                self.calibration_cfg,
                self.dynamic_cfg,
                self.schedule_cfg,
            )
            for step in range(horizon):
                action, controller_row = controller.action(trajectory[-1])
                _, _, terminated, truncated, info = self.base.env.step(action)
                next_state = s24.s21.s16.s9.t11.t1.r1._state_record_full(
                    self.base.env, step + 1, action
                )
                trajectory.append(next_state)
                trace.append(controller_row)
                controller.advance(next_state)
                if terminated:
                    raise RuntimeError(
                        str(info.get("failure_reason", "environment terminated"))
                    )
                if truncated and step + 1 < horizon:
                    raise RuntimeError(
                        "environment truncated before D1R2 formal horizon"
                    )
            calibration_events = [
                row["r3c3t13s16_lattice_event"]
                for row in trace
                if row["r3c3t13s16_lattice_event"] != "none"
            ]
            expected_calibration = [
                "calibration_issue",
                "calibration_cancel",
                "calibration_issue",
                "calibration_cancel",
                "calibration_issue",
                "calibration_cancel",
                "calibration_issue",
                "calibration_cancel",
            ]
            sequence_events = [
                row["r3c3t13s24d1r2_event"]
                for row in trace
                if row["r3c3t13s24d1r2_event"] != "none"
            ]
            expected_sequence = [
                "sequential_issue",
                "sequential_cancel",
                "sequential_issue",
                "sequential_cancel",
                "sequential_issue",
                "sequential_cancel",
                "sequential_issue",
                "sequential_cancel",
            ]
            forbidden_keys = (
                "future_measurement_used",
                "hidden_wire_used",
                "source_action_used",
                "source_coil_current_used",
                "source_wire_current_used",
                "current_run_future_used",
                "pair_or_history_label_used",
                "source_result_used",
                "future_probe_schedule_available_to_underlying_controller",
                "r3c3t13s21_partition_label_used",
                "r3c3t13s24_pair_history_partition_label_used",
                "r3c3t13s24_delay_slew_target_id_label_used",
                "r3c3t13s24_source_or_matched_baseline_used",
                "r3c3t13s24_future_measurement_used",
                "r3c3t13s24_future_executed_action_used",
                "r3c3t13s24_hidden_wire_current_used",
                "r3c3t13s24_schedule_available_to_underlying_controller",
                "r3c3t13s24d1r2_source_selection_label_used",
                "r3c3t13s24d1r2_pair_history_partition_label_used",
                "r3c3t13s24d1r2_source_outcome_used",
                "r3c3t13s24d1r2_future_measurement_used",
                "r3c3t13s24d1r2_future_executed_action_used",
                "r3c3t13s24d1r2_hidden_wire_current_used",
                "r3c3t13s24d1r2_schedule_available_to_underlying_controller",
            )
            forbidden = sum(
                any(bool(row.get(key)) for key in forbidden_keys) for row in trace
            )
            event_details = [
                row["r3c3t13s24d1r2_event_detail"]
                for row in trace
                if row["r3c3t13s24d1r2_event"] != "none"
            ]
            cancels = [
                row for row in event_details if row.get("event") == "sequential_cancel"
            ]
            success = bool(
                len(trajectory) == horizon + 1
                and len(trace) == horizon
                and not any(bool(row.get("abnormal")) for row in trajectory)
                and all(
                    bool(row.get("computed_online"))
                    and bool(row.get("solver_success"))
                    for row in trace
                )
                and calibration_events == expected_calibration
                and sequence_events == expected_sequence
                and len(event_details) == 8
                and all(bool(row.get("passed")) for row in event_details)
                and len(cancels) == 4
                and all(
                    float(row["incremental_normalized_action_linf"])
                    <= 0.24 + 1e-12
                    and bool(row["criteria"]["online_cancel_margin"])
                    for row in cancels
                )
                and forbidden == 0
                and bool(trace[7]["r3c3t13s21_exact_calibration_net_zero"])
                and controller._active_issue is None
            )
            result.update(
                {
                    "success": success,
                    "completed": True,
                    "failure_class": "" if success else "runtime_or_execution_gate",
                    "failure_reason": "" if success else "invalid D1R2 full rollout",
                    "hidden_history_control_summary": {
                        "fresh_controller_actor": True,
                        "fresh_tsc_process": True,
                        "full_tsc_hidden_state_loaded_from_sprsina": True,
                        "controller_history_initialization": (
                            "current_visible_state_only_at_task_step_zero"
                        ),
                        "controller_integral_initialization": "zero",
                        "identification_only": True,
                        "safety_sentinel_only": True,
                        "sequence_index": controller.sequence_index,
                        "calibration_schedule_exact": (
                            calibration_events == expected_calibration
                        ),
                        "sequential_schedule_exact": (
                            sequence_events == expected_sequence
                        ),
                        "sequential_action_gates_passed": all(
                            bool(row.get("passed")) for row in event_details
                        ),
                        "online_cancel_margin_passed": all(
                            float(row["incremental_normalized_action_linf"])
                            <= 0.24 + 1e-12
                            for row in cancels
                        ),
                        "maximum_online_cancel_incremental_normalized_action_linf": max(
                            (
                                float(row["incremental_normalized_action_linf"])
                                for row in cancels
                            ),
                            default=0.0,
                        ),
                        "observation_horizon_steps": horizon,
                        "formal_horizon_steps": horizon,
                        "probe_trajectory_allowed_in_expert_dataset": False,
                        "phase_selection": copy.deepcopy(controller.phase_selection),
                        "visible_reference_manifold_digest": (
                            controller.visible_reference_manifold_digest
                        ),
                        "task_clock_starts_at_zero": True,
                        "formal_clock_shifted": False,
                        "hidden_wire_current_available_to_controller": False,
                        "full_wire_current_recorded_after_action_choice": True,
                        "online_action_computation": True,
                        "future_action_replay_used": False,
                        "future_measurement_used": False,
                        "source_action_used": False,
                        "source_coil_current_used": False,
                        "source_wire_current_used": False,
                        "current_run_future_used": False,
                        "pair_or_history_label_used": False,
                        "partition_label_available_to_controller": False,
                        "source_result_used": False,
                    },
                    "wall_time_s": time.time() - started,
                }
            )
            failed = not success
            return s24.s21.s16.s9.t11.t1._json_safe(result)
        except Exception as exc:
            action_failure = (
                copy.deepcopy(controller._last_failed_event)
                if controller is not None
                else None
            )
            result.update(
                {
                    "success": False,
                    "completed": True,
                    "failure_class": (
                        "structured_action_schedule_gate"
                        if action_failure is not None
                        else "runtime_or_environment"
                    ),
                    "failure_reason": repr(exc),
                    "action_failure_event": action_failure,
                    "trajectory": trajectory,
                    "controller_trace": trace,
                    "traceback": traceback.format_exc(),
                    "wall_time_s": time.time() - started,
                }
            )
            return s24.s21.s16.s9.t11.t1._json_safe(result)
        finally:
            runner = getattr(self.base.env, "runner", None)
            if runner is not None:
                runner.cleanup_episode_workspace(
                    failed=failed,
                    reason=(
                        "stage4_2r3c3t13s24d1r2_geometry_restored_"
                        "amplitude_safety_sentinel"
                    ),
                )


_RAY_ACTOR = None


def _ray_actor_class():
    global _RAY_ACTOR
    if _RAY_ACTOR is None:
        import ray

        @ray.remote(num_cpus=1, max_restarts=0)
        class Stage42R3C3T13S24D1R2Actor:
            def __init__(
                self,
                payload,
                library,
                bundle,
                worker_id,
                selector,
                lattice,
                calibration,
                dynamic,
                schedule,
            ):
                self.worker = LocalWorker(
                    payload,
                    library,
                    bundle,
                    worker_id,
                    selector,
                    lattice,
                    calibration,
                    dynamic,
                    schedule,
                )

            def evaluate(self, spec):
                return self.worker.evaluate(spec)

            def close(self):
                self.worker.close()
                return True

        _RAY_ACTOR = Stage42R3C3T13S24D1R2Actor
    return _RAY_ACTOR


def _read_raw(path: Path) -> dict[str, Any]:
    return s24.s21.s16.s9.t11.t1.r3c3.read_json_gz(path)


def _result_covered(path: Path, spec: Mapping[str, Any]) -> bool:
    if not path.is_file():
        return False
    try:
        result = _read_raw(path)
        horizon = int(spec["horizon_steps"])
        trajectory = result.get("trajectory") or []
        trace = result.get("controller_trace") or []
        identity = bool(
            result.get("completed")
            and result.get("stage") == STAGE
            and result.get("campaign_identity") == CAMPAIGN_IDENTITY
            and result.get("controller_revision") == CONTROLLER_REVISION
            and result.get("probe_primitive_revision") == CONTROLLER_REVISION
            and result.get("experiment_id") == spec["experiment_id"]
            and result.get("spec") == dict(spec)
            and 1 <= len(trajectory) <= horizon + 1
            and 0 <= len(trace) <= horizon
        )
        if not identity:
            return False
        if result.get("success"):
            return len(trajectory) == horizon + 1 and len(trace) == horizon
        return result.get("failure_class") in {
            "structured_action_schedule_gate",
            "runtime_or_environment",
            "runtime_or_execution_gate",
        }
    except Exception:
        return False


def _result_success(path: Path, spec: Mapping[str, Any]) -> bool:
    if not _result_covered(path, spec):
        return False
    result = _read_raw(path)
    return bool(result.get("success"))


def evaluate_specs(
    ctx: Context,
    specs: Sequence[dict[str, Any]],
    *,
    backend: str,
    resume: bool,
) -> dict[str, Any]:
    ctx.paths.raw.mkdir(parents=True, exist_ok=True)
    for spec in specs:
        path = ctx.paths.raw / f"{spec['experiment_id']}.json.gz"
        if path.exists() and not _result_covered(path, spec):
            raise ValueError(
                "D1R2 existing raw is corrupt or incompatible; refusing overwrite"
            )
    pending = [
        spec
        for spec in specs
        if not (
            resume
            and _result_covered(
                ctx.paths.raw / f"{spec['experiment_id']}.json.gz", spec
            )
        )
    ]
    if not resume and any(ctx.paths.raw.glob("*.json.gz")):
        raise ValueError("D1R2 fresh rollout requires empty raw directory")
    payloads = {str(spec["experiment_id"]): _payload(ctx, spec) for spec in specs}
    library, bundle, selector = s24._library_bundle_selector(ctx.base_s24_ctx)
    s21_ctx = ctx.base_s24_ctx.base_ctx
    lattice = s21_ctx.base_ctx.cfg["lattice_probe"]
    calibration = s21_ctx.base_ctx.cfg["active_calibration"]
    dynamic = s21_ctx.cfg["causal_model"]
    schedule = ctx.cfg["schedule_contract"]
    if backend == "serial":
        for index, spec in enumerate(pending):
            worker = LocalWorker(
                payloads[str(spec["experiment_id"])],
                library,
                bundle,
                f"stage42r3c3t13s24d1r2_serial_{index:04d}",
                selector,
                lattice,
                calibration,
                dynamic,
                schedule,
            )
            try:
                result = worker.evaluate(spec)
            finally:
                worker.close()
            _write_json_gz(
                ctx.paths.raw / f"{spec['experiment_id']}.json.gz", result
            )
            print(f"[T13S24D1R2] {index + 1}/{len(pending)}", flush=True)
    elif backend == "ray" and pending:
        import ray

        plan = s24.s21.s16.ensure_ray_worker_plan(
            ray,
            requested_workers=int(ctx.cfg["parallel"]["n_workers"]),
            pending_tasks=len(pending),
            ray_tmpdir=os.environ.get("RAY_TMPDIR")
            or ctx.cfg["storage"]["ray_tmpdir"],
            log_prefix="[T13S24D1R2]",
        )
        Actor = _ray_actor_class()
        completed = 0
        for batch_start in range(0, len(pending), plan.actor_count):
            batch = pending[batch_start : batch_start + plan.actor_count]
            actors, refs = [], {}
            for offset, spec in enumerate(batch):
                actor = Actor.remote(
                    payloads[str(spec["experiment_id"])],
                    library,
                    bundle,
                    f"stage42r3c3t13s24d1r2_{batch_start + offset:04d}",
                    selector,
                    lattice,
                    calibration,
                    dynamic,
                    schedule,
                )
                actors.append(actor)
                refs[actor.evaluate.remote(spec)] = spec
            try:
                while refs:
                    ready, _ = ray.wait(list(refs), num_returns=1, timeout=30.0)
                    if not ready:
                        print(
                            f"[T13S24D1R2] waiting {completed}/{len(pending)}",
                            flush=True,
                        )
                        continue
                    for ref in ready:
                        spec = refs.pop(ref)
                        try:
                            result = ray.get(ref)
                        except Exception as exc:
                            result = {
                                "schema_version": 1,
                                "stage": STAGE,
                                "campaign_identity": CAMPAIGN_IDENTITY,
                                "controller_revision": CONTROLLER_REVISION,
                                "probe_primitive_revision": CONTROLLER_REVISION,
                                "experiment_id": str(spec["experiment_id"]),
                                "spec": copy.deepcopy(spec),
                                "success": False,
                                "completed": True,
                                "failure_class": "runtime_or_environment",
                                "failure_reason": repr(exc),
                                "traceback": traceback.format_exc(),
                                "trajectory": [],
                                "controller_trace": [],
                            }
                        _write_json_gz(
                            ctx.paths.raw / f"{spec['experiment_id']}.json.gz",
                            result,
                        )
                        completed += 1
                        print(
                            f"[T13S24D1R2] {completed}/{len(pending)}", flush=True
                        )
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
        raise ValueError(f"unsupported D1R2 backend: {backend}")
    covered = sum(
        _result_covered(ctx.paths.raw / f"{spec['experiment_id']}.json.gz", spec)
        for spec in specs
    )
    successful = sum(
        _result_success(ctx.paths.raw / f"{spec['experiment_id']}.json.gz", spec)
        for spec in specs
    )
    return {
        "expected": len(specs),
        "pending_at_start": len(pending),
        "covered": covered,
        "successful": successful,
        "all_raw_covered": covered == len(specs),
        "all_successful": successful == len(specs),
    }


def _raw_inventory(paths: Paths) -> dict[str, Any]:
    rows = []
    digest = hashlib.sha256()
    for path in sorted(paths.raw.glob("*.json.gz")):
        sha = _sha256(path)
        size = path.stat().st_size
        digest.update(f"{path.name}\0{size}\0{sha}\n".encode())
        rows.append({"path": path.name, "bytes": size, "sha256": sha})
    return {
        "count": len(rows),
        "total_bytes": sum(int(row["bytes"]) for row in rows),
        "digest": digest.hexdigest(),
        "files": rows,
    }


def _forbidden_trace_count(trace: Sequence[Mapping[str, Any]]) -> int:
    keys = (
        "future_measurement_used",
        "hidden_wire_used",
        "source_action_used",
        "source_coil_current_used",
        "source_wire_current_used",
        "current_run_future_used",
        "pair_or_history_label_used",
        "source_result_used",
        "future_probe_schedule_available_to_underlying_controller",
        "r3c3t13s21_partition_label_used",
        "r3c3t13s24_pair_history_partition_label_used",
        "r3c3t13s24_delay_slew_target_id_label_used",
        "r3c3t13s24_source_or_matched_baseline_used",
        "r3c3t13s24_future_measurement_used",
        "r3c3t13s24_future_executed_action_used",
        "r3c3t13s24_hidden_wire_current_used",
        "r3c3t13s24_schedule_available_to_underlying_controller",
        "r3c3t13s24d1r2_source_selection_label_used",
        "r3c3t13s24d1r2_pair_history_partition_label_used",
        "r3c3t13s24d1r2_source_outcome_used",
        "r3c3t13s24d1r2_future_measurement_used",
        "r3c3t13s24d1r2_future_executed_action_used",
        "r3c3t13s24d1r2_hidden_wire_current_used",
        "r3c3t13s24d1r2_schedule_available_to_underlying_controller",
    )
    return sum(any(bool(row.get(key)) for key in keys) for row in trace)


def _execution_audit(
    ctx: Context, specs: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    state_map = s24.s21.s13._source_state_map(
        ctx.base_s24_ctx.base_ctx.base_ctx.base_ctx
    )
    base_source_ctx = (
        ctx.base_s24_ctx.base_ctx.base_ctx.base_ctx.base_ctx.base_ctx.base_ctx
        .source_ctx.source_ctx
    )
    expected_calibration = [
        "calibration_issue",
        "calibration_cancel",
        "calibration_issue",
        "calibration_cancel",
        "calibration_issue",
        "calibration_cancel",
        "calibration_issue",
        "calibration_cancel",
    ]
    expected_sequence = [
        "sequential_issue",
        "sequential_cancel",
        "sequential_issue",
        "sequential_cancel",
        "sequential_issue",
        "sequential_cancel",
        "sequential_issue",
        "sequential_cancel",
    ]
    rows: list[dict[str, Any]] = []
    for spec in specs:
        path = ctx.paths.raw / f"{spec['experiment_id']}.json.gz"
        base_row = {
            "experiment_id": spec["experiment_id"],
            "pair_id": spec["pair_id"],
            "history_member": spec["history_member"],
            "sequence_index": int(spec["s24_sequence_index"]),
            "horizon_steps": int(spec["horizon_steps"]),
        }
        if not path.is_file():
            rows.append(
                {
                    **base_row,
                    "classification": "runtime_or_raw_error",
                    "failure_reason": "missing raw",
                    "passed": False,
                }
            )
            continue
        try:
            result = _read_raw(path)
        except Exception as exc:
            rows.append(
                {
                    **base_row,
                    "classification": "runtime_or_raw_error",
                    "failure_reason": f"strict parse failed: {exc!r}",
                    "passed": False,
                }
            )
            continue
        identity_pass = bool(
            result.get("completed")
            and result.get("stage") == STAGE
            and result.get("campaign_identity") == CAMPAIGN_IDENTITY
            and result.get("controller_revision") == CONTROLLER_REVISION
            and result.get("probe_primitive_revision") == CONTROLLER_REVISION
            and result.get("experiment_id") == spec["experiment_id"]
            and result.get("spec") == dict(spec)
        )
        trajectory = result.get("trajectory") or []
        trace = result.get("controller_trace") or []
        if not identity_pass:
            rows.append(
                {
                    **base_row,
                    "strict_parse_pass": True,
                    "identity_pass": False,
                    "classification": "runtime_or_raw_error",
                    "failure_reason": "raw identity/spec mismatch",
                    "passed": False,
                }
            )
            continue
        if not result.get("success"):
            event = result.get("action_failure_event")
            structured = bool(
                result.get("failure_class") == "structured_action_schedule_gate"
                and isinstance(event, dict)
                and not bool(event.get("passed"))
                and event.get("event") in {"sequential_issue", "sequential_cancel"}
                and len(trajectory) == len(trace) + 1
            )
            criteria = (event or {}).get("criteria") or {}
            margin_failure = bool(
                (event or {}).get("event") == "sequential_cancel"
                and criteria.get("online_cancel_margin") is False
            )
            original_action_failure = bool(
                structured
                and any(
                    criteria.get(key) is False
                    for key in criteria
                    if key != "online_cancel_margin"
                )
            )
            rows.append(
                {
                    **base_row,
                    "strict_parse_pass": True,
                    "identity_pass": True,
                    "result_success": False,
                    "structured_action_failure": structured,
                    "online_margin_failure": margin_failure,
                    "original_action_gate_failure": original_action_failure,
                    "failure_event": copy.deepcopy(event),
                    "classification": (
                        "action_schedule_design_failure"
                        if structured
                        else "runtime_or_environment_error"
                    ),
                    "failure_reason": str(result.get("failure_reason", "")),
                    "passed": False,
                }
            )
            continue
        horizon = int(spec["horizon_steps"])
        try:
            payload = _payload(ctx, spec)
            currents = np.asarray(
                [row["currents_a_tsc"] for row in trajectory], dtype=float
            )
            actions = np.asarray(
                [row["action_norm_tsc"] for row in trace], dtype=float
            )
            recorded_actions = np.asarray(
                [row["action_norm_tsc"] for row in trajectory[1:]], dtype=float
            )
            minimum, maximum = s24.s21.s13._current_limits_tsc(payload)
            center, half = 0.5 * (minimum + maximum), 0.5 * (maximum - minimum)
            utilization = float(np.max(np.abs((currents - center) / half)))
            restart = s24.s21.s16.s9.t11.t1.r3b._control_row(
                base_source_ctx,
                result,
                state_map[str(spec["state_generation_experiment_id"])],
            )
            phase = s24.s21.s16.s9.t11.t1.r3c1._phase_trace_valid(result)
            calibration = s24.s21._dynamic_calibration_trace_audit(
                result, ctx.base_s24_ctx.base_ctx.cfg
            )
            calibration_events = [
                row.get("r3c3t13s16_lattice_event")
                for row in trace
                if row.get("r3c3t13s16_lattice_event") != "none"
            ]
            sequence_events = [
                row.get("r3c3t13s24d1r2_event")
                for row in trace
                if row.get("r3c3t13s24d1r2_event") != "none"
            ]
            event_details = [
                row["r3c3t13s24d1r2_event_detail"]
                for row in trace
                if row.get("r3c3t13s24d1r2_event") != "none"
            ]
            issues = [
                row for row in event_details if row.get("event") == "sequential_issue"
            ]
            cancels = [
                row for row in event_details if row.get("event") == "sequential_cancel"
            ]
            forbidden = _forbidden_trace_count(trace)
            runtime_pass = bool(
                len(trajectory) == horizon + 1
                and len(trace) == horizon
                and np.all(np.isfinite(currents))
                and np.all(np.isfinite(actions))
                and not any(bool(row.get("abnormal")) for row in trajectory)
            )
            restart_pass = bool(
                restart.get("fresh_controller")
                and restart.get("fresh_tsc_process")
                and restart.get("initial_restart_exact")
                and restart.get("controller_trace_causal")
            )
            action_trace_pass = bool(
                all(
                    bool(row.get("computed_online"))
                    and bool(row.get("solver_success"))
                    for row in trace
                )
                and calibration_events == expected_calibration
                and sequence_events == expected_sequence
                and len(issues) == len(cancels) == 4
                and all(bool(row.get("passed")) for row in event_details)
                and all(
                    bool(row.get("criteria", {}).get("online_cancel_margin"))
                    and float(row["incremental_normalized_action_linf"])
                    <= 0.24 + 1e-12
                    for row in cancels
                )
                and forbidden == 0
                and bool(phase["passed"])
                and np.array_equal(actions, recorded_actions)
                and float(np.max(np.abs(actions))) <= 1.0 + 1e-12
            )
            passed = bool(
                runtime_pass
                and restart_pass
                and action_trace_pass
                and calibration["passed"]
                and utilization
                <= float(ctx.cfg["schedule_contract"]["maximum_current_utilization"])
                + 1e-12
            )
            rows.append(
                {
                    **base_row,
                    "strict_parse_pass": True,
                    "identity_pass": True,
                    "result_success": True,
                    "runtime_full_horizon_pass": runtime_pass,
                    "restart_pass": restart_pass,
                    "phase_causality_pass": bool(phase["passed"]),
                    "calibration_pass": bool(calibration["passed"]),
                    "action_trace_pass": action_trace_pass,
                    "issue_event_count": len(issues),
                    "cancel_event_count": len(cancels),
                    "issue_event_pass_count": sum(
                        bool(row.get("passed")) for row in issues
                    ),
                    "cancel_event_pass_count": sum(
                        bool(row.get("passed")) for row in cancels
                    ),
                    "cancel_margin_pass_count": sum(
                        bool(row.get("criteria", {}).get("online_cancel_margin"))
                        for row in cancels
                    ),
                    "maximum_cancel_incremental_normalized_action_linf": max(
                        (
                            float(row["incremental_normalized_action_linf"])
                            for row in cancels
                        ),
                        default=0.0,
                    ),
                    "maximum_current_utilization": utilization,
                    "forbidden_trace_count": forbidden,
                    "formal_contract_pass_diagnostic": bool(
                        restart.get("formal_contract_pass")
                    ),
                    "classification": "pass" if passed else "runtime_or_audit_error",
                    "passed": passed,
                }
            )
        except Exception as exc:
            rows.append(
                {
                    **base_row,
                    "strict_parse_pass": True,
                    "identity_pass": True,
                    "result_success": True,
                    "classification": "runtime_or_audit_error",
                    "failure_reason": repr(exc),
                    "passed": False,
                }
            )
    success_rows = [row for row in rows if row.get("result_success")]
    action_failures = [
        row
        for row in rows
        if row.get("classification") == "action_schedule_design_failure"
    ]
    runtime_failures = [
        row
        for row in rows
        if row.get("classification")
        not in {"pass", "action_schedule_design_failure"}
    ]
    passed = len(rows) == len(specs) and all(bool(row.get("passed")) for row in rows)
    if passed:
        route = ctx.cfg["routes"]["pass"]
    elif runtime_failures:
        route = ctx.cfg["routes"]["runtime_fail"]
    else:
        route = ctx.cfg["routes"]["action_fail"]
    return {
        "schema_version": 1,
        "stage": STAGE,
        "expected": len(specs),
        "actual_rows": len(rows),
        "strict_parse_count": sum(bool(row.get("strict_parse_pass")) for row in rows),
        "identity_pass_count": sum(bool(row.get("identity_pass")) for row in rows),
        "success_count": len(success_rows),
        "pass_count": sum(bool(row.get("passed")) for row in rows),
        "action_schedule_failure_count": len(action_failures),
        "runtime_or_audit_failure_count": len(runtime_failures),
        "full_horizon_pass_count": sum(
            bool(row.get("runtime_full_horizon_pass")) for row in rows
        ),
        "restart_pass_count": sum(bool(row.get("restart_pass")) for row in rows),
        "causality_pass_count": sum(
            bool(row.get("phase_causality_pass")) for row in rows
        ),
        "calibration_pass_count": sum(
            bool(row.get("calibration_pass")) for row in rows
        ),
        "issue_event_count": sum(int(row.get("issue_event_count", 0)) for row in rows),
        "cancel_event_count": sum(int(row.get("cancel_event_count", 0)) for row in rows),
        "cancel_margin_pass_count": sum(
            int(row.get("cancel_margin_pass_count", 0)) for row in rows
        ),
        "forbidden_trace_count": sum(
            int(row.get("forbidden_trace_count", 0)) for row in rows
        ),
        "formal_tracking_pass_count_diagnostic_only": sum(
            bool(row.get("formal_contract_pass_diagnostic")) for row in rows
        ),
        "maximum_cancel_incremental_normalized_action_linf": max(
            (
                float(row.get("maximum_cancel_incremental_normalized_action_linf", 0.0))
                for row in rows
            ),
            default=0.0,
        ),
        "maximum_current_utilization": max(
            (float(row.get("maximum_current_utilization", 0.0)) for row in rows),
            default=0.0,
        ),
        "route": route,
        "passed": passed,
        "rows": rows,
    }


def run_rollout(ctx: Context, *, backend: str, resume: bool) -> dict[str, Any]:
    state = _read_json(ctx.paths.state)
    if state.get("phase_status") != "offline_ready" or state.get("finished"):
        raise ValueError("D1R2 rollout requires open offline-ready state")
    specs = _saved_specs(ctx)
    execution = evaluate_specs(ctx, specs, backend=backend, resume=resume)
    audit = _execution_audit(ctx, specs)
    inventory = _raw_inventory(ctx.paths)
    final = {
        "schema_version": 1,
        "stage": STAGE,
        "campaign_identity": CAMPAIGN_IDENTITY,
        "controller_revision": CONTROLLER_REVISION,
        "package_revision": PACKAGE_REVISION,
        "execution": execution,
        "execution_audit": audit,
        "raw_inventory": inventory,
        "formal_timing_unchanged": True,
        "formal_tracking_is_diagnostic_only": True,
        "probe_trajectories_allowed_in_expert_dataset": False,
        "full_replacement_campaign_authorized": bool(audit["passed"]),
        "mpc_or_rl_authorized": False,
        "route": audit["route"],
        "passed": bool(audit["passed"]),
    }
    _write_json(ctx.paths.analysis / "internal_execution_audit.json", audit)
    _write_json(ctx.paths.final, final)
    state.update(
        {
            "phase_status": "sentinel_complete" if audit["passed"] else "sentinel_failed",
            "finished": True,
            "primary_pass": bool(audit["passed"]),
            "real_tsc_executed": inventory["count"] > 0,
            "new_raw_count": int(inventory["count"]),
            "stop_reason": "" if audit["passed"] else str(audit["route"]),
            "verdict": {"route": audit["route"], "passed": bool(audit["passed"])},
        }
    )
    _write_json(ctx.paths.state, state)
    manifest = _read_json(ctx.paths.manifest)
    manifest.update(
        {
            "raw_inventory": inventory,
            "final_result_sha256": _sha256(ctx.paths.final),
            "internal_execution_audit_sha256": _sha256(
                ctx.paths.analysis / "internal_execution_audit.json"
            ),
            "finished": True,
            "route": audit["route"],
            "passed": bool(audit["passed"]),
        }
    )
    _write_json(ctx.paths.manifest, manifest)
    return final


def run_postprocess(ctx: Context) -> dict[str, Any]:
    if not ctx.paths.state.is_file() or not ctx.paths.final.is_file():
        raise ValueError("D1R2 postprocess requires completed sentinel outputs")
    specs = _saved_specs(ctx)
    audit = _execution_audit(ctx, specs)
    inventory = _raw_inventory(ctx.paths)
    output = {
        "schema_version": 1,
        "stage": STAGE,
        "phase": "server_internal_raw_recomputation",
        "raw_inventory": inventory,
        "execution_audit": audit,
        "passed": bool(
            inventory["count"] == int(ctx.cfg["execution_gate"]["raw_files_required"])
            and audit["passed"]
        ),
        "route": audit["route"],
    }
    _write_json(ctx.paths.analysis / "server_internal_raw_recomputation.json", output)
    return output


def execute(
    ctx: Context, *, command: str, backend: str, resume: bool
) -> dict[str, Any]:
    if command == "offline":
        if resume:
            raise ValueError("D1R2 offline cannot resume")
        return prepare_offline(ctx)
    if command == "rollout":
        return run_rollout(ctx, backend=backend, resume=resume)
    if command == "postprocess":
        return run_postprocess(ctx)
    if command == "all":
        if resume:
            if not ctx.paths.state.is_file():
                raise ValueError("D1R2 resume requires existing frozen state")
        else:
            prepare_offline(ctx)
        final = run_rollout(ctx, backend=backend, resume=resume)
        internal = run_postprocess(ctx)
        return {"final": final, "postprocess": internal}
    raise ValueError(f"unsupported D1R2 command: {command}")


def self_test(config_path: Path) -> dict[str, Any]:
    config_path = config_path.expanduser().resolve()
    cfg = _read_json(config_path)
    _validate_config(cfg, config_path)
    sample = {
        "experiment_id": "s42r3c3t13s24d2_example",
        "environment_variant": "stage4_2r3c3t13s24d2_s42r3c3t13s24d2_example",
        "kind": cfg["identity_normalization"]["old_kind"],
        "phase": cfg["identity_normalization"]["old_phase"],
        "s24d2_online_cancel_margin_gate": 0.24,
        "unchanged": {"action": [0.29, -0.29]},
    }
    normalized = _normalise_spec(sample, cfg)
    return {
        "schema_version": 1,
        "stage": STAGE,
        "identity_roundtrip_exact": _reverse_normalisation(normalized, cfg) == sample,
        "expected_real_tsc_rollouts": int(cfg["spec_contract"]["expected_specs"]),
        "maximum_online_cancel_incremental_normalized_action_linf": float(
            cfg["schedule_contract"][
                "maximum_online_cancel_incremental_normalized_action_linf"
            ]
        ),
        "real_tsc_executed": False,
        "passed": _reverse_normalisation(normalized, cfg) == sample,
    }


def _source_kwargs(args: argparse.Namespace) -> dict[str, Path]:
    return {
        "source_stage42r3b_run": args.source_stage42r3b_run,
        "source_stage42r3c3_run": args.source_stage42r3c3_run,
        "source_stage42r3c3_bank_dir": args.source_stage42r3c3_bank_dir,
        "source_stage42r3c3t1_run": args.source_stage42r3c3t1_run,
        "source_stage42r3c3t1_audit_dir": args.source_stage42r3c3t1_audit_dir,
        "source_stage42r3c3t3_controller_bank": (
            args.source_stage42r3c3t3_controller_bank
        ),
        "q1_run": args.q1_run,
        "q2_run": args.q2_run,
        "q1_audit": args.q1_audit,
        "q2_audit": args.q2_audit,
        "r3b_server_audit": args.r3b_server_audit,
        "r3b_snapshot_checks": args.r3b_snapshot_checks,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--source-d1r1-output", type=Path, required=True)
    parser.add_argument("--source-d1r1-log", type=Path, required=True)
    parser.add_argument("--source-s21-run", type=Path, required=True)
    parser.add_argument("--source-s23r1-output", type=Path, required=True)
    parser.add_argument("--source-stage42r3b-run", type=Path, required=True)
    parser.add_argument("--source-stage42r3c3-run", type=Path, required=True)
    parser.add_argument("--source-stage42r3c3-bank-dir", type=Path, required=True)
    parser.add_argument("--source-stage42r3c3t1-run", type=Path, required=True)
    parser.add_argument("--source-stage42r3c3t1-audit-dir", type=Path, required=True)
    parser.add_argument("--source-stage42r3c3t3-controller-bank", type=Path, required=True)
    parser.add_argument("--q1-run", type=Path, required=True)
    parser.add_argument("--q2-run", type=Path, required=True)
    parser.add_argument("--q1-audit", type=Path, required=True)
    parser.add_argument("--q2-audit", type=Path, required=True)
    parser.add_argument("--r3b-server-audit", type=Path, required=True)
    parser.add_argument("--r3b-snapshot-checks", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument(
        "--command", choices=("offline", "rollout", "postprocess", "all"), required=True
    )
    parser.add_argument("--backend", choices=("serial", "ray"), default="ray")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        print(json.dumps(self_test(args.config), sort_keys=True, indent=2))
        return
    ctx = load_config(
        args.config,
        source_d1r1_output=args.source_d1r1_output,
        source_d1r1_log=args.source_d1r1_log,
        source_s21_run=args.source_s21_run,
        source_s23r1_output=args.source_s23r1_output,
        run_dir=args.run_dir,
        **_source_kwargs(args),
    )
    result = execute(ctx, command=args.command, backend=args.backend, resume=args.resume)
    print(json.dumps(result, sort_keys=True, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
