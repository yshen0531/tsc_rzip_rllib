"""Stage4.1R16 amplitude-certified probe-derived braking closure.

R15B validated a clean finite four-basis local response model with new
Hadamard superposition probes.  A direct feasibility audit shows that the
externally validated small-signal envelope (one basis coefficient = a 0.015
mode pulse) is not large enough to close the two RZ weak-slew paths under the
immutable 270/370 ms contract.  The validated model predicts that the common
zero-net braking direction needs approximately four to six times that
amplitude.

R16 therefore does not silently extrapolate the small-signal model inside a
controller.  It first validates a preregistered amplitude ladder (1x, 2x, 4x, 6x)
with plus/minus real-TSC trajectories, requires the 6x braking candidate to
close all four modified paths with positive margin, then confirms the same
policy from trusted calibration tokens and recombines it with the fourteen
unchanged source paths.

The formal 250/350 and 270/370 ms timing contracts remain immutable.  This is a
finite clean two-target, two-delay, 0.9x-slew closure test, not restart,
hidden-history, continuous-parameter, noisy-sensing, or deployment validation.
"""
from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import math
import os
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from . import stage2_trajectory_optimization as s2
from . import stage4_1r8_trusted_batch_calibration_queue_tail_closure as r8
from . import stage4_1r13_original_deadline_delay_pipeline_early_braking as r13
from . import stage4_1r15_bounded_early_braking_local_response_identification as r15
from . import stage4_1r15b_probe_derived_symmetric_local_response_superposition_validation as r15b
from tsc_rzip_rllib.utils.ray_runtime import ensure_ray_worker_plan

atomic_write_json = r15.atomic_write_json
atomic_write_json_gz = r15.atomic_write_json_gz
read_json = r15.read_json
read_json_gz = r15.read_json_gz
utc_timestamp = r15.utc_timestamp
write_csv = r15.write_csv

SCHEMA_VERSION = 1
STAGE = "Stage4.1R16"
CONTROLLER_REVISION = "amplitude_certified_probe_derived_braking_closure_v16"
PACKAGE_REVISION = "r16_joint_envelope_amplitude_ladder_formal_closure_v1"
EXPECTED_SOURCE_REVISION = r15b.CONTROLLER_REVISION
EXPECTED_SOURCE_PACKAGE_REVISION = r15b.PACKAGE_REVISION
N_MODES = 3
BASIS_ORDER = r15b.BASIS_ORDER
WEAK_SLEW = 0.9
WEAK_HORIZON = 37


def _json_safe(value: Any) -> Any:
    return r15._json_safe(value)


def _as_float(value: Any, default: float = 0.0) -> float:
    return r15._as_float(value, default)


def _sha256_file(path: Path) -> str:
    return r15._sha256_file(path)


def _result_complete(path: Path) -> bool:
    return r15._result_complete(path)


def _scenario_digest(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(
        _json_safe(dict(payload)), sort_keys=True, separators=(",", ":"), allow_nan=False
    )
    return "s41r16_" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:20]


@dataclass(frozen=True)
class Stage41R16Paths:
    run_dir: Path
    source_reference: Path
    source_audit: Path
    amplitude_validation: Path
    calibrated_confirmation: Path
    formal_grid_confirmation: Path
    analysis: Path
    variants: Path
    state: Path
    manifest: Path

    @classmethod
    def from_run_dir(cls, run_dir: Path) -> "Stage41R16Paths":
        run_dir = run_dir.expanduser().resolve()
        return cls(
            run_dir=run_dir,
            source_reference=run_dir / "stage4_1r16_source_reference",
            source_audit=run_dir / "stage4_1r16_source_audit",
            amplitude_validation=run_dir / "stage4_1r16_amplitude_envelope_validation",
            calibrated_confirmation=run_dir / "stage4_1r16_calibrated_confirmation",
            formal_grid_confirmation=run_dir / "stage4_1r16_formal_grid_confirmation",
            analysis=run_dir / "stage4_1r16_analysis",
            variants=run_dir / "stage4_1r16_environment_variants",
            state=run_dir / "stage4_1r16_state.json",
            manifest=run_dir / "stage4_1r16_manifest.json",
        )


@dataclass
class Stage41R16Context:
    cfg: dict[str, Any]
    paths: Stage41R16Paths
    project_dir: Path
    source_stage41r15b_run: Path
    source_stage41r15_run: Path
    source_stage41r14_run: Path
    source_stage41r13_run: Path
    source_manifest: dict[str, Any]
    source_state: dict[str, Any]
    source_cfg: dict[str, Any]
    source_verdict: dict[str, Any]
    r15b_ctx: r15b.Stage41R15BContext
    source_fingerprint: dict[str, Any]


SOURCE_INVENTORY_CONTRACT = "r16_direct_stage4_1r15b_source_v1"


def _required_source_files(source: Path) -> list[Path]:
    required = [
        source / "stage4_1r15b_manifest.json",
        source / "stage4_1r15b_state.json",
        source / "stage4_1r15b_config.resolved.json",
        source / "stage4_1r15b_analysis" / "stage4_1r15b_verdict.json",
        source / "stage4_1r15b_analysis" / "stage4_1r15b_summary.json",
        source / "stage4_1r15b_source_audit" / "summary.json",
        source / "stage4_1r15b_probe_derived_response_model" / "models.json",
        source / "stage4_1r15b_probe_derived_response_model" / "summary.json",
        source / "stage4_1r15b_probe_derived_response_model" / "group_summary.csv",
        source / "stage4_1r15b_superposition_validation" / "summary.json",
        source / "stage4_1r15b_superposition_validation" / "results.json",
        source / "stage4_1r15b_superposition_validation" / "results.csv",
        source / "stage4_1r15b_superposition_validation" / "central_symmetry.csv",
        source / "stage4_1r15b_superposition_validation" / "basis_reconstruction.csv",
    ]
    required.extend(
        sorted((source / "stage4_1r15b_superposition_validation" / "raw").glob("*.json.gz"))
    )
    return required


def _source_inventory(source: Path) -> dict[str, Any]:
    source = source.expanduser().resolve()
    rows: list[dict[str, Any]] = []
    total = 0
    for path in _required_source_files(source):
        if not path.is_file():
            raise FileNotFoundError(f"required Stage4.1R15B source file missing: {path}")
        size = path.stat().st_size
        total += size
        rows.append(
            {
                "relative_path": str(path.relative_to(source)),
                "size_bytes": size,
                "sha256": _sha256_file(path),
            }
        )
    canonical = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {
        "schema_version": 1,
        "source_stage": "Stage4.1R15B",
        "inventory_contract": SOURCE_INVENTORY_CONTRACT,
        "n_files": len(rows),
        "total_bytes": total,
        "digest": hashlib.sha256(canonical).hexdigest(),
        "files": rows,
    }


def validate_config(cfg: Mapping[str, Any]) -> None:
    if cfg.get("controller_revision") != CONTROLLER_REVISION:
        raise ValueError("R16 controller revision mismatch")
    timing = cfg["formal_timing_contract"]
    if not bool(timing.get("immutable")):
        raise ValueError("R16 formal timing must remain immutable")
    if int(timing["normal_slew"]["arrival_deadline_step"]) != 25 or int(
        timing["normal_slew"]["hold_through_step"]
    ) != 35:
        raise ValueError("R16 normal timing must remain 250/350 ms")
    if int(timing["weak_slew"]["arrival_deadline_step"]) != 27 or int(
        timing["weak_slew"]["hold_through_step"]
    ) != 37:
        raise ValueError("R16 weak timing must remain 270/370 ms")
    if bool(timing.get("arrival_deadline_expansion_allowed")):
        raise ValueError("R16 may not expand arrival deadlines")
    amp = cfg["amplitude_envelope_validation"]
    if list(amp["basis_order"]) != list(BASIS_ORDER):
        raise ValueError("R16 basis order changed")
    if [float(x) for x in amp["magnitude_levels"]] != [1.0, 2.0, 4.0, 6.0]:
        raise ValueError("R16 amplitude ladder must remain 1x/2x/4x/6x")
    if not math.isclose(float(amp["closure_candidate_magnitude"]), 6.0, abs_tol=1e-15):
        raise ValueError("R16 closure candidate must remain the preregistered 6x direction")
    if int(amp["braking_sign"]) != -1 or int(amp["opposite_sign"]) != 1:
        raise ValueError("R16 direction signs changed")
    if int(amp["expected_rollouts"]) != 32:
        raise ValueError("R16 amplitude validation must contain 32 rollouts")
    if [int(x) for x in amp["actual_delay_steps"]] != [1, 2]:
        raise ValueError("R16 amplitude validation must remain delay=1/2")
    if [str(x["target_id"]) for x in amp["required_targets"]] != [
        "nominal",
        "RZ_p10_m10",
    ]:
        raise ValueError("R16 required target bank changed")
    if not math.isclose(float(amp["actual_slew_scale"]), WEAK_SLEW, abs_tol=1e-15):
        raise ValueError("R16 amplitude validation must remain at 0.9x slew")
    if int(amp["horizon_steps"]) != WEAK_HORIZON:
        raise ValueError("R16 amplitude validation horizon must remain 370 ms")
    if [float(x) for x in amp["common_direction"]] != [1.0, 1.0, 1.0, 1.0]:
        raise ValueError("R16 common braking direction changed")
    if not math.isclose(float(amp["maximum_requested_probe_component"]), 0.09, abs_tol=1e-15):
        raise ValueError("R16 maximum pulse component must remain 0.09")
    if not math.isclose(float(amp["maximum_current_utilization"]), 0.55, abs_tol=1e-15):
        raise ValueError("R16 current-utilization guard changed")
    if not math.isclose(
        float(amp["minimum_candidate_formal_signed_margin"]), 0.01, abs_tol=1e-15
    ):
        raise ValueError("R16 closure-candidate margin guard changed")
    if not bool(amp["require_candidate_all_four_formal_pass"]):
        raise ValueError("R16 must require all four modified paths")
    if int(cfg["calibrated_confirmation"]["expected_rollouts"]) != 4:
        raise ValueError("R16 calibrated confirmation must contain 4 rollouts")
    if int(cfg["formal_grid_confirmation"]["expected_cases"]) != 18:
        raise ValueError("R16 formal grid must contain 18 cases")
    if not bool(cfg.get("stage4_2r1_was_not_run_or_reused")):
        raise ValueError("R16 may not reuse Stage4.2R1")


def _validate_source_stage41r15b(
    source: Path, cfg: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    source = source.expanduser().resolve()
    manifest = read_json(source / "stage4_1r15b_manifest.json")
    state = read_json(source / "stage4_1r15b_state.json")
    source_cfg = read_json(source / "stage4_1r15b_config.resolved.json")
    verdict = read_json(source / "stage4_1r15b_analysis" / "stage4_1r15b_verdict.json")
    req = cfg["source_requirements"]
    checks = {
        "stage": manifest.get("stage") == "Stage4.1R15B",
        "controller_revision": manifest.get("controller_revision") == EXPECTED_SOURCE_REVISION,
        "package_revision": manifest.get("package_revision") == EXPECTED_SOURCE_PACKAGE_REVISION,
        "finished": bool(state.get("finished")),
        "empty_stop_reason": str(state.get("stop_reason", "")) == "",
        "source_audit_passed": verdict.get("source_audit_status") == "passed",
        "response_model_passed": verdict.get("probe_derived_model_status") == "passed",
        "superposition_passed": verdict.get("superposition_validation_status") == "passed",
        "identification_only": bool(verdict.get("identification_only")),
        "formal_timing_not_restored": not bool(verdict.get("formal_timing_contract_restored")),
        "stage4_2r1_not_reused": bool(verdict.get("stage4_2r1_was_not_run_or_reused")),
    }
    if not all(checks.values()):
        raise ValueError(f"R16 source R15B validation failed: {checks}")
    raw = sorted((source / "stage4_1r15b_superposition_validation" / "raw").glob("*.json.gz"))
    if len(raw) != int(req["require_r15b_raw_count"]):
        raise ValueError(f"R16 expected 32 R15B raw files, found {len(raw)}")
    return manifest, state, source_cfg, verdict


def _resolve_recorded_run(project_dir: Path, recorded: str, root_name: str) -> Path:
    return r15._resolve_recorded_run(project_dir, recorded, root_name)


def load_stage41r16_config(
    config_path: Path,
    *,
    source_stage41r15b_run: Path,
    run_dir_override: Path | None = None,
) -> Stage41R16Context:
    config_path = config_path.expanduser().resolve()
    cfg = read_json(config_path)
    validate_config(cfg)
    project_dir = config_path.parents[1]
    source_stage41r15b_run = source_stage41r15b_run.expanduser().resolve()
    manifest, state, source_cfg, verdict = _validate_source_stage41r15b(
        source_stage41r15b_run, cfg
    )
    source_stage41r15_run = _resolve_recorded_run(
        project_dir, str(manifest["source_stage4_1r15_run"]), "stage4_1r15_runs"
    )
    source_stage41r14_run = _resolve_recorded_run(
        project_dir, str(manifest["source_stage4_1r14_run"]), "stage4_1r14_runs"
    )
    source_stage41r13_run = _resolve_recorded_run(
        project_dir, str(manifest["source_stage4_1r13_run"]), "stage4_1r13_runs"
    )
    if run_dir_override is None:
        root = project_dir / str(cfg.get("output_root", "stage4_1r16_runs"))
        run_dir = root / f"{cfg.get('run_name', 'stage4_1r16')}_{utc_timestamp()}"
    else:
        run_dir = run_dir_override.expanduser().resolve()
    packaged_r15b_cfg = (
        project_dir
        / "configs"
        / "stage4_1r15b_probe_derived_symmetric_local_response_superposition_validation_370ms.json"
    )
    if not packaged_r15b_cfg.is_file():
        raise FileNotFoundError(f"packaged R15B dependency config missing: {packaged_r15b_cfg}")
    r15b_ctx = r15b.load_stage41r15b_config(
        packaged_r15b_cfg,
        source_stage41r15_run=source_stage41r15_run,
        run_dir_override=run_dir,
    )
    if r15b_ctx.source_stage41r14_run.resolve() != source_stage41r14_run.resolve():
        raise ValueError("R16 reconstructed R14 source mismatch")
    if r15b_ctx.source_stage41r13_run.resolve() != source_stage41r13_run.resolve():
        raise ValueError("R16 reconstructed R13 source mismatch")
    recorded_r15 = manifest.get("source_fingerprint") or {}
    current_r15 = r15b._source_inventory(source_stage41r15_run)
    if recorded_r15.get("digest") != current_r15.get("digest"):
        raise ValueError("R16 nested Stage4.1R15 source fingerprint mismatch")
    storage = cfg["storage"]
    base34 = (
        r15b_ctx.r15_ctx.r14_ctx.r13_ctx.r12_ctx.r11_ctx.r10_ctx.r9_ctx.r8_ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.base34
    )
    env_cfg = copy.deepcopy(base34.env_cfg)
    env_cfg["tsc_timeout_s"] = float(cfg["runtime"]["tsc_timeout_s"])
    env_cfg["tsc_workspace_root"] = str(
        Path(
            os.environ.get(
                "STAGE4_1R16_TSC_WORKSPACE_ROOT", storage["tsc_workspace_root"]
            )
        ).expanduser().resolve()
    )
    env_cfg["run_root"] = str(
        Path(os.environ.get("STAGE4_1R16_TSC_RUN_ROOT", storage["tsc_run_root"]))
        .expanduser()
        .resolve()
    )
    env_cfg["tsc_run_root"] = env_cfg["run_root"]
    env_cfg["keep_failed_episode_dir"] = bool(storage.get("keep_failed_episode_dir", False))
    env_cfg["keep_last_n_failed_episode_dirs"] = int(
        storage.get("keep_last_n_failed_episode_dirs", 0)
    )
    base34.env_cfg = env_cfg
    return Stage41R16Context(
        cfg=cfg,
        paths=Stage41R16Paths.from_run_dir(run_dir),
        project_dir=project_dir,
        source_stage41r15b_run=source_stage41r15b_run,
        source_stage41r15_run=source_stage41r15_run,
        source_stage41r14_run=source_stage41r14_run,
        source_stage41r13_run=source_stage41r13_run,
        source_manifest=manifest,
        source_state=state,
        source_cfg=source_cfg,
        source_verdict=verdict,
        r15b_ctx=r15b_ctx,
        source_fingerprint=_source_inventory(source_stage41r15b_run),
    )


def _initial_state(ctx: Stage41R16Context) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "stage": STAGE,
        "controller_revision": CONTROLLER_REVISION,
        "package_revision": PACKAGE_REVISION,
        "prepared": True,
        "source_audit_complete": False,
        "amplitude_validation_complete": False,
        "calibrated_confirmation_complete": False,
        "formal_grid_confirmation_complete": False,
        "finished": False,
        "stop_reason": "",
        "updated_utc": utc_timestamp(),
    }


def _update_state(ctx: Stage41R16Context, **updates: Any) -> dict[str, Any]:
    state = read_json(ctx.paths.state) if ctx.paths.state.is_file() else _initial_state(ctx)
    state.update(_json_safe(updates))
    state["updated_utc"] = utc_timestamp()
    atomic_write_json(ctx.paths.state, state)
    return state


def prepare(ctx: Stage41R16Context, *, resume: bool) -> None:
    for path in (
        ctx.paths.run_dir,
        ctx.paths.source_reference,
        ctx.paths.source_audit,
        ctx.paths.amplitude_validation,
        ctx.paths.calibrated_confirmation,
        ctx.paths.formal_grid_confirmation,
        ctx.paths.analysis,
        ctx.paths.variants,
    ):
        path.mkdir(parents=True, exist_ok=True)
    if ctx.paths.manifest.is_file():
        existing = read_json(ctx.paths.manifest)
        if existing.get("source_fingerprint", {}).get("digest") != ctx.source_fingerprint["digest"]:
            raise ValueError("R16 resume source fingerprint mismatch")
        if existing.get("controller_revision") != CONTROLLER_REVISION:
            raise ValueError("R16 resume controller revision mismatch")
        if existing.get("package_revision") != PACKAGE_REVISION:
            raise ValueError("R16 resume package revision mismatch")
    elif resume:
        raise FileNotFoundError("R16 resume requested but manifest is missing")
    atomic_write_json(ctx.paths.run_dir / "stage4_1r16_config.resolved.json", ctx.cfg)
    for name, payload in (
        ("stage4_1r15b_manifest.json", ctx.source_manifest),
        ("stage4_1r15b_state.json", ctx.source_state),
        ("stage4_1r15b_config.resolved.json", ctx.source_cfg),
        ("stage4_1r15b_verdict.json", ctx.source_verdict),
        ("source_content_inventory.json", ctx.source_fingerprint),
        ("nested_stage4_1r15_source_inventory.json", ctx.source_manifest.get("source_fingerprint") or {}),
        ("nested_stage4_1r14_source_inventory.json", ctx.source_manifest.get("nested_stage4_1r14_source_fingerprint") or {}),
        ("nested_stage4_1r13_source_inventory.json", ctx.source_manifest.get("nested_stage4_1r13_source_fingerprint") or {}),
    ):
        atomic_write_json(ctx.paths.source_reference / name, payload)
    manifest = {
        "schema_version": 1,
        "stage": STAGE,
        "controller_revision": CONTROLLER_REVISION,
        "package_revision": PACKAGE_REVISION,
        "created_utc": utc_timestamp(),
        "source_stage4_1r15b_run": str(ctx.source_stage41r15b_run),
        "source_stage4_1r15_run": str(ctx.source_stage41r15_run),
        "source_stage4_1r14_run": str(ctx.source_stage41r14_run),
        "source_stage4_1r13_run": str(ctx.source_stage41r13_run),
        "source_fingerprint": ctx.source_fingerprint,
        "source_inventory_contract": SOURCE_INVENTORY_CONTRACT,
        "workers": int(os.environ.get("STAGE4_1R16_WORKERS", ctx.cfg["parallel"]["n_workers"])),
        "formal_timing_contract": ctx.cfg["formal_timing_contract"],
        "closure_candidate_magnitude": ctx.cfg["amplitude_envelope_validation"]["closure_candidate_magnitude"],
        "arrival_deadline_expansion_allowed": False,
        "stage4_2r1_was_not_run_or_reused": True,
        "finite_test_envelope_only": True,
        "final_task": ctx.cfg["final_task"],
    }
    if not ctx.paths.manifest.is_file():
        atomic_write_json(ctx.paths.manifest, manifest)
    if not ctx.paths.state.is_file():
        atomic_write_json(ctx.paths.state, _initial_state(ctx))


def _read_raw_dir(path: Path) -> list[dict[str, Any]]:
    return [read_json_gz(item) for item in sorted(path.glob("*.json.gz"))]


def _models(ctx: Stage41R16Context) -> dict[str, Any]:
    return read_json(
        ctx.source_stage41r15b_run
        / "stage4_1r15b_probe_derived_response_model"
        / "models.json"
    )


def _baseline_map(ctx: Stage41R16Context) -> dict[tuple[str, int], dict[str, Any]]:
    return r15b._baseline_map(ctx.r15b_ctx)


def _formal_policy(ctx: Stage41R16Context, *, policy_id: str) -> dict[str, Any]:
    return {
        "policy_id": policy_id,
        "horizon_steps": WEAK_HORIZON,
        "allowed_arrival_steps": [
            int(x) for x in ctx.cfg["formal_timing_contract"]["weak_slew"]["allowed_arrival_steps"]
        ],
    }


def _formal_metrics(ctx: Stage41R16Context, result: Mapping[str, Any], *, policy_id: str) -> dict[str, Any]:
    r13_ctx = ctx.r15b_ctx.r15_ctx.r14_ctx.r13_ctx
    return r8.tracking_metrics(
        r13_ctx.r12_ctx.r11_ctx.r10_ctx.r9_ctx.r8_ctx,
        result,
        _formal_policy(ctx, policy_id=policy_id),
    )


def _predicted_result_from_model(
    baseline: Mapping[str, Any], model: Mapping[str, Any], coefficients: Sequence[float]
) -> dict[str, Any]:
    result = copy.deepcopy(dict(baseline))
    output = np.asarray(model["baseline_output"], dtype=float) + np.asarray(
        coefficients, dtype=float
    ) @ np.asarray(model["basis_odd_response"], dtype=float)
    count = 15
    trajectory = copy.deepcopy(list(result["trajectory"]))
    for local, state in enumerate(range(23, 38)):
        trajectory[state]["R"] = float(output[2 * count + local])
        trajectory[state]["Z"] = float(output[3 * count + local])
        trajectory[state]["Ip"] = float(output[4 * count + local])
    result["trajectory"] = trajectory
    result["success"] = True
    result["failure_reason"] = ""
    return result


def run_source_audit(ctx: Stage41R16Context) -> dict[str, Any]:
    source_validation = read_json(
        ctx.source_stage41r15b_run / "stage4_1r15b_superposition_validation" / "summary.json"
    )
    source_model = read_json(
        ctx.source_stage41r15b_run / "stage4_1r15b_probe_derived_response_model" / "summary.json"
    )
    source_rows = read_json(
        ctx.source_stage41r15b_run / "stage4_1r15b_superposition_validation" / "results.json"
    )
    h0_rows = [
        row
        for row in source_rows
        if str(row.get("combination_id")) == "hadamard_h0_all_plus"
        and len(row.get("basis_coefficients") or []) == 4
        and all(
            math.isclose(abs(float(value)), 0.5, rel_tol=0.0, abs_tol=1e-15)
            for value in row["basis_coefficients"]
        )
    ]
    h0_keys = {
        (str(row.get("target_id")), int(row.get("actual_delay_steps", -1)), int(row.get("global_sign", 0)))
        for row in h0_rows
    }
    expected_h0_keys = {
        (target, delay, sign)
        for target in ("nominal", "RZ_p10_m10")
        for delay in (1, 2)
        for sign in (-1, 1)
    }
    models = _models(ctx)
    baselines = _baseline_map(ctx)
    rows: list[dict[str, Any]] = []
    small_pass: dict[str, bool] = {}
    candidate_pass: dict[str, bool] = {}
    candidate_margin: dict[str, float] = {}
    for target in ("nominal", "RZ_p10_m10"):
        for delay in (1, 2):
            group_id = f"{target}__d{delay}"
            for magnitude in (0.0, 0.5, 1.0, 6.0):
                coefficients = -magnitude * np.ones(len(BASIS_ORDER), dtype=float)
                predicted = _predicted_result_from_model(
                    baselines[(target, delay)], models[group_id], coefficients
                )
                metrics = _formal_metrics(
                    ctx, predicted, policy_id=f"source_model_{group_id}_m{magnitude:g}"
                )
                row = {
                    "group_id": group_id,
                    "target_id": target,
                    "actual_delay_steps": delay,
                    "all_negative_magnitude": magnitude,
                    "equivalent_peak_component": 0.015 * magnitude,
                    "formal_tracking_pass": bool(metrics.get("stage3_4_target_tracking_pass")),
                    "minimum_signed_margin": _as_float(
                        metrics.get("stage3_4_tracking_minimum_signed_margin"), -math.inf
                    ),
                    "endpoint_late_speed_m_per_s": _as_float(
                        metrics.get("stage3_4_endpoint_late_velocity_rms_m_per_s"), math.inf
                    ),
                    "final_speed_m_per_s": _as_float(
                        metrics.get("stage3_4_final_velocity_m_per_s"), math.inf
                    ),
                    "inside_externally_validated_individual_axis_envelope": magnitude <= 1.0,
                    "inside_externally_validated_joint_combination_envelope": magnitude <= 0.5,
                    "diagnostic_extrapolation": magnitude > 0.5,
                }
                rows.append(row)
                if math.isclose(magnitude, 0.5):
                    small_pass[group_id] = bool(row["formal_tracking_pass"])
                if math.isclose(magnitude, 6.0):
                    candidate_pass[group_id] = bool(row["formal_tracking_pass"])
                    candidate_margin[group_id] = float(row["minimum_signed_margin"])
    req = ctx.cfg["source_requirements"]
    raw_count = len(
        list(
            (
                ctx.source_stage41r15b_run
                / "stage4_1r15b_superposition_validation"
                / "raw"
            ).glob("*.json.gz")
        )
    )
    checks = {
        "source_raw_coverage": raw_count == int(req["require_r15b_raw_count"]),
        "source_model_all_pass": bool(source_model.get("passed")),
        "source_superposition_all_pass": bool(source_validation.get("passed")),
        "source_model_prediction_fraction_one": math.isclose(
            float(source_validation.get("model_prediction_pass_fraction", 0.0)), 1.0
        ),
        "source_runtime_fraction_one": math.isclose(
            float(source_validation.get("runtime_guard_pass_fraction", 0.0)), 1.0
        ),
        "source_joint_h0_coverage_exact": h0_keys == expected_h0_keys and len(h0_rows) == 8,
        "source_joint_h0_runtime_and_model_all_pass": len(h0_rows) == 8
        and all(
            bool(row.get("runtime_guard_pass")) and bool(row.get("model_prediction_pass"))
            for row in h0_rows
        ),
        "source_joint_h0_peak_component_is_0p0075": len(h0_rows) == 8
        and all(
            math.isclose(
                float(row.get("maximum_requested_probe_component", math.nan)),
                0.0075,
                rel_tol=0.0,
                abs_tol=1e-12,
            )
            for row in h0_rows
        ),
        "validated_envelope_nominal_passes": all(
            small_pass.get(f"nominal__d{delay}", False) for delay in (1, 2)
        ),
        "validated_envelope_rz_does_not_close": all(
            not small_pass.get(f"RZ_p10_m10__d{delay}", True) for delay in (1, 2)
        ),
        "diagnostic_6x_predicts_all_four_pass": len(candidate_pass) == 4
        and all(candidate_pass.values()),
        "diagnostic_6x_minimum_margin": min(candidate_margin.values(), default=-math.inf)
        >= float(ctx.cfg["amplitude_envelope_validation"]["minimum_candidate_formal_signed_margin"]),
    }
    summary = {
        "schema_version": 1,
        "stage": STAGE,
        "phase": "source_audit",
        "source_stage4_1r15b_run": str(ctx.source_stage41r15b_run),
        "source_raw_rollouts": raw_count,
        "source_joint_h0_validation_rollouts": len(h0_rows),
        "source_joint_h0_validation_keys": [list(key) for key in sorted(h0_keys)],
        "source_model_prediction_pass_fraction": float(
            source_validation.get("model_prediction_pass_fraction", 0.0)
        ),
        "source_maximum_final_speed_error_m_per_s": float(
            source_validation.get("maximum_final_speed_error_m_per_s", math.inf)
        ),
        "individual_axis_externally_validated_peak_component": 0.015,
        "joint_common_direction_externally_validated_coefficient": 0.5,
        "joint_common_direction_externally_validated_peak_component": 0.0075,
        "small_signal_validated_envelope_closes_nominal_only": True,
        "small_signal_validated_envelope_closes_rz": False,
        "preregistered_amplitude_levels": [1.0, 2.0, 4.0, 6.0],
        "preregistered_candidate_magnitude": 6.0,
        "preregistered_candidate_peak_component": 0.09,
        "candidate_is_diagnostic_model_extrapolation_until_real_tsc_validates_it": True,
        "predicted_candidate_minimum_margin": min(candidate_margin.values()),
        "checks": checks,
        "passed": all(checks.values()),
        "interpretation": (
            "R15B is a valid finite clean small-signal superposition result.  Its externally validated "
            "joint common-direction coefficient 0.5 (0.0075 peak component) does not close either RZ weak-slew path.  A fixed 6x "
            "zero-net common braking direction is preregistered because the source model predicts all four "
            "modified paths with at least 0.01 signed margin, but this is an extrapolation and must be validated "
            "by new real-TSC amplitude-ladder trajectories before it may be used as a controller."
        ),
    }
    write_csv(ctx.paths.source_audit / "model_feasibility.csv", rows)
    atomic_write_json(ctx.paths.source_audit / "summary.json", summary)
    _update_state(ctx, source_audit_complete=True, source_audit_summary=summary)
    return summary


def materialize_variant(ctx: Stage41R16Context) -> tuple[str, dict[str, Any]]:
    variant, payload = r15.materialize_variant(ctx.r15b_ctx.r15_ctx)
    atomic_write_json(ctx.paths.variants / f"{variant}.payload.json", payload)
    return variant, payload


def _combined_schedule(
    ctx: Stage41R16Context, *, actual_delay: int, coefficients: Sequence[float]
) -> dict[int, np.ndarray]:
    return r15b._combined_schedule(
        ctx.r15b_ctx, actual_delay=actual_delay, coefficients=coefficients
    )


class LocalStage41R16Worker:
    def __init__(
        self,
        payload: dict[str, Any],
        library: dict[str, Any],
        bundle: dict[str, Any],
        worker_id: str,
        selector_cfg: dict[str, Any],
    ):
        self.inner = r15.LocalStage41R15ProbeWorker(
            payload, library, bundle, worker_id, selector_cfg
        )

    def close(self) -> None:
        self.inner.close()

    def evaluate(self, spec: dict[str, Any]) -> dict[str, Any]:
        result = self.inner.evaluate(spec)
        result["controller_revision"] = CONTROLLER_REVISION
        result["stage4_1r16_controller_revision"] = CONTROLLER_REVISION
        result["spec"] = copy.deepcopy(spec)
        result["r16_amplitude_summary"] = {
            "magnitude": float(spec["r16_magnitude"]),
            "direction_sign": int(spec["r16_direction_sign"]),
            "basis_order": list(BASIS_ORDER),
            "basis_coefficients": list(spec["r16_basis_coefficients"]),
            "closure_candidate": bool(spec.get("r16_closure_candidate", False)),
        }
        return _json_safe(result)


_RAY_ACTOR = None


def _ray_actor_class():
    global _RAY_ACTOR
    if _RAY_ACTOR is None:
        import ray

        @ray.remote(num_cpus=1, max_restarts=0)
        class Stage41R16Actor:
            def __init__(self, payload, library, bundle, worker_id, selector_cfg):
                self.worker = LocalStage41R16Worker(
                    payload, library, bundle, worker_id, selector_cfg
                )

            def evaluate(self, spec):
                return self.worker.evaluate(spec)

            def close(self):
                self.worker.close()
                return True

        _RAY_ACTOR = Stage41R16Actor
    return _RAY_ACTOR


def _base_spec(
    ctx: Stage41R16Context,
    *,
    phase: str,
    target: Mapping[str, Any],
    actual_delay: int,
    modeled_delay: int,
    calibration_token: str | None,
    trusted: bool,
    magnitude: float,
    direction_sign: int,
    environment_variant: str,
    controller_variant: str,
) -> dict[str, Any]:
    source_probe = ctx.r15b_ctx.source_cfg["bounded_probe_validation"]
    baseline_policy = {
        "policy_id": str(source_probe["baseline_policy_id"]),
        "first_affected_state_step": int(source_probe["baseline_first_affected_state_step"]),
    }
    coefficients = (
        float(direction_sign)
        * float(magnitude)
        * np.asarray(ctx.cfg["amplitude_envelope_validation"]["common_direction"], dtype=float)
    )
    schedule = _combined_schedule(
        ctx, actual_delay=int(actual_delay), coefficients=coefficients
    )
    r13_ctx = ctx.r15b_ctx.r15_ctx.r14_ctx.r13_ctx
    spec = r13._make_spec(
        phase=phase,
        policy=baseline_policy,
        target=target,
        actual_delay=int(actual_delay),
        modeled_delay=int(modeled_delay),
        calibration_token=calibration_token,
        trusted=trusted,
        controller_variant=controller_variant,
        environment_variant=environment_variant,
        ctx=r13_ctx,
    )
    identity = {
        "revision": CONTROLLER_REVISION,
        "phase": phase,
        "target": dict(target),
        "actual_delay": int(actual_delay),
        "modeled_delay": int(modeled_delay),
        "calibration_token": calibration_token,
        "magnitude": float(magnitude),
        "direction_sign": int(direction_sign),
        "coefficients": coefficients.tolist(),
        "schedule": {str(step): value.tolist() for step, value in sorted(schedule.items())},
    }
    spec.update(
        {
            "kind": "stage4_1r16_amplitude_certified_probe_derived_braking_closure",
            "controller_revision": CONTROLLER_REVISION,
            "experiment_id": _scenario_digest(identity),
            "phase": phase,
            "category": phase,
            "scenario": (
                f"m{float(magnitude):g}__sign{int(direction_sign):+d}__"
                f"{target['target_id']}__d{int(actual_delay)}__s0.9"
            ),
            "r15_probe_id": f"r16_common_direction_m{float(magnitude):g}",
            "r15_probe_sign": int(direction_sign),
            "r15_probe_mode": -1,
            "r15_probe_delta_by_issue_step": {
                str(step): value.tolist() for step, value in sorted(schedule.items())
            },
            "r15_identification_only": phase == "amplitude_envelope_validation",
            "r16_magnitude": float(magnitude),
            "r16_direction_sign": int(direction_sign),
            "r16_basis_order": list(BASIS_ORDER),
            "r16_basis_coefficients": coefficients.tolist(),
            "r16_closure_candidate": bool(
                int(direction_sign)
                == int(ctx.cfg["amplitude_envelope_validation"]["braking_sign"])
                and math.isclose(
                    float(magnitude),
                    float(ctx.cfg["amplitude_envelope_validation"]["closure_candidate_magnitude"]),
                    abs_tol=1e-15,
                )
            ),
            "r16_amplitude_validation_only": phase == "amplitude_envelope_validation",
            "formal_tracking_pass_required": phase != "amplitude_envelope_validation",
            "arrival_deadline_expansion_allowed": False,
        }
    )
    return spec


def _amplitude_specs(ctx: Stage41R16Context) -> list[dict[str, Any]]:
    cfg = ctx.cfg["amplitude_envelope_validation"]
    variant, _ = materialize_variant(ctx)
    specs: list[dict[str, Any]] = []
    for delay in cfg["actual_delay_steps"]:
        for target in cfg["required_targets"]:
            for magnitude in cfg["magnitude_levels"]:
                for sign in (int(cfg["braking_sign"]), int(cfg["opposite_sign"])):
                    specs.append(
                        _base_spec(
                            ctx,
                            phase="amplitude_envelope_validation",
                            target=target,
                            actual_delay=int(delay),
                            modeled_delay=int(delay),
                            calibration_token=None,
                            trusted=True,
                            magnitude=float(magnitude),
                            direction_sign=int(sign),
                            environment_variant=variant,
                            controller_variant="r16_oracle_amplitude_envelope",
                        )
                    )
    if len(specs) != int(cfg["expected_rollouts"]):
        raise ValueError("R16 amplitude specification count mismatch")
    ids = [spec["experiment_id"] for spec in specs]
    if len(set(ids)) != len(ids):
        raise ValueError("R16 amplitude experiment IDs are not unique")
    return specs


def _trusted_tokens(ctx: Stage41R16Context) -> dict[tuple[int, float], dict[str, Any]]:
    return r13._trusted_tokens(ctx.r15b_ctx.r15_ctx.r14_ctx.r13_ctx)


def _calibrated_specs(ctx: Stage41R16Context) -> list[dict[str, Any]]:
    cfg = ctx.cfg["amplitude_envelope_validation"]
    variant, _ = materialize_variant(ctx)
    magnitude = float(cfg["closure_candidate_magnitude"])
    sign = int(cfg["braking_sign"])
    tokens = _trusted_tokens(ctx)
    specs: list[dict[str, Any]] = []
    for delay in cfg["actual_delay_steps"]:
        token = tokens[(int(delay), WEAK_SLEW)]
        if not bool(token.get("batch_trusted_correct")) or bool(token.get("batch_wrong_accept")):
            raise ValueError(f"R16 refuses untrusted calibration token for delay={delay}")
        for target in cfg["required_targets"]:
            specs.append(
                _base_spec(
                    ctx,
                    phase="calibrated_confirmation",
                    target=target,
                    actual_delay=int(delay),
                    modeled_delay=int(token["batch_selected_delay_steps"]),
                    calibration_token=str(token["experiment_id"]),
                    trusted=True,
                    magnitude=magnitude,
                    direction_sign=sign,
                    environment_variant=variant,
                    controller_variant="r16_calibrated_confirmation",
                )
            )
    if len(specs) != int(ctx.cfg["calibrated_confirmation"]["expected_rollouts"]):
        raise ValueError("R16 calibrated specification count mismatch")
    return specs


def evaluate_specs(
    ctx: Stage41R16Context,
    specs: Sequence[dict[str, Any]],
    *,
    output_dir: Path,
    backend: str,
    resume: bool,
    log_prefix: str,
) -> list[dict[str, Any]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    _, payload = materialize_variant(ctx)
    chain = (
        ctx.r15b_ctx.r15_ctx.r14_ctx.r13_ctx.r12_ctx.r11_ctx.r10_ctx.r9_ctx.r8_ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx
    )
    variant = str(specs[0]["environment_variant"]) if specs else ""
    if variant:
        chain.variants[variant] = payload
    pending = [
        spec
        for spec in specs
        if not (resume and _result_complete(output_dir / f"{spec['experiment_id']}.json.gz"))
    ]
    library = chain.r3_ctx.source_library
    bundle = chain.r3_ctx.source_bundle
    selector_cfg = ctx.r15b_ctx.r15_ctx.r14_ctx.r13_ctx.r12_ctx.r11_ctx.r10_ctx.r9_ctx.r8_ctx.cfg[
        "batch_selector"
    ]
    if backend == "serial":
        worker = LocalStage41R16Worker(
            payload, library, bundle, "stage41r16_serial", selector_cfg
        )
        try:
            for index, spec in enumerate(pending, 1):
                atomic_write_json_gz(
                    output_dir / f"{spec['experiment_id']}.json.gz",
                    worker.evaluate(spec),
                )
                print(f"{log_prefix} {index}/{len(pending)}", flush=True)
        finally:
            worker.close()
    elif backend == "ray" and pending:
        import ray

        requested = int(
            os.environ.get("STAGE4_1R16_WORKERS", ctx.cfg["parallel"]["n_workers"])
        )
        plan = ensure_ray_worker_plan(
            ray,
            requested_workers=requested,
            pending_tasks=len(pending),
            ray_tmpdir=os.environ.get("RAY_TMPDIR", ctx.cfg["parallel"].get("ray_tmpdir", "")) or None,
            log_prefix=log_prefix,
        )
        Actor = _ray_actor_class()
        actors = [
            Actor.remote(payload, library, bundle, f"stage41r16_{index:03d}", selector_cfg)
            for index in range(plan.actor_count)
        ]
        refs: dict[Any, dict[str, Any]] = {}
        for index, spec in enumerate(pending):
            refs[actors[index % len(actors)].evaluate.remote(spec)] = spec
        done = 0
        try:
            while refs:
                ready, _ = ray.wait(list(refs), num_returns=1, timeout=30.0)
                if not ready:
                    print(f"{log_prefix} waiting {done}/{len(pending)}", flush=True)
                    continue
                for ref in ready:
                    spec = refs.pop(ref)
                    try:
                        result = ray.get(ref)
                    except Exception as exc:
                        result = {
                            "schema_version": 1,
                            "controller_revision": CONTROLLER_REVISION,
                            "experiment_id": spec["experiment_id"],
                            "spec": spec,
                            "success": False,
                            "failure_reason": repr(exc),
                            "traceback": traceback.format_exc(),
                            "trajectory": [],
                            "control_trace": [],
                        }
                    atomic_write_json_gz(
                        output_dir / f"{spec['experiment_id']}.json.gz", result
                    )
                    done += 1
                    if done % 10 == 0 or not refs:
                        print(f"{log_prefix} {done}/{len(pending)}", flush=True)
        finally:
            s2._close_ray_actors(
                actors,
                timeout_s=float(ctx.cfg["storage"].get("actor_close_timeout_s", 1800.0)),
            )
    elif backend not in {"serial", "ray"}:
        raise ValueError("backend must be 'ray' or 'serial'")
    return [
        read_json_gz(output_dir / f"{spec['experiment_id']}.json.gz") for spec in specs
    ]


def _current_utilization(ctx: Stage41R16Context, result: Mapping[str, Any]) -> float:
    r13_ctx = ctx.r15b_ctx.r15_ctx.r14_ctx.r13_ctx
    env_cfg = r13_ctx.r12_ctx.r11_ctx.r10_ctx.r9_ctx.r8_ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.base34.env_cfg
    currents = np.asarray(
        [row["currents_a_display"] for row in result.get("trajectory") or []], dtype=float
    )
    if not currents.size:
        return math.inf
    min_i = np.asarray(env_cfg["min_current_a_display_order"], dtype=float)
    max_i = np.asarray(env_cfg["max_current_a_display_order"], dtype=float)
    center = 0.5 * (min_i + max_i)
    half = np.maximum(0.5 * (max_i - min_i), 1e-9)
    return float(np.max(np.abs((currents - center[None, :]) / half[None, :])))


def _runtime_row(ctx: Stage41R16Context, result: Mapping[str, Any]) -> dict[str, Any]:
    spec = result["spec"]
    target = str(spec["target_id"])
    delay = int(spec["action_delay_steps"])
    baseline = _baseline_map(ctx)[(target, delay)]
    first_effect = int(ctx.r15b_ctx.source_cfg["bounded_probe_validation"]["baseline_first_affected_state_step"])
    physics = r13._physics_array(result)[:first_effect]
    baseline_physics = r13._physics_array(baseline)[:first_effect]
    prefix_exact = bool(
        physics.shape == baseline_physics.shape and np.array_equal(physics, baseline_physics)
    )
    trace = list(result.get("anticipatory_damping_trace") or [])
    probe = result.get("r15_probe_summary") or {}
    expected_max = 0.015 * float(spec["r16_magnitude"])
    applied_equals_requested = bool(
        int(probe.get("probe_issue_count", -1)) == int(probe.get("probe_applied_issue_count", -2))
        and math.isclose(
            _as_float(probe.get("maximum_requested_component"), math.inf),
            _as_float(probe.get("maximum_applied_component"), -math.inf),
            rel_tol=0.0,
            abs_tol=1e-12,
        )
    )
    runtime_pass = bool(
        result.get("success")
        and not str(result.get("failure_reason", "")).strip()
        and not any(bool(row.get("abnormal", False)) for row in result.get("trajectory") or [])
        and all(bool(row.get("solver_success", False)) for row in trace)
        and bool((result.get("anticipatory_damping_summary") or {}).get("streaming_queue_consistent"))
        and not any(bool(row.get("future_measurement_used", True)) for row in trace)
        and bool(probe.get("probe_zero_net"))
        and bool(probe.get("applied_probe_zero_net"))
        and applied_equals_requested
        and math.isclose(
            _as_float(probe.get("maximum_requested_component"), math.inf),
            expected_max,
            rel_tol=0.0,
            abs_tol=1e-12,
        )
        and prefix_exact
        and _current_utilization(ctx, result)
        <= float(ctx.cfg["amplitude_envelope_validation"]["maximum_current_utilization"])
    )
    return {
        "prefix_exact_before_first_effect": prefix_exact,
        "streaming_queue_consistent": bool(
            (result.get("anticipatory_damping_summary") or {}).get("streaming_queue_consistent")
        ),
        "no_future_measurement": not any(
            bool(row.get("future_measurement_used", True)) for row in trace
        ),
        "probe_zero_net": bool(probe.get("probe_zero_net")),
        "applied_probe_zero_net": bool(probe.get("applied_probe_zero_net")),
        "requested_probe_net_norm": _as_float(probe.get("requested_probe_net_norm")),
        "applied_probe_net_norm": _as_float(probe.get("applied_probe_net_norm"), math.inf),
        "probe_issue_count": int(probe.get("probe_issue_count", 0)),
        "probe_applied_issue_count": int(probe.get("probe_applied_issue_count", 0)),
        "maximum_requested_component": _as_float(probe.get("maximum_requested_component")),
        "maximum_applied_component": _as_float(probe.get("maximum_applied_component")),
        "applied_equals_requested_probe": applied_equals_requested,
        "maximum_current_utilization": _current_utilization(ctx, result),
        "runtime_guard_pass": runtime_pass,
    }


def run_amplitude_validation(
    ctx: Stage41R16Context, *, backend: str, resume: bool
) -> dict[str, Any]:
    specs = _amplitude_specs(ctx)
    raw_dir = ctx.paths.amplitude_validation / "raw"
    results = evaluate_specs(
        ctx,
        specs,
        output_dir=raw_dir,
        backend=backend,
        resume=resume,
        log_prefix="[Stage4.1R16 amplitude-envelope]",
    )
    models = _models(ctx)
    baselines = _baseline_map(ctx)
    amp_cfg = ctx.cfg["amplitude_envelope_validation"]
    validation = amp_cfg["model_validation"]
    rows: list[dict[str, Any]] = []
    outputs: dict[tuple[str, int, float, int], np.ndarray] = {}
    for result in results:
        spec = result["spec"]
        target = str(spec["target_id"])
        delay = int(spec["action_delay_steps"])
        magnitude = float(spec["r16_magnitude"])
        sign = int(spec["r16_direction_sign"])
        group_id = f"{target}__d{delay}"
        coefficients = np.asarray(spec["r16_basis_coefficients"], dtype=float)
        predicted = r15b._predict_superposition(models[group_id], coefficients)
        actual = r15._output_vector(
            result,
            start_state=int(ctx.source_cfg["probe_derived_response_model"]["output_state_start"]),
            end_state_inclusive=int(ctx.source_cfg["probe_derived_response_model"]["output_state_end_inclusive"]),
        )
        layout = r15b._output_layout(ctx.r15b_ctx)
        pred_metrics = r15._prediction_metrics(actual, predicted, layout)
        runtime = _runtime_row(ctx, result)
        formal = _formal_metrics(
            ctx,
            result,
            policy_id=f"r16_m{magnitude:g}_sign{sign:+d}_{target}_d{delay}",
        )
        model_pass = bool(
            pred_metrics["velocity_component_rmse_m_per_s"]
            <= float(validation["maximum_velocity_component_rmse_m_per_s"])
            and pred_metrics["endpoint_late_speed_error_m_per_s"]
            <= float(validation["maximum_endpoint_late_speed_error_m_per_s"])
            and pred_metrics["final_speed_error_m_per_s"]
            <= float(validation["maximum_final_speed_error_m_per_s"])
            and pred_metrics["position_rmse_m"]
            <= float(validation["maximum_position_rmse_m"])
            and pred_metrics["ip_rmse_A"] <= float(validation["maximum_ip_rmse_A"])
        )
        row = {
            "experiment_id": result["experiment_id"],
            "target_id": target,
            "actual_delay_steps": delay,
            "magnitude": magnitude,
            "direction_sign": sign,
            "basis_coefficients": list(spec["r16_basis_coefficients"]),
            "environment_success": bool(result.get("success")),
            "failure_reason": str(result.get("failure_reason", "")),
            **runtime,
            **pred_metrics,
            "model_prediction_pass": model_pass,
            "formal_tracking_pass": bool(formal.get("stage3_4_target_tracking_pass")),
            "formal_minimum_signed_margin": _as_float(
                formal.get("stage3_4_tracking_minimum_signed_margin"), -math.inf
            ),
            "formal_best_endpoint_step": formal.get("stage3_4_best_endpoint_step"),
            "endpoint_late_speed_m_per_s": formal.get(
                "stage3_4_endpoint_late_velocity_rms_m_per_s"
            ),
            "final_speed_m_per_s": formal.get("stage3_4_final_velocity_m_per_s"),
            "closure_candidate": bool(spec.get("r16_closure_candidate")),
        }
        rows.append(row)
        outputs[(target, delay, magnitude, sign)] = actual

    layout = r15b._output_layout(ctx.r15b_ctx)
    count = int(layout["state_count"])
    symmetry_rows: list[dict[str, Any]] = []
    scaling_rows: list[dict[str, Any]] = []
    all_symmetry = True
    all_scaling = True
    direction = np.ones(len(BASIS_ORDER), dtype=float)
    for target in ("nominal", "RZ_p10_m10"):
        for delay in (1, 2):
            group_id = f"{target}__d{delay}"
            baseline_y = np.asarray(models[group_id]["baseline_output"], dtype=float)
            unit_response = direction @ np.asarray(
                models[group_id]["basis_odd_response"], dtype=float
            )
            for magnitude in map(float, amp_cfg["magnitude_levels"]):
                braking = outputs[(target, delay, magnitude, int(amp_cfg["braking_sign"]))]
                opposite = outputs[(target, delay, magnitude, int(amp_cfg["opposite_sign"]))]
                even = braking + opposite - 2.0 * baseline_y
                symmetry_velocity = float(
                    np.sqrt(np.mean(even[: 2 * count] ** 2))
                )
                symmetry_pass = symmetry_velocity <= float(
                    validation["maximum_central_symmetry_velocity_rmse_m_per_s"]
                )
                all_symmetry = all_symmetry and symmetry_pass
                symmetry_rows.append(
                    {
                        "target_id": target,
                        "actual_delay_steps": delay,
                        "magnitude": magnitude,
                        "central_symmetry_velocity_rmse_m_per_s": symmetry_velocity,
                        "passed": symmetry_pass,
                    }
                )
                odd_per_unit = 0.5 * (opposite - braking) / magnitude
                diff = odd_per_unit - unit_response
                velocity_rmse = float(np.sqrt(np.mean(diff[: 2 * count] ** 2)))
                position_rmse = float(
                    np.sqrt(np.mean(diff[2 * count : 4 * count] ** 2))
                )
                ip_rmse = float(np.sqrt(np.mean(diff[4 * count :] ** 2)))
                scaling_pass = bool(
                    velocity_rmse
                    <= float(validation["maximum_per_unit_velocity_response_rmse_m_per_s"])
                    and position_rmse
                    <= float(validation["maximum_per_unit_position_response_rmse_m"])
                    and ip_rmse <= float(validation["maximum_per_unit_ip_response_rmse_A"])
                )
                all_scaling = all_scaling and scaling_pass
                scaling_rows.append(
                    {
                        "target_id": target,
                        "actual_delay_steps": delay,
                        "magnitude": magnitude,
                        "per_unit_velocity_response_rmse_m_per_s": velocity_rmse,
                        "per_unit_position_response_rmse_m": position_rmse,
                        "per_unit_ip_response_rmse_A": ip_rmse,
                        "passed": scaling_pass,
                    }
                )

    candidate_mag = float(amp_cfg["closure_candidate_magnitude"])
    candidate_sign = int(amp_cfg["braking_sign"])
    candidate_rows = [
        row
        for row in rows
        if math.isclose(float(row["magnitude"]), candidate_mag, abs_tol=1e-15)
        and int(row["direction_sign"]) == candidate_sign
    ]
    candidate_pass = bool(
        len(candidate_rows) == 4
        and all(bool(row["runtime_guard_pass"]) for row in candidate_rows)
        and all(bool(row["model_prediction_pass"]) for row in candidate_rows)
        and all(bool(row["formal_tracking_pass"]) for row in candidate_rows)
        and min(
            (_as_float(row["formal_minimum_signed_margin"], -math.inf) for row in candidate_rows),
            default=-math.inf,
        )
        >= float(amp_cfg["minimum_candidate_formal_signed_margin"])
    )
    joint_fraction = float(
        np.mean(
            [
                bool(row["runtime_guard_pass"] and row["model_prediction_pass"])
                for row in rows
            ]
        )
    )
    passed = bool(
        len(rows) == int(amp_cfg["expected_rollouts"])
        and len({row["experiment_id"] for row in rows}) == len(rows)
        and joint_fraction >= float(validation["minimum_pass_fraction"])
        and all_symmetry
        and all_scaling
        and candidate_pass
    )
    write_csv(ctx.paths.amplitude_validation / "results.csv", rows)
    atomic_write_json(ctx.paths.amplitude_validation / "results.json", rows)
    write_csv(ctx.paths.amplitude_validation / "central_symmetry.csv", symmetry_rows)
    write_csv(ctx.paths.amplitude_validation / "per_unit_scaling.csv", scaling_rows)
    write_csv(ctx.paths.amplitude_validation / "closure_candidate.csv", candidate_rows)
    summary = {
        "schema_version": 1,
        "stage": STAGE,
        "phase": "amplitude_envelope_validation",
        "n_rollouts": len(rows),
        "expected_rollouts": int(amp_cfg["expected_rollouts"]),
        "coverage_complete": len(rows) == int(amp_cfg["expected_rollouts"]),
        "environment_success_count": sum(bool(row["environment_success"]) for row in rows),
        "runtime_guard_pass_fraction": float(
            np.mean([bool(row["runtime_guard_pass"]) for row in rows])
        ),
        "model_prediction_pass_fraction": float(
            np.mean([bool(row["model_prediction_pass"]) for row in rows])
        ),
        "joint_pass_fraction": joint_fraction,
        "maximum_velocity_component_rmse_m_per_s": max(
            row["velocity_component_rmse_m_per_s"] for row in rows
        ),
        "maximum_endpoint_late_speed_error_m_per_s": max(
            row["endpoint_late_speed_error_m_per_s"] for row in rows
        ),
        "maximum_final_speed_error_m_per_s": max(
            row["final_speed_error_m_per_s"] for row in rows
        ),
        "maximum_position_rmse_m": max(row["position_rmse_m"] for row in rows),
        "maximum_ip_rmse_A": max(row["ip_rmse_A"] for row in rows),
        "maximum_central_symmetry_velocity_rmse_m_per_s": max(
            row["central_symmetry_velocity_rmse_m_per_s"] for row in symmetry_rows
        ),
        "maximum_per_unit_velocity_response_rmse_m_per_s": max(
            row["per_unit_velocity_response_rmse_m_per_s"] for row in scaling_rows
        ),
        "maximum_per_unit_position_response_rmse_m": max(
            row["per_unit_position_response_rmse_m"] for row in scaling_rows
        ),
        "maximum_per_unit_ip_response_rmse_A": max(
            row["per_unit_ip_response_rmse_A"] for row in scaling_rows
        ),
        "maximum_current_utilization": max(row["maximum_current_utilization"] for row in rows),
        "closure_candidate_magnitude": candidate_mag,
        "closure_candidate_peak_component": 0.015 * candidate_mag,
        "closure_candidate_rollouts": len(candidate_rows),
        "closure_candidate_formal_pass_fraction": (
            sum(bool(row["formal_tracking_pass"]) for row in candidate_rows)
            / len(candidate_rows)
            if candidate_rows
            else 0.0
        ),
        "closure_candidate_minimum_signed_margin": min(
            (_as_float(row["formal_minimum_signed_margin"], -math.inf) for row in candidate_rows),
            default=-math.inf,
        ),
        "closure_candidate_passed": candidate_pass,
        "candidate_was_preregistered_from_source_model_not_selected_from_new_tsc": True,
        "formal_timing_contract_unchanged": True,
        "passed": passed,
    }
    atomic_write_json(ctx.paths.amplitude_validation / "summary.json", summary)
    _update_state(
        ctx,
        amplitude_validation_complete=True,
        amplitude_validation_summary=summary,
    )
    return summary


def _oracle_candidate_map(ctx: Stage41R16Context) -> dict[tuple[str, int], dict[str, Any]]:
    output: dict[tuple[str, int], dict[str, Any]] = {}
    cfg = ctx.cfg["amplitude_envelope_validation"]
    for path in sorted((ctx.paths.amplitude_validation / "raw").glob("*.json.gz")):
        result = read_json_gz(path)
        spec = result.get("spec") or {}
        if not (
            math.isclose(
                float(spec.get("r16_magnitude", math.nan)),
                float(cfg["closure_candidate_magnitude"]),
                abs_tol=1e-15,
            )
            and int(spec.get("r16_direction_sign", 0)) == int(cfg["braking_sign"])
        ):
            continue
        key = (str(spec["target_id"]), int(spec["action_delay_steps"]))
        if key in output:
            raise ValueError(f"duplicate R16 candidate Oracle case: {key}")
        output[key] = result
    if len(output) != 4:
        raise ValueError(f"R16 expected four candidate Oracle cases, found {len(output)}")
    return output


def _comparison_components(result: Mapping[str, Any]) -> dict[str, np.ndarray]:
    return r13._comparison_components(result)


def _finite_max_abs(left: np.ndarray, right: np.ndarray) -> float:
    return r13._finite_max_abs(left, right)


def run_calibrated_confirmation(
    ctx: Stage41R16Context, *, backend: str, resume: bool
) -> dict[str, Any]:
    specs = _calibrated_specs(ctx)
    results = evaluate_specs(
        ctx,
        specs,
        output_dir=ctx.paths.calibrated_confirmation / "raw",
        backend=backend,
        resume=resume,
        log_prefix="[Stage4.1R16 calibrated-confirmation]",
    )
    oracle = _oracle_candidate_map(ctx)
    atol = float(ctx.cfg["calibrated_confirmation"]["numeric_trace_equivalence_atol"])
    rows: list[dict[str, Any]] = []
    comparisons: list[dict[str, Any]] = []
    for result in results:
        spec = result["spec"]
        key = (str(spec["target_id"]), int(spec["action_delay_steps"]))
        metrics = _formal_metrics(ctx, result, policy_id=f"r16_calibrated_{key[0]}_d{key[1]}")
        runtime = _runtime_row(ctx, result)
        left = _comparison_components(result)
        right = _comparison_components(oracle[key])
        component_diff = {name: _finite_max_abs(left[name], right[name]) for name in left}
        exact = all(np.array_equal(left[name], right[name]) for name in left)
        numeric = all(
            np.allclose(left[name], right[name], rtol=0.0, atol=atol) for name in left
        )
        row = {
            "experiment_id": result["experiment_id"],
            "target_id": key[0],
            "actual_delay_steps": key[1],
            "calibration_token": spec.get("calibration_token"),
            "trusted_calibration_model": bool(spec.get("trusted_calibration_model")),
            **runtime,
            "formal_tracking_pass": bool(metrics.get("stage3_4_target_tracking_pass")),
            "formal_minimum_signed_margin": metrics.get(
                "stage3_4_tracking_minimum_signed_margin"
            ),
            "exact_trace_equal_to_oracle": exact,
            "numeric_trace_equal_to_oracle": numeric,
            "maximum_trace_abs_difference": max(component_diff.values()),
        }
        rows.append(row)
        comparisons.append(
            {
                "target_id": key[0],
                "actual_delay_steps": key[1],
                "calibration_token": spec.get("calibration_token"),
                "exact_trace_equal_to_oracle": exact,
                "numeric_trace_equal_to_oracle": numeric,
                "maximum_trace_abs_difference": max(component_diff.values()),
                "component_max_abs_difference": component_diff,
            }
        )
    tokens = {str(row["calibration_token"]) for row in rows if row.get("calibration_token")}
    untrusted = sum(not bool(row["trusted_calibration_model"]) for row in rows)
    passed = bool(
        len(rows) == int(ctx.cfg["calibrated_confirmation"]["expected_rollouts"])
        and all(bool(row["runtime_guard_pass"]) for row in rows)
        and all(bool(row["formal_tracking_pass"]) for row in rows)
        and all(bool(row["exact_trace_equal_to_oracle"]) for row in rows)
        and all(bool(row["numeric_trace_equal_to_oracle"]) for row in rows)
        and len(tokens)
        == int(ctx.cfg["calibrated_confirmation"]["require_distinct_calibration_tokens"])
        and untrusted
        == int(ctx.cfg["calibrated_confirmation"]["require_untrusted_start_count"])
    )
    write_csv(ctx.paths.calibrated_confirmation / "results.csv", rows)
    atomic_write_json(ctx.paths.calibrated_confirmation / "results.json", rows)
    summary = {
        "schema_version": 1,
        "stage": STAGE,
        "phase": "calibrated_confirmation",
        "n_rollouts": len(rows),
        "expected_rollouts": int(ctx.cfg["calibrated_confirmation"]["expected_rollouts"]),
        "formal_contract_pass_fraction": (
            sum(bool(row["formal_tracking_pass"]) for row in rows) / len(rows)
            if rows
            else 0.0
        ),
        "distinct_calibration_tokens": len(tokens),
        "untrusted_main_start_count": untrusted,
        "exact_trace_equivalence_fraction": (
            sum(bool(row["exact_trace_equal_to_oracle"]) for row in rows) / len(rows)
            if rows
            else 0.0
        ),
        "numeric_trace_equivalence_fraction": (
            sum(bool(row["numeric_trace_equal_to_oracle"]) for row in rows) / len(rows)
            if rows
            else 0.0
        ),
        "numeric_trace_equivalence_atol": atol,
        "maximum_trace_abs_difference": max(
            (_as_float(row["maximum_trace_abs_difference"], math.inf) for row in rows),
            default=math.inf,
        ),
        "comparisons": comparisons,
        "passed": passed,
    }
    atomic_write_json(ctx.paths.calibrated_confirmation / "summary.json", summary)
    _update_state(
        ctx,
        calibrated_confirmation_complete=True,
        calibrated_confirmation_summary=summary,
    )
    return summary


def _calibrated_map(ctx: Stage41R16Context) -> dict[tuple[str, int], dict[str, Any]]:
    output: dict[tuple[str, int], dict[str, Any]] = {}
    for path in sorted((ctx.paths.calibrated_confirmation / "raw").glob("*.json.gz")):
        result = read_json_gz(path)
        spec = result["spec"]
        key = (str(spec["target_id"]), int(spec["action_delay_steps"]))
        if key in output:
            raise ValueError(f"duplicate R16 calibrated case: {key}")
        output[key] = result
    return output


def run_formal_grid_confirmation(ctx: Stage41R16Context) -> dict[str, Any]:
    r13_ctx = ctx.r15b_ctx.r15_ctx.r14_ctx.r13_ctx
    source_oracle = r13._source_oracle_map(r13_ctx)
    source_calibrated = r13._source_calibrated_map(r13_ctx)
    modified_oracle = _oracle_candidate_map(ctx)
    modified_calibrated = _calibrated_map(ctx)
    affected = {
        (target, delay, WEAK_SLEW)
        for target in ("nominal", "RZ_p10_m10")
        for delay in (1, 2)
    }
    rows: list[dict[str, Any]] = []
    atol = float(ctx.cfg["calibrated_confirmation"]["numeric_trace_equivalence_atol"])
    for key in sorted(source_oracle):
        target, delay, slew = key
        if key in affected:
            pair = (target, delay)
            oracle_result = modified_oracle[pair]
            calibrated_result = modified_calibrated[pair]
            path = "r16_amplitude_certified_common_braking_direction"
        else:
            oracle_result = source_oracle[key]
            calibrated_result = source_calibrated[key]
            path = "source_unchanged_r11_original_deadline"
        policy = r13._timing_policy(r13_ctx, slew, policy_id=f"r16_formal_{target}_d{delay}_s{slew:.1f}")
        horizon = int(policy["horizon_steps"])
        oracle_slice = r13._slice_result(oracle_result, horizon)
        calibrated_slice = r13._slice_result(calibrated_result, horizon)
        metrics = r8.tracking_metrics(
            r13_ctx.r12_ctx.r11_ctx.r10_ctx.r9_ctx.r8_ctx,
            oracle_slice,
            policy,
        )
        left = r13._formal_equivalence_components(calibrated_slice, horizon=horizon)
        right = r13._formal_equivalence_components(oracle_slice, horizon=horizon)
        component_diff = {name: _finite_max_abs(left[name], right[name]) for name in left}
        exact = all(np.array_equal(left[name], right[name]) for name in left)
        numeric = all(
            np.allclose(left[name], right[name], rtol=0.0, atol=atol) for name in left
        )
        case_pass = bool(metrics.get("stage3_4_target_tracking_pass") and exact and numeric)
        rows.append(
            {
                "target_id": target,
                "actual_delay_steps": delay,
                "actual_slew_scale": slew,
                "controller_path": path,
                "formal_horizon_steps": horizon,
                "formal_arrival_deadline_step": max(policy["allowed_arrival_steps"]),
                "oracle_formal_tracking_pass": bool(
                    metrics.get("stage3_4_target_tracking_pass")
                ),
                "oracle_minimum_signed_margin": metrics.get(
                    "stage3_4_tracking_minimum_signed_margin"
                ),
                "calibrated_exact_equal_to_oracle": exact,
                "calibrated_numeric_equal_to_oracle": numeric,
                "maximum_trace_abs_difference": max(component_diff.values()),
                "component_max_abs_difference": component_diff,
                "formal_grid_case_pass": case_pass,
            }
        )
    modified_rows = [
        row
        for row in rows
        if row["controller_path"] == "r16_amplitude_certified_common_braking_direction"
    ]
    unchanged_rows = [row for row in rows if row not in modified_rows]
    passed = bool(
        len(rows) == int(ctx.cfg["formal_grid_confirmation"]["expected_cases"])
        and len(modified_rows)
        == int(ctx.cfg["formal_grid_confirmation"]["modified_cases"])
        and len(unchanged_rows)
        == int(ctx.cfg["formal_grid_confirmation"]["unchanged_source_cases"])
        and all(bool(row["formal_grid_case_pass"]) for row in rows)
    )
    write_csv(ctx.paths.formal_grid_confirmation / "results.csv", rows)
    atomic_write_json(ctx.paths.formal_grid_confirmation / "results.json", rows)
    summary = {
        "schema_version": 1,
        "stage": STAGE,
        "phase": "formal_grid_confirmation",
        "n_cases": len(rows),
        "expected_cases": int(ctx.cfg["formal_grid_confirmation"]["expected_cases"]),
        "modified_r16_cases": len(modified_rows),
        "source_unchanged_cases": len(unchanged_rows),
        "formal_contract_pass_fraction": (
            sum(bool(row["formal_grid_case_pass"]) for row in rows) / len(rows)
            if rows
            else 0.0
        ),
        "calibrated_exact_trace_equivalence_fraction": (
            sum(bool(row["calibrated_exact_equal_to_oracle"]) for row in rows)
            / len(rows)
            if rows
            else 0.0
        ),
        "maximum_trace_abs_difference": max(
            (_as_float(row["maximum_trace_abs_difference"], math.inf) for row in rows),
            default=math.inf,
        ),
        "normal_slew_and_weak_delay0_reused_without_new_tsc": True,
        "arrival_deadline_expanded": False,
        "unseen_target_generalization_validated": False,
        "passed": passed,
    }
    atomic_write_json(ctx.paths.formal_grid_confirmation / "summary.json", summary)
    _update_state(
        ctx,
        formal_grid_confirmation_complete=True,
        formal_grid_confirmation_summary=summary,
    )
    return summary


def _phase_status(payload: Mapping[str, Any]) -> str:
    if not payload:
        return "not_run"
    return "passed" if bool(payload.get("passed")) else "failed"


def finalize(ctx: Stage41R16Context) -> dict[str, Any]:
    state = read_json(ctx.paths.state)
    source = state.get("source_audit_summary") or {}
    amplitude = state.get("amplitude_validation_summary") or {}
    calibrated = state.get("calibrated_confirmation_summary") or {}
    formal = state.get("formal_grid_confirmation_summary") or {}
    passed = bool(
        source.get("passed")
        and amplitude.get("passed")
        and calibrated.get("passed")
        and formal.get("passed")
    )
    verdict = {
        "schema_version": 1,
        "stage": STAGE,
        "created_utc": utc_timestamp(),
        "verdict": (
            "STAGE4_1R16_AMPLITUDE_CERTIFIED_ORIGINAL_DEADLINE_CLOSURE"
            if passed
            else "STAGE4_1R16_AMPLITUDE_CERTIFIED_ORIGINAL_DEADLINE_INCOMPLETE"
        ),
        "source_stage4_1r15b_run": str(ctx.source_stage41r15b_run),
        "source_audit_status": _phase_status(source),
        "amplitude_envelope_validation_status": _phase_status(amplitude),
        "calibrated_confirmation_status": _phase_status(calibrated),
        "formal_grid_confirmation_status": _phase_status(formal),
        "closure_candidate_was_preregistered_before_new_r16_tsc": True,
        "closure_candidate_magnitude": 6.0,
        "closure_candidate_peak_component": 0.09,
        "formal_timing_contract_restored": bool(formal.get("passed")),
        "arrival_deadline_expanded": False,
        "true_restart_validation_performed": False,
        "continuous_parameter_change_validated": False,
        "plant_parameter_robustness_validated": False,
        "terminal_measurement_noise_robustness_validated": False,
        "unseen_target_generalization_validated": False,
        "unseen_hidden_state_robustness_validated": False,
        "deployment_robustness_validated": False,
        "stage4_2r1_was_not_run_or_reused": True,
        "finite_test_envelope_only": True,
        "next_if_pass": ctx.cfg["next_if_pass"],
        "next_if_fail": ctx.cfg["next_if_fail"],
        "final_task": ctx.cfg["final_task"],
        "phases": {
            "source_audit": source,
            "amplitude_envelope_validation": amplitude,
            "calibrated_confirmation": calibrated,
            "formal_grid_confirmation": formal,
        },
    }
    ctx.paths.analysis.mkdir(parents=True, exist_ok=True)
    atomic_write_json(ctx.paths.analysis / "stage4_1r16_verdict.json", verdict)
    atomic_write_json(ctx.paths.analysis / "stage4_1r16_summary.json", verdict)
    if passed:
        stop_reason = ""
    elif source and not bool(source.get("passed")):
        stop_reason = "source_audit_failed"
    elif not amplitude:
        stop_reason = "amplitude_validation_not_run"
    elif not bool(amplitude.get("passed")):
        stop_reason = "amplitude_envelope_or_fixed_candidate_failed"
    elif not calibrated:
        stop_reason = "calibrated_confirmation_not_run"
    elif not bool(calibrated.get("passed")):
        stop_reason = "calibrated_confirmation_failed"
    elif not formal:
        stop_reason = "formal_grid_confirmation_not_run"
    else:
        stop_reason = "formal_grid_confirmation_failed"
    _update_state(
        ctx,
        finished=True,
        stop_reason=stop_reason,
        final_verdict=verdict["verdict"],
    )
    return verdict


def execute(
    ctx: Stage41R16Context,
    *,
    command: str,
    backend: str,
    resume: bool,
) -> dict[str, Any]:
    prepare(ctx, resume=resume)
    order = {"audit": 0, "amplitude": 1, "calibrated": 2, "grid": 3, "all": 3}
    if command not in order:
        raise ValueError("command must be all/audit/amplitude/calibrated/grid")
    target_phase = order[command]

    state = read_json(ctx.paths.state)
    if target_phase >= 0 and not bool(state.get("source_audit_complete")):
        source = run_source_audit(ctx)
        if not source.get("passed"):
            return finalize(ctx)
    if target_phase == 0:
        return finalize(ctx)

    state = read_json(ctx.paths.state)
    source_summary = state.get("source_audit_summary") or {}
    if not source_summary.get("passed"):
        raise RuntimeError("R16 amplitude validation requires a passed source audit")
    if target_phase >= 1 and not bool(state.get("amplitude_validation_complete")):
        amplitude = run_amplitude_validation(ctx, backend=backend, resume=resume)
        if not amplitude.get("passed"):
            return finalize(ctx)
    if target_phase == 1:
        return finalize(ctx)

    state = read_json(ctx.paths.state)
    amplitude_summary = state.get("amplitude_validation_summary") or {}
    if not amplitude_summary.get("passed"):
        raise RuntimeError("R16 calibrated confirmation requires passed amplitude validation")
    if target_phase >= 2 and not bool(state.get("calibrated_confirmation_complete")):
        calibrated = run_calibrated_confirmation(ctx, backend=backend, resume=resume)
        if not calibrated.get("passed"):
            return finalize(ctx)
    if target_phase == 2:
        return finalize(ctx)

    state = read_json(ctx.paths.state)
    calibrated_summary = state.get("calibrated_confirmation_summary") or {}
    if not calibrated_summary.get("passed"):
        raise RuntimeError("R16 formal grid requires passed calibrated confirmation")
    if target_phase >= 3 and not bool(state.get("formal_grid_confirmation_complete")):
        formal = run_formal_grid_confirmation(ctx)
        if not formal.get("passed"):
            return finalize(ctx)
    return finalize(ctx)


def self_test(project_dir: Path) -> dict[str, Any]:
    cfg_path = (
        project_dir
        / "configs"
        / "stage4_1r16_amplitude_certified_probe_derived_braking_closure_370ms.json"
    )
    cfg = read_json(cfg_path)
    validate_config(cfg)
    source_r15_cfg = read_json(
        project_dir
        / "configs"
        / "stage4_1r15_bounded_early_braking_local_response_identification_370ms.json"
    )
    source_r15b_cfg = read_json(
        project_dir
        / "configs"
        / "stage4_1r15b_probe_derived_symmetric_local_response_superposition_validation_370ms.json"
    )
    schedule_rows: list[dict[str, Any]] = []
    for delay in (1, 2):
        for magnitude in (1.0, 2.0, 4.0, 6.0):
            for sign in (-1, 1):
                coefficients = sign * magnitude * np.ones(4)
                # Reconstruct without a full context by using the R15 basis directly.
                basis_by_id = {
                    str(row["probe_id"]): row
                    for row in source_r15_cfg["bounded_probe_validation"]["probe_basis"]
                }
                combined: dict[int, np.ndarray] = {}
                for probe_id, coefficient in zip(BASIS_ORDER, coefficients):
                    schedule = r15._probe_schedule(
                        first_effect_state=int(
                            source_r15_cfg["bounded_probe_validation"]["baseline_first_affected_state_step"]
                        ),
                        actual_delay=delay,
                        basis=basis_by_id[probe_id],
                        sign=1,
                        amplitude_by_mode=source_r15_cfg["bounded_probe_validation"]["probe_amplitude_by_mode"],
                    )
                    for step, value in schedule.items():
                        combined[step] = combined.get(step, np.zeros(3)) + coefficient * value
                net = np.sum(np.stack(list(combined.values())), axis=0)
                schedule_rows.append(
                    {
                        "delay": delay,
                        "magnitude": magnitude,
                        "sign": sign,
                        "zero_net": bool(
                            np.allclose(net, np.zeros(3), atol=1e-12, rtol=0.0)
                        ),
                        "maximum_component": float(
                            max(np.max(np.abs(value)) for value in combined.values())
                        ),
                    }
                )
    passed = bool(
        len(schedule_rows) == 16
        and all(row["zero_net"] for row in schedule_rows)
        and math.isclose(
            max(row["maximum_component"] for row in schedule_rows),
            0.09,
            rel_tol=0.0,
            abs_tol=1e-12,
        )
        and int(cfg["amplitude_envelope_validation"]["expected_rollouts"]) == 32
        and int(cfg["calibrated_confirmation"]["expected_rollouts"]) == 4
        and cfg["formal_timing_contract"]["normal_slew"]["arrival_deadline_step"] == 25
        and cfg["formal_timing_contract"]["weak_slew"]["arrival_deadline_step"] == 27
        and source_r15b_cfg["identification_only"] is True
        and cfg.get("stage4_2r1_was_not_run_or_reused")
    )
    return {
        "schema_version": 1,
        "stage": STAGE,
        "controller_revision": CONTROLLER_REVISION,
        "package_revision": PACKAGE_REVISION,
        "config_valid": True,
        "amplitude_schedule_variants": len(schedule_rows),
        "expected_true_tsc_amplitude_rollouts": 32,
        "expected_true_tsc_calibrated_rollouts": 4,
        "maximum_true_tsc_rollouts": 36,
        "all_schedules_zero_net": all(row["zero_net"] for row in schedule_rows),
        "maximum_schedule_component": max(
            row["maximum_component"] for row in schedule_rows
        ),
        "closure_candidate_magnitude_fixed": 6.0,
        "formal_timing_contract_immutable": True,
        "stage4_2r1_was_not_run_or_reused": True,
        "passed": passed,
    }


def _default_source(project_dir: Path) -> Path:
    env = os.environ.get("STAGE4_1R16_SOURCE_STAGE4_1R15B_RUN")
    if env:
        return Path(env).expanduser().resolve()
    latest = project_dir / "stage4_1r15b_runs" / "latest_stage4_1r15b_run.txt"
    if latest.is_file():
        return Path(latest.read_text(encoding="utf-8").strip()).expanduser().resolve()
    raise FileNotFoundError(
        "set STAGE4_1R16_SOURCE_STAGE4_1R15B_RUN or provide --source-stage4-1r15b-run"
    )


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Stage4.1R16 amplitude-certified probe-derived braking closure"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(
            "configs/stage4_1r16_amplitude_certified_probe_derived_braking_closure_370ms.json"
        ),
    )
    parser.add_argument("--source-stage4-1r15b-run", type=Path, default=None)
    parser.add_argument("--run-dir", type=Path, default=None)
    parser.add_argument(
        "--command",
        choices=["all", "audit", "amplitude", "calibrated", "grid"],
        default=os.environ.get("STAGE4_1R16_COMMAND", "all"),
    )
    parser.add_argument(
        "--backend",
        choices=["ray", "serial"],
        default=os.environ.get("STAGE4_1R16_BACKEND", "ray"),
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        default=os.environ.get("STAGE4_1R16_RESUME", "0") == "1",
    )
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    config_path = args.config.expanduser().resolve()
    project_dir = config_path.parents[1]
    if args.self_test:
        print(json.dumps(self_test(project_dir), indent=2, sort_keys=True))
        return
    source = args.source_stage4_1r15b_run or _default_source(project_dir)
    run_dir = args.run_dir
    env_run = os.environ.get("STAGE4_1R16_RUN_DIR")
    if run_dir is None and env_run:
        run_dir = Path(env_run)
    ctx = load_stage41r16_config(
        config_path,
        source_stage41r15b_run=source,
        run_dir_override=run_dir,
    )
    payload = execute(
        ctx,
        command=args.command,
        backend=args.backend,
        resume=bool(args.resume),
    )
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
