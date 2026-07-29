"""Stage4.1R17 one-sided robust braking closure under the original deadline.

R16 completed normally and established several facts that must be kept separate:

* all 32 real-TSC amplitude-ladder rollouts satisfied runtime, queue, causality,
  zero-net and current-utilisation guards;
* the symmetric plus/minus large-amplitude response model was not validated;
* every *negative* (braking-direction) R16 rollout remained within the
  preregistered model-error gates;
* the preregistered 6x braking candidate closed three of four modified paths;
* only RZ_p10_m10 with delay=2 missed the 270 ms endpoint-late speed gate,
  by 0.101 mm/s.

The generic R16 endpoint prediction tolerance (8 mm/s) was wider than the
candidate's predicted safety cushion, so model pass alone could never certify
constraint satisfaction.  R17 therefore does not reinterpret the failed
symmetric envelope as valid.  It uses a one-sided, delay-conditioned finite
policy:

* delay=1 keeps the already-executed R16 6x braking trajectory;
* delay=2 uses one preregistered 7x braking trajectory (0.105 peak component),
  selected before any R17 TSC evidence from a source-only robust-margin audit.

The new delay=2 Oracle is executed directly in TSC.  Only if both required
targets pass the immutable 270/370 ms contract with at least 0.01 signed
margin are trusted-token confirmation and the complete 18-case formal-grid
recombination executed.

This is a finite clean two-target, two-delay, 0.9x-slew closure test.  It does
not validate a bidirectional local model, restart, hidden-history,
continuous-parameter, noisy-sensing, disturbance-recovery, or deployment
robustness.  The final task remains a causal and safe controller across those
conditions; BC, DAgger and residual RL remain downstream.
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
from . import stage4_1r16_amplitude_certified_probe_derived_braking_closure as r16
from tsc_rzip_rllib.utils.ray_runtime import ensure_ray_worker_plan

atomic_write_json = r15.atomic_write_json
atomic_write_json_gz = r15.atomic_write_json_gz
read_json = r15.read_json
read_json_gz = r15.read_json_gz
utc_timestamp = r15.utc_timestamp
write_csv = r15.write_csv

SCHEMA_VERSION = 1
STAGE = "Stage4.1R17"
CONTROLLER_REVISION = "original_deadline_one_sided_robust_braking_closure_v17"
PACKAGE_REVISION = "r17_delay_conditioned_one_sided_margin_closure_v1"
EXPECTED_SOURCE_REVISION = r16.CONTROLLER_REVISION
EXPECTED_SOURCE_PACKAGE_REVISION = r16.PACKAGE_REVISION
SOURCE_INVENTORY_CONTRACT = "r17_direct_stage4_1r16_source_v1"
WEAK_SLEW = 0.9
WEAK_HORIZON = 37
N_MODES = 3


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
    return "s41r17_" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:20]


@dataclass(frozen=True)
class Stage41R17Paths:
    run_dir: Path
    source_reference: Path
    source_audit: Path
    oracle_validation: Path
    calibrated_confirmation: Path
    formal_grid_confirmation: Path
    analysis: Path
    variants: Path
    state: Path
    manifest: Path

    @classmethod
    def from_run_dir(cls, run_dir: Path) -> "Stage41R17Paths":
        run_dir = run_dir.expanduser().resolve()
        return cls(
            run_dir=run_dir,
            source_reference=run_dir / "stage4_1r17_source_reference",
            source_audit=run_dir / "stage4_1r17_source_audit",
            oracle_validation=run_dir / "stage4_1r17_oracle_candidate_validation",
            calibrated_confirmation=run_dir / "stage4_1r17_calibrated_confirmation",
            formal_grid_confirmation=run_dir / "stage4_1r17_formal_grid_confirmation",
            analysis=run_dir / "stage4_1r17_analysis",
            variants=run_dir / "stage4_1r17_environment_variants",
            state=run_dir / "stage4_1r17_state.json",
            manifest=run_dir / "stage4_1r17_manifest.json",
        )


@dataclass
class Stage41R17Context:
    cfg: dict[str, Any]
    paths: Stage41R17Paths
    project_dir: Path
    source_stage41r16_run: Path
    source_stage41r15b_run: Path
    source_manifest: dict[str, Any]
    source_state: dict[str, Any]
    source_cfg: dict[str, Any]
    source_verdict: dict[str, Any]
    r16_ctx: r16.Stage41R16Context
    source_fingerprint: dict[str, Any]


def _required_source_files(source: Path) -> list[Path]:
    required = [
        source / "stage4_1r16_manifest.json",
        source / "stage4_1r16_state.json",
        source / "stage4_1r16_config.resolved.json",
        source / "stage4_1r16_analysis" / "stage4_1r16_verdict.json",
        source / "stage4_1r16_analysis" / "stage4_1r16_summary.json",
        source / "stage4_1r16_source_audit" / "summary.json",
        source / "stage4_1r16_source_audit" / "model_feasibility.csv",
        source / "stage4_1r16_amplitude_envelope_validation" / "summary.json",
        source / "stage4_1r16_amplitude_envelope_validation" / "results.json",
        source / "stage4_1r16_amplitude_envelope_validation" / "results.csv",
        source / "stage4_1r16_amplitude_envelope_validation" / "central_symmetry.csv",
        source / "stage4_1r16_amplitude_envelope_validation" / "per_unit_scaling.csv",
        source / "stage4_1r16_amplitude_envelope_validation" / "closure_candidate.csv",
    ]
    required.extend(
        sorted((source / "stage4_1r16_amplitude_envelope_validation" / "raw").glob("*.json.gz"))
    )
    return required


def _source_inventory(source: Path) -> dict[str, Any]:
    source = source.expanduser().resolve()
    files = _required_source_files(source)
    missing = [path for path in files if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"required Stage4.1R16 source file missing: {missing[0]}")
    rows = []
    for path in files:
        rows.append(
            {
                "relative_path": str(path.relative_to(source)),
                "size_bytes": int(path.stat().st_size),
                "sha256": _sha256_file(path),
            }
        )
    canonical = json.dumps(rows, sort_keys=True, separators=(",", ":"))
    return {
        "schema_version": 1,
        "source_stage": "Stage4.1R16",
        "inventory_contract": SOURCE_INVENTORY_CONTRACT,
        "n_files": len(rows),
        "total_bytes": sum(int(row["size_bytes"]) for row in rows),
        "digest": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        "files": rows,
    }


def validate_config(cfg: Mapping[str, Any]) -> None:
    if cfg.get("stage") != STAGE:
        raise ValueError("R17 config stage mismatch")
    if cfg.get("controller_revision") != CONTROLLER_REVISION:
        raise ValueError("R17 controller revision mismatch")
    if cfg.get("package_revision") != PACKAGE_REVISION:
        raise ValueError("R17 package revision mismatch")
    timing = cfg["formal_timing_contract"]
    normal = timing["normal_slew"]
    weak = timing["weak_slew"]
    if (
        int(normal["arrival_deadline_step"]) != 25
        or int(normal["hold_through_step"]) != 35
        or max(int(x) for x in normal["allowed_arrival_steps"]) != 25
    ):
        raise ValueError("R17 normal-slew timing changed")
    if (
        int(weak["arrival_deadline_step"]) != 27
        or int(weak["hold_through_step"]) != 37
        or max(int(x) for x in weak["allowed_arrival_steps"]) != 27
    ):
        raise ValueError("R17 weak-slew timing changed")
    candidate = cfg["one_sided_candidate"]
    if int(candidate["source_delay1"]) != 1 or int(candidate["new_delay2"]) != 2:
        raise ValueError("R17 delay-conditioned candidate mapping changed")
    if not math.isclose(float(candidate["source_delay1_magnitude"]), 6.0, abs_tol=1e-15):
        raise ValueError("R17 delay=1 source magnitude changed")
    if not math.isclose(float(candidate["new_delay2_magnitude"]), 7.0, abs_tol=1e-15):
        raise ValueError("R17 delay=2 preregistered magnitude changed")
    if int(candidate["direction_sign"]) != -1:
        raise ValueError("R17 must retain the one-sided braking sign")
    if not math.isclose(float(candidate["peak_component"]), 0.105, abs_tol=1e-15):
        raise ValueError("R17 preregistered peak component changed")
    if int(candidate["expected_oracle_rollouts"]) != 2:
        raise ValueError("R17 Oracle rollout matrix changed")
    if float(candidate["minimum_actual_signed_margin"]) < 0.01:
        raise ValueError("R17 actual candidate margin guard weakened")
    if float(candidate["endpoint_error_safety_factor"]) < 1.25:
        raise ValueError("R17 source-only robust error factor weakened")
    if not bool(candidate["candidate_fixed_before_new_tsc"]):
        raise ValueError("R17 candidate must be preregistered before new TSC")
    if not bool(candidate["require_exact_per_step_probe_application"]):
        raise ValueError("R17 exact per-step probe application guard disabled")
    if int(cfg["calibrated_confirmation"]["expected_rollouts"]) != 4:
        raise ValueError("R17 calibrated rollout matrix changed")
    if int(cfg["formal_grid_confirmation"]["expected_cases"]) != 18:
        raise ValueError("R17 formal-grid size changed")
    if int(cfg["formal_grid_confirmation"]["modified_cases"]) != 4:
        raise ValueError("R17 modified formal-grid count changed")
    if bool(cfg.get("arrival_deadline_expansion_allowed", True)):
        raise ValueError("R17 may not expand arrival timing")
    if not bool(cfg.get("finite_test_envelope_only", False)):
        raise ValueError("R17 must remain a finite-envelope test")
    for flag in (
        "bidirectional_response_model_validated",
        "unseen_target_generalization_validated",
        "continuous_parameter_change_validated",
        "true_restart_validation_performed",
        "unseen_hidden_state_robustness_validated",
        "terminal_measurement_noise_robustness_validated",
        "deployment_robustness_validated",
    ):
        if bool(cfg.get(flag, False)):
            raise ValueError(f"R17 unsupported robustness claim enabled: {flag}")
    if not bool(cfg.get("stage4_2r1_was_not_run_or_reused", False)):
        raise ValueError("R17 may not reuse Stage4.2R1")


def _validate_source_stage41r16(
    source: Path, cfg: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    source = source.expanduser().resolve()
    manifest = read_json(source / "stage4_1r16_manifest.json")
    state = read_json(source / "stage4_1r16_state.json")
    source_cfg = read_json(source / "stage4_1r16_config.resolved.json")
    verdict = read_json(source / "stage4_1r16_analysis" / "stage4_1r16_verdict.json")
    req = cfg["source_requirements"]
    checks = {
        "stage": manifest.get("stage") == "Stage4.1R16",
        "controller_revision": manifest.get("controller_revision") == EXPECTED_SOURCE_REVISION,
        "package_revision": manifest.get("package_revision") == EXPECTED_SOURCE_PACKAGE_REVISION,
        "finished": bool(state.get("finished")),
        "stop_reason": str(state.get("stop_reason")) == "amplitude_envelope_or_fixed_candidate_failed",
        "source_audit_passed": verdict.get("source_audit_status") == "passed",
        "amplitude_failed": verdict.get("amplitude_envelope_validation_status") == "failed",
        "calibrated_not_run": verdict.get("calibrated_confirmation_status") == "not_run",
        "grid_not_run": verdict.get("formal_grid_confirmation_status") == "not_run",
        "formal_not_restored": not bool(verdict.get("formal_timing_contract_restored")),
        "stage4_2r1_not_reused": bool(verdict.get("stage4_2r1_was_not_run_or_reused")),
    }
    if not all(checks.values()):
        raise ValueError(f"R17 source R16 validation failed: {checks}")
    raw = sorted((source / "stage4_1r16_amplitude_envelope_validation" / "raw").glob("*.json.gz"))
    if len(raw) != int(req["require_r16_raw_count"]):
        raise ValueError(f"R17 expected 32 R16 raw files, found {len(raw)}")
    return manifest, state, source_cfg, verdict


def _resolve_recorded_run(project_dir: Path, recorded: str, root_name: str) -> Path:
    return r15._resolve_recorded_run(project_dir, recorded, root_name)


def load_stage41r17_config(
    config_path: Path,
    *,
    source_stage41r16_run: Path,
    run_dir_override: Path | None = None,
) -> Stage41R17Context:
    config_path = config_path.expanduser().resolve()
    cfg = read_json(config_path)
    validate_config(cfg)
    project_dir = config_path.parents[1]
    source_stage41r16_run = source_stage41r16_run.expanduser().resolve()
    source_manifest, source_state, source_cfg, source_verdict = _validate_source_stage41r16(
        source_stage41r16_run, cfg
    )
    source_stage41r15b_run = _resolve_recorded_run(
        project_dir, str(source_manifest["source_stage4_1r15b_run"]), "stage4_1r15b_runs"
    )
    if run_dir_override is None:
        root = project_dir / str(cfg.get("output_root", "stage4_1r17_runs"))
        run_dir = root / f"{cfg.get('run_name', 'stage4_1r17')}_{utc_timestamp()}"
    else:
        run_dir = run_dir_override.expanduser().resolve()
    packaged_r16_cfg = (
        project_dir
        / "configs"
        / "stage4_1r16_amplitude_certified_probe_derived_braking_closure_370ms.json"
    )
    if not packaged_r16_cfg.is_file():
        raise FileNotFoundError(f"packaged R16 dependency config missing: {packaged_r16_cfg}")
    r16_ctx = r16.load_stage41r16_config(
        packaged_r16_cfg,
        source_stage41r15b_run=source_stage41r15b_run,
        run_dir_override=run_dir,
    )
    recorded_r15b = source_manifest.get("source_fingerprint") or {}
    current_r15b = r16._source_inventory(source_stage41r15b_run)
    if recorded_r15b.get("digest") != current_r15b.get("digest"):
        raise ValueError("R17 nested Stage4.1R15B source fingerprint mismatch")
    storage = cfg["storage"]
    base34 = (
        r16_ctx.r15b_ctx.r15_ctx.r14_ctx.r13_ctx.r12_ctx.r11_ctx.r10_ctx.r9_ctx.r8_ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.base34
    )
    env_cfg = copy.deepcopy(base34.env_cfg)
    env_cfg["tsc_timeout_s"] = float(cfg["runtime"]["tsc_timeout_s"])
    env_cfg["tsc_workspace_root"] = str(
        Path(
            os.environ.get(
                "STAGE4_1R17_TSC_WORKSPACE_ROOT", storage["tsc_workspace_root"]
            )
        )
        .expanduser()
        .resolve()
    )
    env_cfg["run_root"] = str(
        Path(os.environ.get("STAGE4_1R17_TSC_RUN_ROOT", storage["tsc_run_root"]))
        .expanduser()
        .resolve()
    )
    env_cfg["tsc_run_root"] = env_cfg["run_root"]
    env_cfg["keep_failed_episode_dir"] = bool(storage.get("keep_failed_episode_dir", False))
    env_cfg["keep_last_n_failed_episode_dirs"] = int(
        storage.get("keep_last_n_failed_episode_dirs", 0)
    )
    base34.env_cfg = env_cfg
    return Stage41R17Context(
        cfg=cfg,
        paths=Stage41R17Paths.from_run_dir(run_dir),
        project_dir=project_dir,
        source_stage41r16_run=source_stage41r16_run,
        source_stage41r15b_run=source_stage41r15b_run,
        source_manifest=source_manifest,
        source_state=source_state,
        source_cfg=source_cfg,
        source_verdict=source_verdict,
        r16_ctx=r16_ctx,
        source_fingerprint=_source_inventory(source_stage41r16_run),
    )


def _initial_state(ctx: Stage41R17Context) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "stage": STAGE,
        "controller_revision": CONTROLLER_REVISION,
        "package_revision": PACKAGE_REVISION,
        "prepared": True,
        "source_audit_complete": False,
        "oracle_candidate_validation_complete": False,
        "calibrated_confirmation_complete": False,
        "formal_grid_confirmation_complete": False,
        "finished": False,
        "stop_reason": "",
        "updated_utc": utc_timestamp(),
    }


def _update_state(ctx: Stage41R17Context, **updates: Any) -> dict[str, Any]:
    state = read_json(ctx.paths.state) if ctx.paths.state.is_file() else _initial_state(ctx)
    state.update(_json_safe(updates))
    state["updated_utc"] = utc_timestamp()
    atomic_write_json(ctx.paths.state, state)
    return state


def prepare(ctx: Stage41R17Context, *, resume: bool) -> None:
    for path in (
        ctx.paths.run_dir,
        ctx.paths.source_reference,
        ctx.paths.source_audit,
        ctx.paths.oracle_validation,
        ctx.paths.calibrated_confirmation,
        ctx.paths.formal_grid_confirmation,
        ctx.paths.analysis,
        ctx.paths.variants,
    ):
        path.mkdir(parents=True, exist_ok=True)
    if ctx.paths.manifest.is_file():
        existing = read_json(ctx.paths.manifest)
        if existing.get("source_fingerprint", {}).get("digest") != ctx.source_fingerprint["digest"]:
            raise ValueError("R17 resume source fingerprint mismatch")
        if existing.get("controller_revision") != CONTROLLER_REVISION:
            raise ValueError("R17 resume controller revision mismatch")
        if existing.get("package_revision") != PACKAGE_REVISION:
            raise ValueError("R17 resume package revision mismatch")
    elif resume:
        raise FileNotFoundError("R17 resume requested but manifest is missing")
    atomic_write_json(ctx.paths.run_dir / "stage4_1r17_config.resolved.json", ctx.cfg)
    for name, payload in (
        ("stage4_1r16_manifest.json", ctx.source_manifest),
        ("stage4_1r16_state.json", ctx.source_state),
        ("stage4_1r16_config.resolved.json", ctx.source_cfg),
        ("stage4_1r16_verdict.json", ctx.source_verdict),
        ("source_content_inventory.json", ctx.source_fingerprint),
        (
            "nested_stage4_1r15b_source_inventory.json",
            ctx.source_manifest.get("source_fingerprint") or {},
        ),
    ):
        atomic_write_json(ctx.paths.source_reference / name, payload)
    manifest = {
        "schema_version": 1,
        "stage": STAGE,
        "controller_revision": CONTROLLER_REVISION,
        "underlying_worker_revision": r16.CONTROLLER_REVISION,
        "package_revision": PACKAGE_REVISION,
        "created_utc": utc_timestamp(),
        "source_stage4_1r16_run": str(ctx.source_stage41r16_run),
        "source_stage4_1r15b_run": str(ctx.source_stage41r15b_run),
        "source_fingerprint": ctx.source_fingerprint,
        "source_inventory_contract": SOURCE_INVENTORY_CONTRACT,
        "workers": int(os.environ.get("STAGE4_1R17_WORKERS", ctx.cfg["parallel"]["n_workers"])),
        "formal_timing_contract": ctx.cfg["formal_timing_contract"],
        "delay_conditioned_magnitudes": {
            "delay1": ctx.cfg["one_sided_candidate"]["source_delay1_magnitude"],
            "delay2": ctx.cfg["one_sided_candidate"]["new_delay2_magnitude"],
        },
        "candidate_fixed_before_new_tsc": True,
        "arrival_deadline_expansion_allowed": False,
        "bidirectional_response_model_validated": False,
        "stage4_2r1_was_not_run_or_reused": True,
        "finite_test_envelope_only": True,
        "final_task": ctx.cfg["final_task"],
    }
    if not ctx.paths.manifest.is_file():
        atomic_write_json(ctx.paths.manifest, manifest)
    if not ctx.paths.state.is_file():
        atomic_write_json(ctx.paths.state, _initial_state(ctx))


def _read_source_rows(ctx: Stage41R17Context) -> list[dict[str, Any]]:
    return read_json(
        ctx.source_stage41r16_run
        / "stage4_1r16_amplitude_envelope_validation"
        / "results.json"
    )


def _read_source_raw(ctx: Stage41R17Context) -> list[dict[str, Any]]:
    return [
        read_json_gz(path)
        for path in sorted(
            (
                ctx.source_stage41r16_run
                / "stage4_1r16_amplitude_envelope_validation"
                / "raw"
            ).glob("*.json.gz")
        )
    ]


def _source_raw_map(ctx: Stage41R17Context) -> dict[tuple[str, int, float, int], dict[str, Any]]:
    output: dict[tuple[str, int, float, int], dict[str, Any]] = {}
    for result in _read_source_raw(ctx):
        spec = result["spec"]
        key = (
            str(spec["target_id"]),
            int(spec["action_delay_steps"]),
            float(spec["r16_magnitude"]),
            int(spec["r16_direction_sign"]),
        )
        if key in output:
            raise ValueError(f"duplicate R16 source raw key: {key}")
        output[key] = result
    return output


def _exact_probe_application(result: Mapping[str, Any]) -> bool:
    spec = result.get("spec") or {}
    schedule = {
        int(step): np.asarray(value, dtype=float).reshape(N_MODES)
        for step, value in (spec.get("r15_probe_delta_by_issue_step") or {}).items()
    }
    seen: dict[int, np.ndarray] = {}
    for row in result.get("anticipatory_damping_trace") or []:
        if not bool(row.get("r15_identification_probe")):
            continue
        step = int(row.get("step", -1))
        requested = np.asarray(row.get("r15_probe_requested_delta"), dtype=float).reshape(N_MODES)
        applied = np.asarray(row.get("r15_probe_applied_delta"), dtype=float).reshape(N_MODES)
        if step not in schedule:
            return False
        if not np.allclose(requested, schedule[step], atol=1e-12, rtol=0.0):
            return False
        if not np.allclose(applied, requested, atol=1e-12, rtol=0.0):
            return False
        seen[step] = applied
    return set(seen) == set(schedule)


def _formal_metrics(ctx: Stage41R17Context, result: Mapping[str, Any], *, policy_id: str) -> dict[str, Any]:
    return r16._formal_metrics(ctx.r16_ctx, result, policy_id=policy_id)


def _predicted_result(
    ctx: Stage41R17Context, *, target: str, delay: int, magnitude: float
) -> dict[str, Any]:
    group_id = f"{target}__d{delay}"
    baseline = r16._baseline_map(ctx.r16_ctx)[(target, delay)]
    model = r16._models(ctx.r16_ctx)[group_id]
    coefficients = -float(magnitude) * np.ones(len(r16.BASIS_ORDER), dtype=float)
    return r16._predicted_result_from_model(baseline, model, coefficients)


def run_source_audit(ctx: Stage41R17Context) -> dict[str, Any]:
    rows = _read_source_rows(ctx)
    raw = _read_source_raw(ctx)
    source_summary = read_json(
        ctx.source_stage41r16_run
        / "stage4_1r16_amplitude_envelope_validation"
        / "summary.json"
    )
    central = []
    with (
        ctx.source_stage41r16_run
        / "stage4_1r16_amplitude_envelope_validation"
        / "central_symmetry.csv"
    ).open(newline="", encoding="utf-8") as handle:
        central = list(csv.DictReader(handle))
    keys = {
        (
            str(row["target_id"]),
            int(row["actual_delay_steps"]),
            float(row["magnitude"]),
            int(row["direction_sign"]),
        )
        for row in rows
    }
    expected_keys = {
        (target, delay, magnitude, sign)
        for target in ("nominal", "RZ_p10_m10")
        for delay in (1, 2)
        for magnitude in (1.0, 2.0, 4.0, 6.0)
        for sign in (-1, 1)
    }
    negative = [row for row in rows if int(row["direction_sign"]) == -1]
    positive_failures = [
        row
        for row in rows
        if int(row["direction_sign"]) == 1 and not bool(row["model_prediction_pass"])
    ]
    symmetry_failures = [row for row in central if str(row.get("passed")).lower() != "true"]
    exact_probe_count = sum(_exact_probe_application(result) for result in raw)
    monotonic_rows: list[dict[str, Any]] = []
    all_monotonic = True
    for target in ("nominal", "RZ_p10_m10"):
        for delay in (1, 2):
            group = sorted(
                [
                    row
                    for row in negative
                    if str(row["target_id"]) == target
                    and int(row["actual_delay_steps"]) == delay
                ],
                key=lambda row: float(row["magnitude"]),
            )
            speeds = [float(row["endpoint_late_speed_m_per_s"]) for row in group]
            monotonic = all(right <= left + 1e-12 for left, right in zip(speeds, speeds[1:]))
            all_monotonic = all_monotonic and monotonic
            monotonic_rows.append(
                {
                    "target_id": target,
                    "actual_delay_steps": delay,
                    "magnitudes": [float(row["magnitude"]) for row in group],
                    "endpoint_late_speeds_m_per_s": speeds,
                    "monotone_nonincreasing": monotonic,
                }
            )
    source_candidate = {
        (str(row["target_id"]), int(row["actual_delay_steps"])): row
        for row in negative
        if math.isclose(float(row["magnitude"]), 6.0, abs_tol=1e-15)
    }
    failure_keys = {
        key
        for key, row in source_candidate.items()
        if not bool(row["formal_tracking_pass"])
    }
    max_negative_endpoint_error = max(
        float(row["endpoint_late_speed_error_m_per_s"]) for row in negative
    )
    max_negative_final_error = max(float(row["final_speed_error_m_per_s"]) for row in negative)
    safety_factor = float(ctx.cfg["one_sided_candidate"]["endpoint_error_safety_factor"])
    prediction_rows: list[dict[str, Any]] = []
    robust_prediction_pass = True
    speed_gate = float(ctx.cfg["formal_timing_contract"]["speed_gate_m_per_s"])
    required_margin = float(ctx.cfg["one_sided_candidate"]["minimum_actual_signed_margin"])
    robust_speed_limit = speed_gate * (1.0 - required_margin)
    for target in ("nominal", "RZ_p10_m10"):
        predicted = _predicted_result(ctx, target=target, delay=2, magnitude=7.0)
        metrics = _formal_metrics(ctx, predicted, policy_id=f"r17_source_prediction_{target}_d2")
        endpoint = _as_float(
            metrics.get("stage3_4_endpoint_late_velocity_rms_m_per_s"), math.inf
        )
        final = _as_float(metrics.get("stage3_4_final_velocity_m_per_s"), math.inf)
        robust_endpoint = endpoint + safety_factor * max_negative_endpoint_error
        robust_final = final + safety_factor * max_negative_final_error
        passed = bool(
            robust_endpoint <= robust_speed_limit
            and robust_final <= robust_speed_limit
        )
        robust_prediction_pass = robust_prediction_pass and passed
        prediction_rows.append(
            {
                "target_id": target,
                "actual_delay_steps": 2,
                "candidate_magnitude": 7.0,
                "predicted_endpoint_late_speed_m_per_s": endpoint,
                "predicted_final_speed_m_per_s": final,
                "source_maximum_negative_endpoint_error_m_per_s": max_negative_endpoint_error,
                "source_maximum_negative_final_error_m_per_s": max_negative_final_error,
                "error_safety_factor": safety_factor,
                "robust_endpoint_upper_m_per_s": robust_endpoint,
                "robust_final_upper_m_per_s": robust_final,
                "required_speed_upper_m_per_s": robust_speed_limit,
                "source_only_robust_prediction_pass": passed,
            }
        )
    cfg_req = ctx.cfg["source_requirements"]
    checks = {
        "coverage_exact": len(rows) == 32 and keys == expected_keys,
        "raw_coverage_exact": len(raw) == int(cfg_req["require_r16_raw_count"]),
        "environment_success_32": sum(bool(row["environment_success"]) for row in rows) == 32,
        "runtime_guard_fraction_one": math.isclose(
            sum(bool(row["runtime_guard_pass"]) for row in rows) / len(rows), 1.0
        ),
        "source_summary_failed": not bool(source_summary.get("passed")),
        "source_model_fraction_expected": math.isclose(
            float(source_summary.get("model_prediction_pass_fraction", 0.0)), 0.84375
        ),
        "negative_direction_all_runtime": len(negative) == 16
        and all(bool(row["runtime_guard_pass"]) for row in negative),
        "negative_direction_all_model_pass": len(negative) == 16
        and all(bool(row["model_prediction_pass"]) for row in negative),
        "positive_model_failure_count_five": len(positive_failures) == 5,
        "symmetric_envelope_not_validated": len(symmetry_failures) == 4,
        "per_step_probe_application_exact": exact_probe_count == len(raw),
        "negative_endpoint_monotonic": all_monotonic,
        "source_candidate_four_cases": len(source_candidate) == 4,
        "source_candidate_exact_failure": failure_keys == {("RZ_p10_m10", 2)},
        "source_delay1_both_pass_with_margin": all(
            bool(source_candidate[(target, 1)]["formal_tracking_pass"])
            and float(source_candidate[(target, 1)]["formal_minimum_signed_margin"]) >= 0.01
            for target in ("nominal", "RZ_p10_m10")
        ),
        "source_delay2_nominal_passes": bool(
            source_candidate[("nominal", 2)]["formal_tracking_pass"]
        ),
        "source_delay2_rz_fails_by_endpoint_speed": (
            not bool(source_candidate[("RZ_p10_m10", 2)]["formal_tracking_pass"])
            and float(source_candidate[("RZ_p10_m10", 2)]["endpoint_late_speed_m_per_s"])
            > speed_gate
            and float(source_candidate[("RZ_p10_m10", 2)]["final_speed_m_per_s"])
            < speed_gate
        ),
        "candidate_fixed_at_seven": math.isclose(
            float(ctx.cfg["one_sided_candidate"]["new_delay2_magnitude"]),
            7.0,
            abs_tol=1e-15,
        ),
        "source_only_robust_prediction_pass": robust_prediction_pass,
    }
    if not all(checks.values()):
        raise ValueError(f"R17 source audit failed: {checks}")
    write_csv(ctx.paths.source_audit / "negative_direction_monotonicity.csv", monotonic_rows)
    write_csv(ctx.paths.source_audit / "candidate_prediction_tightening.csv", prediction_rows)
    summary = {
        "schema_version": 1,
        "stage": STAGE,
        "phase": "source_audit",
        "source_stage4_1r16_run": str(ctx.source_stage41r16_run),
        "source_rollouts": len(rows),
        "source_raw_rollouts": len(raw),
        "source_runtime_guard_pass_fraction": 1.0,
        "source_model_prediction_pass_fraction": float(
            source_summary["model_prediction_pass_fraction"]
        ),
        "source_symmetric_envelope_validated": False,
        "source_positive_model_failure_count": len(positive_failures),
        "source_central_symmetry_failure_count": len(symmetry_failures),
        "source_negative_direction_rollouts": len(negative),
        "source_negative_direction_model_pass_fraction": 1.0,
        "source_negative_direction_exact_probe_application_fraction": 1.0,
        "source_negative_endpoint_monotonic": all_monotonic,
        "source_6x_candidate_formal_pass_fraction": 0.75,
        "source_6x_candidate_failure_key": ["RZ_p10_m10", 2],
        "source_6x_rz_d2_endpoint_speed_m_per_s": float(
            source_candidate[("RZ_p10_m10", 2)]["endpoint_late_speed_m_per_s"]
        ),
        "source_6x_rz_d2_final_speed_m_per_s": float(
            source_candidate[("RZ_p10_m10", 2)]["final_speed_m_per_s"]
        ),
        "source_6x_rz_d2_signed_margin": float(
            source_candidate[("RZ_p10_m10", 2)]["formal_minimum_signed_margin"]
        ),
        "source_maximum_negative_endpoint_prediction_error_m_per_s": max_negative_endpoint_error,
        "source_maximum_negative_final_prediction_error_m_per_s": max_negative_final_error,
        "source_generic_endpoint_error_gate_m_per_s": float(
            ctx.source_cfg["amplitude_envelope_validation"]["model_validation"][
                "maximum_endpoint_late_speed_error_m_per_s"
            ]
        ),
        "source_candidate_predicted_cushion_was_smaller_than_generic_error_gate": True,
        "delay1_source_magnitude": 6.0,
        "delay2_preregistered_magnitude": 7.0,
        "delay2_preregistered_peak_component": 0.105,
        "candidate_fixed_before_new_tsc": True,
        "bidirectional_response_model_reinterpreted_as_validated": False,
        "prediction_tightening_rows": prediction_rows,
        "checks": checks,
        "passed": True,
        "interpretation": (
            "R16 ran normally.  Its symmetric large-amplitude response envelope failed, "
            "but all sixteen braking-direction trajectories passed the model and runtime "
            "guards, were applied exactly at every probe step, and reduced endpoint speed "
            "monotonically.  The 6x candidate closed three of four paths; only RZ/delay=2 "
            "missed by 0.101 mm/s.  R17 therefore tests one fixed, source-preregistered "
            "7x delay=2 braking trajectory while retaining the already-passing 6x delay=1 "
            "source trajectory.  No bidirectional-model claim is made."
        ),
    }
    atomic_write_json(ctx.paths.source_audit / "summary.json", summary)
    _update_state(ctx, source_audit_complete=True, source_audit_summary=summary)
    return summary


def materialize_variant(ctx: Stage41R17Context) -> tuple[str, dict[str, Any]]:
    return r16.materialize_variant(ctx.r16_ctx)


def _make_spec(
    ctx: Stage41R17Context,
    *,
    phase: str,
    target: Mapping[str, Any],
    actual_delay: int,
    modeled_delay: int,
    magnitude: float,
    calibration_token: str | None,
    trusted: bool,
    controller_variant: str,
) -> dict[str, Any]:
    variant, _ = materialize_variant(ctx)
    spec = r16._base_spec(
        ctx.r16_ctx,
        phase=phase,
        target=target,
        actual_delay=int(actual_delay),
        modeled_delay=int(modeled_delay),
        calibration_token=calibration_token,
        trusted=trusted,
        magnitude=float(magnitude),
        direction_sign=-1,
        environment_variant=variant,
        controller_variant=controller_variant,
    )
    identity = {
        "stage": STAGE,
        "phase": phase,
        "target_id": str(target["target_id"]),
        "actual_delay_steps": int(actual_delay),
        "modeled_delay_steps": int(modeled_delay),
        "magnitude": float(magnitude),
        "direction_sign": -1,
        "calibration_token": calibration_token,
        "controller_revision": CONTROLLER_REVISION,
    }
    spec.update(
        {
            "kind": "stage4_1r17_original_deadline_one_sided_robust_braking_closure",
            "controller_revision": CONTROLLER_REVISION,
            "experiment_id": _scenario_digest(identity),
            "phase": phase,
            "category": phase,
            "scenario": (
                f"one_sided_m{float(magnitude):g}__{target['target_id']}__"
                f"d{int(actual_delay)}__s0.9"
            ),
            "r17_one_sided_braking": True,
            "r17_bidirectional_model_claimed": False,
            "r17_delay_conditioned_magnitude": float(magnitude),
            "r17_candidate_fixed_before_new_tsc": True,
            "r17_formal_tracking_required": True,
            "arrival_deadline_expansion_allowed": False,
        }
    )
    return spec


def _oracle_specs(ctx: Stage41R17Context) -> list[dict[str, Any]]:
    specs = []
    for target in ctx.cfg["one_sided_candidate"]["required_targets"]:
        specs.append(
            _make_spec(
                ctx,
                phase="oracle_candidate_validation",
                target=target,
                actual_delay=2,
                modeled_delay=2,
                magnitude=float(ctx.cfg["one_sided_candidate"]["new_delay2_magnitude"]),
                calibration_token=None,
                trusted=True,
                controller_variant="r17_oracle_one_sided_delay2_candidate",
            )
        )
    if len(specs) != int(ctx.cfg["one_sided_candidate"]["expected_oracle_rollouts"]):
        raise ValueError("R17 Oracle candidate specification count mismatch")
    return specs


def _trusted_tokens(ctx: Stage41R17Context) -> dict[tuple[int, float], dict[str, Any]]:
    return r16._trusted_tokens(ctx.r16_ctx)


def _calibrated_specs(ctx: Stage41R17Context) -> list[dict[str, Any]]:
    tokens = _trusted_tokens(ctx)
    specs: list[dict[str, Any]] = []
    magnitudes = {
        1: float(ctx.cfg["one_sided_candidate"]["source_delay1_magnitude"]),
        2: float(ctx.cfg["one_sided_candidate"]["new_delay2_magnitude"]),
    }
    for delay in (1, 2):
        token = tokens.get((delay, WEAK_SLEW))
        if token is None:
            raise KeyError(f"R17 trusted token missing for delay={delay}, slew=0.9")
        if not bool(token.get("batch_trusted_correct")) or bool(
            token.get("batch_wrong_accept")
        ):
            raise ValueError(f"R17 refuses untrusted calibration token for delay={delay}")
        modeled = int(token.get("batch_selected_delay_steps", -1))
        if modeled != delay:
            raise ValueError(f"R17 token delay mismatch: actual={delay}, modeled={modeled}")
        for target in ctx.cfg["one_sided_candidate"]["required_targets"]:
            specs.append(
                _make_spec(
                    ctx,
                    phase="calibrated_confirmation",
                    target=target,
                    actual_delay=delay,
                    modeled_delay=modeled,
                    magnitude=magnitudes[delay],
                    calibration_token=str(token["experiment_id"]),
                    trusted=True,
                    controller_variant="r17_calibrated_one_sided_candidate",
                )
            )
    if len(specs) != int(ctx.cfg["calibrated_confirmation"]["expected_rollouts"]):
        raise ValueError("R17 calibrated specification count mismatch")
    return specs


def _normalize_result(result: dict[str, Any], spec: Mapping[str, Any]) -> dict[str, Any]:
    output = dict(result)
    output["controller_revision"] = CONTROLLER_REVISION
    output["stage4_1r17_controller_revision"] = CONTROLLER_REVISION
    output["stage4_1r16_underlying_worker_revision"] = r16.CONTROLLER_REVISION
    output["experiment_id"] = str(spec["experiment_id"])
    output["spec"] = copy.deepcopy(dict(spec))
    output["r17_one_sided_summary"] = {
        "actual_delay_steps": int(spec["action_delay_steps"]),
        "magnitude": float(spec["r17_delay_conditioned_magnitude"]),
        "direction_sign": -1,
        "candidate_fixed_before_new_tsc": True,
        "bidirectional_model_claimed": False,
    }
    return _json_safe(output)


def evaluate_specs(
    ctx: Stage41R17Context,
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
        ctx.r16_ctx.r15b_ctx.r15_ctx.r14_ctx.r13_ctx.r12_ctx.r11_ctx.r10_ctx.r9_ctx.r8_ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx
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
    selector_cfg = ctx.r16_ctx.r15b_ctx.r15_ctx.r14_ctx.r13_ctx.r12_ctx.r11_ctx.r10_ctx.r9_ctx.r8_ctx.cfg[
        "batch_selector"
    ]
    if backend == "serial":
        worker = r16.LocalStage41R16Worker(
            payload, library, bundle, "stage41r17_serial", selector_cfg
        )
        try:
            for index, spec in enumerate(pending, 1):
                result = _normalize_result(worker.evaluate(spec), spec)
                atomic_write_json_gz(
                    output_dir / f"{spec['experiment_id']}.json.gz", result
                )
                print(f"{log_prefix} {index}/{len(pending)}", flush=True)
        finally:
            worker.close()
    elif backend == "ray" and pending:
        import ray

        requested = int(
            os.environ.get("STAGE4_1R17_WORKERS", ctx.cfg["parallel"]["n_workers"])
        )
        plan = ensure_ray_worker_plan(
            ray,
            requested_workers=requested,
            pending_tasks=len(pending),
            ray_tmpdir=os.environ.get("RAY_TMPDIR", ctx.cfg["parallel"].get("ray_tmpdir", ""))
            or None,
            log_prefix=log_prefix,
        )
        Actor = r16._ray_actor_class()
        actors = [
            Actor.remote(payload, library, bundle, f"stage41r17_{index:03d}", selector_cfg)
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
                        result = _normalize_result(ray.get(ref), spec)
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


def _current_utilization(ctx: Stage41R17Context, result: Mapping[str, Any]) -> float:
    return r16._current_utilization(ctx.r16_ctx, result)


def _runtime_row(ctx: Stage41R17Context, result: Mapping[str, Any]) -> dict[str, Any]:
    spec = result["spec"]
    target = str(spec["target_id"])
    delay = int(spec["action_delay_steps"])
    baseline = r16._baseline_map(ctx.r16_ctx)[(target, delay)]
    first_effect = int(
        ctx.r16_ctx.r15b_ctx.source_cfg["bounded_probe_validation"][
            "baseline_first_affected_state_step"
        ]
    )
    physics = r13._physics_array(result)[:first_effect]
    baseline_physics = r13._physics_array(baseline)[:first_effect]
    prefix_exact = bool(
        physics.shape == baseline_physics.shape and np.array_equal(physics, baseline_physics)
    )
    trace = list(result.get("anticipatory_damping_trace") or [])
    probe = result.get("r15_probe_summary") or {}
    expected_max = 0.015 * float(spec["r17_delay_conditioned_magnitude"])
    exact_applied = _exact_probe_application(result)
    runtime_pass = bool(
        result.get("success")
        and not str(result.get("failure_reason", "")).strip()
        and not any(bool(row.get("abnormal", False)) for row in result.get("trajectory") or [])
        and all(bool(row.get("solver_success", False)) for row in trace)
        and bool((result.get("anticipatory_damping_summary") or {}).get("streaming_queue_consistent"))
        and not any(bool(row.get("future_measurement_used", True)) for row in trace)
        and bool(probe.get("probe_zero_net"))
        and bool(probe.get("applied_probe_zero_net"))
        and exact_applied
        and math.isclose(
            _as_float(probe.get("maximum_requested_component"), math.inf),
            expected_max,
            rel_tol=0.0,
            abs_tol=1e-12,
        )
        and math.isclose(
            _as_float(probe.get("maximum_applied_component"), math.inf),
            expected_max,
            rel_tol=0.0,
            abs_tol=1e-12,
        )
        and prefix_exact
        and _current_utilization(ctx, result)
        <= float(ctx.cfg["one_sided_candidate"]["maximum_current_utilization"])
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
        "exact_per_step_probe_application": exact_applied,
        "requested_probe_net_norm": _as_float(probe.get("requested_probe_net_norm")),
        "applied_probe_net_norm": _as_float(probe.get("applied_probe_net_norm"), math.inf),
        "probe_issue_count": int(probe.get("probe_issue_count", 0)),
        "probe_applied_issue_count": int(probe.get("probe_applied_issue_count", 0)),
        "maximum_requested_component": _as_float(probe.get("maximum_requested_component")),
        "maximum_applied_component": _as_float(probe.get("maximum_applied_component")),
        "maximum_current_utilization": _current_utilization(ctx, result),
        "runtime_guard_pass": runtime_pass,
    }


def _prediction_metrics(
    ctx: Stage41R17Context, result: Mapping[str, Any]
) -> dict[str, float | bool]:
    spec = result["spec"]
    target = str(spec["target_id"])
    delay = int(spec["action_delay_steps"])
    magnitude = float(spec["r17_delay_conditioned_magnitude"])
    predicted = _predicted_result(ctx, target=target, delay=delay, magnitude=magnitude)
    actual_output = r16.r15b._output_vector(
        result,
        start_state=23,
        end_state_exclusive=38,
    )
    predicted_output = r16.r15b._output_vector(
        predicted,
        start_state=23,
        end_state_exclusive=38,
    )
    count = 15
    velocity_rmse = float(
        np.sqrt(np.mean((actual_output[: 2 * count] - predicted_output[: 2 * count]) ** 2))
    )
    position_rmse = float(
        np.sqrt(
            np.mean(
                (
                    actual_output[2 * count : 4 * count]
                    - predicted_output[2 * count : 4 * count]
                )
                ** 2
            )
        )
    )
    ip_rmse = float(
        np.sqrt(np.mean((actual_output[4 * count :] - predicted_output[4 * count :]) ** 2))
    )
    actual_metrics = _formal_metrics(
        ctx, result, policy_id=f"r17_actual_{target}_d{delay}"
    )
    predicted_metrics = _formal_metrics(
        ctx, predicted, policy_id=f"r17_predicted_{target}_d{delay}"
    )
    endpoint_error = abs(
        _as_float(actual_metrics.get("stage3_4_endpoint_late_velocity_rms_m_per_s"), math.inf)
        - _as_float(
            predicted_metrics.get("stage3_4_endpoint_late_velocity_rms_m_per_s"), math.inf
        )
    )
    final_error = abs(
        _as_float(actual_metrics.get("stage3_4_final_velocity_m_per_s"), math.inf)
        - _as_float(predicted_metrics.get("stage3_4_final_velocity_m_per_s"), math.inf)
    )
    guard = ctx.cfg["one_sided_candidate"]["candidate_model_guard"]
    passed = bool(
        velocity_rmse <= float(guard["maximum_velocity_component_rmse_m_per_s"])
        and endpoint_error <= float(guard["maximum_endpoint_late_speed_error_m_per_s"])
        and final_error <= float(guard["maximum_final_speed_error_m_per_s"])
        and position_rmse <= float(guard["maximum_position_rmse_m"])
        and ip_rmse <= float(guard["maximum_ip_rmse_A"])
    )
    return {
        "velocity_component_rmse_m_per_s": velocity_rmse,
        "endpoint_late_speed_error_m_per_s": endpoint_error,
        "final_speed_error_m_per_s": final_error,
        "position_rmse_m": position_rmse,
        "ip_rmse_A": ip_rmse,
        "candidate_model_guard_pass": passed,
    }


def run_oracle_candidate_validation(
    ctx: Stage41R17Context, *, backend: str, resume: bool
) -> dict[str, Any]:
    specs = _oracle_specs(ctx)
    results = evaluate_specs(
        ctx,
        specs,
        output_dir=ctx.paths.oracle_validation / "raw",
        backend=backend,
        resume=resume,
        log_prefix="[Stage4.1R17 one-sided-oracle]",
    )
    rows: list[dict[str, Any]] = []
    minimum_required = float(ctx.cfg["one_sided_candidate"]["minimum_actual_signed_margin"])
    for result in results:
        spec = result["spec"]
        target = str(spec["target_id"])
        runtime = _runtime_row(ctx, result)
        prediction = _prediction_metrics(ctx, result)
        metrics = _formal_metrics(ctx, result, policy_id=f"r17_oracle_{target}_d2")
        margin = _as_float(
            metrics.get("stage3_4_tracking_minimum_signed_margin"), -math.inf
        )
        row = {
            "experiment_id": result["experiment_id"],
            "target_id": target,
            "actual_delay_steps": 2,
            "magnitude": float(spec["r17_delay_conditioned_magnitude"]),
            "direction_sign": -1,
            **runtime,
            **prediction,
            "formal_tracking_pass": bool(metrics.get("stage3_4_target_tracking_pass")),
            "formal_minimum_signed_margin": margin,
            "formal_best_endpoint_step": metrics.get("stage3_4_best_arrival_endpoint_step"),
            "endpoint_late_speed_m_per_s": metrics.get(
                "stage3_4_endpoint_late_velocity_rms_m_per_s"
            ),
            "final_speed_m_per_s": metrics.get("stage3_4_final_velocity_m_per_s"),
            "candidate_pass": bool(
                runtime["runtime_guard_pass"]
                and prediction["candidate_model_guard_pass"]
                and bool(metrics.get("stage3_4_target_tracking_pass"))
                and margin >= minimum_required
            ),
        }
        rows.append(row)
    passed = bool(
        len(rows) == int(ctx.cfg["one_sided_candidate"]["expected_oracle_rollouts"])
        and all(bool(row["candidate_pass"]) for row in rows)
    )
    write_csv(ctx.paths.oracle_validation / "results.csv", rows)
    atomic_write_json(ctx.paths.oracle_validation / "results.json", rows)
    summary = {
        "schema_version": 1,
        "stage": STAGE,
        "phase": "oracle_candidate_validation",
        "n_rollouts": len(rows),
        "expected_rollouts": int(ctx.cfg["one_sided_candidate"]["expected_oracle_rollouts"]),
        "candidate_magnitude": float(
            ctx.cfg["one_sided_candidate"]["new_delay2_magnitude"]
        ),
        "candidate_peak_component": float(ctx.cfg["one_sided_candidate"]["peak_component"]),
        "candidate_fixed_before_new_tsc": True,
        "bidirectional_response_model_validated": False,
        "runtime_guard_pass_fraction": (
            sum(bool(row["runtime_guard_pass"]) for row in rows) / len(rows) if rows else 0.0
        ),
        "model_guard_pass_fraction": (
            sum(bool(row["candidate_model_guard_pass"]) for row in rows) / len(rows)
            if rows
            else 0.0
        ),
        "formal_contract_pass_fraction": (
            sum(bool(row["formal_tracking_pass"]) for row in rows) / len(rows)
            if rows
            else 0.0
        ),
        "minimum_actual_signed_margin": min(
            (_as_float(row["formal_minimum_signed_margin"], -math.inf) for row in rows),
            default=-math.inf,
        ),
        "maximum_current_utilization": max(
            (_as_float(row["maximum_current_utilization"], math.inf) for row in rows),
            default=math.inf,
        ),
        "passed": passed,
    }
    atomic_write_json(ctx.paths.oracle_validation / "summary.json", summary)
    _update_state(
        ctx,
        oracle_candidate_validation_complete=True,
        oracle_candidate_validation_summary=summary,
    )
    return summary


def _oracle_candidate_map(ctx: Stage41R17Context) -> dict[tuple[str, int], dict[str, Any]]:
    source = _source_raw_map(ctx)
    output: dict[tuple[str, int], dict[str, Any]] = {}
    for target in ("nominal", "RZ_p10_m10"):
        output[(target, 1)] = source[(target, 1, 6.0, -1)]
    for path in sorted((ctx.paths.oracle_validation / "raw").glob("*.json.gz")):
        result = read_json_gz(path)
        spec = result["spec"]
        key = (str(spec["target_id"]), int(spec["action_delay_steps"]))
        if key[1] != 2:
            raise ValueError(f"unexpected R17 Oracle delay: {key}")
        if key in output:
            raise ValueError(f"duplicate R17 Oracle candidate: {key}")
        output[key] = result
    if set(output) != {
        ("nominal", 1),
        ("RZ_p10_m10", 1),
        ("nominal", 2),
        ("RZ_p10_m10", 2),
    }:
        raise ValueError(f"R17 Oracle candidate map incomplete: {sorted(output)}")
    return output


def _comparison_components(result: Mapping[str, Any]) -> dict[str, np.ndarray]:
    return r16._comparison_components(result)


def _finite_max_abs(left: np.ndarray, right: np.ndarray) -> float:
    return r16._finite_max_abs(left, right)


def run_calibrated_confirmation(
    ctx: Stage41R17Context, *, backend: str, resume: bool
) -> dict[str, Any]:
    specs = _calibrated_specs(ctx)
    results = evaluate_specs(
        ctx,
        specs,
        output_dir=ctx.paths.calibrated_confirmation / "raw",
        backend=backend,
        resume=resume,
        log_prefix="[Stage4.1R17 calibrated-confirmation]",
    )
    oracle = _oracle_candidate_map(ctx)
    atol = float(ctx.cfg["calibrated_confirmation"]["numeric_trace_equivalence_atol"])
    rows: list[dict[str, Any]] = []
    comparisons: list[dict[str, Any]] = []
    for result in results:
        spec = result["spec"]
        key = (str(spec["target_id"]), int(spec["action_delay_steps"]))
        metrics = _formal_metrics(ctx, result, policy_id=f"r17_calibrated_{key[0]}_d{key[1]}")
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
            "magnitude": float(spec["r17_delay_conditioned_magnitude"]),
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
                "magnitude": float(spec["r17_delay_conditioned_magnitude"]),
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


def _calibrated_map(ctx: Stage41R17Context) -> dict[tuple[str, int], dict[str, Any]]:
    output: dict[tuple[str, int], dict[str, Any]] = {}
    for path in sorted((ctx.paths.calibrated_confirmation / "raw").glob("*.json.gz")):
        result = read_json_gz(path)
        spec = result["spec"]
        key = (str(spec["target_id"]), int(spec["action_delay_steps"]))
        if key in output:
            raise ValueError(f"duplicate R17 calibrated case: {key}")
        output[key] = result
    if len(output) != 4:
        raise ValueError(f"R17 expected four calibrated cases, found {len(output)}")
    return output


def run_formal_grid_confirmation(ctx: Stage41R17Context) -> dict[str, Any]:
    r13_ctx = ctx.r16_ctx.r15b_ctx.r15_ctx.r14_ctx.r13_ctx
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
            path = (
                "r17_one_sided_6x_delay1"
                if delay == 1
                else "r17_one_sided_7x_delay2"
            )
        else:
            oracle_result = source_oracle[key]
            calibrated_result = source_calibrated[key]
            path = "source_unchanged_r11_original_deadline"
        policy = r13._timing_policy(
            r13_ctx, slew, policy_id=f"r17_formal_{target}_d{delay}_s{slew:.1f}"
        )
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
        row for row in rows if row["controller_path"].startswith("r17_one_sided_")
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
        "modified_r17_cases": len(modified_rows),
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
        "bidirectional_response_model_validated": False,
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


def _phase_status(ctx: Stage41R17Context, phase: str) -> str:
    path = {
        "source_audit": ctx.paths.source_audit / "summary.json",
        "oracle_candidate_validation": ctx.paths.oracle_validation / "summary.json",
        "calibrated_confirmation": ctx.paths.calibrated_confirmation / "summary.json",
        "formal_grid_confirmation": ctx.paths.formal_grid_confirmation / "summary.json",
    }[phase]
    if not path.is_file():
        return "not_run"
    return "passed" if bool(read_json(path).get("passed")) else "failed"


def finalize(ctx: Stage41R17Context) -> dict[str, Any]:
    source_status = _phase_status(ctx, "source_audit")
    oracle_status = _phase_status(ctx, "oracle_candidate_validation")
    calibrated_status = _phase_status(ctx, "calibrated_confirmation")
    grid_status = _phase_status(ctx, "formal_grid_confirmation")
    passed = all(
        status == "passed"
        for status in (source_status, oracle_status, calibrated_status, grid_status)
    )
    verdict = (
        "STAGE4_1R17_ORIGINAL_DEADLINE_ONE_SIDED_BRAKING_CLOSURE"
        if passed
        else "STAGE4_1R17_ORIGINAL_DEADLINE_ONE_SIDED_BRAKING_INCOMPLETE"
    )
    payload = {
        "schema_version": 1,
        "stage": STAGE,
        "created_utc": utc_timestamp(),
        "verdict": verdict,
        "source_stage4_1r16_run": str(ctx.source_stage41r16_run),
        "source_audit_status": source_status,
        "oracle_candidate_validation_status": oracle_status,
        "calibrated_confirmation_status": calibrated_status,
        "formal_grid_confirmation_status": grid_status,
        "delay1_braking_magnitude": 6.0,
        "delay2_braking_magnitude": 7.0,
        "delay2_peak_component": 0.105,
        "candidate_fixed_before_new_tsc": True,
        "formal_timing_contract_restored": passed,
        "arrival_deadline_expanded": False,
        "bidirectional_response_model_validated": False,
        "one_sided_finite_static_grid_only": True,
        "true_restart_validation_performed": False,
        "unseen_hidden_state_robustness_validated": False,
        "continuous_parameter_change_validated": False,
        "terminal_measurement_noise_robustness_validated": False,
        "disturbance_recovery_validated": False,
        "deployment_robustness_validated": False,
        "stage4_2r1_was_not_run_or_reused": True,
        "finite_test_envelope_only": True,
        "warning": (
            "R17 can only validate a fixed one-sided, delay-conditioned braking patch "
            "for two targets, static delay={1,2}, slew=0.9 in the same clean digital twin. "
            "R16's large-amplitude bidirectional model remains invalid.  R17 does not "
            "validate restart, hidden history, continuous parameters, noise, disturbances "
            "or deployment."
        ),
        "next_if_pass": ctx.cfg["next_if_pass"],
        "next_if_fail": ctx.cfg["next_if_fail"],
        "final_task": ctx.cfg["final_task"],
        "phases": {
            name: read_json(path)
            if path.is_file()
            else {}
            for name, path in (
                ("source_audit", ctx.paths.source_audit / "summary.json"),
                (
                    "oracle_candidate_validation",
                    ctx.paths.oracle_validation / "summary.json",
                ),
                (
                    "calibrated_confirmation",
                    ctx.paths.calibrated_confirmation / "summary.json",
                ),
                (
                    "formal_grid_confirmation",
                    ctx.paths.formal_grid_confirmation / "summary.json",
                ),
            )
        },
    }
    atomic_write_json(ctx.paths.analysis / "stage4_1r17_summary.json", payload)
    atomic_write_json(ctx.paths.analysis / "stage4_1r17_verdict.json", payload)
    stop_reason = "" if passed else next(
        (
            f"{name}_failed"
            for name, status in (
                ("source_audit", source_status),
                ("oracle_candidate_validation", oracle_status),
                ("calibrated_confirmation", calibrated_status),
                ("formal_grid_confirmation", grid_status),
            )
            if status == "failed"
        ),
        "incomplete",
    )
    _update_state(
        ctx,
        finished=True,
        stop_reason=stop_reason,
        final_verdict=verdict,
    )
    return payload


def execute(
    ctx: Stage41R17Context,
    *,
    command: str,
    backend: str,
    resume: bool,
) -> dict[str, Any]:
    prepare(ctx, resume=resume)
    if command in {"all", "audit"}:
        audit = run_source_audit(ctx)
        if command == "audit":
            return finalize(ctx)
        if not audit.get("passed"):
            return finalize(ctx)
    if command in {"all", "oracle"}:
        oracle = run_oracle_candidate_validation(ctx, backend=backend, resume=resume)
        if command == "oracle":
            return finalize(ctx)
        if not oracle.get("passed"):
            return finalize(ctx)
    if command in {"all", "calibrated"}:
        calibrated = run_calibrated_confirmation(ctx, backend=backend, resume=resume)
        if command == "calibrated":
            return finalize(ctx)
        if not calibrated.get("passed"):
            return finalize(ctx)
    if command in {"all", "grid"}:
        run_formal_grid_confirmation(ctx)
    return finalize(ctx)


def self_test(project_dir: Path) -> dict[str, Any]:
    cfg_path = (
        project_dir
        / "configs"
        / "stage4_1r17_original_deadline_one_sided_robust_braking_closure_370ms.json"
    )
    cfg = read_json(cfg_path)
    validate_config(cfg)
    source_r15_cfg = read_json(
        project_dir
        / "configs"
        / "stage4_1r15_bounded_early_braking_local_response_identification_370ms.json"
    )
    schedule_ctx = type(
        "ScheduleContext",
        (),
        {
            "r16_ctx": type(
                "R16Context",
                (),
                {
                    "r15b_ctx": type(
                        "R15BContext",
                        (),
                        {"source_cfg": source_r15_cfg},
                    )()
                },
            )()
        },
    )()
    schedules = {}
    maximum = 0.0
    for delay, magnitude in ((1, 6.0), (2, 7.0)):
        coefficients = -magnitude * np.ones(4, dtype=float)
        schedule = r16._combined_schedule(
            schedule_ctx.r16_ctx, actual_delay=delay, coefficients=coefficients
        )
        net = np.sum(np.stack(list(schedule.values())), axis=0)
        if not np.allclose(net, np.zeros(3), atol=1e-12, rtol=0.0):
            raise AssertionError("R17 schedule lost zero-net property")
        local_max = max(float(np.max(np.abs(value))) for value in schedule.values())
        expected = 0.015 * magnitude
        if not math.isclose(local_max, expected, abs_tol=1e-12):
            raise AssertionError("R17 schedule component mismatch")
        maximum = max(maximum, local_max)
        schedules[f"d{delay}"] = {
            "magnitude": magnitude,
            "issue_steps": sorted(schedule),
            "maximum_component": local_max,
            "net": net.tolist(),
        }
    return {
        "schema_version": 1,
        "stage": STAGE,
        "passed": True,
        "formal_timing_contract_immutable": True,
        "candidate_fixed_before_new_tsc": True,
        "delay_conditioned_schedules": schedules,
        "maximum_schedule_component": maximum,
        "expected_true_tsc_oracle_rollouts": 2,
        "expected_true_tsc_calibrated_rollouts": 4,
        "maximum_true_tsc_rollouts": 6,
        "bidirectional_response_model_validated": False,
    }


def _default_source(project_dir: Path) -> Path:
    latest = project_dir / "stage4_1r16_runs" / "latest_stage4_1r16_run.txt"
    if latest.is_file():
        candidate = Path(latest.read_text(encoding="utf-8").strip())
        if candidate.is_dir():
            return candidate.resolve()
    candidates = sorted(
        (
            project_dir / "stage4_1r16_runs"
        ).glob("stage4_1r16_amplitude_certified_probe_derived_braking_closure_*"),
        reverse=True,
    )
    for candidate in candidates:
        if (candidate / "stage4_1r16_state.json").is_file():
            return candidate.resolve()
    raise FileNotFoundError("no complete Stage4.1R16 source run found")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stage4.1R17 original-deadline one-sided robust braking closure"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(
            "configs/stage4_1r17_original_deadline_one_sided_robust_braking_closure_370ms.json"
        ),
    )
    parser.add_argument("--source-stage4-1r16-run", type=Path, default=None)
    parser.add_argument("--run-dir", type=Path, default=None)
    parser.add_argument(
        "--command",
        choices=["all", "audit", "oracle", "calibrated", "grid"],
        default=os.environ.get("STAGE4_1R17_COMMAND", "all"),
    )
    parser.add_argument(
        "--backend",
        choices=["ray", "serial"],
        default=os.environ.get("STAGE4_1R17_BACKEND", "ray"),
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        default=os.environ.get("STAGE4_1R17_RESUME", "0") == "1",
    )
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    project_dir = args.config.expanduser().resolve().parents[1]
    if args.self_test:
        print(json.dumps(self_test(project_dir), indent=2, sort_keys=True))
        return
    source = (
        args.source_stage4_1r16_run.expanduser().resolve()
        if args.source_stage4_1r16_run
        else _default_source(project_dir)
    )
    ctx = load_stage41r17_config(
        args.config,
        source_stage41r16_run=source,
        run_dir_override=args.run_dir,
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
