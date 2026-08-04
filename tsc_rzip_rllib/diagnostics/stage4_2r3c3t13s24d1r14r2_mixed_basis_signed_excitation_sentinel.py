"""Stage4.2R3c3T13S24D1R14R2 mixed-basis signed-excitation sentinel."""

from __future__ import annotations

import argparse
import copy
from dataclasses import dataclass
from decimal import Decimal
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
    stage4_2r3c3t13s24d1r13_zero_increment_deconfounding_sentinel as d1r13,
)


d1r11 = d1r13.d1r11
SCHEMA_VERSION = 1
STAGE = "Stage4.2R3c3T13S24D1R14R2"
RUN_NAME = "stage4_2r3c3t13s24d1r14r2_mixed_basis_signed_excitation_sentinel"
CAMPAIGN_IDENTITY = "mixed_basis_signed_excitation_safety_geometry_sentinel_v1"
CONTROLLER_REVISION = "mixed_basis_signed_excitation_v42r3c3t13s24d1r14r2_v1"
N_COILS = 14
PREFIX_END = 10
ISSUE_STEP = 10
CANCEL_STEP = 11
ZERO_AFTER = 12
DIRECTIONS = (
    "pooled_mixed_0",
    "pooled_mixed_1",
    "pooled_mixed_2",
    "pooled_mixed_3",
)
EXPECTED_CALIBRATION = [
    "calibration_issue",
    "calibration_cancel",
    "calibration_issue",
    "calibration_cancel",
    "calibration_issue",
    "calibration_cancel",
    "calibration_issue",
    "calibration_cancel",
]


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _sha256(path: Path) -> str:
    return d1r13._sha256(path)


def _digest(value: Any) -> str:
    return d1r13._digest(value)


def _matrix_digest(value: np.ndarray) -> str:
    matrix = np.ascontiguousarray(np.asarray(value, dtype="<f8"))
    return hashlib.sha256(matrix.tobytes(order="C")).hexdigest()


def _read_json(path: Path) -> Any:
    return d1r13._read_json(path)


def _write_json(path: Path, value: Any) -> None:
    d1r13._write_json(path, value)


def _write_json_gz(path: Path, value: Any) -> None:
    d1r13._write_json_gz(path, value)


def _read_gz(path: Path) -> dict[str, Any]:
    return d1r13._read_gz(path)


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
    )


@dataclass(frozen=True)
class Context:
    cfg: dict[str, Any]
    config_path: Path
    source_ctx: Any
    source_d1r13_run: Path
    source_d1r13_audit: Path
    source_r1a_output: Path
    paths: Paths


def _validate_config(cfg: Mapping[str, Any], path: Path) -> None:
    root = _project_root()
    exact = {
        "schema_version": 1,
        "stage": STAGE,
        "run_name": RUN_NAME,
        "campaign_identity": CAMPAIGN_IDENTITY,
        "controller_revision": CONTROLLER_REVISION,
        "package_revision": "r42r3c3t13s24d1r14r2_mixed_basis_signed_excitation_v1",
    }
    for key, value in exact.items():
        if cfg.get(key) != value:
            raise ValueError(f"D1R14R2 frozen {key} changed")
    for key in ("design_document", "source_d1r13_config"):
        source = (root / str(cfg[key])).resolve()
        if root not in source.parents or not source.is_file():
            raise ValueError(f"D1R14R2 {key} is outside package")
        if _sha256(source) != str(cfg[f"{key}_sha256"]):
            raise ValueError(f"D1R14R2 {key} hash changed")
    r1a = cfg["source_r1a_contract"]
    expected_r1a = {
        "output_name": "stage4_2r3c3t13s24d1r14r1a_quantization_margin_preflight_20260804_b8040b6_v1",
        "implementation_checkpoint": "58912e7",
        "package_checkpoint": "b8040b6",
        "package_revision": "r42r3c3t13s24d1r14r1a_quantization_margin_preflight_v1",
        "config": "configs/stage4_2r3c3t13s24d1r14r1a_quantization_margin_preflight_v1.json",
        "config_sha256": "e767d8c5f1e5f3434e247492259a3dbb7ea9de0849cc0d189f756e301545664d",
        "implementation": "docs/codex/audit_tools/stage4_2r3c3t13s24d1r14r1a_quantization_margin_preflight.py",
        "implementation_sha256": "ee9a094f3b6e58dc30e9e4e7ecd819fa583a3a196eb9205ae242f7b93d09d5c8",
        "detailed_filename": "stage4_2r3c3t13s24d1r14r1a_detailed_v1.json",
        "detailed_sha256": "a9ffc98b798d4735d7302b1ca4407dbc60266228007d82d34418a291df2b0e8d",
        "summary_filename": "stage4_2r3c3t13s24d1r14r1a_summary_v1.json",
        "summary_sha256": "77194861b0406257d055b5ebe0e087b9f9c8222e76600fa443de9d34e7fc682f",
        "manifest_filename": "stage4_2r3c3t13s24d1r14r1a_manifest_v1.json",
        "manifest_sha256": "d6b4c53c46b8948d979d3eaee1861885f61d33ac70097a7576110361f0bafa87",
        "required_route": "QUANTIZATION_MARGIN_PREFLIGHT_PASS_R2_SENTINEL_DESIGN_REQUIRED",
        "required_static_issue_pass_count": 64,
        "required_static_issue_count": 64,
        "required_source_raw_count": 72,
        "required_source_raw_bytes": 2239479,
        "required_source_raw_digest": "0433a64ebaea73186bb193d5102686721497219acfcbecbb721e7fad62e8d7a3",
        "required_source_final_sha256": "1a65a37c301ba52325f586e0948b0b94b1266c540e2f2a332e5bc02df60a7da2",
        "required_source_independent_audit_sha256": "8e7d3d045477502c1060fe621f2c43235e1d530b59c5d22849337dd20aac3eae",
        "required_online_cancellation_proved": False,
        "required_new_raw_count": 0,
        "required_tsc_executed": False,
    }
    if dict(r1a) != expected_r1a:
        raise ValueError("D1R14R2 immutable R1A contract changed")
    for key in ("config", "implementation"):
        source_path = (root / str(r1a[key])).resolve()
        if root not in source_path.parents or not source_path.is_file():
            raise ValueError(f"D1R14R2 R1A {key} is outside package")
        if _sha256(source_path) != str(r1a[f"{key}_sha256"]):
            raise ValueError(f"D1R14R2 R1A {key} hash changed")
    source = cfg["source_contract"]
    expected_source = {
        "d1r13_execution_package_checkpoint": "df3910f",
        "d1r13_independent_audit_checkpoint": "23148e9",
        "d1r13_raw_count": 8,
        "d1r13_raw_total_bytes": 241738,
        "d1r13_raw_inventory_digest": "f9b4dd9259736ebe2d26f9fcfd06bb0497be69a886de7ecc8d359009992f1c0a",
        "d1r13_final_result_sha256": "f8570641d5dd4e41962660712790bcd60c4ce8bf6a33e1f360235ffc8c69b9ca",
        "d1r13_stage_state_sha256": "7e72c8975a8d0ee0ad325cd5ac0c44340a335d0d22c2f5cd8c8e40790e19dd7d",
        "d1r13_stage_manifest_sha256": "2809e7e261dfb88404a96b0a89fb60b74a834f578e98c707529cb059d5a0d3fe",
        "d1r13_independent_audit_sha256": "bd778f42d8755e8b45d572e895cefb171acad8f0fa688b238fd1acb3402e5ee4",
        "d1r13_final_route": "ZERO_INCREMENT_DECONFOUNDING_SENTINEL_PASS_EXCITATION_SENTINEL_DESIGN_REQUIRED",
        "d1r11_training_raw_count": 600,
        "d1r11_training_raw_total_bytes": 35511922,
        "d1r11_training_raw_inventory_digest": "8812d9fb0a5cb5a8b8309e17985bd85d180a82bbb0f08c02105fb1a749c7c0e7",
    }
    if dict(source) != expected_source:
        raise ValueError("D1R14R2 immutable source contract changed")
    selected = list(map(str, cfg["selected_source_d1r13_experiment_ids"]))
    expected_selected = [
        "s42r3c3_7dca3ca415ee7fae3748",
        "s42r3c3_a6b6eeea6d48d7a79585",
        "s42r3c3_4571fd0668fa016c2636",
        "s42r3c3_44878cc615a1d3ea18b9",
        "s42r3c3_3a3dc1fe08a9a6984e8c",
        "s42r3c3_f96b02b6e296f16b840c",
        "s42r3c3_b72b7cdb52af15409a54",
        "s42r3c3_39edf644f2fdf0ee6c5a",
    ]
    if selected != expected_selected or len(set(selected)) != 8:
        raise ValueError("D1R14R2 selected D1R13 identities changed")
    controller = cfg["controller_contract"]
    requested_matrix = np.asarray(
        controller["requested_coordinate_matrix_columns"], dtype=float
    )
    expected_controller = {
        "delegated_last_task_step": 9,
        "issue_task_step": 10,
        "cancel_task_step": 11,
        "zero_after_cancel_first_task_step": 12,
        "zero_action_width": 14,
        "direction_names": list(DIRECTIONS),
        "requested_coordinate_matrix_columns": requested_matrix.tolist(),
        "requested_matrix_float64_le_c_sha256": "c8cd62c00c1f60b46312927789659657dc8cc35717533193433b0e398c1ec94c",
        "baseline_count": 8,
        "signed_probe_count": 64,
        "expected_task_count": 72,
        "expected_baseline_post_prefix_action_count": 208,
        "expected_probe_issue_count": 64,
        "expected_probe_cancel_count": 64,
        "expected_probe_zero_after_cancel_action_count": 1536,
        "maximum_incremental_normalized_action_linf": 0.25,
        "maximum_online_cancel_incremental_linf": 0.24,
        "maximum_total_normalized_action_abs": 1.0,
        "maximum_current_utilization": 0.55,
        "minimum_desired_applied_current_cosine": 0.98,
        "maximum_relative_off_basis_residual": 0.10,
        "require_exact_stored_center_cancellation": True,
        "require_exact_zero_target_jump_net": True,
        "require_exact_source_prefix": True,
        "require_fresh_baseline_reproduction": True,
        "forbid_future_r17_controller_execution": True,
    }
    if (
        requested_matrix.shape != (4, 4)
        or not np.all(np.isfinite(requested_matrix))
        or _matrix_digest(requested_matrix)
        != controller["requested_matrix_float64_le_c_sha256"]
        or dict(controller) != expected_controller
    ):
        raise ValueError("D1R14R2 controller contract changed")
    geometry = cfg["response_geometry"]
    expected_geometry = {
        "visible_output_names": ["R", "Z", "vR", "vZ", "Ip"],
        "visible_output_scales": [0.03, 0.03, 0.1, 0.1, 10000.0],
        "first_response_state": 11,
        "minimum_odd_peak_normalized_outputs5": 0.005,
        "maximum_even_to_odd_peak_ratio": 0.5,
        "rank_relative_tolerance": 1e-10,
        "required_rank": 4,
        "maximum_condition_number": 20.0,
        "normalize_columns_to_unit_l2": True,
        "matched_hidden_history_response_is_report_only": True,
    }
    if dict(geometry) != expected_geometry:
        raise ValueError("D1R14R2 response geometry changed")
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
        raise ValueError("D1R14R2 formal timing changed")
    if int(cfg["parallel"]["n_workers"]) != 72:
        raise ValueError("D1R14R2 Ray capacity changed")
    if cfg["routes"] != {
        "offline_fail": "MIXED_BASIS_SENTINEL_OFFLINE_FAIL_NO_TSC",
        "runtime_fail": "MIXED_BASIS_SENTINEL_RUNTIME_OR_PREFIX_FAIL_STOP",
        "safety_fail": "MIXED_BASIS_SENTINEL_ACTION_SAFETY_FAIL_REDESIGN_REQUIRED",
        "geometry_fail": "MIXED_BASIS_SENTINEL_RESPONSE_GEOMETRY_FAIL_REDESIGN_REQUIRED",
        "pass": "MIXED_BASIS_SENTINEL_PASS_TIME_DISTRIBUTED_ID_DESIGN_REQUIRED",
    }:
        raise ValueError("D1R14R2 routes changed")
    if (
        not bool(cfg["identification_only"])
        or not bool(cfg["formal_tracking_diagnostic_only"])
        or bool(cfg["probe_trajectories_allowed_in_expert_dataset"])
        or bool(cfg["bc_dagger_or_rl_allowed"])
    ):
        raise ValueError("D1R14R2 scope changed")
    expected_path = root / "configs/stage4_2r3c3t13s24d1r14r2_mixed_basis_signed_excitation_sentinel_370ms.json"
    if path.resolve() != expected_path.resolve():
        raise ValueError("D1R14R2 config path changed")


def load_config(
    config_path: Path,
    *,
    source_d1r13_run: Path,
    source_d1r13_audit: Path,
    source_r1a_output: Path,
    source_d1r11_run: Path,
    run_dir: Path,
    source_s21_run: Path,
    source_s23r1_output: Path,
    source_s24_run: Path,
    source_d1r9_v1: Path,
    source_d1r9_v2: Path,
    source_d1r10_run: Path,
    source_d1r10_audit: Path,
    **source_kwargs: Path,
) -> Context:
    config_path = config_path.expanduser().resolve()
    cfg = _read_json(config_path)
    _validate_config(cfg, config_path)
    source_d1r13_run = source_d1r13_run.expanduser().resolve()
    source_d1r13_audit = source_d1r13_audit.expanduser().resolve()
    source_r1a_output = source_r1a_output.expanduser().resolve()
    source_cfg = (_project_root() / str(cfg["source_d1r13_config"])).resolve()
    source_ctx = d1r13.load_config(
        source_cfg,
        source_d1r11_run=source_d1r11_run,
        source_s21_run=source_s21_run,
        source_s23r1_output=source_s23r1_output,
        source_s24_run=source_s24_run,
        source_d1r9_v1=source_d1r9_v1,
        source_d1r9_v2=source_d1r9_v2,
        source_d1r10_run=source_d1r10_run,
        source_d1r10_audit=source_d1r10_audit,
        run_dir=source_d1r13_run,
        **source_kwargs,
    )
    if source_ctx.paths.run_dir != source_d1r13_run:
        raise ValueError("D1R14R2 source D1R13 run path changed")
    return Context(
        cfg=cfg,
        config_path=config_path,
        source_ctx=source_ctx,
        source_d1r13_run=source_d1r13_run,
        source_d1r13_audit=source_d1r13_audit,
        source_r1a_output=source_r1a_output,
        paths=_paths(run_dir),
    )


def _raw_inventory(raw_dir: Path) -> dict[str, Any]:
    return d1r13._raw_inventory(raw_dir)


def _source_d1r13_results(ctx: Context) -> list[dict[str, Any]]:
    output = []
    for experiment_id in map(str, ctx.cfg["selected_source_d1r13_experiment_ids"]):
        path = ctx.source_ctx.paths.raw / f"{experiment_id}.json.gz"
        result = _read_gz(path)
        if (
            not result.get("success")
            or not result.get("completed")
            or result.get("stage") != d1r13.STAGE
            or result.get("campaign_identity") != d1r13.CAMPAIGN_IDENTITY
            or result.get("experiment_id") != experiment_id
            or not result.get("spec", {}).get("d1r13_zero_action_required")
        ):
            raise ValueError(f"D1R14R2 invalid selected D1R13 source: {experiment_id}")
        output.append(result)
    return output


def _authenticate_r1a(ctx: Context) -> dict[str, Any]:
    contract = ctx.cfg["source_r1a_contract"]
    root = _project_root()
    paths = {
        "detailed": ctx.source_r1a_output / str(contract["detailed_filename"]),
        "summary": ctx.source_r1a_output / str(contract["summary_filename"]),
        "manifest": ctx.source_r1a_output / str(contract["manifest_filename"]),
    }
    expected_hashes = {
        "detailed": str(contract["detailed_sha256"]),
        "summary": str(contract["summary_sha256"]),
        "manifest": str(contract["manifest_sha256"]),
    }
    hashes = {name: _sha256(path) for name, path in paths.items()}
    config_path = (root / str(contract["config"])).resolve()
    implementation_path = (root / str(contract["implementation"])).resolve()
    if (
        ctx.source_r1a_output.name != str(contract["output_name"])
        or any(not path.is_file() for path in paths.values())
        or hashes != expected_hashes
        or _sha256(config_path) != str(contract["config_sha256"])
        or _sha256(implementation_path) != str(contract["implementation_sha256"])
    ):
        raise ValueError("D1R14R2 immutable R1A source changed")
    detailed = _read_json(paths["detailed"])
    summary = _read_json(paths["summary"])
    manifest = _read_json(paths["manifest"])
    source = detailed.get("source_d1r14_authentication") or {}
    inventory = source.get("raw_inventory") or {}
    evidence = source.get("evidence_hashes") or {}
    fixed = detailed.get("fixed_matrix") or {}
    issue = detailed.get("static_issue_preflight") or {}
    execution = detailed.get("execution") or {}
    manifest_outputs = manifest.get("outputs") or {}
    if (
        not detailed.get("passed")
        or not summary.get("passed")
        or detailed.get("route") != contract["required_route"]
        or summary.get("route") != contract["required_route"]
        or manifest.get("route") != contract["required_route"]
        or not fixed.get("exact")
        or fixed.get("matrix_float64_le_c_sha256")
        != ctx.cfg["controller_contract"]["requested_matrix_float64_le_c_sha256"]
        or int(issue.get("construction_pass_count", -1))
        != int(contract["required_static_issue_pass_count"])
        or int(issue.get("construction_count", -1))
        != int(contract["required_static_issue_count"])
        or bool(issue.get("online_cancellation_proved"))
        != bool(contract["required_online_cancellation_proved"])
        or int(inventory.get("count", -1))
        != int(contract["required_source_raw_count"])
        or int(inventory.get("bytes", -1))
        != int(contract["required_source_raw_bytes"])
        or inventory.get("digest") != contract["required_source_raw_digest"]
        or evidence.get("final") != contract["required_source_final_sha256"]
        or evidence.get("audit")
        != contract["required_source_independent_audit_sha256"]
        or int(execution.get("new_raw_count", -1))
        != int(contract["required_new_raw_count"])
        or bool(execution.get("tsc_executed"))
        != bool(contract["required_tsc_executed"])
        or any(
            bool(execution.get(key))
            for key in (
                "controller_executed",
                "gotsc_executed",
                "plant_steps_executed",
                "ray_executed",
            )
        )
        or manifest_outputs.get(paths["detailed"].name) != hashes["detailed"]
        or manifest_outputs.get(paths["summary"].name) != hashes["summary"]
    ):
        raise ValueError("D1R14R2 R1A scientific boundary changed")
    return {
        "output": str(ctx.source_r1a_output),
        "hashes": hashes,
        "matrix_digest": fixed["matrix_float64_le_c_sha256"],
        "static_issue_pass_count": int(issue["construction_pass_count"]),
        "source_d1r14_raw_inventory": inventory,
        "source_d1r14_evidence_hashes": evidence,
        "online_cancellation_proved": False,
        "passed": True,
    }


def _authenticate_source(ctx: Context) -> dict[str, Any]:
    r1a = _authenticate_r1a(ctx)
    expected = ctx.cfg["source_contract"]
    d1r13_inventory = _raw_inventory(ctx.source_ctx.paths.raw)
    if (
        d1r13_inventory["count"] != int(expected["d1r13_raw_count"])
        or d1r13_inventory["bytes"] != int(expected["d1r13_raw_total_bytes"])
        or d1r13_inventory["digest"] != str(expected["d1r13_raw_inventory_digest"])
    ):
        raise ValueError("D1R14R2 D1R13 raw inventory changed")
    final_path = ctx.source_d1r13_run / "final_result.json"
    if _sha256(final_path) != str(expected["d1r13_final_result_sha256"]):
        raise ValueError("D1R14R2 D1R13 final result hash changed")
    final = _read_json(final_path)
    if (
        not final.get("passed")
        or final.get("route") != str(expected["d1r13_final_route"])
        or int(final.get("pass_count", -1)) != 8
    ):
        raise ValueError("D1R14R2 D1R13 final result changed")
    if _sha256(ctx.source_ctx.paths.state) != str(expected["d1r13_stage_state_sha256"]):
        raise ValueError("D1R14R2 D1R13 state hash changed")
    if _sha256(ctx.source_ctx.paths.manifest) != str(expected["d1r13_stage_manifest_sha256"]):
        raise ValueError("D1R14R2 D1R13 manifest hash changed")
    if _sha256(ctx.source_d1r13_audit) != str(expected["d1r13_independent_audit_sha256"]):
        raise ValueError("D1R14R2 D1R13 independent audit hash changed")
    audit = _read_json(ctx.source_d1r13_audit)
    if (
        not audit.get("passed")
        or int(audit.get("strict_raw_parse_count", -1)) != 8
        or int(audit.get("snapshot_pass_count", -1)) != 8
        or int(audit.get("zero_action_row_count", -1)) != 8
        or int(audit.get("zero_current_increment_row_count", -1)) != 8
    ):
        raise ValueError("D1R14R2 D1R13 independent audit changed")
    d1r11_inventory = _raw_inventory(ctx.source_ctx.source_ctx.paths.raw)
    if (
        d1r11_inventory["count"] != int(expected["d1r11_training_raw_count"])
        or d1r11_inventory["bytes"] != int(expected["d1r11_training_raw_total_bytes"])
        or d1r11_inventory["digest"] != str(expected["d1r11_training_raw_inventory_digest"])
    ):
        raise ValueError("D1R14R2 D1R11 training inventory changed")
    sources = _source_d1r13_results(ctx)
    snapshots = d1r13._snapshot_audit(
        [
            {
                "pair_id": row["spec"]["pair_id"],
                "history_member": row["spec"]["history_member"],
                "restart_snapshot_dir": row["spec"]["restart_snapshot_dir"],
                "restart_snapshot_manifest_digest": row["spec"]["restart_snapshot_manifest_digest"],
                "state_generation_experiment_id": row["spec"]["state_generation_experiment_id"],
            }
            for row in sources
        ]
    )
    if not snapshots.get("passed") or int(snapshots.get("pass_count", -1)) != 8:
        raise ValueError("D1R14R2 selected snapshot authentication failed")
    return {
        "r1a": r1a,
        "d1r13_inventory": d1r13_inventory,
        "d1r11_inventory": d1r11_inventory,
        "d1r13_final": final,
        "d1r13_independent_audit": audit,
        "snapshots": snapshots,
        "source_results": sources,
    }


def _package_fingerprint() -> dict[str, Any]:
    project = _project_root()
    manifest = _read_json(project / "PACKAGE_MANIFEST.json")
    files = [str(path) for path in manifest["file_inventory"]]
    hashes = {path: _sha256(project / path) for path in files}
    required = {
        "configs/stage4_2r3c3t13s24d1r14r2_mixed_basis_signed_excitation_sentinel_370ms.json",
        "docs/codex/reports/STAGE4_2R3C3T13S24D1R14R2_REAL_TSC_MIXED_BASIS_SENTINEL_DESIGN.md",
        "docs/codex/audit_tools/stage4_2r3c3t13s24d1r14r2_independent_forensics.py",
        "scripts/stage4_2r3c3t13s24d1r14r2_mixed_basis_signed_excitation_sentinel.py",
        "tsc_rzip_rllib/diagnostics/stage4_2r3c3t13s24d1r14r2_mixed_basis_signed_excitation_sentinel.py",
        "tsc_rzip_rllib/diagnostics/stage4_2r3c3t13s24d1r13_zero_increment_deconfounding_sentinel.py",
    }
    if not required.issubset(hashes):
        raise ValueError(
            "D1R14R2 package import closure is incomplete: "
            + repr(sorted(required.difference(hashes)))
        )
    return {
        "declared_file_count": len(files),
        "hashes": hashes,
        "digest": _digest(hashes),
    }


def build_specs(
    ctx: Context, source_results: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    requested_matrix = np.asarray(
        ctx.cfg["controller_contract"]["requested_coordinate_matrix_columns"],
        dtype=float,
    )
    matrix_digest = str(
        ctx.cfg["controller_contract"]["requested_matrix_float64_le_c_sha256"]
    )
    roles = [("baseline", -1, "", 0)] + [
        ("signed_probe", index, name, sign)
        for index, name in enumerate(DIRECTIONS)
        for sign in (1, -1)
    ]
    for source_result in source_results:
        source = source_result["spec"]
        source_path = ctx.source_ctx.paths.raw / f"{source_result['experiment_id']}.json.gz"
        for role, direction_index, direction_name, sign in roles:
            requested = np.zeros(4, dtype=float)
            if role == "signed_probe":
                requested = requested_matrix[:, direction_index] * sign
            identity = {
                "stage": STAGE,
                "campaign_identity": CAMPAIGN_IDENTITY,
                "controller_revision": CONTROLLER_REVISION,
                "source_d1r13_experiment_id": source_result["experiment_id"],
                "role": role,
                "direction_index": direction_index,
                "sign": sign,
                "requested_matrix_digest": matrix_digest,
                "snapshot_manifest_digest": source["restart_snapshot_manifest_digest"],
            }
            experiment_id = d1r11.s21.s16.s9.t11.t1.r3c3._scenario_digest(identity)
            spec = copy.deepcopy(source)
            spec.update(
                {
                    "kind": "stage4_2r3c3t13s24d1r14r2_mixed_basis_signed_excitation_sentinel",
                    "stage": STAGE,
                    "campaign_identity": CAMPAIGN_IDENTITY,
                    "controller_revision": CONTROLLER_REVISION,
                    "experiment_id": experiment_id,
                    "phase": "mixed_basis_signed_excitation_safety_geometry_sentinel",
                    "category": "safety_geometry_identification_only",
                    "environment_variant": f"stage4_2r3c3t13s24d1r14r2_{experiment_id}",
                    "source_d1r13_experiment_id": str(source_result["experiment_id"]),
                    "source_d1r13_raw_sha256": _sha256(source_path),
                    "source_d1r13_raw_size_bytes": source_path.stat().st_size,
                    "source_d1r11_experiment_id": str(source["source_d1r11_experiment_id"]),
                    "d1r14r2_role": role,
                    "d1r14r2_direction_index": direction_index,
                    "d1r14r2_direction_name": direction_name,
                    "d1r14r2_sign": sign,
                    "d1r14r2_requested_coordinate": requested.tolist(),
                    "d1r14r2_requested_matrix_digest": matrix_digest,
                    "d1r14r2_issue_task_step": ISSUE_STEP if role == "signed_probe" else -1,
                    "d1r14r2_cancel_task_step": CANCEL_STEP if role == "signed_probe" else -1,
                    "d1r14r2_zero_after_task_step": ZERO_AFTER,
                    "d1r14r2_future_r17_controller_execution_allowed": False,
                    "probe_trajectory_allowed_in_expert_dataset": False,
                    "pair_or_history_label_available_to_controller": False,
                    "partition_label_available_to_controller": False,
                    "source_result_available_to_controller": False,
                    "source_action_available_to_controller": False,
                    "source_coil_current_available_to_controller": False,
                    "source_wire_current_available_to_controller": False,
                    "hidden_wire_current_available_to_controller": False,
                    "future_action_count": 0,
                    "future_measurement_count": 0,
                    "formal_timing_unchanged": True,
                }
            )
            output.append(spec)
    if len(output) != 72 or len({row["experiment_id"] for row in output}) != 72:
        raise ValueError("D1R14R2 spec identity coverage changed")
    counts: dict[str, int] = {}
    horizons = {35: 0, 37: 0}
    for spec in output:
        counts[str(spec["source_d1r13_experiment_id"])] = (
            counts.get(str(spec["source_d1r13_experiment_id"]), 0) + 1
        )
        horizons[int(spec["horizon_steps"])] += 1
    if set(counts.values()) != {9} or horizons != {35: 36, 37: 36}:
        raise ValueError("D1R14R2 matrix coverage changed")
    return output


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
    if ctx.paths.stage_dir.exists() or ctx.paths.state.exists() or ctx.paths.manifest.exists():
        raise ValueError("D1R14R2 offline requires a fresh run identity")
    source = _authenticate_source(ctx)
    specs = build_specs(ctx, source["source_results"])
    package = _package_fingerprint()
    _prepare_dirs(ctx.paths)
    _write_json(ctx.paths.specs / "sentinel_specs.json", specs)
    _write_json(
        ctx.paths.source_reference / "r1a_authentication.json",
        source["r1a"],
    )
    _write_json(
        ctx.paths.source_reference / "d1r13_raw_inventory.json",
        source["d1r13_inventory"],
    )
    _write_json(
        ctx.paths.source_reference / "d1r11_training_inventory.json",
        source["d1r11_inventory"],
    )
    _write_json(
        ctx.paths.source_reference / "selected_snapshot_audit.json",
        source["snapshots"],
    )
    _write_json(
        ctx.paths.source_reference / "selected_d1r13_sources.json",
        [
            {
                "experiment_id": row["experiment_id"],
                "sha256": _sha256(
                    ctx.source_ctx.paths.raw / f"{row['experiment_id']}.json.gz"
                ),
                "size": (
                    ctx.source_ctx.paths.raw / f"{row['experiment_id']}.json.gz"
                ).stat().st_size,
                "source_d1r11_experiment_id": row["spec"]["source_d1r11_experiment_id"],
            }
            for row in source["source_results"]
        ],
    )
    manifest = {
        "schema_version": 1,
        "stage": STAGE,
        "campaign_identity": CAMPAIGN_IDENTITY,
        "controller_revision": CONTROLLER_REVISION,
        "package_revision": ctx.cfg["package_revision"],
        "config_path": str(ctx.config_path),
        "config_sha256": _sha256(ctx.config_path),
        "design_document_sha256": ctx.cfg["design_document_sha256"],
        "source_d1r13_run": str(ctx.source_d1r13_run),
        "source_d1r13_audit": str(ctx.source_d1r13_audit),
        "source_r1a_output": str(ctx.source_r1a_output),
        "source_r1a_hashes": source["r1a"]["hashes"],
        "requested_matrix_digest": source["r1a"]["matrix_digest"],
        "source_d1r13_inventory_digest": source["d1r13_inventory"]["digest"],
        "source_d1r11_inventory_digest": source["d1r11_inventory"]["digest"],
        "spec_count": len(specs),
        "spec_digest": _digest(specs),
        "snapshot_pass_count": source["snapshots"]["pass_count"],
        "package_fingerprint": package,
        "formal_timing_unchanged": True,
        "formal_tracking_diagnostic_only": True,
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
        "spec_digest": manifest["spec_digest"],
        "package_digest": package["digest"],
        "stop_reason": "",
        "verdict": {},
    }
    _write_json(ctx.paths.manifest, manifest)
    _write_json(ctx.paths.state, state)
    output = {
        "schema_version": 1,
        "stage": STAGE,
        "phase": "zero_plant_offline_preflight",
        "source_d1r13_raw_count": source["d1r13_inventory"]["count"],
        "source_r1a_authenticated": source["r1a"]["passed"],
        "source_d1r11_raw_count": source["d1r11_inventory"]["count"],
        "selected_context_count": 8,
        "selected_spec_count": len(specs),
        "baseline_count": 8,
        "signed_probe_count": 64,
        "snapshot_pass_count": source["snapshots"]["pass_count"],
        "new_raw_count": 0,
        "real_tsc_executed": False,
        "passed": True,
    }
    _write_json(ctx.paths.analysis / "offline_preflight.json", output)
    return output


def _controller_source_spec(spec: Mapping[str, Any], schedule: Mapping[str, Any]) -> dict[str, Any]:
    output = d1r11.s21.s16.s9._controller_spec(spec)
    forbidden = {
        "pair_id",
        "history_member",
        "partition",
        "common_prefix_steps",
        "state_generation_experiment_id",
        "restart_snapshot_dir",
        "restart_snapshot_manifest_digest",
        "source_d1r13_experiment_id",
        "source_d1r13_raw_sha256",
        "source_d1r13_raw_size_bytes",
        "source_d1r11_experiment_id",
        "d1r14r2_role",
        "d1r14r2_direction_index",
        "d1r14r2_direction_name",
        "d1r14r2_sign",
        "d1r14r2_requested_coordinate",
    }
    prefixed_forbidden = {
        key
        for key in output
        if key.startswith(("d1r13_", "d1r14r2_", "source_d1r13_"))
    }
    forbidden.update(prefixed_forbidden)
    for key in forbidden:
        output.pop(key, None)
    if forbidden.intersection(output) or any(
        key.startswith(("d1r13_", "d1r14r2_", "source_d1r13_")) for key in output
    ):
        raise ValueError("D1R14R2 forbidden experiment label reached controller")
    output["s24_sequence_index"] = -1
    output["s24_requested_matrix_row"] = [0.0] * 16
    action_by_step = {
        str(step): [0.0] * 4
        for step in tuple(map(int, schedule["issue_task_steps"]))
        + tuple(map(int, schedule["cancel_task_steps"]))
    }
    output["s24_requested_action_by_task_step"] = action_by_step
    return output


def zero_action(step: int) -> np.ndarray:
    if int(step) < ISSUE_STEP:
        raise ValueError("D1R14R2 zero branch called before task step 10")
    return np.zeros(N_COILS, dtype=float)


def _trace_template(step: int, action: np.ndarray) -> dict[str, Any]:
    return {
        "step": step,
        "task_step": step,
        "action_norm_tsc": action.tolist(),
        "computed_online": True,
        "solver_success": True,
        "measurement_max_state_index_used": step,
        "future_measurement_used": False,
        "hidden_wire_used": False,
        "source_action_used": False,
        "source_coil_current_used": False,
        "source_wire_current_used": False,
        "current_run_future_used": False,
        "pair_or_history_label_used": False,
        "source_result_used": False,
        "future_probe_schedule_available_to_underlying_controller": False,
        "r3c3t13s21_partition_label_used": False,
        "r3c3t13s24_pair_history_partition_label_used": False,
        "r3c3t13s24_delay_slew_target_id_label_used": False,
        "r3c3t13s24_source_or_matched_baseline_used": False,
        "r3c3t13s24_future_measurement_used": False,
        "r3c3t13s24_future_executed_action_used": False,
        "r3c3t13s24_hidden_wire_current_used": False,
        "r3c3t13s24_schedule_available_to_underlying_controller": False,
        "r3c3t13s24_event": "none",
        "r3c3t13s16_lattice_event": "none",
        "r3c3t13s24d1r14r2_controller_revision": CONTROLLER_REVISION,
        "r3c3t13s24d1r14r2_delegated_prefix": False,
        "r3c3t13s24d1r14r2_future_r17_executed": False,
        "r3c3t13s24d1r14r2_event": "none",
        "r3c3t13s24d1r14r2_event_detail": {},
        "r3c3t13s24d1r14r2_zero_increment": True,
    }


class MixedBasisSignedExcitationController(
    d1r11.SequentialAmplitudeCodedProbeController
):
    """Exact D1R11 prefix followed by one fixed signed issue/cancel pair."""

    def __init__(
        self,
        base_worker: Any,
        bundle: Mapping[str, Any],
        source_spec: Mapping[str, Any],
        initial_state: Mapping[str, Any],
        lattice_cfg: Mapping[str, Any],
        calibration_cfg: Mapping[str, Any],
        dynamic_cfg: Mapping[str, Any],
        schedule_cfg: Mapping[str, Any],
        controller_contract: Mapping[str, Any],
        *,
        role: str,
        direction_index: int,
        sign: int,
        requested_coordinate: Sequence[float],
    ):
        prepared = _controller_source_spec(source_spec, schedule_cfg)
        requested = np.asarray(requested_coordinate, dtype=float)
        frozen_matrix = np.asarray(
            controller_contract["requested_coordinate_matrix_columns"], dtype=float
        )
        if role == "signed_probe":
            if direction_index not in range(4) or sign not in (-1, 1):
                raise ValueError("D1R14R2 invalid fixed signed coordinate")
            expected = frozen_matrix[:, direction_index] * sign
            if requested.shape != (4,) or not np.array_equal(requested, expected):
                raise ValueError("D1R14R2 requested mixed coordinate changed")
            prepared["s24_requested_action_by_task_step"][
                str(schedule_cfg["issue_task_steps"][direction_index])
            ] = requested.tolist()
        elif (
            role != "baseline"
            or direction_index != -1
            or sign != 0
            or requested.shape != (4,)
            or not np.array_equal(requested, np.zeros(4, dtype=float))
        ):
            raise ValueError("D1R14R2 invalid baseline coordinate")
        super().__init__(
            base_worker,
            bundle,
            prepared,
            initial_state,
            lattice_cfg,
            calibration_cfg,
            dynamic_cfg,
            schedule_cfg,
        )
        self.d1r14r2_role = role
        self.d1r14r2_direction_index = int(direction_index)
        self.d1r14r2_sign = int(sign)
        self.d1r14r2_requested_coordinate = requested
        self.d1r14r2_controller_contract = copy.deepcopy(dict(controller_contract))

    def _issue(
        self, slot: int, currents: np.ndarray, baseline_action: np.ndarray
    ) -> tuple[np.ndarray, dict[str, Any]]:
        """Construct the exact Card15 action under the frozen mixed-basis gates."""
        self._freeze_fixed_basis(currents, baseline_action)
        center = self.actuator.apply(currents, baseline_action)
        desired_coordinate = self.requested_by_step[self.issue_steps[slot]]
        field_basis, current_basis = self._basis_current()
        desired_field = field_basis @ desired_coordinate
        target_fields, actual_decimal, integer_counts = d1r11.s21._dynamic_exact_target(
            center.card15_fields,
            tuple(Decimal(str(value)) for value in desired_field),
            search_radius=int(self.schedule_cfg["dynamic_exact_search_radius"]),
        )
        chosen = d1r11.s21.s16.s9.exact_stored_center_action(
            stored_fields=target_fields,
            measured_current_a_tsc=currents,
            baseline_action_norm_tsc=baseline_action,
            turns_tsc=self.turns_tsc,
            max_slew_step_a=float(self.base.max_delta_a),
            minimum_current_a_tsc=self.base.min_current,
            maximum_current_a_tsc=self.base.max_current,
            cfg=self.lattice_cfg,
        )
        issued = self.actuator.apply(currents, chosen["action_norm_tsc"])
        actual_field = np.asarray(
            [float(value) for value in actual_decimal], dtype=float
        )
        actual_current = actual_field * 1000.0 / np.asarray(
            self.turns_tsc, dtype=float
        )
        desired_current = current_basis @ desired_coordinate
        coordinate = np.linalg.lstsq(current_basis, actual_current, rcond=None)[0]
        reconstructed = current_basis @ coordinate
        desired_norm = float(np.linalg.norm(desired_current))
        actual_norm = float(np.linalg.norm(actual_current))
        cosine = float(
            np.dot(desired_current, actual_current)
            / max(desired_norm * actual_norm, 1e-300)
        )
        off_basis = float(
            np.linalg.norm(actual_current - reconstructed) / max(actual_norm, 1e-300)
        )
        coordinate_error = float(np.max(np.abs(coordinate - desired_coordinate)))
        contract = self.d1r14r2_controller_contract
        frozen_expected = np.asarray(
            contract["requested_coordinate_matrix_columns"], dtype=float
        )[:, slot] * self.d1r14r2_sign
        criteria = {
            "finite": bool(
                np.all(np.isfinite(coordinate))
                and np.all(np.isfinite(actual_field))
                and math.isfinite(cosine)
                and math.isfinite(off_basis)
            ),
            "requested_mixed_coordinate_exact": bool(
                desired_coordinate.shape == (4,)
                and np.array_equal(desired_coordinate, frozen_expected)
                and np.count_nonzero(desired_coordinate) == 4
            ),
            "center_exact": all(len(field) == 10 for field in center.card15_fields),
            "target_exact": all(len(field) == 10 for field in target_fields),
            "target_reproduction": list(issued.card15_fields) == list(target_fields),
            "no_saturation": not any(issued.action_saturated),
            "no_current_clip": not any(issued.current_limit_clipped),
            "incremental_action": float(chosen["incremental_normalized_action_linf"])
            <= float(contract["maximum_incremental_normalized_action_linf"]) + 1e-12,
            "total_action": float(chosen["total_normalized_action_abs"])
            <= float(contract["maximum_total_normalized_action_abs"]) + 1e-12,
            "current_utilization": float(chosen["predicted_maximum_current_utilization"])
            <= float(contract["maximum_current_utilization"]) + 1e-12,
            "cosine": cosine
            >= float(contract["minimum_desired_applied_current_cosine"]) - 1e-12,
            "off_basis": off_basis
            <= float(contract["maximum_relative_off_basis_residual"]) + 1e-12,
            "actuator_gate": bool(chosen["passed"]),
        }
        event = {
            "event": "sequential_issue",
            "gate_revision": "d1r14r2_fixed_mixed_action_safety_v1",
            "slot": slot,
            "task_step": self.step,
            "requested_coordinate": desired_coordinate.tolist(),
            "actual_coordinate": coordinate.tolist(),
            "center_card15_fields": list(center.card15_fields),
            "target_card15_fields": list(target_fields),
            "integer_grid_steps_tsc": list(map(int, integer_counts)),
            "actual_signed_delta_field_kAt_tsc": actual_field.tolist(),
            "maximum_absolute_coordinate_error_diagnostic_only": coordinate_error,
            "desired_applied_current_cosine": cosine,
            "relative_off_basis_residual": off_basis,
            "incremental_normalized_action_linf": float(
                chosen["incremental_normalized_action_linf"]
            ),
            "total_normalized_action_abs": float(chosen["total_normalized_action_abs"]),
            "predicted_current_utilization": float(
                chosen["predicted_maximum_current_utilization"]
            ),
            "criteria": criteria,
            "passed": bool(all(criteria.values())),
            "actuator_prediction": copy.deepcopy(chosen),
        }
        if not event["passed"]:
            raise ValueError(
                "D1R14R2 mixed-basis issue action failed: "
                + json.dumps(event, sort_keys=True)
            )
        self._active_issue = copy.deepcopy(event)
        return np.asarray(chosen["action_norm_tsc"], dtype=float), event

    def action(self, current_state: Mapping[str, Any]) -> tuple[np.ndarray, dict[str, Any]]:
        if int(current_state["step_index"]) != self.step:
            raise ValueError("D1R14R2 controller/current task-state index mismatch")
        if self.step < ISSUE_STEP:
            action, trace = super().action(current_state)
            trace.update(
                {
                    "r3c3t13s24d1r14r2_controller_revision": CONTROLLER_REVISION,
                    "r3c3t13s24d1r14r2_delegated_prefix": True,
                    "r3c3t13s24d1r14r2_future_r17_executed": False,
                    "r3c3t13s24d1r14r2_event": "none",
                    "r3c3t13s24d1r14r2_event_detail": {},
                    "r3c3t13s24d1r14r2_zero_increment": False,
                }
            )
            return np.asarray(action, dtype=float), trace
        action = zero_action(self.step)
        trace = _trace_template(self.step, action)
        if self.d1r14r2_role == "signed_probe" and self.step == ISSUE_STEP:
            currents = np.asarray(current_state["currents_a_tsc"], dtype=float)
            action, event = self._issue(
                self.d1r14r2_direction_index, currents, np.zeros(N_COILS, dtype=float)
            )
            trace.update(
                {
                    "action_norm_tsc": action.tolist(),
                    "r3c3t13s24d1r14r2_event": "signed_issue",
                    "r3c3t13s24d1r14r2_event_detail": event,
                    "r3c3t13s24d1r14r2_zero_increment": False,
                }
            )
        elif self.d1r14r2_role == "signed_probe" and self.step == CANCEL_STEP:
            currents = np.asarray(current_state["currents_a_tsc"], dtype=float)
            action, event = self._cancel(
                self.d1r14r2_direction_index, currents, np.zeros(N_COILS, dtype=float)
            )
            trace.update(
                {
                    "action_norm_tsc": action.tolist(),
                    "r3c3t13s24d1r14r2_event": "stored_center_cancel",
                    "r3c3t13s24d1r14r2_event_detail": event,
                    "r3c3t13s24d1r14r2_zero_increment": False,
                }
            )
        return np.asarray(action, dtype=float), trace


def _payload(ctx: Context, spec: Mapping[str, Any]) -> dict[str, Any]:
    source_d1r11_ctx = ctx.source_ctx.source_ctx
    proxy = SimpleNamespace(
        base_ctx=source_d1r11_ctx.base_ctx.base_ctx,
        paths=ctx.paths,
        cfg=source_d1r11_ctx.base_ctx.cfg,
    )
    payload = d1r11.s21._payload(proxy, spec)
    experiment_id = str(spec["experiment_id"])
    payload.update(
        {
            "variant_id": f"stage4_2r3c3t13s24d1r14r2_{experiment_id}",
            "stage4_2r3c3t13s24d1r14r2_restart_snapshot_dir": str(
                spec["restart_snapshot_dir"]
            ),
            "stage4_2r3c3t13s24d1r14r2_snapshot_manifest_digest": str(
                spec["restart_snapshot_manifest_digest"]
            ),
            "stage4_2r3c3t13s24d1r14r2_issue_task_step": int(
                spec["d1r14r2_issue_task_step"]
            ),
            "stage4_2r3c3t13s24d1r14r2_cancel_task_step": int(
                spec["d1r14r2_cancel_task_step"]
            ),
        }
    )
    _write_json(ctx.paths.variants / f"payload_{experiment_id}.json", payload)
    return payload


class LocalWorker:
    """One fresh authentic TSC process and D1R14R2 controller per rollout."""

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
        controller_contract: dict[str, Any],
    ):
        self.plant = d1r11.s21.s16.s9.t11.t1.r1.LocalPlantReplayWorker(
            payload, library, bundle, worker_id, selector
        )
        self.base = self.plant.base_worker
        self.bundle = bundle
        self.lattice_cfg = lattice_cfg
        self.calibration_cfg = calibration_cfg
        self.dynamic_cfg = dynamic_cfg
        self.schedule_cfg = schedule_cfg
        self.controller_contract = controller_contract

    def close(self) -> None:
        self.plant.close()

    def evaluate(self, spec: dict[str, Any]) -> dict[str, Any]:
        started = time.time()
        failed = True
        trajectory: list[dict[str, Any]] = []
        trace: list[dict[str, Any]] = []
        result: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "stage": STAGE,
            "campaign_identity": CAMPAIGN_IDENTITY,
            "controller_revision": CONTROLLER_REVISION,
            "underlying_prefix_controller_revision": d1r11.CONTROLLER_REVISION,
            "experiment_id": str(spec["experiment_id"]),
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
            if (
                horizon != d1r11.s21.s13._formal_horizon(float(spec["slew_scale"]))
                or horizon != int(spec["formal_horizon_steps"])
                or horizon != int(self.base.env.max_episode_steps)
            ):
                raise ValueError("D1R14R2 formal horizon changed")
            self.base.env.reset()
            zero = np.zeros(N_COILS, dtype=np.float32)
            trajectory.append(
                d1r11.s21.s16.s9.t11.t1.r1._state_record_full(
                    self.base.env, 0, zero
                )
            )
            controller = MixedBasisSignedExcitationController(
                self.base,
                self.bundle,
                spec,
                trajectory[0],
                self.lattice_cfg,
                self.calibration_cfg,
                self.dynamic_cfg,
                self.schedule_cfg,
                self.controller_contract,
                role=str(spec["d1r14r2_role"]),
                direction_index=int(spec["d1r14r2_direction_index"]),
                sign=int(spec["d1r14r2_sign"]),
                requested_coordinate=spec["d1r14r2_requested_coordinate"],
            )
            for step in range(horizon):
                try:
                    action, controller_row = controller.action(trajectory[-1])
                except ValueError as exc:
                    if (
                        "D1R14R2 mixed-basis issue action failed" in str(exc)
                        or "S24 sequential cancel action failed" in str(exc)
                    ):
                        result["execution_failure_class"] = "controller_action_safety_gate_failure"
                    raise
                _, _, terminated, truncated, info = self.base.env.step(action)
                next_state = d1r11.s21.s16.s9.t11.t1.r1._state_record_full(
                    self.base.env, step + 1, action
                )
                trajectory.append(next_state)
                trace.append(controller_row)
                controller.advance(next_state)
                if terminated:
                    result["execution_failure_class"] = "plant_abnormal_termination"
                    raise RuntimeError(
                        str(info.get("failure_reason", "environment terminated"))
                    )
                if truncated and step + 1 < horizon:
                    result["execution_failure_class"] = "plant_early_truncation"
                    raise RuntimeError("environment truncated before D1R14R2 horizon")
            calibration_events = [
                row.get("r3c3t13s16_lattice_event")
                for row in trace[:PREFIX_END]
                if row.get("r3c3t13s16_lattice_event") != "none"
            ]
            currents = np.asarray(
                [row["currents_a_tsc"] for row in trajectory], dtype=float
            )
            role = str(spec["d1r14r2_role"])
            if role == "baseline":
                post_actions = np.asarray(
                    [row["action_norm_tsc"] for row in trace[PREFIX_END:]],
                    dtype=float,
                )
                post_current_delta = np.diff(currents[PREFIX_END:], axis=0)
                role_success = bool(
                    post_actions.shape == (horizon - PREFIX_END, N_COILS)
                    and np.array_equal(post_actions, np.zeros_like(post_actions))
                    and post_current_delta.shape == (horizon - PREFIX_END, N_COILS)
                    and np.array_equal(
                        post_current_delta, np.zeros_like(post_current_delta)
                    )
                )
            else:
                after_actions = np.asarray(
                    [row["action_norm_tsc"] for row in trace[ZERO_AFTER:]],
                    dtype=float,
                )
                after_current_delta = np.diff(currents[ZERO_AFTER:], axis=0)
                issue = trace[ISSUE_STEP].get("r3c3t13s24d1r14r2_event_detail") or {}
                cancel = trace[CANCEL_STEP].get("r3c3t13s24d1r14r2_event_detail") or {}
                role_success = bool(
                    trace[ISSUE_STEP].get("r3c3t13s24d1r14r2_event") == "signed_issue"
                    and trace[CANCEL_STEP].get("r3c3t13s24d1r14r2_event")
                    == "stored_center_cancel"
                    and issue.get("passed")
                    and cancel.get("passed")
                    and after_actions.shape == (horizon - ZERO_AFTER, N_COILS)
                    and np.array_equal(after_actions, np.zeros_like(after_actions))
                    and after_current_delta.shape
                    == (horizon - ZERO_AFTER, N_COILS)
                    and np.array_equal(
                        after_current_delta, np.zeros_like(after_current_delta)
                    )
                )
            success = bool(
                len(trajectory) == horizon + 1
                and len(trace) == horizon
                and calibration_events == EXPECTED_CALIBRATION
                and bool(trace[7].get("r3c3t13s21_exact_calibration_net_zero"))
                and all(
                    bool(row.get("r3c3t13s24d1r14r2_delegated_prefix"))
                    for row in trace[:PREFIX_END]
                )
                and role_success
                and not any(bool(row.get("abnormal")) for row in trajectory)
                and np.all(np.isfinite(currents))
            )
            result.update(
                {
                    "success": success,
                    "completed": True,
                    "failure_reason": "" if success else "incomplete or invalid D1R14R2 rollout",
                    "execution_failure_class": (
                        "" if success else "controller_or_action_semantics_error"
                    ),
                    "hidden_history_control_summary": {
                        "fresh_controller_actor": True,
                        "fresh_tsc_process": True,
                        "full_tsc_hidden_state_loaded_from_sprsina": True,
                        "prefix_controller_revision": d1r11.CONTROLLER_REVISION,
                        "role": role,
                        "issue_task_step": ISSUE_STEP if role == "signed_probe" else -1,
                        "cancel_task_step": CANCEL_STEP if role == "signed_probe" else -1,
                        "future_r17_controller_executed": False,
                        "formal_tracking_diagnostic_only": True,
                        "probe_trajectory_allowed_in_expert_dataset": False,
                        "hidden_wire_current_available_to_controller": False,
                        "full_wire_current_recorded_after_action_choice": True,
                        "future_action_replay_used": False,
                        "future_measurement_used": False,
                        "source_action_used": False,
                        "source_coil_current_used": False,
                        "source_wire_current_used": False,
                        "current_run_future_used": False,
                        "pair_or_history_label_used": False,
                        "source_result_used": False,
                    },
                    "wall_time_s": time.time() - started,
                }
            )
            failed = not success
            return d1r11.s21.s16.s9.t11.t1._json_safe(result)
        except Exception as exc:
            failure_class = str(result.get("execution_failure_class") or "")
            if not failure_class:
                failure_class = "runtime_or_controller_error"
            result.update(
                {
                    "success": False,
                    "completed": True,
                    "failure_reason": repr(exc),
                    "execution_failure_class": failure_class,
                    "trajectory": trajectory,
                    "controller_trace": trace,
                    "traceback": traceback.format_exc(),
                    "wall_time_s": time.time() - started,
                }
            )
            return d1r11.s21.s16.s9.t11.t1._json_safe(result)
        finally:
            runner = getattr(self.base.env, "runner", None)
            if runner is not None:
                runner.cleanup_episode_workspace(
                    failed=failed,
                    reason="stage4_2r3c3t13s24d1r14r2_mixed_basis_signed_excitation",
                )


_RAY_ACTOR = None


def _ray_actor_class():
    global _RAY_ACTOR
    if _RAY_ACTOR is None:
        import ray

        @ray.remote(num_cpus=1, max_restarts=0)
        class Stage42R3C3T13S24D1R14R2Actor:
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
                controller_contract,
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
                    controller_contract,
                )

            def evaluate(self, spec):
                return self.worker.evaluate(spec)

            def close(self):
                self.worker.close()
                return True

        _RAY_ACTOR = Stage42R3C3T13S24D1R14R2Actor
    return _RAY_ACTOR


def _saved_specs(ctx: Context) -> list[dict[str, Any]]:
    saved = _read_json(ctx.paths.specs / "sentinel_specs.json")
    rebuilt = build_specs(ctx, _source_d1r13_results(ctx))
    if _digest(saved) != _digest(rebuilt):
        raise ValueError("D1R14R2 frozen specs changed")
    return saved


def _assert_run_identity(ctx: Context) -> list[dict[str, Any]]:
    """Fail closed if a prepared run no longer matches package or source evidence."""
    manifest = _read_json(ctx.paths.manifest)
    state = _read_json(ctx.paths.state)
    source = _authenticate_source(ctx)
    specs = _saved_specs(ctx)
    package = _package_fingerprint()
    if (
        manifest.get("stage") != STAGE
        or manifest.get("campaign_identity") != CAMPAIGN_IDENTITY
        or manifest.get("controller_revision") != CONTROLLER_REVISION
        or manifest.get("package_revision") != ctx.cfg["package_revision"]
        or manifest.get("config_sha256") != _sha256(ctx.config_path)
        or manifest.get("design_document_sha256")
        != ctx.cfg["design_document_sha256"]
        or manifest.get("source_r1a_hashes") != source["r1a"]["hashes"]
        or manifest.get("requested_matrix_digest")
        != source["r1a"]["matrix_digest"]
        or manifest.get("source_d1r13_inventory_digest")
        != source["d1r13_inventory"]["digest"]
        or manifest.get("source_d1r11_inventory_digest")
        != source["d1r11_inventory"]["digest"]
        or int(manifest.get("snapshot_pass_count", -1))
        != int(source["snapshots"]["pass_count"])
        or manifest.get("package_fingerprint") != package
        or manifest.get("spec_digest") != _digest(specs)
        or state.get("stage") != STAGE
        or state.get("spec_digest") != manifest.get("spec_digest")
        or state.get("package_digest") != package["digest"]
    ):
        raise ValueError("D1R14R2 prepared run/package/source identity changed")
    return specs


def _result_complete(
    path: Path, spec: Mapping[str, Any], *, require_success: bool
) -> bool:
    if not path.is_file():
        return False
    try:
        result = _read_gz(path)
        horizon = int(spec["horizon_steps"])
        return bool(
            result.get("completed")
            and (result.get("success") or not require_success)
            and result.get("stage") == STAGE
            and result.get("campaign_identity") == CAMPAIGN_IDENTITY
            and result.get("controller_revision") == CONTROLLER_REVISION
            and result.get("experiment_id") == spec["experiment_id"]
            and result.get("spec") == dict(spec)
            and len(result.get("trajectory") or []) <= horizon + 1
            and len(result.get("controller_trace") or []) <= horizon
        )
    except Exception:
        return False


def evaluate_specs(
    ctx: Context,
    specs: Sequence[dict[str, Any]],
    *,
    backend: str,
    resume: bool,
) -> dict[str, Any]:
    ctx.paths.raw.mkdir(parents=True, exist_ok=True)
    pending = [
        spec
        for spec in specs
        if not (
            resume
            and _result_complete(
                ctx.paths.raw / f"{spec['experiment_id']}.json.gz",
                spec,
                require_success=True,
            )
        )
    ]
    payloads = {str(spec["experiment_id"]): _payload(ctx, spec) for spec in specs}
    source_d1r11_ctx = ctx.source_ctx.source_ctx
    library, bundle, selector = d1r11._library_bundle_selector(source_d1r11_ctx)
    lattice = source_d1r11_ctx.base_ctx.base_ctx.cfg["lattice_probe"]
    calibration = source_d1r11_ctx.base_ctx.base_ctx.cfg["active_calibration"]
    dynamic = source_d1r11_ctx.base_ctx.cfg["causal_model"]
    schedule = source_d1r11_ctx.cfg["schedule_contract"]
    controller_contract = ctx.cfg["controller_contract"]
    if backend == "serial":
        for index, spec in enumerate(pending):
            worker = LocalWorker(
                payloads[str(spec["experiment_id"])],
                library,
                bundle,
                f"stage42r3c3t13s24d1r14r2_serial_{index:04d}",
                selector,
                lattice,
                calibration,
                dynamic,
                schedule,
                controller_contract,
            )
            try:
                result = worker.evaluate(spec)
            finally:
                worker.close()
            _write_json_gz(
                ctx.paths.raw / f"{spec['experiment_id']}.json.gz", result
            )
            print(f"[D1R14R2] {index + 1}/{len(pending)}", flush=True)
    elif backend == "ray" and pending:
        import ray

        plan = d1r11.s21.s16.ensure_ray_worker_plan(
            ray,
            requested_workers=int(ctx.cfg["parallel"]["n_workers"]),
            pending_tasks=len(pending),
            ray_tmpdir=os.environ.get("RAY_TMPDIR")
            or ctx.cfg["storage"]["ray_tmpdir"],
            log_prefix="[D1R14R2]",
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
                    f"stage42r3c3t13s24d1r14r2_{batch_start + offset:04d}",
                    selector,
                    lattice,
                    calibration,
                    dynamic,
                    schedule,
                    controller_contract,
                )
                actors.append(actor)
                refs[actor.evaluate.remote(spec)] = spec
            try:
                while refs:
                    ready, _ = ray.wait(list(refs), num_returns=1, timeout=30.0)
                    if not ready:
                        print(
                            f"[D1R14R2] waiting {completed}/{len(pending)}",
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
                                "experiment_id": str(spec["experiment_id"]),
                                "spec": copy.deepcopy(spec),
                                "success": False,
                                "completed": True,
                                "failure_reason": repr(exc),
                                "execution_failure_class": "ray_actor_runtime_error",
                                "traceback": traceback.format_exc(),
                                "trajectory": [],
                                "controller_trace": [],
                            }
                        _write_json_gz(
                            ctx.paths.raw / f"{spec['experiment_id']}.json.gz",
                            result,
                        )
                        completed += 1
                        print(f"[D1R14R2] {completed}/{len(pending)}", flush=True)
            finally:
                close_refs = [actor.close.remote() for actor in actors]
                if close_refs:
                    ray.get(
                        close_refs,
                        timeout=float(
                            ctx.cfg["storage"]["actor_close_timeout_s"]
                        ),
                    )
                for actor in actors:
                    ray.kill(actor, no_restart=True)
    elif backend not in {"serial", "ray"}:
        raise ValueError(f"unsupported D1R14R2 backend: {backend}")
    completed = sum(
        _result_complete(
            ctx.paths.raw / f"{spec['experiment_id']}.json.gz",
            spec,
            require_success=False,
        )
        for spec in specs
    )
    successful = sum(
        _result_complete(
            ctx.paths.raw / f"{spec['experiment_id']}.json.gz",
            spec,
            require_success=True,
        )
        for spec in specs
    )
    return {
        "expected": len(specs),
        "pending_at_start": len(pending),
        "completed": completed,
        "successful": successful,
        "passed": completed == len(specs) and successful == len(specs),
    }


def _semantic_state(row: Mapping[str, Any]) -> dict[str, Any]:
    return d1r13._semantic_state(row)


def _source_trace_projection(
    source: Mapping[str, Any], current: Mapping[str, Any]
) -> bool:
    return d1r13._source_trace_projection(source, current)


FORBIDDEN_TRACE_KEYS = tuple(
    dict.fromkeys(
        d1r13.FORBIDDEN_TRACE_KEYS
        + ("r3c3t13s24d1r14r2_future_r17_executed",)
    )
)


def _calibration_exact(trace: Sequence[Mapping[str, Any]]) -> bool:
    events = [
        row.get("r3c3t13s16_lattice_event")
        for row in trace[:PREFIX_END]
        if row.get("r3c3t13s16_lattice_event") != "none"
    ]
    return bool(
        events == EXPECTED_CALIBRATION
        and len(trace) > 7
        and trace[7].get("r3c3t13s21_exact_calibration_net_zero")
    )


def _visible_outputs5(
    trajectory: Sequence[Mapping[str, Any]], scales: np.ndarray
) -> np.ndarray:
    if len(trajectory) < 2:
        raise ValueError("D1R14R2 trajectory is too short for visible velocity")
    rows = []
    for index, state in enumerate(trajectory):
        if index == 0:
            other = trajectory[1]
            v_r = (float(other["R"]) - float(state["R"])) / float(d1r11.DT_S)
            v_z = (float(other["Z"]) - float(state["Z"])) / float(d1r11.DT_S)
        else:
            previous = trajectory[index - 1]
            v_r = (float(state["R"]) - float(previous["R"])) / float(d1r11.DT_S)
            v_z = (float(state["Z"]) - float(previous["Z"])) / float(d1r11.DT_S)
        rows.append(
            [
                float(state["R"]),
                float(state["Z"]),
                v_r,
                v_z,
                float(state["Ip"]),
            ]
        )
    values = np.asarray(rows, dtype=float) / scales[None, :]
    if values.shape != (len(trajectory), 5) or not np.all(np.isfinite(values)):
        raise ValueError("D1R14R2 normalized visible trajectory is invalid")
    return values - values[PREFIX_END][None, :]


def _response_geometry(
    ctx: Context,
    specs: Sequence[Mapping[str, Any]],
    results: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    geometry_cfg = ctx.cfg["response_geometry"]
    scales = np.asarray(geometry_cfg["visible_output_scales"], dtype=float)
    first = int(geometry_cfg["first_response_state"])
    minimum_signal = float(geometry_cfg["minimum_odd_peak_normalized_outputs5"])
    maximum_ratio = float(geometry_cfg["maximum_even_to_odd_peak_ratio"])
    rank_tolerance = float(geometry_cfg["rank_relative_tolerance"])
    required_rank = int(geometry_cfg["required_rank"])
    maximum_condition = float(geometry_cfg["maximum_condition_number"])
    by_context: dict[str, dict[tuple[str, int, int], Mapping[str, Any]]] = {}
    spec_by_id = {str(spec["experiment_id"]): spec for spec in specs}
    for experiment_id, result in results.items():
        spec = spec_by_id[experiment_id]
        context_id = str(spec["source_d1r13_experiment_id"])
        key = (
            str(spec["d1r14r2_role"]),
            int(spec["d1r14r2_direction_index"]),
            int(spec["d1r14r2_sign"]),
        )
        by_context.setdefault(context_id, {})[key] = result
    pair_rows = []
    context_rows = []
    odd_by_context_direction: dict[tuple[str, int], np.ndarray] = {}
    for context_id in map(str, ctx.cfg["selected_source_d1r13_experiment_ids"]):
        group = by_context.get(context_id, {})
        baseline = group.get(("baseline", -1, 0))
        if baseline is None:
            raise ValueError(f"D1R14R2 baseline missing for context {context_id}")
        baseline_values = _visible_outputs5(baseline["trajectory"], scales)[first:]
        columns = []
        direction_passes = []
        for direction_index, direction_name in enumerate(DIRECTIONS):
            positive = group.get(("signed_probe", direction_index, 1))
            negative = group.get(("signed_probe", direction_index, -1))
            if positive is None or negative is None:
                raise ValueError(
                    f"D1R14R2 signed pair missing: {context_id} {direction_name}"
                )
            positive_values = _visible_outputs5(positive["trajectory"], scales)[first:]
            negative_values = _visible_outputs5(negative["trajectory"], scales)[first:]
            if not (
                positive_values.shape
                == negative_values.shape
                == baseline_values.shape
            ):
                raise ValueError("D1R14R2 signed response shape mismatch")
            odd = 0.5 * (positive_values - negative_values)
            even = 0.5 * (positive_values + negative_values) - baseline_values
            odd_peak = float(np.max(np.abs(odd)))
            even_peak = float(np.max(np.abs(even)))
            ratio = even_peak / odd_peak if odd_peak > 0.0 else None
            signal_pass = bool(odd_peak >= minimum_signal - 1e-15)
            symmetry_pass = bool(
                ratio is not None and ratio <= maximum_ratio + 1e-12
            )
            column = odd.reshape(-1)
            norm = float(np.linalg.norm(column))
            if not math.isfinite(norm) or norm <= 0.0:
                normalized = np.full(column.shape, math.nan)
            else:
                normalized = column / norm
            columns.append(normalized)
            odd_by_context_direction[(context_id, direction_index)] = odd
            direction_passes.append(signal_pass and symmetry_pass)
            source_spec = spec_by_id[str(positive["experiment_id"])]
            pair_rows.append(
                {
                    "source_d1r13_experiment_id": context_id,
                    "pair_id": source_spec["pair_id"],
                    "history_member": source_spec["history_member"],
                    "direction_index": direction_index,
                    "direction_name": direction_name,
                    "positive_experiment_id": positive["experiment_id"],
                    "negative_experiment_id": negative["experiment_id"],
                    "odd_peak_normalized_outputs5": odd_peak,
                    "even_peak_normalized_outputs5": even_peak,
                    "even_to_odd_peak_ratio": ratio,
                    "signal_pass": signal_pass,
                    "symmetry_pass": symmetry_pass,
                    "passed": signal_pass and symmetry_pass,
                }
            )
        matrix = np.column_stack(columns)
        finite = bool(np.all(np.isfinite(matrix)))
        singular = (
            np.linalg.svd(matrix, compute_uv=False)
            if finite
            else np.full(4, math.nan)
        )
        rank = (
            int(np.sum(singular > singular[0] * rank_tolerance))
            if finite and singular[0] > 0.0
            else 0
        )
        condition = (
            float(singular[0] / singular[-1])
            if rank == 4 and singular[-1] > 0.0
            else None
        )
        source_spec = next(
            spec
            for spec in specs
            if str(spec["source_d1r13_experiment_id"]) == context_id
        )
        context_pass = bool(
            all(direction_passes)
            and rank == required_rank
            and condition is not None
            and condition <= maximum_condition + 1e-12
        )
        context_rows.append(
            {
                "source_d1r13_experiment_id": context_id,
                "pair_id": source_spec["pair_id"],
                "history_member": source_spec["history_member"],
                "horizon": int(source_spec["horizon_steps"]),
                "singular_values": [
                    float(value) if math.isfinite(float(value)) else None
                    for value in singular
                ],
                "rank": rank,
                "condition_number": condition,
                "direction_gate_pass_count": sum(direction_passes),
                "passed": context_pass,
            }
        )
    history_rows = []
    pair_to_contexts: dict[str, list[str]] = {}
    for row in context_rows:
        pair_to_contexts.setdefault(str(row["pair_id"]), []).append(
            str(row["source_d1r13_experiment_id"])
        )
    for pair_id, contexts in sorted(pair_to_contexts.items()):
        if len(contexts) != 2:
            raise ValueError(f"D1R14R2 hidden-history pair coverage changed: {pair_id}")
        for direction_index, direction_name in enumerate(DIRECTIONS):
            left = odd_by_context_direction[(contexts[0], direction_index)]
            right = odd_by_context_direction[(contexts[1], direction_index)]
            if left.shape != right.shape:
                raise ValueError("D1R14R2 matched-history odd shape changed")
            difference = float(np.max(np.abs(left - right)))
            peak = max(float(np.max(np.abs(left))), float(np.max(np.abs(right))))
            history_rows.append(
                {
                    "pair_id": pair_id,
                    "direction_index": direction_index,
                    "direction_name": direction_name,
                    "context_experiment_ids": contexts,
                    "maximum_absolute_odd_difference": difference,
                    "relative_to_pair_odd_peak": (
                        difference / peak if peak > 0.0 else None
                    ),
                    "report_only": True,
                }
            )
    return {
        "evaluated": True,
        "signed_pair_count": len(pair_rows),
        "signal_pass_count": sum(bool(row["signal_pass"]) for row in pair_rows),
        "symmetry_pass_count": sum(
            bool(row["symmetry_pass"]) for row in pair_rows
        ),
        "context_count": len(context_rows),
        "rank_pass_count": sum(
            int(row["rank"]) == required_rank for row in context_rows
        ),
        "condition_pass_count": sum(
            row["condition_number"] is not None
            and float(row["condition_number"]) <= maximum_condition + 1e-12
            for row in context_rows
        ),
        "minimum_odd_peak_normalized_outputs5": min(
            (float(row["odd_peak_normalized_outputs5"]) for row in pair_rows),
            default=0.0,
        ),
        "maximum_even_to_odd_peak_ratio": max(
            (
                float(row["even_to_odd_peak_ratio"])
                for row in pair_rows
                if row["even_to_odd_peak_ratio"] is not None
            ),
            default=None,
        ),
        "maximum_condition_number": max(
            (
                float(row["condition_number"])
                for row in context_rows
                if row["condition_number"] is not None
            ),
            default=None,
        ),
        "pair_rows": pair_rows,
        "context_rows": context_rows,
        "matched_hidden_history_rows_report_only": history_rows,
        "passed": bool(
            len(pair_rows) == 32
            and all(bool(row["passed"]) for row in pair_rows)
            and len(context_rows) == 8
            and all(bool(row["passed"]) for row in context_rows)
        ),
    }


def _event_passes(
    event: Mapping[str, Any], *, expected_name: str, slot: int, task_step: int
) -> bool:
    criteria = event.get("criteria") or {}
    return bool(
        event.get("event") == expected_name
        and int(event.get("slot", -1)) == slot
        and int(event.get("task_step", -1)) == task_step
        and event.get("passed")
        and criteria
        and all(bool(value) for value in criteria.values())
    )


def postprocess(ctx: Context) -> dict[str, Any]:
    specs = _assert_run_identity(ctx)
    source_d1r13 = {
        str(row["experiment_id"]): row for row in _source_d1r13_results(ctx)
    }
    source_d1r11 = {
        str(row["experiment_id"]): row for row in d1r13._source_results(ctx.source_ctx)
    }
    evaluators, _ = d1r11._formal_callback(ctx.source_ctx.source_ctx, specs)
    rows = []
    valid_results: dict[str, dict[str, Any]] = {}
    controller_cfg = ctx.cfg["controller_contract"]
    for spec in specs:
        experiment_id = str(spec["experiment_id"])
        path = ctx.paths.raw / f"{experiment_id}.json.gz"
        if not _result_complete(path, spec, require_success=False):
            rows.append(
                {
                    "experiment_id": experiment_id,
                    "source_d1r13_experiment_id": spec["source_d1r13_experiment_id"],
                    "role": spec["d1r14r2_role"],
                    "execution_failure_class": "runtime_or_raw_error",
                    "runtime_success": False,
                    "prefix_pass": False,
                    "safety_pass": False,
                    "passed": False,
                }
            )
            continue
        result = _read_gz(path)
        valid_results[experiment_id] = result
        source13 = source_d1r13[str(spec["source_d1r13_experiment_id"])]
        source11 = source_d1r11[str(spec["source_d1r11_experiment_id"])]
        trajectory = result.get("trajectory") or []
        trace = result.get("controller_trace") or []
        horizon = int(spec["horizon_steps"])
        full_horizon = len(trajectory) == horizon + 1 and len(trace) == horizon
        prefix_state = bool(
            len(trajectory) >= PREFIX_END + 1
            and all(
                _semantic_state(current) == _semantic_state(reference)
                for current, reference in zip(
                    trajectory[: PREFIX_END + 1],
                    source13["trajectory"][: PREFIX_END + 1],
                )
            )
        )
        prefix_trace = bool(
            len(trace) >= PREFIX_END
            and all(
                _source_trace_projection(reference, current)
                for current, reference in zip(
                    trace[:PREFIX_END], source11["controller_trace"][:PREFIX_END]
                )
            )
        )
        calibration = _calibration_exact(trace)
        currents = np.asarray(
            [row.get("currents_a_tsc", []) for row in trajectory], dtype=float
        )
        wire_currents = [
            np.asarray(row.get("wire_currents_a", []), dtype=float)
            for row in trajectory
        ]
        finite = bool(
            full_horizon
            and currents.shape == (horizon + 1, N_COILS)
            and np.all(np.isfinite(currents))
            and all(
                values.size > 0 and np.all(np.isfinite(values))
                for values in wire_currents
            )
            and all(
                math.isfinite(float(state[key]))
                for state in trajectory
                for key in ("R", "Z", "Ip")
            )
            and not any(bool(state.get("abnormal")) for state in trajectory)
        )
        forbidden = sum(
            any(bool(row.get(key)) for key in FORBIDDEN_TRACE_KEYS) for row in trace
        )
        payload = _read_json(ctx.paths.variants / f"payload_{experiment_id}.json")
        minimum, maximum = d1r11.s21.s13._current_limits_tsc(payload)
        center = 0.5 * (minimum + maximum)
        half = 0.5 * (maximum - minimum)
        utilization = (
            float(np.max(np.abs((currents - center) / half)))
            if currents.shape == (horizon + 1, N_COILS)
            else None
        )
        formal = (
            evaluators[experiment_id].evaluate(
                np.asarray(
                    [[row["R"], row["Z"], row["Ip"]] for row in trajectory],
                    dtype=float,
                )
            )
            if full_horizon
            else {"formal_contract_pass": False}
        )
        baseline_reproduction = False
        baseline_zero_actions = False
        baseline_zero_currents = False
        issue_exact = False
        cancel_exact = False
        zero_after_actions = False
        zero_after_currents = False
        role = str(spec["d1r14r2_role"])
        if role == "baseline" and full_horizon:
            baseline_reproduction = bool(
                len(source13["trajectory"]) == len(trajectory)
                and all(
                    _semantic_state(current) == _semantic_state(reference)
                    for current, reference in zip(
                        trajectory, source13["trajectory"]
                    )
                )
                and [row.get("action_norm_tsc") for row in trace]
                == [
                    row.get("action_norm_tsc")
                    for row in source13["controller_trace"]
                ]
            )
            actions = np.asarray(
                [row.get("action_norm_tsc", []) for row in trace[PREFIX_END:]],
                dtype=float,
            )
            delta = np.diff(currents[PREFIX_END:], axis=0)
            baseline_zero_actions = bool(
                actions.shape == (horizon - PREFIX_END, N_COILS)
                and np.array_equal(actions, np.zeros_like(actions))
            )
            baseline_zero_currents = bool(
                delta.shape == (horizon - PREFIX_END, N_COILS)
                and np.array_equal(delta, np.zeros_like(delta))
            )
            role_pass = bool(
                baseline_reproduction
                and baseline_zero_actions
                and baseline_zero_currents
            )
        elif role == "signed_probe" and full_horizon:
            direction_index = int(spec["d1r14r2_direction_index"])
            expected_coordinate = list(map(float, spec["d1r14r2_requested_coordinate"]))
            issue = trace[ISSUE_STEP].get("r3c3t13s24d1r14r2_event_detail") or {}
            cancel = trace[CANCEL_STEP].get("r3c3t13s24d1r14r2_event_detail") or {}
            issue_exact = bool(
                _event_passes(
                    issue,
                    expected_name="sequential_issue",
                    slot=direction_index,
                    task_step=ISSUE_STEP,
                )
                and list(map(float, issue.get("requested_coordinate", [])))
                == expected_coordinate
            )
            cancel_exact = bool(
                _event_passes(
                    cancel,
                    expected_name="sequential_cancel",
                    slot=direction_index,
                    task_step=CANCEL_STEP,
                )
                and cancel.get("stored_center_card15_fields")
                == issue.get("center_card15_fields")
            )
            actions = np.asarray(
                [row.get("action_norm_tsc", []) for row in trace[ZERO_AFTER:]],
                dtype=float,
            )
            delta = np.diff(currents[ZERO_AFTER:], axis=0)
            zero_after_actions = bool(
                actions.shape == (horizon - ZERO_AFTER, N_COILS)
                and np.array_equal(actions, np.zeros_like(actions))
            )
            zero_after_currents = bool(
                delta.shape == (horizon - ZERO_AFTER, N_COILS)
                and np.array_equal(delta, np.zeros_like(delta))
            )
            role_pass = bool(
                issue_exact
                and cancel_exact
                and zero_after_actions
                and zero_after_currents
            )
        else:
            role_pass = False
        prefix_pass = bool(prefix_state and prefix_trace and calibration)
        safety_pass = bool(
            result.get("success")
            and full_horizon
            and prefix_pass
            and role_pass
            and finite
            and forbidden == 0
            and utilization is not None
            and utilization
            <= float(controller_cfg["maximum_current_utilization"]) + 1e-12
        )
        rows.append(
            {
                "experiment_id": experiment_id,
                "source_d1r13_experiment_id": spec["source_d1r13_experiment_id"],
                "source_d1r11_experiment_id": spec["source_d1r11_experiment_id"],
                "pair_id": spec["pair_id"],
                "history_member": spec["history_member"],
                "role": role,
                "direction_index": int(spec["d1r14r2_direction_index"]),
                "direction_name": str(spec["d1r14r2_direction_name"]),
                "sign": int(spec["d1r14r2_sign"]),
                "horizon": horizon,
                "runtime_success": bool(result.get("success")),
                "execution_failure_class": str(
                    result.get("execution_failure_class") or ""
                ),
                "full_horizon": full_horizon,
                "source_prefix_state_exact": prefix_state,
                "source_prefix_trace_exact": prefix_trace,
                "calibration_exact": calibration,
                "prefix_pass": prefix_pass,
                "fresh_baseline_reproduces_d1r13": baseline_reproduction,
                "baseline_actions_exact_zero": baseline_zero_actions,
                "baseline_current_increments_exact_zero": baseline_zero_currents,
                "issue_exact": issue_exact,
                "cancel_exact": cancel_exact,
                "zero_after_cancel_actions_exact": zero_after_actions,
                "zero_after_cancel_current_increments_exact": zero_after_currents,
                "finite": finite,
                "forbidden_trace_count": forbidden,
                "maximum_current_utilization": utilization,
                "formal_contract_pass_diagnostic_only": bool(
                    formal.get("formal_contract_pass")
                ),
                "failure_reason": result.get("failure_reason", ""),
                "safety_pass": safety_pass,
                "passed": safety_pass,
            }
        )
    inventory = _raw_inventory(ctx.paths.raw)
    runtime_error_count = sum(
        row.get("execution_failure_class")
        in {"runtime_or_raw_error", "runtime_or_controller_error", "ray_actor_runtime_error"}
        for row in rows
    )
    prefix_failure_count = sum(not bool(row.get("prefix_pass")) for row in rows)
    plant_failure_count = sum(
        str(row.get("execution_failure_class", "")).startswith("plant_")
        for row in rows
    )
    action_safety_failure_count = sum(
        row.get("execution_failure_class")
        in {"controller_action_safety_gate_failure", "controller_or_action_semantics_error"}
        for row in rows
    )
    safety_pass_count = sum(bool(row.get("safety_pass")) for row in rows)
    if safety_pass_count == 72 and len(valid_results) == 72:
        geometry = _response_geometry(ctx, specs, valid_results)
    else:
        geometry = {
            "evaluated": False,
            "passed": False,
            "reason": "safety_or_prefix_gate_failed",
        }
    if runtime_error_count > 0 or prefix_failure_count > 0 or inventory["count"] != 72:
        route = ctx.cfg["routes"]["runtime_fail"]
    elif safety_pass_count != 72:
        route = ctx.cfg["routes"]["safety_fail"]
    elif not geometry.get("passed"):
        route = ctx.cfg["routes"]["geometry_fail"]
    else:
        route = ctx.cfg["routes"]["pass"]
    passed = route == ctx.cfg["routes"]["pass"]
    output = {
        "schema_version": 1,
        "stage": STAGE,
        "campaign_identity": CAMPAIGN_IDENTITY,
        "controller_revision": CONTROLLER_REVISION,
        "expected_task_count": 72,
        "actual_row_count": len(rows),
        "strict_raw_count": len(valid_results),
        "safety_pass_count": safety_pass_count,
        "runtime_error_count": runtime_error_count,
        "prefix_failure_count": prefix_failure_count,
        "plant_failure_count": plant_failure_count,
        "action_safety_failure_count": action_safety_failure_count,
        "baseline_reproduction_count": sum(
            bool(row.get("fresh_baseline_reproduces_d1r13")) for row in rows
        ),
        "issue_exact_count": sum(bool(row.get("issue_exact")) for row in rows),
        "cancel_exact_count": sum(bool(row.get("cancel_exact")) for row in rows),
        "finite_count": sum(bool(row.get("finite")) for row in rows),
        "forbidden_trace_count": sum(
            int(row.get("forbidden_trace_count", 0)) for row in rows
        ),
        "formal_tracking_pass_count_diagnostic_only": sum(
            bool(row.get("formal_contract_pass_diagnostic_only")) for row in rows
        ),
        "maximum_current_utilization": max(
            (
                float(row["maximum_current_utilization"])
                for row in rows
                if row.get("maximum_current_utilization") is not None
            ),
            default=None,
        ),
        "raw_inventory": inventory,
        "response_geometry": geometry,
        "rows": rows,
        "route": route,
        "passed": passed,
        "scientific_scope": {
            "formal_tracking_diagnostic_only": True,
            "time_distributed_identification_validated": False,
            "transition_model_validated": False,
            "mpc_validated": False,
            "long_hold_validated": False,
            "expert_data_allowed": False,
            "bc_dagger_or_rl_allowed": False,
        },
    }
    _write_json(ctx.paths.analysis / "final_result.json", output)
    _write_json(ctx.paths.run_dir / "final_result.json", output)
    state = _read_json(ctx.paths.state)
    state.update(
        {
            "phase_status": "complete" if passed else "failed",
            "finished": True,
            "primary_pass": passed,
            "real_tsc_executed": True,
            "new_raw_count": inventory["count"],
            "stop_reason": "" if passed else route,
            "verdict": {"route": route, "passed": passed},
        }
    )
    _write_json(ctx.paths.state, state)
    return output


def run_real(ctx: Context, *, backend: str, resume: bool) -> dict[str, Any]:
    state = _read_json(ctx.paths.state)
    if state.get("phase_status") != "offline_ready" or bool(state.get("finished")):
        raise ValueError("D1R14R2 run requires offline_ready state")
    specs = _assert_run_identity(ctx)
    execution = evaluate_specs(ctx, specs, backend=backend, resume=resume)
    state.update(
        {
            "phase_status": "real_complete",
            "real_tsc_executed": True,
            "new_raw_count": len(list(ctx.paths.raw.glob("*.json.gz"))),
        }
    )
    _write_json(ctx.paths.state, state)
    _write_json(ctx.paths.analysis / "execution.json", execution)
    return execution


def execute(
    ctx: Context, *, command: str, backend: str, resume: bool
) -> dict[str, Any]:
    if command == "offline":
        if resume:
            raise ValueError("D1R14R2 offline does not support resume")
        return prepare_offline(ctx)
    if command == "run":
        return run_real(ctx, backend=backend, resume=resume)
    if command == "postprocess":
        state = _read_json(ctx.paths.state)
        if state.get("phase_status") != "real_complete" or bool(state.get("finished")):
            raise ValueError("D1R14R2 postprocess requires real_complete state")
        return postprocess(ctx)
    raise ValueError(f"unsupported D1R14R2 command: {command}")


def self_test(config_path: Path) -> dict[str, Any]:
    config_path = config_path.expanduser().resolve()
    cfg = _read_json(config_path)
    _validate_config(cfg, config_path)
    action = zero_action(ISSUE_STEP)
    synthetic = np.column_stack(
        [
            np.eye(4, dtype=float)[:, index]
            for index in range(4)
        ]
    )
    singular = np.linalg.svd(synthetic, compute_uv=False)
    requested = np.asarray(
        cfg["controller_contract"]["requested_coordinate_matrix_columns"],
        dtype=float,
    )
    return {
        "stage": STAGE,
        "selected_context_count": len(cfg["selected_source_d1r13_experiment_ids"]),
        "expected_task_count": cfg["controller_contract"]["expected_task_count"],
        "issue_step": ISSUE_STEP,
        "cancel_step": CANCEL_STEP,
        "zero_after_step": ZERO_AFTER,
        "zero_action_width": len(action),
        "zero_action_exact": bool(np.array_equal(action, np.zeros(N_COILS))),
        "direction_names": list(DIRECTIONS),
        "requested_matrix_digest": _matrix_digest(requested),
        "synthetic_rank": int(np.linalg.matrix_rank(synthetic)),
        "synthetic_condition": float(singular[0] / singular[-1]),
        "real_tsc_executed": False,
        "passed": True,
    }


def _source_kwargs(args: argparse.Namespace) -> dict[str, Path]:
    return d1r13._source_kwargs(args)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--source-d1r13-run", type=Path, required=True)
    parser.add_argument("--source-d1r13-audit", type=Path, required=True)
    parser.add_argument("--source-r1a-output", type=Path, required=True)
    parser.add_argument("--source-d1r11-run", type=Path, required=True)
    parser.add_argument("--source-s21-run", type=Path, required=True)
    parser.add_argument("--source-s23r1-output", type=Path, required=True)
    parser.add_argument("--source-s24-run", type=Path, required=True)
    parser.add_argument("--source-d1r9-v1", type=Path, required=True)
    parser.add_argument("--source-d1r9-v2", type=Path, required=True)
    parser.add_argument("--source-d1r10-run", type=Path, required=True)
    parser.add_argument("--source-d1r10-audit", type=Path, required=True)
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
        "--command", choices=("offline", "run", "postprocess"), required=True
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
        source_d1r13_run=args.source_d1r13_run,
        source_d1r13_audit=args.source_d1r13_audit,
        source_r1a_output=args.source_r1a_output,
        source_d1r11_run=args.source_d1r11_run,
        run_dir=args.run_dir,
        source_s21_run=args.source_s21_run,
        source_s23r1_output=args.source_s23r1_output,
        source_s24_run=args.source_s24_run,
        source_d1r9_v1=args.source_d1r9_v1,
        source_d1r9_v2=args.source_d1r9_v2,
        source_d1r10_run=args.source_d1r10_run,
        source_d1r10_audit=args.source_d1r10_audit,
        **_source_kwargs(args),
    )
    result = execute(
        ctx,
        command=args.command,
        backend=args.backend,
        resume=bool(args.resume),
    )
    print(json.dumps(result, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
