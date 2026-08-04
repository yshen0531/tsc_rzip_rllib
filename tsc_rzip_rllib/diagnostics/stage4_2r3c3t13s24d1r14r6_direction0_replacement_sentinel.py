"""Stage4.2R3c3T13S24D1R14R6 direction-0 replacement sentinel."""

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
    stage4_2r3c3t13s24d1r14r2_mixed_basis_signed_excitation_sentinel as d1r14r2,
    stage4_2r3c3t13s24d1r14r4_time_shifted_sign_split_sentinel as source_r4,
)


d1r11 = d1r13.d1r11
SCHEMA_VERSION = 1
STAGE = "Stage4.2R3c3T13S24D1R14R6"
RUN_NAME = "stage4_2r3c3t13s24d1r14r6_direction0_replacement_sentinel"
CAMPAIGN_IDENTITY = "direction0_replacement_safety_identification_sentinel_v1"
CONTROLLER_REVISION = "direction0_replacement_v42r3c3t13s24d1r14r6_v1"
N_COILS = 14
PREFIX_END = 10
ISSUE_STEPS = (14, 18, 22)
CANCEL_OFFSET = 1
ZERO_AFTER_OFFSET = 2
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
    source_r2_run: Path
    source_r3_initial_output: Path
    source_r3_corrected_output: Path
    source_r4_run: Path
    source_r5_output: Path
    paths: Paths


def _validate_config(cfg: Mapping[str, Any], path: Path) -> None:
    root = _project_root()
    exact = {
        "schema_version": 1,
        "stage": STAGE,
        "run_name": RUN_NAME,
        "campaign_identity": CAMPAIGN_IDENTITY,
        "controller_revision": CONTROLLER_REVISION,
        "package_revision": "r42r3c3t13s24d1r14r6_direction0_replacement_v1",
    }
    for key, value in exact.items():
        if cfg.get(key) != value:
            raise ValueError(f"D1R14R6 frozen {key} changed")
    for key in ("design_document", "source_d1r13_config"):
        source = (root / str(cfg[key])).resolve()
        if root not in source.parents or not source.is_file():
            raise ValueError(f"D1R14R6 {key} is outside package")
        if _sha256(source) != str(cfg[f"{key}_sha256"]):
            raise ValueError(f"D1R14R6 {key} hash changed")
    expected_r4 = {
        "run_name": "stage4_2r3c3t13s24d1r14r4_time_shifted_sign_split_sentinel_20260804_f5b8348_v1",
        "stage_directory": source_r4.RUN_NAME,
        "package_checkpoint": "f5b8348",
        "package_digest": "c9c6fc870618ecbefe1bf9891a6f918927c2062753e2750596d2e73ec7ecf523",
        "raw_count": 200,
        "raw_total_bytes": 6285765,
        "raw_inventory_digest": "44a7eb8e677f88f32c57a6be59273501e73f7657527371e1b59578a95c2ae7a9",
        "spec_digest": "080a2df84c86801d76251853a165839e8db59f6614f6b2b446141b0691841059",
        "final_result_sha256": "af9acfb9e524e6ad33799b832981ec7fb2e265ff7c1d3e78796413e83382db71",
        "independent_result_sha256": "6a4eec4a660beb6a29e11e184906b8b7a737834280091f1997af74e86fbd761c",
        "required_route": "TIME_SHIFTED_SIGN_SPLIT_SENTINEL_GEOMETRY_FAIL_REDESIGN_REQUIRED",
        "required_safety_pass_count": 200,
        "required_baseline_count": 8,
        "required_retained_probe_count": 144,
    }
    if dict(cfg["source_r4_contract"]) != expected_r4:
        raise ValueError("D1R14R6 immutable R4 contract changed")
    expected_r5 = {
        "output_name": "stage4_2r3c3t13s24d1r14r5_global_direction0_gain_preflight_20260804_bb829f3_v3",
        "final_package_checkpoint": "a4c43bb",
        "compact_evidence_sha256": "930a36087efca7fb1a6ffa7ce31f76835db48ffd56154a38bd282f7316c2d6ad",
        "primary_detailed_sha256": "deb57e9c774ef792ed9f8464987e4528b69f3876a09dcd7ff4ca55ea8d9dedc9",
        "primary_summary_sha256": "fc9d1fded5bf63e2658ad0c8da5aca642011006edd04ae1ee8aaaec58051a213",
        "primary_manifest_sha256": "be2b358bbe35f5fff1029f4cb94b8a1638fd7e5b2c3bb244fe51fb1de0fd0d35",
        "independent_result_sha256": "306fd16a65ad44bea1972fb37f4ce316363eeff8a3834ceea8973afe1f42f3cb",
        "required_route": "GLOBAL_DIRECTION0_GAIN_PREFLIGHT_PASS_REAL_SENTINEL_DESIGN_REQUIRED",
        "required_construction_pass_count": 48,
        "required_antipodal_pair_pass_count": 24,
        "required_new_raw_count": 0,
        "required_tsc_executed": False,
    }
    if dict(cfg["source_r5_contract"]) != expected_r5:
        raise ValueError("D1R14R6 immutable R5 contract changed")
    r3 = cfg["source_r3_contract"]
    expected_r3 = {
        "initial_output_name": "stage4_2r3c3t13s24d1r14r3_sign_split_response_feasibility_20260804_85012c1_v1",
        "corrected_output_name": "stage4_2r3c3t13s24d1r14r3_sign_split_response_feasibility_20260804_ca49a36_v2",
        "design_checkpoint": "343a516",
        "source_hash_hotfix_checkpoint": "aa3325a",
        "package_checkpoint": "ca49a36",
        "config": "configs/stage4_2r3c3t13s24d1r14r3_sign_split_response_feasibility_v1.json",
        "config_sha256": "a3537ff0012f25929949e2d7f00c523e622b74a3ca35f0af44ac7a1ccc44e626",
        "primary_implementation": "tsc_rzip_rllib/diagnostics/stage4_2r3c3t13s24d1r14r3_sign_split_response_feasibility.py",
        "primary_implementation_sha256": "944d7fc2a016dfac67041690acc60d0fb4374deace6d72ca90d754334c36397d",
        "independent_implementation": "docs/codex/audit_tools/stage4_2r3c3t13s24d1r14r3_independent_forensics.py",
        "independent_implementation_sha256": "15e90d8662fc18ed255a0fd3bfe0020e5a3b15e1f71f1762f136b45ec3179d9d",
        "source_hash_erratum": "docs/codex/reports/STAGE4_2R3C3T13S24D1R14R3_SOURCE_STATE_HASH_ERRATUM.md",
        "source_hash_erratum_sha256": "720a9537f6f468c3131ccbf72f2d0e3cdce53a8ec310a76ad33e84270719a85f",
        "initial_primary_sha256": "945bb981df05940b26cd4087b3b9404583aa0adf2dd6d66036f9bf3bc1c46857",
        "initial_independent_sha256": "044564fb42c2741080f44fdf2a9f6c6202601adc3fc92aa2276c318171ca945d",
        "corrected_primary_sha256": "30755ebccee65a5bcfd08d04632368979ec1c309ac42d4a46df49b3b921cd590",
        "corrected_independent_sha256": "f138611d56b77839bb3d87744b49eb08df4c4409947038e25b520f8d43764d90",
        "compact_manifest_sha256": "cd8c6c679cbe78b02141358a55928896be6623488b81de73b8bd876a5a6d546f",
        "required_initial_route": "SIGN_SPLIT_RESPONSE_FEASIBILITY_SOURCE_FAIL_NO_TSC",
        "required_corrected_route": "SIGN_SPLIT_RESPONSE_FEASIBILITY_PASS_TIME_SHIFT_SENTINEL_DESIGN_REQUIRED",
        "required_signal_pass_count": 64,
        "required_rank_pass_count": 16,
        "required_condition_pass_count": 16,
        "required_issue_symmetry_count": 32,
        "required_new_raw_count": 0,
        "required_tsc_executed": False,
    }
    if dict(r3) != expected_r3:
        raise ValueError("D1R14R6 immutable R3 contract changed")
    for key in (
        "config",
        "primary_implementation",
        "independent_implementation",
        "source_hash_erratum",
    ):
        source_path = (root / str(r3[key])).resolve()
        if root not in source_path.parents or not source_path.is_file():
            raise ValueError(f"D1R14R6 R3 {key} is outside package")
        if _sha256(source_path) != str(r3[f"{key}_sha256"]):
            raise ValueError(f"D1R14R6 R3 {key} hash changed")
    r2 = cfg["source_r2_contract"]
    expected_r2 = {
        "run_name": "stage4_2r3c3t13s24d1r14r2_mixed_basis_signed_excitation_sentinel_20260804_ca2815a_v1",
        "package_checkpoint": "ca2815a",
        "raw_count": 72,
        "raw_total_bytes": 2254876,
        "raw_inventory_digest": "c210f959e5ce85739dd0b1f70a2513f64f40c6697d01bf7b56db9621759a1649",
        "final_result_sha256": "3df193e52ee0ce8fe72620af9f72597f58af4419c6386c37d62fb051bcefd79a",
        "independent_result_sha256": "68f21e95694c607084b9cc7d39732bcda05d57a14f6f3cc4f1e78e8941e7e2df",
        "required_route": "MIXED_BASIS_SENTINEL_RESPONSE_GEOMETRY_FAIL_REDESIGN_REQUIRED",
        "required_safety_pass_count": 72,
        "required_baseline_count": 8,
        "required_signed_probe_count": 64,
        "required_issue_task_step": 10,
    }
    if dict(r2) != expected_r2:
        raise ValueError("D1R14R6 immutable R2 contract changed")
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
        raise ValueError("D1R14R6 immutable R1A contract changed")
    for key in ("config", "implementation"):
        source_path = (root / str(r1a[key])).resolve()
        if root not in source_path.parents or not source_path.is_file():
            raise ValueError(f"D1R14R6 R1A {key} is outside package")
        if _sha256(source_path) != str(r1a[f"{key}_sha256"]):
            raise ValueError(f"D1R14R6 R1A {key} hash changed")
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
        raise ValueError("D1R14R6 immutable source contract changed")
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
        raise ValueError("D1R14R6 selected D1R13 identities changed")
    controller = cfg["controller_contract"]
    requested_matrix = np.asarray(
        controller["requested_coordinate_matrix_columns"], dtype=float
    )
    expected_controller = {
        "delegated_last_task_step": 9,
        "issue_task_steps": [14, 18, 22],
        "cancel_step_offset": 1,
        "zero_after_cancel_step_offset": 2,
        "zero_action_width": 14,
        "direction_names": list(DIRECTIONS),
        "requested_coordinate_matrix_columns": requested_matrix.tolist(),
        "requested_matrix_float64_le_c_sha256": "69528f0e204b51847c1d2a7df428555a557454e9fa6bc76768d39e7cc5a90da8",
        "executed_direction_index": 0,
        "source_baseline_count": 8,
        "baseline_count": 0,
        "signed_probe_count": 48,
        "expected_task_count": 48,
        "expected_baseline_post_prefix_action_count": 0,
        "expected_probe_preissue_zero_action_count": 384,
        "expected_probe_issue_count": 48,
        "expected_probe_cancel_count": 48,
        "expected_probe_zero_after_cancel_action_count": 768,
        "maximum_incremental_normalized_action_linf": 0.25,
        "maximum_online_cancel_incremental_linf": 0.24,
        "maximum_total_normalized_action_abs": 1.0,
        "maximum_current_utilization": 0.55,
        "minimum_desired_applied_current_cosine": 0.98,
        "maximum_relative_off_basis_residual": 0.10,
        "require_exact_stored_center_cancellation": True,
        "require_exact_zero_target_jump_net": True,
        "require_exact_source_prefix": True,
        "require_fresh_baseline_reproduction": False,
        "require_exact_r4_baseline_issue_state_reproduction": True,
        "forbid_future_r17_controller_execution": True,
    }
    if (
        requested_matrix.shape != (4, 4)
        or not np.all(np.isfinite(requested_matrix))
        or _matrix_digest(requested_matrix)
        != controller["requested_matrix_float64_le_c_sha256"]
        or dict(controller) != expected_controller
    ):
        raise ValueError("D1R14R6 controller contract changed")
    geometry = cfg["response_geometry"]
    expected_geometry = {
        "visible_output_names": ["R", "Z", "vR", "vZ", "Ip"],
        "visible_output_scales": [0.03, 0.03, 0.1, 0.1, 10000.0],
        "combined_issue_task_steps": [10, 14, 18, 22],
        "minimum_direction_peak_normalized_outputs5": 0.005,
        "rank_relative_tolerance": 1e-10,
        "required_rank": 4,
        "maximum_condition_number": 20.0,
        "normalize_columns_to_unit_l2": True,
        "expected_branch_count": 64,
        "expected_branch_direction_count": 256,
        "cross_sign_symmetry_is_acceptance_gate": False,
        "matched_hidden_history_response_is_report_only": True,
        "cross_time_response_difference_is_report_only": True,
    }
    if dict(geometry) != expected_geometry:
        raise ValueError("D1R14R6 response geometry changed")
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
        raise ValueError("D1R14R6 formal timing changed")
    if int(cfg["parallel"]["n_workers"]) != 96:
        raise ValueError("D1R14R6 Ray capacity changed")
    if cfg["routes"] != {
        "offline_fail": "DIRECTION0_REPLACEMENT_SENTINEL_SOURCE_FAIL_NO_TSC",
        "runtime_fail": "DIRECTION0_REPLACEMENT_SENTINEL_EXECUTION_OR_SAFETY_FAIL_STOP",
        "safety_fail": "DIRECTION0_REPLACEMENT_SENTINEL_EXECUTION_OR_SAFETY_FAIL_STOP",
        "geometry_fail": "DIRECTION0_REPLACEMENT_SENTINEL_GEOMETRY_FAIL_REDESIGN_REQUIRED",
        "pass": "DIRECTION0_REPLACEMENT_SENTINEL_PASS_MODEL_FIT_DESIGN_REQUIRED",
    }:
        raise ValueError("D1R14R6 routes changed")
    if (
        not bool(cfg["identification_only"])
        or not bool(cfg["formal_tracking_diagnostic_only"])
        or bool(cfg["probe_trajectories_allowed_in_expert_dataset"])
        or bool(cfg["bc_dagger_or_rl_allowed"])
    ):
        raise ValueError("D1R14R6 scope changed")
    expected_path = root / "configs/stage4_2r3c3t13s24d1r14r6_direction0_replacement_sentinel_370ms.json"
    if path.resolve() != expected_path.resolve():
        raise ValueError("D1R14R6 config path changed")


def load_config(
    config_path: Path,
    *,
    source_d1r13_run: Path,
    source_d1r13_audit: Path,
    source_r1a_output: Path,
    source_r2_run: Path,
    source_r3_initial_output: Path,
    source_r3_corrected_output: Path,
    source_r4_run: Path,
    source_r5_output: Path,
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
    source_r2_run = source_r2_run.expanduser().resolve()
    source_r3_initial_output = source_r3_initial_output.expanduser().resolve()
    source_r3_corrected_output = source_r3_corrected_output.expanduser().resolve()
    source_r4_run = source_r4_run.expanduser().resolve()
    source_r5_output = source_r5_output.expanduser().resolve()
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
        raise ValueError("D1R14R6 source D1R13 run path changed")
    return Context(
        cfg=cfg,
        config_path=config_path,
        source_ctx=source_ctx,
        source_d1r13_run=source_d1r13_run,
        source_d1r13_audit=source_d1r13_audit,
        source_r1a_output=source_r1a_output,
        source_r2_run=source_r2_run,
        source_r3_initial_output=source_r3_initial_output,
        source_r3_corrected_output=source_r3_corrected_output,
        source_r4_run=source_r4_run,
        source_r5_output=source_r5_output,
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
            raise ValueError(f"D1R14R6 invalid selected D1R13 source: {experiment_id}")
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
        raise ValueError("D1R14R6 immutable R1A source changed")
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
        raise ValueError("D1R14R6 R1A scientific boundary changed")
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


def _authenticate_r3_r2(ctx: Context) -> dict[str, Any]:
    r3_contract = ctx.cfg["source_r3_contract"]
    r2_contract = ctx.cfg["source_r2_contract"]
    if (
        ctx.source_r3_initial_output.name != r3_contract["initial_output_name"]
        or ctx.source_r3_corrected_output.name
        != r3_contract["corrected_output_name"]
        or ctx.source_r2_run.name != r2_contract["run_name"]
    ):
        raise ValueError("D1R14R6 R3/R2 source directory identity changed")
    r3_paths = {
        "initial_primary": ctx.source_r3_initial_output
        / "stage4_2r3c3t13s24d1r14r3_primary_v1.json",
        "initial_independent": ctx.source_r3_initial_output
        / "stage4_2r3c3t13s24d1r14r3_independent_v1.json",
        "corrected_primary": ctx.source_r3_corrected_output
        / "stage4_2r3c3t13s24d1r14r3_primary_v1.json",
        "corrected_independent": ctx.source_r3_corrected_output
        / "stage4_2r3c3t13s24d1r14r3_independent_v1.json",
        "compact_manifest": ctx.source_r3_corrected_output
        / "compact_evidence_manifest_v2.json",
    }
    expected_hashes = {
        name: str(r3_contract[f"{name}_sha256"])
        for name in r3_paths
    }
    hashes = {name: _sha256(path) for name, path in r3_paths.items()}
    if any(not path.is_file() for path in r3_paths.values()) or hashes != expected_hashes:
        raise ValueError("D1R14R6 R3 compact source hashes changed")
    initial_primary = _read_json(r3_paths["initial_primary"])
    initial_independent = _read_json(r3_paths["initial_independent"])
    corrected_primary = _read_json(r3_paths["corrected_primary"])
    corrected_independent = _read_json(r3_paths["corrected_independent"])
    split = corrected_primary.get("sign_split_geometry") or {}
    issue = corrected_primary.get("issue_coordinate_and_field_symmetry") or {}
    execution = corrected_primary.get("execution") or {}
    if (
        initial_primary.get("route") != r3_contract["required_initial_route"]
        or initial_independent.get("route")
        != r3_contract["required_initial_route"]
        or bool(initial_primary.get("passed"))
        or bool(initial_independent.get("passed"))
        or corrected_primary.get("route")
        != r3_contract["required_corrected_route"]
        or corrected_independent.get("route")
        != r3_contract["required_corrected_route"]
        or corrected_primary.get("passed") is not True
        or corrected_independent.get("passed") is not True
        or corrected_independent.get("primary_exact_agreement") is not True
        or int(split.get("signal_pass_count", -1))
        != int(r3_contract["required_signal_pass_count"])
        or int(split.get("rank_pass_count", -1))
        != int(r3_contract["required_rank_pass_count"])
        or int(split.get("condition_pass_count", -1))
        != int(r3_contract["required_condition_pass_count"])
        or int(issue.get("coordinate_exact_count", -1))
        != int(r3_contract["required_issue_symmetry_count"])
        or int(issue.get("physical_field_exact_count", -1))
        != int(r3_contract["required_issue_symmetry_count"])
        or int(execution.get("new_raw_count", -1))
        != int(r3_contract["required_new_raw_count"])
        or bool(execution.get("tsc_executed"))
        != bool(r3_contract["required_tsc_executed"])
    ):
        raise ValueError("D1R14R6 R3 scientific source boundary changed")
    r2_stage = ctx.source_r2_run / d1r14r2.RUN_NAME
    r2_inventory = _raw_inventory(r2_stage / "raw")
    r2_final_path = r2_stage / "analysis" / "final_result.json"
    r2_independent_path = ctx.source_r2_run / "server_independent_forensics_v1.json"
    r2_final = _read_json(r2_final_path)
    r2_independent = _read_json(r2_independent_path)
    r2_specs = _read_json(r2_stage / "specs" / "sentinel_specs.json")
    if (
        r2_inventory["count"] != int(r2_contract["raw_count"])
        or r2_inventory["bytes"] != int(r2_contract["raw_total_bytes"])
        or r2_inventory["digest"] != r2_contract["raw_inventory_digest"]
        or _sha256(r2_final_path) != r2_contract["final_result_sha256"]
        or _sha256(r2_independent_path) != r2_contract["independent_result_sha256"]
        or r2_final.get("route") != r2_contract["required_route"]
        or r2_independent.get("independent_route") != r2_contract["required_route"]
        or r2_independent.get("audit_completed") is not True
        or int(r2_final.get("safety_pass_count", -1))
        != int(r2_contract["required_safety_pass_count"])
        or len(r2_specs) != int(r2_contract["raw_count"])
        or sum(spec.get("d1r14r2_role") == "baseline" for spec in r2_specs)
        != int(r2_contract["required_baseline_count"])
        or sum(spec.get("d1r14r2_role") == "signed_probe" for spec in r2_specs)
        != int(r2_contract["required_signed_probe_count"])
        or any(
            int(spec.get("d1r14r2_issue_task_step", -1))
            != int(r2_contract["required_issue_task_step"])
            for spec in r2_specs
            if spec.get("d1r14r2_role") == "signed_probe"
        )
    ):
        raise ValueError("D1R14R6 R2 authentic source boundary changed")
    return {
        "r3_paths": {name: str(path) for name, path in r3_paths.items()},
        "r3_hashes": hashes,
        "r3_split_aggregate": {
            key: value for key, value in split.items() if key != "rows"
        },
        "r2_run": str(ctx.source_r2_run),
        "r2_stage": str(r2_stage),
        "r2_inventory": r2_inventory,
        "r2_final_sha256": _sha256(r2_final_path),
        "r2_independent_sha256": _sha256(r2_independent_path),
        "r2_specs_count": len(r2_specs),
        "passed": True,
    }


def _authenticate_r4_r5(ctx: Context) -> dict[str, Any]:
    """Authenticate the real R4 bank and the zero-TSC R5 gain decision."""
    r4_contract = ctx.cfg["source_r4_contract"]
    r4_stage = ctx.source_r4_run / source_r4.RUN_NAME
    r4_specs_path = r4_stage / "specs" / "sentinel_specs.json"
    r4_manifest_path = r4_stage / "stage_manifest.json"
    r4_final_path = ctx.source_r4_run / "final_result.json"
    r4_independent_path = ctx.source_r4_run / "server_independent_forensics_v1.json"
    if ctx.source_r4_run.name != str(r4_contract["run_name"]):
        raise ValueError("D1R14R6 R4 run identity changed")
    r4_inventory = _raw_inventory(r4_stage / "raw")
    if (
        r4_inventory["count"] != int(r4_contract["raw_count"])
        or r4_inventory["bytes"] != int(r4_contract["raw_total_bytes"])
        or r4_inventory["digest"] != str(r4_contract["raw_inventory_digest"])
        or _sha256(r4_final_path) != str(r4_contract["final_result_sha256"])
        or _sha256(r4_independent_path)
        != str(r4_contract["independent_result_sha256"])
    ):
        raise ValueError("D1R14R6 R4 raw or result boundary changed")
    r4_manifest = _read_json(r4_manifest_path)
    r4_final = _read_json(r4_final_path)
    r4_independent = _read_json(r4_independent_path)
    r4_specs = _read_json(r4_specs_path)
    if (
        r4_manifest.get("stage") != source_r4.STAGE
        or r4_manifest.get("spec_digest") != str(r4_contract["spec_digest"])
        or (r4_manifest.get("package_fingerprint") or {}).get("digest")
        != str(r4_contract["package_digest"])
        or r4_final.get("route") != str(r4_contract["required_route"])
        or int(r4_final.get("safety_pass_count", -1))
        != int(r4_contract["required_safety_pass_count"])
        or not r4_independent.get("audit_completed")
        or not r4_independent.get("passed")
        or int(r4_independent.get("strict_raw_parse_count", -1))
        != int(r4_contract["raw_count"])
        or len(r4_specs) != int(r4_contract["raw_count"])
        or _digest(r4_specs) != str(r4_contract["spec_digest"])
    ):
        raise ValueError("D1R14R6 R4 manifest, specs, or audit changed")
    r4_results: dict[str, dict[str, Any]] = {}
    baseline_count = 0
    retained_count = 0
    for spec in r4_specs:
        experiment_id = str(spec["experiment_id"])
        path = r4_stage / "raw" / f"{experiment_id}.json.gz"
        if not source_r4._result_complete(path, spec, require_success=True):
            raise ValueError(f"D1R14R6 invalid R4 raw: {experiment_id}")
        r4_results[experiment_id] = _read_gz(path)
        role = str(spec["d1r14r4_role"])
        if role == "baseline":
            baseline_count += 1
        elif role == "signed_probe" and int(spec["d1r14r4_direction_index"]) in (1, 2, 3):
            retained_count += 1
    if (
        baseline_count != int(r4_contract["required_baseline_count"])
        or retained_count != int(r4_contract["required_retained_probe_count"])
    ):
        raise ValueError("D1R14R6 R4 retained-bank coverage changed")

    r5_contract = ctx.cfg["source_r5_contract"]
    r5_names = {
        "detailed": "stage4_2r3c3t13s24d1r14r5_detailed_v1.json",
        "summary": "stage4_2r3c3t13s24d1r14r5_summary_v1.json",
        "manifest": "stage4_2r3c3t13s24d1r14r5_manifest_v1.json",
        "independent": "stage4_2r3c3t13s24d1r14r5_independent_v1.json",
    }
    r5_paths = {key: ctx.source_r5_output / name for key, name in r5_names.items()}
    r5_expected_hashes = {
        "detailed": str(r5_contract["primary_detailed_sha256"]),
        "summary": str(r5_contract["primary_summary_sha256"]),
        "manifest": str(r5_contract["primary_manifest_sha256"]),
        "independent": str(r5_contract["independent_result_sha256"]),
    }
    if (
        ctx.source_r5_output.name != str(r5_contract["output_name"])
        or {key: _sha256(path) for key, path in r5_paths.items()}
        != r5_expected_hashes
    ):
        raise ValueError("D1R14R6 R5 output boundary changed")
    r5_summary = _read_json(r5_paths["summary"])
    r5_manifest = _read_json(r5_paths["manifest"])
    r5_independent = _read_json(r5_paths["independent"])
    compact_path = (
        _project_root()
        / "docs/codex/audits/stage4_2r3c3t13s24d1r14r5_20260804_a4c43bb/compact_evidence_manifest_v1.json"
    )
    if (
        _sha256(compact_path) != str(r5_contract["compact_evidence_sha256"])
        or r5_summary.get("route") != str(r5_contract["required_route"])
        or not r5_summary.get("passed")
        or int(r5_summary.get("construction_pass_count", -1))
        != int(r5_contract["required_construction_pass_count"])
        or int(r5_summary.get("antipodal_pair_pass_count", -1))
        != int(r5_contract["required_antipodal_pair_pass_count"])
        or int(r5_summary.get("new_raw_count", -1))
        != int(r5_contract["required_new_raw_count"])
        or bool(r5_summary.get("tsc_executed"))
        != bool(r5_contract["required_tsc_executed"])
        or r5_summary.get("candidate_matrix_digest")
        != ctx.cfg["controller_contract"]["requested_matrix_float64_le_c_sha256"]
        or r5_manifest.get("route") != str(r5_contract["required_route"])
        or bool(r5_manifest.get("ray_gotsc_tsc_plant_or_controller_executed"))
        or r5_manifest.get("outputs", {}).get(r5_names["detailed"])
        != r5_expected_hashes["detailed"]
        or r5_manifest.get("outputs", {}).get(r5_names["summary"])
        != r5_expected_hashes["summary"]
        or not r5_independent.get("passed")
        or r5_independent.get("route") != str(r5_contract["required_route"])
    ):
        raise ValueError("D1R14R6 R5 scientific decision changed")
    return {
        "r4_run": str(ctx.source_r4_run),
        "r4_stage": str(r4_stage),
        "r4_inventory": r4_inventory,
        "r4_manifest_sha256": _sha256(r4_manifest_path),
        "r4_final_sha256": _sha256(r4_final_path),
        "r4_independent_sha256": _sha256(r4_independent_path),
        "r4_spec_digest": _digest(r4_specs),
        "r4_baseline_count": baseline_count,
        "r4_retained_probe_count": retained_count,
        "r4_specs": r4_specs,
        "r4_results": r4_results,
        "r5_output": str(ctx.source_r5_output),
        "r5_hashes": r5_expected_hashes,
        "r5_compact_sha256": _sha256(compact_path),
        "r5_summary": r5_summary,
        "passed": True,
    }


def _authenticate_source(ctx: Context) -> dict[str, Any]:
    r1a = _authenticate_r1a(ctx)
    r3_r2 = _authenticate_r3_r2(ctx)
    r4_r5 = _authenticate_r4_r5(ctx)
    expected = ctx.cfg["source_contract"]
    d1r13_inventory = _raw_inventory(ctx.source_ctx.paths.raw)
    if (
        d1r13_inventory["count"] != int(expected["d1r13_raw_count"])
        or d1r13_inventory["bytes"] != int(expected["d1r13_raw_total_bytes"])
        or d1r13_inventory["digest"] != str(expected["d1r13_raw_inventory_digest"])
    ):
        raise ValueError("D1R14R6 D1R13 raw inventory changed")
    final_path = ctx.source_d1r13_run / "final_result.json"
    if _sha256(final_path) != str(expected["d1r13_final_result_sha256"]):
        raise ValueError("D1R14R6 D1R13 final result hash changed")
    final = _read_json(final_path)
    if (
        not final.get("passed")
        or final.get("route") != str(expected["d1r13_final_route"])
        or int(final.get("pass_count", -1)) != 8
    ):
        raise ValueError("D1R14R6 D1R13 final result changed")
    if _sha256(ctx.source_ctx.paths.state) != str(expected["d1r13_stage_state_sha256"]):
        raise ValueError("D1R14R6 D1R13 state hash changed")
    if _sha256(ctx.source_ctx.paths.manifest) != str(expected["d1r13_stage_manifest_sha256"]):
        raise ValueError("D1R14R6 D1R13 manifest hash changed")
    if _sha256(ctx.source_d1r13_audit) != str(expected["d1r13_independent_audit_sha256"]):
        raise ValueError("D1R14R6 D1R13 independent audit hash changed")
    audit = _read_json(ctx.source_d1r13_audit)
    if (
        not audit.get("passed")
        or int(audit.get("strict_raw_parse_count", -1)) != 8
        or int(audit.get("snapshot_pass_count", -1)) != 8
        or int(audit.get("zero_action_row_count", -1)) != 8
        or int(audit.get("zero_current_increment_row_count", -1)) != 8
    ):
        raise ValueError("D1R14R6 D1R13 independent audit changed")
    d1r11_inventory = _raw_inventory(ctx.source_ctx.source_ctx.paths.raw)
    if (
        d1r11_inventory["count"] != int(expected["d1r11_training_raw_count"])
        or d1r11_inventory["bytes"] != int(expected["d1r11_training_raw_total_bytes"])
        or d1r11_inventory["digest"] != str(expected["d1r11_training_raw_inventory_digest"])
    ):
        raise ValueError("D1R14R6 D1R11 training inventory changed")
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
        raise ValueError("D1R14R6 selected snapshot authentication failed")
    return {
        "r1a": r1a,
        "r3_r2": r3_r2,
        "r4_r5": r4_r5,
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
        "configs/stage4_2r3c3t13s24d1r14r6_direction0_replacement_sentinel_370ms.json",
        "docs/codex/reports/STAGE4_2R3C3T13S24D1R14R6_REAL_TSC_DIRECTION0_REPLACEMENT_SENTINEL_DESIGN.md",
        "docs/codex/audit_tools/stage4_2r3c3t13s24d1r14r6_independent_forensics.py",
        "docs/codex/audit_tools/stage4_2r3c3t13s24d1r14r5_global_direction0_gain_preflight.py",
        "docs/codex/audit_tools/stage4_2r3c3t13s24d1r14r5_independent_forensics.py",
        "docs/codex/audit_tools/stage4_2r3c3t13s24d1r14r4_independent_forensics.py",
        "docs/codex/audit_tools/stage4_2r3c3t13s24d1r14r3_independent_forensics.py",
        "docs/codex/reports/STAGE4_2R3C3T13S24D1R14R3_SOURCE_STATE_HASH_ERRATUM.md",
        "scripts/stage4_2r3c3t13s24d1r14r6_direction0_replacement_sentinel.py",
        "tsc_rzip_rllib/diagnostics/stage4_2r3c3t13s24d1r14r6_direction0_replacement_sentinel.py",
        "tsc_rzip_rllib/diagnostics/stage4_2r3c3t13s24d1r14r4_time_shifted_sign_split_sentinel.py",
        "tsc_rzip_rllib/diagnostics/stage4_2r3c3t13s24d1r14r3_sign_split_response_feasibility.py",
        "tsc_rzip_rllib/diagnostics/stage4_2r3c3t13s24d1r14r2_mixed_basis_signed_excitation_sentinel.py",
        "tsc_rzip_rllib/diagnostics/stage4_2r3c3t13s24d1r13_zero_increment_deconfounding_sentinel.py",
    }
    if not required.issubset(hashes):
        raise ValueError(
            "D1R14R6 package import closure is incomplete: "
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
    roles = [
        ("signed_probe", 0, DIRECTIONS[0], sign, issue_step)
        for issue_step in ISSUE_STEPS
        for sign in (1, -1)
    ]
    for source_result in source_results:
        source = source_result["spec"]
        source_path = ctx.source_ctx.paths.raw / f"{source_result['experiment_id']}.json.gz"
        for role, direction_index, direction_name, sign, issue_step in roles:
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
                "issue_task_step": issue_step,
                "requested_matrix_digest": matrix_digest,
                "snapshot_manifest_digest": source["restart_snapshot_manifest_digest"],
            }
            experiment_id = d1r11.s21.s16.s9.t11.t1.r3c3._scenario_digest(identity)
            spec = copy.deepcopy(source)
            spec.update(
                {
                    "kind": "stage4_2r3c3t13s24d1r14r6_direction0_replacement_sentinel",
                    "stage": STAGE,
                    "campaign_identity": CAMPAIGN_IDENTITY,
                    "controller_revision": CONTROLLER_REVISION,
                    "experiment_id": experiment_id,
                    "phase": "direction0_replacement_safety_identification_sentinel",
                    "category": "direction0_replacement_safety_identification_only",
                    "environment_variant": f"stage4_2r3c3t13s24d1r14r6_{experiment_id}",
                    "source_d1r13_experiment_id": str(source_result["experiment_id"]),
                    "source_d1r13_raw_sha256": _sha256(source_path),
                    "source_d1r13_raw_size_bytes": source_path.stat().st_size,
                    "source_d1r11_experiment_id": str(source["source_d1r11_experiment_id"]),
                    "d1r14r6_role": role,
                    "d1r14r6_direction_index": direction_index,
                    "d1r14r6_direction_name": direction_name,
                    "d1r14r6_sign": sign,
                    "d1r14r6_requested_coordinate": requested.tolist(),
                    "d1r14r6_requested_matrix_digest": matrix_digest,
                    "d1r14r6_issue_task_step": issue_step,
                    "d1r14r6_cancel_task_step": (
                        issue_step + CANCEL_OFFSET if role == "signed_probe" else -1
                    ),
                    "d1r14r6_zero_after_task_step": (
                        issue_step + ZERO_AFTER_OFFSET if role == "signed_probe" else 10
                    ),
                    "d1r14r6_future_r17_controller_execution_allowed": False,
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
    if len(output) != 48 or len({row["experiment_id"] for row in output}) != 48:
        raise ValueError("D1R14R6 spec identity coverage changed")
    counts: dict[str, int] = {}
    horizons = {35: 0, 37: 0}
    for spec in output:
        counts[str(spec["source_d1r13_experiment_id"])] = (
            counts.get(str(spec["source_d1r13_experiment_id"]), 0) + 1
        )
        horizons[int(spec["horizon_steps"])] += 1
    if set(counts.values()) != {6} or horizons != {35: 24, 37: 24}:
        raise ValueError("D1R14R6 matrix coverage changed")
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
        raise ValueError("D1R14R6 offline requires a fresh run identity")
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
        ctx.paths.source_reference / "r3_r2_authentication.json",
        source["r3_r2"],
    )
    _write_json(
        ctx.paths.source_reference / "r4_r5_authentication.json",
        {
            key: value
            for key, value in source["r4_r5"].items()
            if key not in {"r4_specs", "r4_results"}
        },
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
        "source_r2_run": str(ctx.source_r2_run),
        "source_r3_initial_output": str(ctx.source_r3_initial_output),
        "source_r3_corrected_output": str(ctx.source_r3_corrected_output),
        "source_r3_hashes": source["r3_r2"]["r3_hashes"],
        "source_r2_inventory_digest": source["r3_r2"]["r2_inventory"]["digest"],
        "source_r4_run": str(ctx.source_r4_run),
        "source_r4_inventory_digest": source["r4_r5"]["r4_inventory"]["digest"],
        "source_r4_spec_digest": source["r4_r5"]["r4_spec_digest"],
        "source_r4_final_sha256": source["r4_r5"]["r4_final_sha256"],
        "source_r4_independent_sha256": source["r4_r5"]["r4_independent_sha256"],
        "source_r5_output": str(ctx.source_r5_output),
        "source_r5_hashes": source["r4_r5"]["r5_hashes"],
        "source_r5_compact_sha256": source["r4_r5"]["r5_compact_sha256"],
        "requested_matrix_digest": ctx.cfg["controller_contract"]["requested_matrix_float64_le_c_sha256"],
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
        "source_r3_r2_authenticated": source["r3_r2"]["passed"],
        "source_r4_r5_authenticated": source["r4_r5"]["passed"],
        "source_r4_raw_count": source["r4_r5"]["r4_inventory"]["count"],
        "source_r4_retained_probe_count": source["r4_r5"]["r4_retained_probe_count"],
        "source_r2_raw_count": source["r3_r2"]["r2_inventory"]["count"],
        "source_d1r11_raw_count": source["d1r11_inventory"]["count"],
        "selected_context_count": 8,
        "selected_spec_count": len(specs),
        "baseline_count": 0,
        "signed_probe_count": 48,
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
        "d1r14r6_role",
        "d1r14r6_direction_index",
        "d1r14r6_direction_name",
        "d1r14r6_sign",
        "d1r14r6_requested_coordinate",
    }
    prefixed_forbidden = {
        key
        for key in output
        if key.startswith(("d1r13_", "d1r14r6_", "source_d1r13_"))
    }
    forbidden.update(prefixed_forbidden)
    for key in forbidden:
        output.pop(key, None)
    if forbidden.intersection(output) or any(
        key.startswith(("d1r13_", "d1r14r6_", "source_d1r13_")) for key in output
    ):
        raise ValueError("D1R14R6 forbidden experiment label reached controller")
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
    if int(step) < PREFIX_END:
        raise ValueError("D1R14R6 zero branch called before task step 10")
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
        "r3c3t13s24d1r14r6_controller_revision": CONTROLLER_REVISION,
        "r3c3t13s24d1r14r6_delegated_prefix": False,
        "r3c3t13s24d1r14r6_future_r17_executed": False,
        "r3c3t13s24d1r14r6_event": "none",
        "r3c3t13s24d1r14r6_event_detail": {},
        "r3c3t13s24d1r14r6_zero_increment": True,
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
        issue_step: int,
        cancel_step: int,
        zero_after_step: int,
    ):
        prepared = _controller_source_spec(source_spec, schedule_cfg)
        requested = np.asarray(requested_coordinate, dtype=float)
        frozen_matrix = np.asarray(
            controller_contract["requested_coordinate_matrix_columns"], dtype=float
        )
        if role == "signed_probe":
            if direction_index not in range(4) or sign not in (-1, 1):
                raise ValueError("D1R14R6 invalid fixed signed coordinate")
            expected = frozen_matrix[:, direction_index] * sign
            if requested.shape != (4,) or not np.array_equal(requested, expected):
                raise ValueError("D1R14R6 requested mixed coordinate changed")
            if (
                int(issue_step) not in ISSUE_STEPS
                or int(cancel_step) != int(issue_step) + CANCEL_OFFSET
                or int(zero_after_step) != int(issue_step) + ZERO_AFTER_OFFSET
            ):
                raise ValueError("D1R14R6 per-spec issue schedule changed")
        elif (
            role != "baseline"
            or direction_index != -1
            or sign != 0
            or requested.shape != (4,)
            or not np.array_equal(requested, np.zeros(4, dtype=float))
            or int(issue_step) != -1
            or int(cancel_step) != -1
            or int(zero_after_step) != PREFIX_END
        ):
            raise ValueError("D1R14R6 invalid baseline coordinate")
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
        self.d1r14r6_role = role
        self.d1r14r6_direction_index = int(direction_index)
        self.d1r14r6_sign = int(sign)
        self.d1r14r6_requested_coordinate = requested
        self.d1r14r6_issue_step = int(issue_step)
        self.d1r14r6_cancel_step = int(cancel_step)
        self.d1r14r6_zero_after_step = int(zero_after_step)
        self.d1r14r6_controller_contract = copy.deepcopy(dict(controller_contract))

    def _issue(
        self, slot: int, currents: np.ndarray, baseline_action: np.ndarray
    ) -> tuple[np.ndarray, dict[str, Any]]:
        """Construct the exact Card15 action under the frozen mixed-basis gates."""
        self._freeze_fixed_basis(currents, baseline_action)
        center = self.actuator.apply(currents, baseline_action)
        desired_coordinate = self.d1r14r6_requested_coordinate
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
        contract = self.d1r14r6_controller_contract
        frozen_expected = np.asarray(
            contract["requested_coordinate_matrix_columns"], dtype=float
        )[:, slot] * self.d1r14r6_sign
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
            "gate_revision": "d1r14r6_fixed_mixed_action_safety_v1",
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
                "D1R14R6 mixed-basis issue action failed: "
                + json.dumps(event, sort_keys=True)
            )
        self._active_issue = copy.deepcopy(event)
        return np.asarray(chosen["action_norm_tsc"], dtype=float), event

    def action(self, current_state: Mapping[str, Any]) -> tuple[np.ndarray, dict[str, Any]]:
        if int(current_state["step_index"]) != self.step:
            raise ValueError("D1R14R6 controller/current task-state index mismatch")
        if self.step < PREFIX_END:
            action, trace = super().action(current_state)
            trace.update(
                {
                    "r3c3t13s24d1r14r6_controller_revision": CONTROLLER_REVISION,
                    "r3c3t13s24d1r14r6_delegated_prefix": True,
                    "r3c3t13s24d1r14r6_future_r17_executed": False,
                    "r3c3t13s24d1r14r6_event": "none",
                    "r3c3t13s24d1r14r6_event_detail": {},
                    "r3c3t13s24d1r14r6_zero_increment": False,
                }
            )
            return np.asarray(action, dtype=float), trace
        action = zero_action(self.step)
        trace = _trace_template(self.step, action)
        if (
            self.d1r14r6_role == "signed_probe"
            and self.step == self.d1r14r6_issue_step
        ):
            currents = np.asarray(current_state["currents_a_tsc"], dtype=float)
            action, event = self._issue(
                self.d1r14r6_direction_index, currents, np.zeros(N_COILS, dtype=float)
            )
            trace.update(
                {
                    "action_norm_tsc": action.tolist(),
                    "r3c3t13s24d1r14r6_event": "signed_issue",
                    "r3c3t13s24d1r14r6_event_detail": event,
                    "r3c3t13s24d1r14r6_zero_increment": False,
                }
            )
        elif (
            self.d1r14r6_role == "signed_probe"
            and self.step == self.d1r14r6_cancel_step
        ):
            currents = np.asarray(current_state["currents_a_tsc"], dtype=float)
            action, event = self._cancel(
                self.d1r14r6_direction_index, currents, np.zeros(N_COILS, dtype=float)
            )
            trace.update(
                {
                    "action_norm_tsc": action.tolist(),
                    "r3c3t13s24d1r14r6_event": "stored_center_cancel",
                    "r3c3t13s24d1r14r6_event_detail": event,
                    "r3c3t13s24d1r14r6_zero_increment": False,
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
            "variant_id": f"stage4_2r3c3t13s24d1r14r6_{experiment_id}",
            "stage4_2r3c3t13s24d1r14r6_restart_snapshot_dir": str(
                spec["restart_snapshot_dir"]
            ),
            "stage4_2r3c3t13s24d1r14r6_snapshot_manifest_digest": str(
                spec["restart_snapshot_manifest_digest"]
            ),
            "stage4_2r3c3t13s24d1r14r6_issue_task_step": int(
                spec["d1r14r6_issue_task_step"]
            ),
            "stage4_2r3c3t13s24d1r14r6_cancel_task_step": int(
                spec["d1r14r6_cancel_task_step"]
            ),
        }
    )
    _write_json(ctx.paths.variants / f"payload_{experiment_id}.json", payload)
    return payload


class LocalWorker:
    """One fresh authentic TSC process and D1R14R6 controller per rollout."""

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
                raise ValueError("D1R14R6 formal horizon changed")
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
                role=str(spec["d1r14r6_role"]),
                direction_index=int(spec["d1r14r6_direction_index"]),
                sign=int(spec["d1r14r6_sign"]),
                requested_coordinate=spec["d1r14r6_requested_coordinate"],
                issue_step=int(spec["d1r14r6_issue_task_step"]),
                cancel_step=int(spec["d1r14r6_cancel_task_step"]),
                zero_after_step=int(spec["d1r14r6_zero_after_task_step"]),
            )
            for step in range(horizon):
                try:
                    action, controller_row = controller.action(trajectory[-1])
                except ValueError as exc:
                    if (
                        "D1R14R6 mixed-basis issue action failed" in str(exc)
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
                    raise RuntimeError("environment truncated before D1R14R6 horizon")
            calibration_events = [
                row.get("r3c3t13s16_lattice_event")
                for row in trace[:PREFIX_END]
                if row.get("r3c3t13s16_lattice_event") != "none"
            ]
            currents = np.asarray(
                [row["currents_a_tsc"] for row in trajectory], dtype=float
            )
            role = str(spec["d1r14r6_role"])
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
                issue_step = int(spec["d1r14r6_issue_task_step"])
                cancel_step = int(spec["d1r14r6_cancel_task_step"])
                zero_after_step = int(spec["d1r14r6_zero_after_task_step"])
                preissue_actions = np.asarray(
                    [row["action_norm_tsc"] for row in trace[PREFIX_END:issue_step]],
                    dtype=float,
                )
                preissue_current_delta = np.diff(
                    currents[PREFIX_END : issue_step + 1], axis=0
                )
                after_actions = np.asarray(
                    [row["action_norm_tsc"] for row in trace[zero_after_step:]],
                    dtype=float,
                )
                after_current_delta = np.diff(currents[zero_after_step:], axis=0)
                issue = trace[issue_step].get("r3c3t13s24d1r14r6_event_detail") or {}
                cancel = trace[cancel_step].get("r3c3t13s24d1r14r6_event_detail") or {}
                role_success = bool(
                    preissue_actions.shape == (issue_step - PREFIX_END, N_COILS)
                    and np.array_equal(preissue_actions, np.zeros_like(preissue_actions))
                    and preissue_current_delta.shape
                    == (issue_step - PREFIX_END, N_COILS)
                    and np.array_equal(
                        preissue_current_delta, np.zeros_like(preissue_current_delta)
                    )
                    and trace[issue_step].get("r3c3t13s24d1r14r6_event")
                    == "signed_issue"
                    and trace[cancel_step].get("r3c3t13s24d1r14r6_event")
                    == "stored_center_cancel"
                    and issue.get("passed")
                    and cancel.get("passed")
                    and after_actions.shape == (horizon - zero_after_step, N_COILS)
                    and np.array_equal(after_actions, np.zeros_like(after_actions))
                    and after_current_delta.shape
                    == (horizon - zero_after_step, N_COILS)
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
                    bool(row.get("r3c3t13s24d1r14r6_delegated_prefix"))
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
                    "failure_reason": "" if success else "incomplete or invalid D1R14R6 rollout",
                    "execution_failure_class": (
                        "" if success else "controller_or_action_semantics_error"
                    ),
                    "hidden_history_control_summary": {
                        "fresh_controller_actor": True,
                        "fresh_tsc_process": True,
                        "full_tsc_hidden_state_loaded_from_sprsina": True,
                        "prefix_controller_revision": d1r11.CONTROLLER_REVISION,
                        "role": role,
                        "issue_task_step": int(spec["d1r14r6_issue_task_step"]),
                        "cancel_task_step": int(spec["d1r14r6_cancel_task_step"]),
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
                    reason="stage4_2r3c3t13s24d1r14r6_mixed_basis_signed_excitation",
                )


_RAY_ACTOR = None


def _ray_actor_class():
    global _RAY_ACTOR
    if _RAY_ACTOR is None:
        import ray

        @ray.remote(num_cpus=1, max_restarts=0)
        class Stage42R3C3T13S24D1R14R6Actor:
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

        _RAY_ACTOR = Stage42R3C3T13S24D1R14R6Actor
    return _RAY_ACTOR


def _saved_specs(ctx: Context) -> list[dict[str, Any]]:
    saved = _read_json(ctx.paths.specs / "sentinel_specs.json")
    rebuilt = build_specs(ctx, _source_d1r13_results(ctx))
    if _digest(saved) != _digest(rebuilt):
        raise ValueError("D1R14R6 frozen specs changed")
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
        != ctx.cfg["controller_contract"]["requested_matrix_float64_le_c_sha256"]
        or manifest.get("source_r4_inventory_digest")
        != source["r4_r5"]["r4_inventory"]["digest"]
        or manifest.get("source_r4_spec_digest")
        != source["r4_r5"]["r4_spec_digest"]
        or manifest.get("source_r4_final_sha256")
        != source["r4_r5"]["r4_final_sha256"]
        or manifest.get("source_r4_independent_sha256")
        != source["r4_r5"]["r4_independent_sha256"]
        or manifest.get("source_r5_hashes") != source["r4_r5"]["r5_hashes"]
        or manifest.get("source_r5_compact_sha256")
        != source["r4_r5"]["r5_compact_sha256"]
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
        raise ValueError("D1R14R6 prepared run/package/source identity changed")
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
                f"stage42r3c3t13s24d1r14r6_serial_{index:04d}",
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
            print(f"[D1R14R6] {index + 1}/{len(pending)}", flush=True)
    elif backend == "ray" and pending:
        import ray

        plan = d1r11.s21.s16.ensure_ray_worker_plan(
            ray,
            requested_workers=int(ctx.cfg["parallel"]["n_workers"]),
            pending_tasks=len(pending),
            ray_tmpdir=os.environ.get("RAY_TMPDIR")
            or ctx.cfg["storage"]["ray_tmpdir"],
            log_prefix="[D1R14R6]",
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
                    f"stage42r3c3t13s24d1r14r6_{batch_start + offset:04d}",
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
                            f"[D1R14R6] waiting {completed}/{len(pending)}",
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
                        print(f"[D1R14R6] {completed}/{len(pending)}", flush=True)
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
        raise ValueError(f"unsupported D1R14R6 backend: {backend}")
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
        + ("r3c3t13s24d1r14r6_future_r17_executed",)
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
        raise ValueError("D1R14R6 trajectory is too short for visible velocity")
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
        raise ValueError("D1R14R6 normalized visible trajectory is invalid")
    return values - values[PREFIX_END][None, :]


def _combined_response_geometry(
    ctx: Context,
    specs: Sequence[Mapping[str, Any]],
    results: Mapping[str, Mapping[str, Any]],
    *,
    source_r2_specs: Sequence[Mapping[str, Any]] | None = None,
    source_r2_results: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Replace only R4 direction 0 while retaining every other bank column."""
    source = _authenticate_r4_r5(ctx)
    combined_specs: list[dict[str, Any]] = []
    combined_results: dict[str, dict[str, Any]] = {}
    for r4_spec in source["r4_specs"]:
        role = str(r4_spec["d1r14r4_role"])
        direction_index = int(r4_spec["d1r14r4_direction_index"])
        if role == "baseline" or (role == "signed_probe" and direction_index in (1, 2, 3)):
            experiment_id = str(r4_spec["experiment_id"])
            combined_specs.append(copy.deepcopy(r4_spec))
            combined_results[experiment_id] = source["r4_results"][experiment_id]
    for r6_spec in specs:
        experiment_id = str(r6_spec["experiment_id"])
        if (
            str(r6_spec["d1r14r6_role"]) != "signed_probe"
            or int(r6_spec["d1r14r6_direction_index"]) != 0
        ):
            raise ValueError("D1R14R6 contains a non-replacement probe")
        adapted_spec = copy.deepcopy(dict(r6_spec))
        for suffix in (
            "role",
            "direction_index",
            "direction_name",
            "sign",
            "requested_coordinate",
            "requested_matrix_digest",
            "issue_task_step",
            "cancel_task_step",
            "zero_after_task_step",
        ):
            adapted_spec[f"d1r14r4_{suffix}"] = adapted_spec[f"d1r14r6_{suffix}"]
        adapted_result = copy.deepcopy(dict(results[experiment_id]))
        for trace_row in adapted_result.get("controller_trace") or []:
            if "r3c3t13s24d1r14r6_event_detail" in trace_row:
                trace_row["r3c3t13s24d1r14r4_event_detail"] = copy.deepcopy(
                    trace_row["r3c3t13s24d1r14r6_event_detail"]
                )
        combined_specs.append(adapted_spec)
        combined_results[experiment_id] = adapted_result
    if len(combined_specs) != 200 or len(combined_results) != 200:
        raise ValueError("D1R14R6 combined response-bank coverage changed")
    geometry = source_r4._response_geometry(
        SimpleNamespace(cfg=ctx.cfg, source_r2_run=ctx.source_r2_run),
        combined_specs,
        combined_results,
        source_r2_specs=source_r2_specs,
        source_r2_results=source_r2_results,
    )
    symmetry = geometry["issue_coordinate_and_field_symmetry"]
    replacement_rows = [
        row
        for row in symmetry["rows"]
        if int(row["issue_task_step"]) in ISSUE_STEPS
        and int(row["direction_index"]) == 0
    ]
    replacement_pass_count = sum(bool(row["passed"]) for row in replacement_rows)
    geometry["r6_direction0_antipodal_pair_count"] = len(replacement_rows)
    geometry["r6_direction0_antipodal_pair_pass_count"] = replacement_pass_count
    geometry["r6_direction0_antipodal_passed"] = bool(
        len(replacement_rows) == 24 and replacement_pass_count == 24
    )
    geometry["passed"] = bool(
        geometry.get("passed") and geometry["r6_direction0_antipodal_passed"]
    )
    geometry["bank_composition"] = {
        "r2_issue10_all_directions": 64,
        "r4_issue14_18_22_directions1_2_3": 144,
        "r6_issue14_18_22_direction0": 48,
        "combined_signed_probe_count": 256,
        "r4_baseline_count": 8,
    }
    return geometry


def _response_geometry(
    ctx: Context,
    specs: Sequence[Mapping[str, Any]],
    results: Mapping[str, Mapping[str, Any]],
    *,
    source_r2_specs: Sequence[Mapping[str, Any]] | None = None,
    source_r2_results: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    return _combined_response_geometry(
        ctx,
        specs,
        results,
        source_r2_specs=source_r2_specs,
        source_r2_results=source_r2_results,
    )
    geometry_cfg = ctx.cfg["response_geometry"]
    scales = np.asarray(geometry_cfg["visible_output_scales"], dtype=float)
    minimum_signal = float(geometry_cfg["minimum_direction_peak_normalized_outputs5"])
    rank_tolerance = float(geometry_cfg["rank_relative_tolerance"])
    required_rank = int(geometry_cfg["required_rank"])
    maximum_condition = float(geometry_cfg["maximum_condition_number"])
    issue_steps = tuple(map(int, geometry_cfg["combined_issue_task_steps"]))
    if issue_steps != (10, 14, 18, 22):
        raise ValueError("D1R14R6 combined issue-time contract changed")
    if source_r2_specs is None or source_r2_results is None:
        r2_stage = ctx.source_r2_run / d1r14r2.RUN_NAME
        source_r2_specs = _read_json(r2_stage / "specs" / "sentinel_specs.json")
        loaded: dict[str, Mapping[str, Any]] = {}
        for spec in source_r2_specs:
            experiment_id = str(spec["experiment_id"])
            path = r2_stage / "raw" / f"{experiment_id}.json.gz"
            if not d1r14r2._result_complete(path, spec, require_success=True):
                raise ValueError(f"D1R14R6 invalid source R2 raw: {experiment_id}")
            loaded[experiment_id] = _read_gz(path)
        source_r2_results = loaded
    if len(source_r2_specs) != 72 or len(source_r2_results) != 72:
        raise ValueError("D1R14R6 source R2 raw coverage changed")

    def grouped(
        bank_specs: Sequence[Mapping[str, Any]],
        bank_results: Mapping[str, Mapping[str, Any]],
        prefix: str,
        default_issue: int,
    ) -> tuple[
        dict[str, Mapping[str, Any]],
        dict[str, dict[tuple[str, int, int, int], Mapping[str, Any]]],
    ]:
        spec_index = {str(spec["experiment_id"]): spec for spec in bank_specs}
        output: dict[
            str, dict[tuple[str, int, int, int], Mapping[str, Any]]
        ] = {}
        for experiment_id, result in bank_results.items():
            spec = spec_index.get(str(experiment_id))
            if spec is None:
                raise ValueError("D1R14R6 result/spec identity mismatch")
            role = str(spec[f"{prefix}_role"])
            issue = (
                int(spec.get(f"{prefix}_issue_task_step", default_issue))
                if role == "signed_probe"
                else -1
            )
            key = (
                role,
                issue,
                int(spec[f"{prefix}_direction_index"]),
                int(spec[f"{prefix}_sign"]),
            )
            context_id = str(spec["source_d1r13_experiment_id"])
            if key in output.setdefault(context_id, {}):
                raise ValueError("D1R14R6 duplicate response-bank member")
            output[context_id][key] = result
        return spec_index, output

    r2_spec_index, r2_groups = grouped(
        source_r2_specs, source_r2_results, "d1r14r2", 10
    )
    r4_spec_index, r4_groups = grouped(specs, results, "d1r14r6", -1)
    branch_rows: list[dict[str, Any]] = []
    issue_rows: list[dict[str, Any]] = []
    cross_sign_rows: list[dict[str, Any]] = []
    responses: dict[tuple[str, int, int, int], np.ndarray] = {}
    context_meta: dict[str, Mapping[str, Any]] = {}
    for context_id in map(str, ctx.cfg["selected_source_d1r13_experiment_ids"]):
        r2_group = r2_groups.get(context_id, {})
        r4_group = r4_groups.get(context_id, {})
        r2_baseline = r2_group.get(("baseline", -1, -1, 0))
        r4_baseline = r4_group.get(("baseline", -1, -1, 0))
        if r2_baseline is None or r4_baseline is None:
            raise ValueError(f"D1R14R6 baseline missing for context {context_id}")
        meta = next(
            spec
            for spec in specs
            if str(spec["source_d1r13_experiment_id"]) == context_id
        )
        context_meta[context_id] = meta
        for issue_step in issue_steps:
            source_name = "D1R14R2" if issue_step == 10 else "D1R14R6"
            group = r2_group if issue_step == 10 else r4_group
            spec_index = r2_spec_index if issue_step == 10 else r4_spec_index
            prefix = "d1r14r2" if issue_step == 10 else "d1r14r6"
            baseline = r2_baseline if issue_step == 10 else r4_baseline
            baseline_values = _visible_outputs5(baseline["trajectory"], scales)[
                issue_step + 1 :
            ]
            sign_members: dict[int, list[Mapping[str, Any]]] = {}
            for sign in (1, -1):
                columns: list[np.ndarray] = []
                directions: list[dict[str, Any]] = []
                sign_members[sign] = []
                for direction_index, direction_name in enumerate(DIRECTIONS):
                    member = group.get(
                        ("signed_probe", issue_step, direction_index, sign)
                    )
                    if member is None:
                        raise ValueError(
                            "D1R14R6 signed branch missing: "
                            f"{context_id} {issue_step} {direction_name} {sign}"
                        )
                    member_values = _visible_outputs5(member["trajectory"], scales)[
                        issue_step + 1 :
                    ]
                    if member_values.shape != baseline_values.shape:
                        raise ValueError("D1R14R6 signed response shape mismatch")
                    response = (
                        member_values - baseline_values
                        if sign == 1
                        else baseline_values - member_values
                    )
                    flattened = response.reshape(-1)
                    finite = bool(np.all(np.isfinite(response)))
                    peak = float(np.max(np.abs(response)))
                    norm = float(np.linalg.norm(flattened))
                    signal_pass = bool(
                        finite
                        and norm > 0.0
                        and peak >= minimum_signal - 1e-15
                    )
                    columns.append(
                        flattened / norm
                        if finite and norm > 0.0
                        else np.full(flattened.shape, math.nan)
                    )
                    experiment_id = str(member["experiment_id"])
                    member_spec = spec_index[experiment_id]
                    sign_members[sign].append(member)
                    responses[(context_id, issue_step, sign, direction_index)] = response
                    directions.append(
                        {
                            "direction_index": direction_index,
                            "direction_name": direction_name,
                            "experiment_id": experiment_id,
                            "peak_normalized_outputs5": peak,
                            "l2_norm": norm,
                            "finite": finite,
                            "signal_pass": signal_pass,
                        }
                    )
                matrix = np.column_stack(columns)
                finite_matrix = bool(np.all(np.isfinite(matrix)))
                singular = (
                    np.linalg.svd(matrix, compute_uv=False)
                    if finite_matrix
                    else np.full(4, math.nan)
                )
                rank = (
                    int(np.sum(singular > singular[0] * rank_tolerance))
                    if finite_matrix and singular[0] > 0.0
                    else 0
                )
                condition = (
                    float(singular[0] / singular[-1])
                    if rank == required_rank and singular[-1] > 0.0
                    else None
                )
                passed = bool(
                    all(row["signal_pass"] for row in directions)
                    and rank == required_rank
                    and condition is not None
                    and condition <= maximum_condition + 1e-12
                )
                branch_rows.append(
                    {
                        "source_d1r13_experiment_id": context_id,
                        "pair_id": meta["pair_id"],
                        "history_member": meta["history_member"],
                        "source_stage": source_name,
                        "issue_task_step": issue_step,
                        "first_response_state": issue_step + 1,
                        "sign": sign,
                        "directions": directions,
                        "singular_values": [
                            float(value) if math.isfinite(float(value)) else None
                            for value in singular
                        ],
                        "rank": rank,
                        "condition_number": condition,
                        "passed": passed,
                    }
                )
            for direction_index, direction_name in enumerate(DIRECTIONS):
                positive = sign_members[1][direction_index]
                negative = sign_members[-1][direction_index]
                positive_event = positive["controller_trace"][issue_step].get(
                    f"r3c3t13s24{prefix}_event_detail"
                ) or {}
                negative_event = negative["controller_trace"][issue_step].get(
                    f"r3c3t13s24{prefix}_event_detail"
                ) or {}
                positive_coordinate = np.asarray(
                    positive_event.get("requested_coordinate", []), dtype=float
                )
                negative_coordinate = np.asarray(
                    negative_event.get("requested_coordinate", []), dtype=float
                )
                positive_field = np.asarray(
                    positive_event.get("actual_signed_delta_field_kAt_tsc", []),
                    dtype=float,
                )
                negative_field = np.asarray(
                    negative_event.get("actual_signed_delta_field_kAt_tsc", []),
                    dtype=float,
                )
                coordinate_exact = bool(
                    positive_coordinate.shape == negative_coordinate.shape == (4,)
                    and np.array_equal(positive_coordinate, -negative_coordinate)
                )
                field_exact = bool(
                    positive_field.shape == negative_field.shape == (N_COILS,)
                    and np.array_equal(positive_field, -negative_field)
                )
                issue_rows.append(
                    {
                        "source_d1r13_experiment_id": context_id,
                        "source_stage": source_name,
                        "issue_task_step": issue_step,
                        "direction_index": direction_index,
                        "direction_name": direction_name,
                        "coordinate_exact_sign_opposite": coordinate_exact,
                        "physical_field_exact_sign_opposite": field_exact,
                        "passed": coordinate_exact and field_exact,
                    }
                )
                positive_response = responses[(context_id, issue_step, 1, direction_index)]
                negative_response = responses[(context_id, issue_step, -1, direction_index)]
                difference = float(np.max(np.abs(positive_response - negative_response)))
                peak = max(
                    float(np.max(np.abs(positive_response))),
                    float(np.max(np.abs(negative_response))),
                )
                cross_sign_rows.append(
                    {
                        "source_d1r13_experiment_id": context_id,
                        "issue_task_step": issue_step,
                        "direction_index": direction_index,
                        "direction_name": direction_name,
                        "maximum_absolute_branch_difference": difference,
                        "relative_to_branch_peak": difference / peak if peak > 0.0 else None,
                        "acceptance_gate": False,
                    }
                )
    history_rows = []
    pair_to_contexts: dict[str, list[str]] = {}
    for context_id, meta in context_meta.items():
        pair_to_contexts.setdefault(str(meta["pair_id"]), []).append(context_id)
    for pair_id, contexts in sorted(pair_to_contexts.items()):
        if len(contexts) != 2:
            raise ValueError(f"D1R14R6 hidden-history pair coverage changed: {pair_id}")
        for issue_step in issue_steps:
            for sign in (1, -1):
                for direction_index, direction_name in enumerate(DIRECTIONS):
                    left = responses[(contexts[0], issue_step, sign, direction_index)]
                    right = responses[(contexts[1], issue_step, sign, direction_index)]
                    if left.shape != right.shape:
                        raise ValueError("D1R14R6 matched-history response shape changed")
                    difference = float(np.max(np.abs(left - right)))
                    peak = max(float(np.max(np.abs(left))), float(np.max(np.abs(right))))
                    history_rows.append(
                        {
                            "pair_id": pair_id,
                            "issue_task_step": issue_step,
                            "sign": sign,
                            "direction_index": direction_index,
                            "direction_name": direction_name,
                            "context_experiment_ids": contexts,
                            "maximum_absolute_response_difference": difference,
                            "relative_to_pair_response_peak": (
                                difference / peak if peak > 0.0 else None
                            ),
                            "acceptance_gate": False,
                        }
                    )
    cross_time_rows = []
    for context_id in context_meta:
        for sign in (1, -1):
            for direction_index, direction_name in enumerate(DIRECTIONS):
                for left_index, left_time in enumerate(issue_steps):
                    for right_time in issue_steps[left_index + 1 :]:
                        left = responses[(context_id, left_time, sign, direction_index)]
                        right = responses[(context_id, right_time, sign, direction_index)]
                        common = min(len(left), len(right))
                        difference = float(np.max(np.abs(left[:common] - right[:common])))
                        peak = max(
                            float(np.max(np.abs(left[:common]))),
                            float(np.max(np.abs(right[:common]))),
                        )
                        cross_time_rows.append(
                            {
                                "source_d1r13_experiment_id": context_id,
                                "sign": sign,
                                "direction_index": direction_index,
                                "direction_name": direction_name,
                                "issue_task_steps": [left_time, right_time],
                                "common_relative_state_count": common,
                                "maximum_absolute_response_difference": difference,
                                "relative_to_response_peak": (
                                    difference / peak if peak > 0.0 else None
                                ),
                                "acceptance_gate": False,
                            }
                        )
    all_directions = [row for branch in branch_rows for row in branch["directions"]]
    source_issue_rows = [row for row in issue_rows if row["source_stage"] == "D1R14R2"]
    new_issue_rows = [row for row in issue_rows if row["source_stage"] == "D1R14R6"]
    issue_symmetry = {
        "source_pair_count": len(source_issue_rows),
        "new_pair_count": len(new_issue_rows),
        "combined_pair_count": len(issue_rows),
        "coordinate_exact_count": sum(
            bool(row["coordinate_exact_sign_opposite"]) for row in issue_rows
        ),
        "physical_field_exact_count": sum(
            bool(row["physical_field_exact_sign_opposite"]) for row in issue_rows
        ),
        "rows": issue_rows,
        "passed": bool(
            len(source_issue_rows) == 32
            and len(new_issue_rows) == 96
            and len(issue_rows) == 128
            and all(bool(row["passed"]) for row in issue_rows)
        ),
    }
    branch_count = len(branch_rows)
    branch_direction_count = len(all_directions)
    signal_pass_count = sum(bool(row["signal_pass"]) for row in all_directions)
    rank_pass_count = sum(int(row["rank"]) == required_rank for row in branch_rows)
    condition_pass_count = sum(
        row["condition_number"] is not None
        and float(row["condition_number"]) <= maximum_condition + 1e-12
        for row in branch_rows
    )
    return {
        "evaluated": True,
        "context_count": len(context_meta),
        "issue_task_steps": list(issue_steps),
        "branch_count": branch_count,
        "branch_direction_count": branch_direction_count,
        "signal_pass_count": signal_pass_count,
        "rank_pass_count": rank_pass_count,
        "condition_pass_count": condition_pass_count,
        "minimum_direction_peak_normalized_outputs5": min(
            (float(row["peak_normalized_outputs5"]) for row in all_directions),
            default=None,
        ),
        "maximum_condition_number": max(
            (
                float(row["condition_number"])
                for row in branch_rows
                if row["condition_number"] is not None
            ),
            default=None,
        ),
        "branch_rows": branch_rows,
        "issue_coordinate_and_field_symmetry": issue_symmetry,
        "cross_sign_response_rows_report_only": cross_sign_rows,
        "matched_hidden_history_rows_report_only": history_rows,
        "cross_time_response_rows_report_only": cross_time_rows,
        "passed": bool(
            len(context_meta) == 8
            and branch_count == int(geometry_cfg["expected_branch_count"])
            and branch_direction_count
            == int(geometry_cfg["expected_branch_direction_count"])
            and signal_pass_count == branch_direction_count
            and rank_pass_count == branch_count
            and condition_pass_count == branch_count
            and issue_symmetry["passed"]
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
    r4_source = _authenticate_r4_r5(ctx)
    r4_baselines = {
        str(spec["source_d1r13_experiment_id"]): r4_source["r4_results"][str(spec["experiment_id"])]
        for spec in r4_source["r4_specs"]
        if str(spec["d1r14r4_role"]) == "baseline"
    }
    if len(r4_baselines) != 8:
        raise ValueError("D1R14R6 R4 baseline lookup changed")
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
                    "role": spec["d1r14r6_role"],
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
        preissue_zero_actions = False
        preissue_zero_currents = False
        issue_exact = False
        cancel_exact = False
        zero_after_actions = False
        zero_after_currents = False
        r4_baseline_issue_state_exact = False
        role = str(spec["d1r14r6_role"])
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
            direction_index = int(spec["d1r14r6_direction_index"])
            issue_step = int(spec["d1r14r6_issue_task_step"])
            cancel_step = int(spec["d1r14r6_cancel_task_step"])
            zero_after_step = int(spec["d1r14r6_zero_after_task_step"])
            expected_coordinate = list(map(float, spec["d1r14r6_requested_coordinate"]))
            r4_baseline = r4_baselines[str(spec["source_d1r13_experiment_id"])]
            r4_baseline_trajectory = r4_baseline.get("trajectory") or []
            r4_baseline_issue_state_exact = bool(
                len(r4_baseline_trajectory) > issue_step
                and _semantic_state(trajectory[issue_step])
                == _semantic_state(r4_baseline_trajectory[issue_step])
            )
            issue = trace[issue_step].get("r3c3t13s24d1r14r6_event_detail") or {}
            cancel = trace[cancel_step].get("r3c3t13s24d1r14r6_event_detail") or {}
            preissue_actions_array = np.asarray(
                [row.get("action_norm_tsc", []) for row in trace[PREFIX_END:issue_step]],
                dtype=float,
            )
            preissue_delta = np.diff(currents[PREFIX_END : issue_step + 1], axis=0)
            preissue_zero_actions = bool(
                preissue_actions_array.shape == (issue_step - PREFIX_END, N_COILS)
                and np.array_equal(
                    preissue_actions_array, np.zeros_like(preissue_actions_array)
                )
            )
            preissue_zero_currents = bool(
                preissue_delta.shape == (issue_step - PREFIX_END, N_COILS)
                and np.array_equal(preissue_delta, np.zeros_like(preissue_delta))
            )
            issue_exact = bool(
                _event_passes(
                    issue,
                    expected_name="sequential_issue",
                    slot=direction_index,
                    task_step=issue_step,
                )
                and list(map(float, issue.get("requested_coordinate", [])))
                == expected_coordinate
            )
            cancel_exact = bool(
                _event_passes(
                    cancel,
                    expected_name="sequential_cancel",
                    slot=direction_index,
                    task_step=cancel_step,
                )
                and cancel.get("stored_center_card15_fields")
                == issue.get("center_card15_fields")
            )
            actions = np.asarray(
                [row.get("action_norm_tsc", []) for row in trace[zero_after_step:]],
                dtype=float,
            )
            delta = np.diff(currents[zero_after_step:], axis=0)
            zero_after_actions = bool(
                actions.shape == (horizon - zero_after_step, N_COILS)
                and np.array_equal(actions, np.zeros_like(actions))
            )
            zero_after_currents = bool(
                delta.shape == (horizon - zero_after_step, N_COILS)
                and np.array_equal(delta, np.zeros_like(delta))
            )
            role_pass = bool(
                preissue_zero_actions
                and preissue_zero_currents
                and r4_baseline_issue_state_exact
                and issue_exact
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
                "direction_index": int(spec["d1r14r6_direction_index"]),
                "direction_name": str(spec["d1r14r6_direction_name"]),
                "sign": int(spec["d1r14r6_sign"]),
                "issue_task_step": int(spec["d1r14r6_issue_task_step"]),
                "cancel_task_step": int(spec["d1r14r6_cancel_task_step"]),
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
                "preissue_actions_exact_zero": preissue_zero_actions,
                "preissue_current_increments_exact_zero": preissue_zero_currents,
                "r4_baseline_issue_state_exact": r4_baseline_issue_state_exact,
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
    if safety_pass_count == 48 and len(valid_results) == 48:
        geometry = _response_geometry(ctx, specs, valid_results)
    else:
        geometry = {
            "evaluated": False,
            "passed": False,
            "reason": "safety_or_prefix_gate_failed",
        }
    if runtime_error_count > 0 or prefix_failure_count > 0 or inventory["count"] != 48:
        route = ctx.cfg["routes"]["runtime_fail"]
    elif safety_pass_count != 48:
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
        "expected_task_count": 48,
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
        "r4_baseline_issue_state_exact_count": sum(
            bool(row.get("r4_baseline_issue_state_exact")) for row in rows
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
        raise ValueError("D1R14R6 run requires offline_ready state")
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
            raise ValueError("D1R14R6 offline does not support resume")
        return prepare_offline(ctx)
    if command == "run":
        return run_real(ctx, backend=backend, resume=resume)
    if command == "postprocess":
        state = _read_json(ctx.paths.state)
        if state.get("phase_status") != "real_complete" or bool(state.get("finished")):
            raise ValueError("D1R14R6 postprocess requires real_complete state")
        return postprocess(ctx)
    raise ValueError(f"unsupported D1R14R6 command: {command}")


def self_test(config_path: Path) -> dict[str, Any]:
    config_path = config_path.expanduser().resolve()
    cfg = _read_json(config_path)
    _validate_config(cfg, config_path)
    action = zero_action(PREFIX_END)
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
        "issue_steps": list(ISSUE_STEPS),
        "cancel_steps": [step + CANCEL_OFFSET for step in ISSUE_STEPS],
        "zero_after_steps": [step + ZERO_AFTER_OFFSET for step in ISSUE_STEPS],
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
    parser.add_argument("--source-r2-run", type=Path, required=True)
    parser.add_argument("--source-r3-initial-output", type=Path, required=True)
    parser.add_argument("--source-r3-corrected-output", type=Path, required=True)
    parser.add_argument("--source-r4-run", type=Path, required=True)
    parser.add_argument("--source-r5-output", type=Path, required=True)
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
        source_r2_run=args.source_r2_run,
        source_r3_initial_output=args.source_r3_initial_output,
        source_r3_corrected_output=args.source_r3_corrected_output,
        source_r4_run=args.source_r4_run,
        source_r5_output=args.source_r5_output,
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
