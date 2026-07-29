"""Stage4.2R1 authentic TSC plant-state restart action-replay certification.

Stage4.1R17 restored the immutable formal timing contract on a finite clean
18-case static grid.  This stage deliberately separates two questions that
must not be conflated:

1. Can the complete TSC plant state (including vessel/wire currents) be saved
   through the authentic ``sprsina`` filesystem restart interface and restored
   in a fresh TSC process without changing the trajectory?
2. Can a controller reconstruct or persist its own observer/integrator/queue
   state across restart?

R1 answers only question 1.  It replays the exact, already-validated R17 expert
actions, exports authentic TSC snapshots at 200 ms elapsed time, starts fresh
TSC environments from those snapshots, and replays the exact remaining action
suffix.  It compares R/Z/Ip, all 14 coil currents, the complete wire-current
vector and the action trace.  It then re-evaluates the original 250/350 and
270/370 ms contracts.

No controller checkpoint is reconstructed or replayed here.  A pass therefore
certifies plant-state serialization/restart plumbing for the same finite clean
cases; it does not validate cold controller restart, unseen hidden histories,
new targets, plant mismatch, continuous actuator changes, noise, disturbances
or deployment.  BC, DAgger and residual RL remain downstream of a robust MPC
expert baseline.
"""
from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import math
import os
import resource
import shutil
import tempfile
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd

from . import stage2_trajectory_optimization as s2
from . import stage4_1r3_control_aware_robustness as r3
from . import stage4_1r8_trusted_batch_calibration_queue_tail_closure as r8
from . import stage4_1r10_queue_preview_terminal_transition_hold as r10
from . import stage4_1r13_original_deadline_delay_pipeline_early_braking as r13
from . import stage4_1r15_bounded_early_braking_local_response_identification as r15
from . import stage4_1r16_amplitude_certified_probe_derived_braking_closure as r16
from . import stage4_1r17_original_deadline_one_sided_robust_braking_closure as r17
from tsc_rzip_rllib.utils.ray_runtime import ensure_ray_worker_plan

atomic_write_json = r17.atomic_write_json
atomic_write_json_gz = r17.atomic_write_json_gz
read_json = r17.read_json
read_json_gz = r17.read_json_gz
utc_timestamp = r17.utc_timestamp
write_csv = r17.write_csv

SCHEMA_VERSION = 1
STAGE = "Stage4.2R1"
CONTROLLER_REVISION = "true_tsc_plant_restart_action_replay_v42r1"
PACKAGE_REVISION = "r42r1_plant_restart_action_replay_v1"
EXPECTED_SOURCE_REVISION = r17.CONTROLLER_REVISION
EXPECTED_SOURCE_PACKAGE_REVISION = r17.PACKAGE_REVISION
SOURCE_INVENTORY_CONTRACT = "r42r1_direct_r17_and_selected_expert_raw_v1"
N_COILS = 14
CHECKPOINT_STEP = 20
DT_MS = 10
NORMAL_HORIZON = 35
WEAK_HORIZON = 37


def _json_safe(value: Any) -> Any:
    return r17._json_safe(value)


def _as_float(value: Any, default: float = 0.0) -> float:
    return r17._as_float(value, default)


def _sha256_file(path: Path) -> str:
    return r17._sha256_file(path)


def _result_complete(path: Path) -> bool:
    return r17._result_complete(path)


def _scenario_digest(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(
        _json_safe(dict(payload)), sort_keys=True, separators=(",", ":"), allow_nan=False
    )
    return "s42r1_" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:20]


def _finite_max_abs(left: np.ndarray, right: np.ndarray) -> float:
    a = np.asarray(left, dtype=float)
    b = np.asarray(right, dtype=float)
    if a.shape != b.shape:
        return math.inf
    return float(np.max(np.abs(a - b))) if a.size else 0.0


def _case_key(result_or_spec: Mapping[str, Any]) -> tuple[str, int, float]:
    spec = result_or_spec.get("spec", result_or_spec)
    return (
        str(spec["target_id"]),
        int(spec["action_delay_steps"]),
        float(spec["slew_scale"]),
    )


def _formal_horizon(slew: float) -> int:
    return WEAK_HORIZON if math.isclose(float(slew), 0.9, abs_tol=1e-12) else NORMAL_HORIZON


@dataclass(frozen=True)
class Stage42R1Paths:
    run_dir: Path
    source_reference: Path
    source_audit: Path
    capture: Path
    restart_bank: Path
    variants: Path
    restart: Path
    analysis: Path
    state: Path
    manifest: Path

    @classmethod
    def from_run_dir(cls, run_dir: Path) -> "Stage42R1Paths":
        run_dir = run_dir.expanduser().resolve()
        return cls(
            run_dir=run_dir,
            source_reference=run_dir / "stage4_2r1_source_reference",
            source_audit=run_dir / "stage4_2r1_source_audit",
            capture=run_dir / "stage4_2r1_plant_checkpoint_capture",
            restart_bank=run_dir / "stage4_2r1_restart_bank",
            variants=run_dir / "stage4_2r1_restart_variants",
            restart=run_dir / "stage4_2r1_plant_restart_replay",
            analysis=run_dir / "stage4_2r1_analysis",
            state=run_dir / "stage4_2r1_state.json",
            manifest=run_dir / "stage4_2r1_manifest.json",
        )


@dataclass
class Stage42R1Context:
    cfg: dict[str, Any]
    paths: Stage42R1Paths
    project_dir: Path
    source_stage41r17_run: Path
    source_stage41r16_run: Path
    source_manifest: dict[str, Any]
    source_state: dict[str, Any]
    source_cfg: dict[str, Any]
    source_verdict: dict[str, Any]
    r17_ctx: r17.Stage41R17Context
    source_fingerprint: dict[str, Any]
    expert_fingerprint: dict[str, Any]
    materialized_variants: dict[str, dict[str, Any]]


def _required_source_files(source: Path) -> list[Path]:
    required = [
        source / "stage4_1r17_manifest.json",
        source / "stage4_1r17_state.json",
        source / "stage4_1r17_config.resolved.json",
        source / "stage4_1r17_analysis" / "stage4_1r17_verdict.json",
        source / "stage4_1r17_analysis" / "stage4_1r17_summary.json",
        source / "stage4_1r17_source_audit" / "summary.json",
        source / "stage4_1r17_oracle_candidate_validation" / "summary.json",
        source / "stage4_1r17_oracle_candidate_validation" / "results.json",
        source / "stage4_1r17_calibrated_confirmation" / "summary.json",
        source / "stage4_1r17_calibrated_confirmation" / "results.json",
        source / "stage4_1r17_formal_grid_confirmation" / "summary.json",
        source / "stage4_1r17_formal_grid_confirmation" / "results.json",
    ]
    required.extend(sorted((source / "stage4_1r17_oracle_candidate_validation" / "raw").glob("*.json.gz")))
    required.extend(sorted((source / "stage4_1r17_calibrated_confirmation" / "raw").glob("*.json.gz")))
    return required


def _inventory(source: Path, files: Sequence[Path], *, contract: str, stage: str) -> dict[str, Any]:
    source = source.expanduser().resolve()
    rows: list[dict[str, Any]] = []
    total = 0
    for path in files:
        path = path.expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(f"required {stage} source file missing: {path}")
        size = int(path.stat().st_size)
        total += size
        try:
            relative = str(path.relative_to(source))
        except ValueError:
            relative = str(path)
        rows.append({"relative_path": relative, "size_bytes": size, "sha256": _sha256_file(path)})
    rows.sort(key=lambda row: row["relative_path"])
    canonical = json.dumps(rows, sort_keys=True, separators=(",", ":"))
    return {
        "schema_version": 1,
        "source_stage": stage,
        "inventory_contract": contract,
        "n_files": len(rows),
        "total_bytes": total,
        "digest": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        "files": rows,
    }


def _source_inventory(source: Path) -> dict[str, Any]:
    files = _required_source_files(source)
    if len(list((source / "stage4_1r17_oracle_candidate_validation" / "raw").glob("*.json.gz"))) != 2:
        raise ValueError("Stage4.2R1 requires exactly two R17 Oracle raw files")
    if len(list((source / "stage4_1r17_calibrated_confirmation" / "raw").glob("*.json.gz"))) != 4:
        raise ValueError("Stage4.2R1 requires exactly four R17 calibrated raw files")
    return _inventory(
        source, files, contract="r42r1_direct_stage4_1r17_source_v1", stage="Stage4.1R17"
    )


def _resolve_recorded_run(project_dir: Path, recorded: str, root_name: str) -> Path:
    return r15._resolve_recorded_run(project_dir, recorded, root_name)


def validate_config(cfg: Mapping[str, Any]) -> None:
    if cfg.get("stage") != STAGE:
        raise ValueError("Stage4.2R1 config stage mismatch")
    if cfg.get("controller_revision") != CONTROLLER_REVISION:
        raise ValueError("Stage4.2R1 controller revision mismatch")
    if cfg.get("package_revision") != PACKAGE_REVISION:
        raise ValueError("Stage4.2R1 package revision mismatch")
    checkpoint = cfg["checkpoint"]
    if int(checkpoint["checkpoint_step"]) != CHECKPOINT_STEP:
        raise ValueError("Stage4.2R1 checkpoint step changed")
    if int(checkpoint["checkpoint_elapsed_ms"]) != CHECKPOINT_STEP * DT_MS:
        raise ValueError("Stage4.2R1 checkpoint elapsed time changed")
    if int(checkpoint["dt_ms"]) != DT_MS:
        raise ValueError("Stage4.2R1 dt must remain 10 ms")
    if int(checkpoint["normal_horizon_steps"]) != NORMAL_HORIZON:
        raise ValueError("Stage4.2R1 normal formal horizon changed")
    if int(checkpoint["weak_horizon_steps"]) != WEAK_HORIZON:
        raise ValueError("Stage4.2R1 weak formal horizon changed")
    for key in (
        "require_snapshot_sha256",
        "require_capture_source_exact",
        "require_restart_initial_state_exact",
        "require_restart_suffix_exact",
        "require_full_wire_current_vector",
        "require_exact_source_action_replay",
        "require_fresh_restart_actor",
        "require_formal_contract_preservation",
    ):
        if not bool(checkpoint.get(key)):
            raise ValueError(f"Stage4.2R1 scientific guard disabled: {key}")
    if bool(checkpoint.get("controller_checkpoint_replay_in_this_stage", True)):
        raise ValueError("Stage4.2R1 must isolate plant restart from controller checkpoint replay")
    required = set(map(str, checkpoint["required_snapshot_files"]))
    if not {
        "inputa",
        "sprsina",
        "geqdsk",
        "outputa",
        "coil_currents.csv",
        "wire_currents.csv",
    }.issubset(required):
        raise ValueError("Stage4.2R1 snapshot file contract weakened")
    timing = cfg["formal_timing_contract"]
    normal = timing["normal_slew"]
    weak = timing["weak_slew"]
    if int(normal["arrival_deadline_step"]) != 25 or int(normal["hold_through_step"]) != 35:
        raise ValueError("Stage4.2R1 normal formal timing changed")
    if max(map(int, normal["allowed_arrival_steps"])) != 25:
        raise ValueError("Stage4.2R1 normal arrival window changed")
    if int(weak["arrival_deadline_step"]) != 27 or int(weak["hold_through_step"]) != 37:
        raise ValueError("Stage4.2R1 weak formal timing changed")
    if max(map(int, weak["allowed_arrival_steps"])) != 27:
        raise ValueError("Stage4.2R1 weak arrival window changed")
    if bool(timing.get("arrival_deadline_expansion_allowed", True)):
        raise ValueError("Stage4.2R1 may not expand formal timing")
    matrix = cfg["matrix"]
    if list(map(str, matrix["targets"])) != ["nominal", "RZ_p10_m10"]:
        raise ValueError("Stage4.2R1 target matrix changed")
    if list(map(int, matrix["actual_delay_steps"])) != [0, 1, 2]:
        raise ValueError("Stage4.2R1 delay matrix changed")
    if list(map(float, matrix["actual_slew_scales"])) != [0.9, 1.0, 1.1]:
        raise ValueError("Stage4.2R1 slew matrix changed")
    for key in ("expected_source_cases", "expected_capture_rollouts", "expected_restart_rollouts"):
        if int(matrix[key]) != 18:
            raise ValueError("Stage4.2R1 requires the complete 18-case matrix")
    if not bool(cfg.get("plant_restart_only")):
        raise ValueError("Stage4.2R1 must remain plant-restart only")
    if not bool(cfg.get("finite_test_envelope_only")):
        raise ValueError("Stage4.2R1 must remain finite-envelope only")
    if not bool(cfg.get("stage4_1r10_r11_long_horizons_are_auxiliary_only")):
        raise ValueError("Stage4.2R1 may not replace original timing with R10/R11 long horizons")
    if not bool(cfg.get("stage4_2r1_old_r11_based_package_was_not_run_or_reused")):
        raise ValueError("Stage4.2R1 may not reuse the unrun old R11-based package")
    for flag in (
        "true_filesystem_tsc_restart_executed",
        "controller_checkpoint_replay_validated",
        "cold_controller_restart_validated",
        "unseen_hidden_history_generalization_validated",
        "unseen_target_generalization_validated",
        "plant_parameter_robustness_validated",
        "continuous_parameter_change_validated",
        "terminal_measurement_noise_robustness_validated",
        "disturbance_recovery_validated",
        "deployment_robustness_validated",
    ):
        if bool(cfg.get(flag, False)):
            raise ValueError(f"Stage4.2R1 config pre-claims unsupported result: {flag}")


def _validate_source_stage41r17(
    source: Path, cfg: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    source = source.expanduser().resolve()
    for path in _required_source_files(source):
        if not path.is_file():
            raise FileNotFoundError(f"required Stage4.1R17 source file missing: {path}")
    manifest = read_json(source / "stage4_1r17_manifest.json")
    state = read_json(source / "stage4_1r17_state.json")
    source_cfg = read_json(source / "stage4_1r17_config.resolved.json")
    verdict = read_json(source / "stage4_1r17_analysis" / "stage4_1r17_verdict.json")
    req = cfg["source_requirements"]
    checks = {
        "stage": manifest.get("stage") == req["required_stage"],
        "controller_revision": manifest.get("controller_revision") == req["required_controller_revision"],
        "package_revision": manifest.get("package_revision") == req["required_package_revision"],
        "resolved_revision": source_cfg.get("controller_revision") == EXPECTED_SOURCE_REVISION,
        "finished": bool(state.get("finished")),
        "stop_reason": str(state.get("stop_reason", "")) == str(req["require_stop_reason"]),
        "formal_grid_pass": verdict.get("formal_grid_confirmation_status") == "passed",
        "formal_timing_restored": bool(verdict.get("formal_timing_contract_restored")),
        "arrival_not_expanded": not bool(verdict.get("arrival_deadline_expanded")),
        "old_r1_not_reused": bool(verdict.get("stage4_2r1_was_not_run_or_reused")),
    }
    formal_summary = read_json(source / "stage4_1r17_formal_grid_confirmation" / "summary.json")
    cal_summary = read_json(source / "stage4_1r17_calibrated_confirmation" / "summary.json")
    checks.update(
        {
            "formal_summary_pass": bool(formal_summary.get("passed")),
            "formal_case_count": int(formal_summary.get("n_cases", 0)) == int(req["require_formal_case_count"]),
            "modified_count": int(formal_summary.get("modified_r17_cases", 0)) == int(req["require_modified_case_count"]),
            "unchanged_count": int(formal_summary.get("source_unchanged_cases", 0)) == int(req["require_unchanged_case_count"]),
            "formal_fraction_one": math.isclose(_as_float(formal_summary.get("formal_contract_pass_fraction")), 1.0, abs_tol=1e-15),
            "calibrated_exact": math.isclose(_as_float(cal_summary.get("exact_trace_equivalence_fraction")), float(req["require_exact_calibrated_trace_fraction"]), abs_tol=1e-15),
        }
    )
    if not all(checks.values()):
        raise ValueError(f"Stage4.2R1 source R17 validation failed: {checks}")
    return manifest, state, source_cfg, verdict


def _r13_ctx(ctx: Stage42R1Context) -> r13.Stage41R13Context:
    return ctx.r17_ctx.r16_ctx.r15b_ctx.r15_ctx.r14_ctx.r13_ctx


def _r10_ctx(ctx: Stage42R1Context):
    return _r13_ctx(ctx).r12_ctx.r11_ctx.r10_ctx


def _selected_source_cases(ctx: Stage42R1Context) -> dict[tuple[str, int, float], dict[str, Any]]:
    r13_ctx = _r13_ctx(ctx)
    unchanged = r13._source_calibrated_map(r13_ctx)
    modified: dict[tuple[str, int, float], dict[str, Any]] = {}
    for path in sorted((ctx.source_stage41r17_run / "stage4_1r17_calibrated_confirmation" / "raw").glob("*.json.gz")):
        result = read_json_gz(path)
        key = _case_key(result)
        if key in modified:
            raise ValueError(f"duplicate R17 calibrated source case: {key}")
        modified[key] = result
    affected = {
        (target, delay, 0.9)
        for target in ("nominal", "RZ_p10_m10")
        for delay in (1, 2)
    }
    output: dict[tuple[str, int, float], dict[str, Any]] = {}
    for key, result in unchanged.items():
        output[key] = modified[key] if key in affected else result
    expected = {
        (target, delay, slew)
        for target in ("nominal", "RZ_p10_m10")
        for delay in (0, 1, 2)
        for slew in (0.9, 1.0, 1.1)
    }
    if set(output) != expected:
        raise ValueError(f"Stage4.2R1 selected expert coverage mismatch: {set(output) ^ expected}")
    return output


def _selected_source_files(ctx: Stage42R1Context) -> list[Path]:
    selected = _selected_source_cases(ctx)
    r11_run = _r13_ctx(ctx).source_stage41r11_run
    r17_dir = ctx.source_stage41r17_run / "stage4_1r17_calibrated_confirmation" / "raw"
    r11_dir = r11_run / "stage4_1r11_calibrated_long_hold" / "raw"
    by_id: dict[str, Path] = {}
    for path in list(r17_dir.glob("*.json.gz")) + list(r11_dir.glob("*.json.gz")):
        row = read_json_gz(path)
        by_id[str(row.get("experiment_id"))] = path
    files: list[Path] = []
    for result in selected.values():
        experiment_id = str(result["experiment_id"])
        path = by_id.get(experiment_id)
        if path is None:
            raise FileNotFoundError(f"selected expert raw not found for {experiment_id}")
        files.append(path)
    return sorted(files)


def _expert_inventory(ctx: Stage42R1Context) -> dict[str, Any]:
    files = _selected_source_files(ctx)
    rows = []
    total = 0
    selected = _selected_source_cases(ctx)
    by_id = {str(result["experiment_id"]): key for key, result in selected.items()}
    for path in files:
        result = read_json_gz(path)
        key = by_id[str(result["experiment_id"])]
        size = int(path.stat().st_size)
        total += size
        rows.append(
            {
                "target_id": key[0],
                "actual_delay_steps": key[1],
                "actual_slew_scale": key[2],
                "experiment_id": str(result["experiment_id"]),
                "path": str(path.resolve()),
                "size_bytes": size,
                "sha256": _sha256_file(path),
            }
        )
    rows.sort(key=lambda row: (row["target_id"], row["actual_slew_scale"], row["actual_delay_steps"]))
    canonical = json.dumps(rows, sort_keys=True, separators=(",", ":"))
    return {
        "schema_version": 1,
        "source_stage": "Stage4.1R17 formal expert map",
        "inventory_contract": "r42r1_selected_18_calibrated_expert_raw_v1",
        "n_files": len(rows),
        "total_bytes": total,
        "digest": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        "files": rows,
    }


def load_stage42r1_config(
    config_path: Path,
    *,
    source_stage41r17_run: Path,
    run_dir_override: Path | None = None,
) -> Stage42R1Context:
    config_path = config_path.expanduser().resolve()
    cfg = read_json(config_path)
    validate_config(cfg)
    project_dir = config_path.parents[1]
    source_stage41r17_run = source_stage41r17_run.expanduser().resolve()
    source_manifest, source_state, source_cfg, source_verdict = _validate_source_stage41r17(
        source_stage41r17_run, cfg
    )
    source_stage41r16_run = _resolve_recorded_run(
        project_dir,
        str(source_manifest["source_stage4_1r16_run"]),
        "stage4_1r16_runs",
    )
    if run_dir_override is None:
        root = project_dir / str(cfg.get("output_root", "stage4_2r1_runs"))
        run_dir = root / f"{cfg.get('run_name', 'stage4_2r1')}_{utc_timestamp()}"
    else:
        run_dir = run_dir_override.expanduser().resolve()
    packaged_r17_cfg = (
        project_dir
        / "configs"
        / "stage4_1r17_original_deadline_one_sided_robust_braking_closure_370ms.json"
    )
    if not packaged_r17_cfg.is_file():
        raise FileNotFoundError(f"packaged R17 dependency config missing: {packaged_r17_cfg}")
    r17_ctx = r17.load_stage41r17_config(
        packaged_r17_cfg,
        source_stage41r16_run=source_stage41r16_run,
        run_dir_override=run_dir,
    )
    direct_fingerprint = _source_inventory(source_stage41r17_run)
    ctx = Stage42R1Context(
        cfg=cfg,
        paths=Stage42R1Paths.from_run_dir(run_dir),
        project_dir=project_dir,
        source_stage41r17_run=source_stage41r17_run,
        source_stage41r16_run=source_stage41r16_run,
        source_manifest=source_manifest,
        source_state=source_state,
        source_cfg=source_cfg,
        source_verdict=source_verdict,
        r17_ctx=r17_ctx,
        source_fingerprint=direct_fingerprint,
        expert_fingerprint={},
        materialized_variants={},
    )
    ctx.expert_fingerprint = _expert_inventory(ctx)
    storage = cfg["storage"]
    base34 = (
        r17_ctx.r16_ctx.r15b_ctx.r15_ctx.r14_ctx.r13_ctx.r12_ctx.r11_ctx.r10_ctx.r9_ctx.r8_ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.base34
    )
    env_cfg = copy.deepcopy(base34.env_cfg)
    env_cfg["tsc_timeout_s"] = float(cfg["runtime"]["tsc_timeout_s"])
    env_cfg["tsc_workspace_root"] = str(
        Path(os.environ.get("STAGE4_2R1_TSC_WORKSPACE_ROOT", storage["tsc_workspace_root"]))
        .expanduser()
        .resolve()
    )
    env_cfg["run_root"] = str(
        Path(os.environ.get("STAGE4_2R1_TSC_RUN_ROOT", storage["tsc_run_root"]))
        .expanduser()
        .resolve()
    )
    env_cfg["tsc_run_root"] = env_cfg["run_root"]
    env_cfg["keep_failed_episode_dir"] = bool(storage.get("keep_failed_episode_dir", False))
    env_cfg["keep_last_n_failed_episode_dirs"] = int(storage.get("keep_last_n_failed_episode_dirs", 0))
    base34.env_cfg = env_cfg
    return ctx


def _initial_state(ctx: Stage42R1Context) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "stage": STAGE,
        "controller_revision": CONTROLLER_REVISION,
        "package_revision": PACKAGE_REVISION,
        "plant_restart_only": True,
        "prepared": True,
        "source_audit_complete": False,
        "capture_complete": False,
        "restart_replay_complete": False,
        "finished": False,
        "stop_reason": "",
        "updated_utc": utc_timestamp(),
    }


def _update_state(ctx: Stage42R1Context, **updates: Any) -> dict[str, Any]:
    state = read_json(ctx.paths.state) if ctx.paths.state.is_file() else _initial_state(ctx)
    state.update(_json_safe(updates))
    state["package_revision"] = PACKAGE_REVISION
    state["plant_restart_only"] = True
    state["updated_utc"] = utc_timestamp()
    atomic_write_json(ctx.paths.state, state)
    return state


def _manifest_payload(ctx: Stage42R1Context) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "stage": STAGE,
        "controller_revision": CONTROLLER_REVISION,
        "package_revision": PACKAGE_REVISION,
        "created_utc": utc_timestamp(),
        "source_stage4_1r17_run": str(ctx.source_stage41r17_run),
        "source_stage4_1r16_run": str(ctx.source_stage41r16_run),
        "source_fingerprint": ctx.source_fingerprint,
        "selected_expert_fingerprint": ctx.expert_fingerprint,
        "source_inventory_contract": SOURCE_INVENTORY_CONTRACT,
        "checkpoint_step": CHECKPOINT_STEP,
        "checkpoint_elapsed_ms": CHECKPOINT_STEP * DT_MS,
        "formal_timing_contract": ctx.cfg["formal_timing_contract"],
        "plant_restart_only": True,
        "controller_checkpoint_replay_in_this_stage": False,
        "maximum_true_tsc_rollouts": 36,
        "workers": int(os.environ.get("STAGE4_2R1_WORKERS", ctx.cfg["parallel"]["n_workers"])),
        "finite_test_envelope_only": True,
        "final_task": ctx.cfg["final_task"],
    }


def prepare(ctx: Stage42R1Context, *, resume: bool) -> None:
    for path in (
        ctx.paths.run_dir,
        ctx.paths.source_reference,
        ctx.paths.source_audit,
        ctx.paths.capture,
        ctx.paths.restart_bank,
        ctx.paths.variants,
        ctx.paths.restart,
        ctx.paths.analysis,
    ):
        path.mkdir(parents=True, exist_ok=True)
    current = _manifest_payload(ctx)
    if ctx.paths.manifest.is_file():
        old = read_json(ctx.paths.manifest)
        for key in (
            "controller_revision",
            "package_revision",
            "source_stage4_1r17_run",
            "source_fingerprint",
            "selected_expert_fingerprint",
            "checkpoint_step",
            "formal_timing_contract",
            "plant_restart_only",
        ):
            if old.get(key) != current.get(key):
                raise ValueError(f"Stage4.2R1 resume manifest mismatch for {key}")
        if not resume:
            raise FileExistsError(
                f"Stage4.2R1 run already exists; use resume=1 or a new run directory: {ctx.paths.run_dir}"
            )
    else:
        if resume:
            raise FileNotFoundError(f"Stage4.2R1 resume manifest missing: {ctx.paths.manifest}")
        atomic_write_json(ctx.paths.manifest, current)
        atomic_write_json(ctx.paths.state, _initial_state(ctx))
    atomic_write_json(ctx.paths.run_dir / "stage4_2r1_config.resolved.json", ctx.cfg)
    atomic_write_json(ctx.paths.source_reference / "stage4_1r17_manifest.json", ctx.source_manifest)
    atomic_write_json(ctx.paths.source_reference / "stage4_1r17_state.json", ctx.source_state)
    atomic_write_json(ctx.paths.source_reference / "stage4_1r17_verdict.json", ctx.source_verdict)
    atomic_write_json(ctx.paths.source_reference / "direct_stage4_1r17_inventory.json", ctx.source_fingerprint)
    atomic_write_json(ctx.paths.source_reference / "selected_expert_inventory.json", ctx.expert_fingerprint)


def _source_action_sequence(result: Mapping[str, Any], *, horizon: int) -> list[list[float]]:
    trajectory = list(result.get("trajectory") or [])
    if len(trajectory) < horizon + 1:
        raise ValueError("source trajectory does not cover the formal horizon")
    actions: list[list[float]] = []
    for index in range(horizon):
        action = np.asarray(trajectory[index + 1].get("action_norm_tsc"), dtype=float)
        if action.shape != (N_COILS,) or not np.all(np.isfinite(action)):
            raise ValueError(f"invalid source action at transition {index}")
        actions.append(action.tolist())
    return actions


def _source_initial_action(result: Mapping[str, Any]) -> list[float]:
    trajectory = list(result.get("trajectory") or [])
    if not trajectory:
        raise ValueError("source trajectory is empty")
    action = np.asarray(trajectory[0].get("action_norm_tsc"), dtype=float)
    if action.shape != (N_COILS,) or not np.all(np.isfinite(action)):
        raise ValueError("invalid source initial action")
    return action.tolist()


def _visible_array(result: Mapping[str, Any], *, trajectory_key: str = "trajectory") -> np.ndarray:
    rows = list(result.get(trajectory_key) or [])
    values: list[list[float]] = []
    for row in rows:
        currents = np.asarray(row.get("currents_a_tsc"), dtype=float).reshape(-1)
        action = np.asarray(row.get("action_norm_tsc"), dtype=float).reshape(-1)
        if currents.shape != (N_COILS,) or action.shape != (N_COILS,):
            raise ValueError("visible state coil/action shape mismatch")
        values.append(
            [
                float(row["R"]),
                float(row["Z"]),
                float(row["Ip"]),
                float(row.get("vessel_current_total_a", 0.0)),
                float(row.get("vessel_current_abs_sum_a", 0.0)),
                float(row.get("vessel_current_rms_a", 0.0)),
                float(row.get("vessel_current_max_abs_a", 0.0)),
                *currents.tolist(),
                *action.tolist(),
            ]
        )
    array = np.asarray(values, dtype=float)
    if not np.all(np.isfinite(array)):
        raise ValueError("visible trajectory contains non-finite values")
    return array


def _wire_array(result: Mapping[str, Any], *, trajectory_key: str = "trajectory") -> np.ndarray:
    rows = list(result.get(trajectory_key) or [])
    vectors = [np.asarray(row.get("wire_currents_a"), dtype=float).reshape(-1) for row in rows]
    if not vectors:
        return np.empty((0, 0), dtype=float)
    size = vectors[0].size
    if size <= 0 or any(vector.size != size for vector in vectors):
        raise ValueError("wire-current vector shape changed inside a trajectory")
    array = np.stack(vectors)
    if not np.all(np.isfinite(array)):
        raise ValueError("wire-current trajectory contains non-finite values")
    return array


def _read_wire_currents_a(runner: Any) -> np.ndarray:
    folder = Path(runner.current_folder)
    path = folder / "wire_currents.csv"
    if not path.is_file():
        raise FileNotFoundError(f"wire-current file missing: {path}")
    try:
        frame = pd.read_csv(path, skipinitialspace=True)
    except Exception as exc:
        raise RuntimeError(f"failed to read full wire-current vector: {path}") from exc
    frame.columns = [str(column).strip() for column in frame.columns]
    column = str(runner.cfg.vessel_current_column).strip()
    if column not in frame.columns:
        raise ValueError(f"wire-current column {column!r} missing from {path}")
    values = pd.to_numeric(frame[column], errors="coerce").to_numpy(dtype=float)
    if values.size == 0 or not np.all(np.isfinite(values)):
        raise ValueError(f"wire-current vector is empty or non-finite: {path}")
    return values * float(runner.cfg.vessel_current_raw_to_a)


def _state_record_full(env: Any, step_index: int, action: np.ndarray) -> dict[str, Any]:
    row = r3.base._state_record(env, step_index, np.asarray(action, dtype=float))
    row["wire_currents_a"] = _read_wire_currents_a(env.runner).tolist()
    row["wire_current_count"] = len(row["wire_currents_a"])
    return row


def _compare_arrays(left: np.ndarray, right: np.ndarray, *, atol: float) -> dict[str, Any]:
    a = np.asarray(left, dtype=float)
    b = np.asarray(right, dtype=float)
    same_shape = a.shape == b.shape
    return {
        "left_shape": list(a.shape),
        "right_shape": list(b.shape),
        "exact": bool(same_shape and np.array_equal(a, b)),
        "numeric": bool(same_shape and np.allclose(a, b, rtol=0.0, atol=float(atol))),
        "maximum_abs_difference": _finite_max_abs(a, b),
    }


def _snapshot_file_inventory(snapshot_dir: Path, checkpoint_cfg: Mapping[str, Any]) -> dict[str, Any]:
    required = list(map(str, checkpoint_cfg["required_snapshot_files"]))
    optional = list(map(str, checkpoint_cfg.get("optional_snapshot_files", [])))
    missing = [name for name in required if not (snapshot_dir / name).is_file()]
    rows = []
    total = 0
    for name in required + optional:
        path = snapshot_dir / name
        if not path.is_file():
            continue
        size = int(path.stat().st_size)
        total += size
        rows.append(
            {
                "name": name,
                "size_bytes": size,
                "sha256": _sha256_file(path),
                "required": name in required,
            }
        )
    rows.sort(key=lambda row: row["name"])
    canonical = json.dumps(rows, sort_keys=True, separators=(",", ":"))
    return {
        "schema_version": 1,
        "snapshot_dir": str(snapshot_dir.resolve()),
        "required_files": required,
        "optional_files": optional,
        "missing_required_files": missing,
        "n_files": len(rows),
        "total_bytes": total,
        "digest": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        "files": rows,
        "passed": bool(not missing and all(row["size_bytes"] > 0 for row in rows if row["required"])),
    }


def _snapshot_inventory_digest(rows: Sequence[Mapping[str, Any]]) -> str:
    canonical = json.dumps(
        [dict(row) for row in rows],
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _validate_snapshot_inventory(snapshot_dir: Path, expected: Mapping[str, Any]) -> bool:
    if not snapshot_dir.is_dir() or expected.get("missing_required_files"):
        return False
    try:
        rows = list(expected.get("files") or [])
        if not rows:
            return False
        if str(expected.get("digest", "")) != _snapshot_inventory_digest(rows):
            return False
        for row in rows:
            path = snapshot_dir / str(row["name"])
            if not path.is_file():
                return False
            if int(path.stat().st_size) != int(row["size_bytes"]):
                return False
            if _sha256_file(path) != str(row["sha256"]):
                return False
        return bool(expected.get("passed"))
    except Exception:
        return False


def _snapshot_wire_vector_a(
    snapshot_dir: Path,
    *,
    column_name: str,
    raw_to_a: float,
) -> np.ndarray:
    path = snapshot_dir / "wire_currents.csv"
    frame = pd.read_csv(path, skipinitialspace=True)
    frame.columns = [str(column).strip() for column in frame.columns]
    column = str(column_name).strip()
    if column not in frame.columns:
        raise ValueError(
            f"wire-current column {column!r} missing from restart snapshot {path}; "
            f"available columns={list(frame.columns)}"
        )
    values = pd.to_numeric(frame[column], errors="coerce").to_numpy(dtype=float)
    if values.size == 0 or not np.all(np.isfinite(values)):
        raise ValueError("snapshot wire-current vector is empty or non-finite")
    scale = float(raw_to_a)
    if not math.isfinite(scale) or scale == 0.0:
        raise ValueError(f"invalid wire-current raw-to-A scale: {raw_to_a!r}")
    return values * scale


def _materialize_variant(ctx: Stage42R1Context, *, slew: float, horizon: int) -> tuple[str, dict[str, Any]]:
    key = f"s{float(slew):.3f}_h{int(horizon)}"
    if key in ctx.materialized_variants:
        payload = ctx.materialized_variants[key]
        return str(payload["variant_id"]), payload
    variant, payload = r10.materialize_variant(
        _r10_ctx(ctx), slew_scale=float(slew), horizon_steps=int(horizon)
    )
    payload = copy.deepcopy(payload)
    payload["stage4_2r1_formal_horizon_steps"] = int(horizon)
    payload["stage4_2r1_slew_scale"] = float(slew)
    ctx.materialized_variants[key] = payload
    atomic_write_json(ctx.paths.variants / f"source_{variant}.payload.json", payload)
    return variant, payload


def _library_bundle_selector(ctx: Stage42R1Context):
    chain = _r13_ctx(ctx).r12_ctx.r11_ctx.r10_ctx.r9_ctx.r8_ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx
    library = chain.r3_ctx.source_library
    bundle = chain.r3_ctx.source_bundle
    selector = _r13_ctx(ctx).r12_ctx.r11_ctx.r10_ctx.r9_ctx.r8_ctx.cfg["batch_selector"]
    return library, bundle, selector


def _base_worker_from_container(container: r16.LocalStage41R16Worker):
    # R16 -> R15 probe -> R13 -> R12 -> base Stage4.1 worker.
    return container.inner.inner.inner.base_worker


class LocalPlantReplayWorker:
    def __init__(
        self,
        payload: dict[str, Any],
        library: dict[str, Any],
        bundle: dict[str, Any],
        worker_id: str,
        selector_cfg: dict[str, Any],
        snapshot_root: str | None = None,
        checkpoint_cfg: dict[str, Any] | None = None,
    ):
        self.container = r16.LocalStage41R16Worker(
            payload, library, bundle, worker_id, selector_cfg
        )
        self.base_worker = _base_worker_from_container(self.container)
        self.snapshot_root = Path(snapshot_root).expanduser().resolve() if snapshot_root else None
        self.checkpoint_cfg = copy.deepcopy(checkpoint_cfg or {})

    @property
    def runner(self):
        return self.base_worker.env.runner

    def close(self) -> None:
        self.container.close()

    def _cleanup(self, *, failed: bool, reason: str) -> None:
        runner = getattr(self.base_worker.env, "runner", None)
        if runner is not None:
            runner.cleanup_episode_workspace(failed=failed, reason=reason)

    def evaluate_capture(self, spec: dict[str, Any]) -> dict[str, Any]:
        started = time.time()
        failed = True
        runner = self.runner
        result: dict[str, Any] = {
            "schema_version": 1,
            "controller_revision": CONTROLLER_REVISION,
            "experiment_id": spec.get("experiment_id"),
            "spec": copy.deepcopy(spec),
            "success": False,
            "failure_reason": "",
            "trajectory": [],
        }
        try:
            if self.snapshot_root is None:
                raise ValueError("capture worker has no snapshot root")
            horizon = int(spec["horizon_steps"])
            checkpoint_step = int(spec["checkpoint_step"])
            actions = [np.asarray(row, dtype=np.float32).reshape(N_COILS) for row in spec["source_actions"]]
            if len(actions) != horizon:
                raise ValueError("capture source action count/horizon mismatch")
            initial_action = np.asarray(spec["source_initial_action"], dtype=np.float32).reshape(N_COILS)
            start_ms = int(str(runner.cfg.start_folder).rstrip("ms"))
            snapshot_time_ms = start_ms + checkpoint_step * int(runner.cfg.dt_ms)
            snapshot_dir = self.snapshot_root / str(spec["experiment_id"]) / f"{snapshot_time_ms}ms"
            if snapshot_dir.parent.exists():
                shutil.rmtree(snapshot_dir.parent)
            snapshot_dir.parent.mkdir(parents=True, exist_ok=True)
            runner.clear_restart_snapshot_requests()
            runner.request_restart_snapshot(local_step_index=checkpoint_step, destination=snapshot_dir)
            self.base_worker.env.reset()
            trajectory = [_state_record_full(self.base_worker.env, 0, initial_action)]
            failure_reason = ""
            for index, action in enumerate(actions):
                _, _, terminated, truncated, info = self.base_worker.env.step(action)
                trajectory.append(_state_record_full(self.base_worker.env, index + 1, action))
                if terminated:
                    failure_reason = str(info.get("failure_reason", "terminated"))
                    break
                if truncated and index + 1 < horizon:
                    failure_reason = "environment truncated before requested capture horizon"
                    break
            inventory = _snapshot_file_inventory(snapshot_dir, self.checkpoint_cfg)
            manifest_path = snapshot_dir / "restart_snapshot_manifest.json"
            atomic_write_json(manifest_path, inventory)
            checkpoint_wire = np.asarray(trajectory[checkpoint_step]["wire_currents_a"], dtype=float)
            snapshot_wire = _snapshot_wire_vector_a(
                snapshot_dir,
                column_name=str(runner.cfg.vessel_current_column),
                raw_to_a=float(runner.cfg.vessel_current_raw_to_a),
            )
            snapshot_wire_exact = bool(
                checkpoint_wire.shape == snapshot_wire.shape
                and np.array_equal(checkpoint_wire, snapshot_wire)
            )
            success = bool(
                not failure_reason
                and len(trajectory) == horizon + 1
                and not any(bool(row.get("abnormal")) for row in trajectory)
                and inventory.get("passed")
                and snapshot_wire_exact
            )
            result.update(
                {
                    "success": success,
                    "failure_reason": "" if success else failure_reason or "incomplete plant checkpoint capture",
                    "trajectory": trajectory,
                    "restart_snapshot": {
                        "snapshot_dir": str(snapshot_dir),
                        "snapshot_time_ms": snapshot_time_ms,
                        "snapshot_manifest_path": str(manifest_path),
                        "snapshot_manifest_digest": inventory["digest"],
                        "snapshot_files_valid": bool(inventory["passed"]),
                        "snapshot_wire_vector_exact_to_capture_state": snapshot_wire_exact,
                        "wire_current_count": int(checkpoint_wire.size),
                        "wire_current_column": str(runner.cfg.vessel_current_column),
                        "wire_current_raw_to_a": float(runner.cfg.vessel_current_raw_to_a),
                    },
                    "exact_source_action_replay_requested": True,
                    "wall_time_s": float(time.time() - started),
                }
            )
            failed = not success
            return _json_safe(result)
        except Exception as exc:
            result.update(
                {
                    "success": False,
                    "failure_reason": repr(exc),
                    "traceback": traceback.format_exc(),
                    "wall_time_s": float(time.time() - started),
                }
            )
            return _json_safe(result)
        finally:
            try:
                runner.clear_restart_snapshot_requests()
            except Exception:
                pass
            self._cleanup(failed=failed, reason="stage4_2r1_capture")

    def evaluate_restart(self, spec: dict[str, Any]) -> dict[str, Any]:
        started = time.time()
        failed = True
        result: dict[str, Any] = {
            "schema_version": 1,
            "controller_revision": CONTROLLER_REVISION,
            "experiment_id": spec.get("experiment_id"),
            "spec": copy.deepcopy(spec),
            "success": False,
            "failure_reason": "",
            "restart_trajectory": [],
        }
        try:
            suffix_actions = [
                np.asarray(row, dtype=np.float32).reshape(N_COILS)
                for row in spec["source_suffix_actions"]
            ]
            checkpoint_step = int(spec["checkpoint_step"])
            horizon = int(spec["horizon_steps"])
            if len(suffix_actions) != horizon - checkpoint_step:
                raise ValueError("restart suffix action count mismatch")
            initial_action = np.asarray(spec["source_checkpoint_action"], dtype=np.float32).reshape(N_COILS)
            self.base_worker.env.reset()
            trajectory = [_state_record_full(self.base_worker.env, checkpoint_step, initial_action)]
            failure_reason = ""
            for local_index, action in enumerate(suffix_actions):
                _, _, terminated, truncated, info = self.base_worker.env.step(action)
                global_step = checkpoint_step + local_index + 1
                trajectory.append(_state_record_full(self.base_worker.env, global_step, action))
                if terminated:
                    failure_reason = str(info.get("failure_reason", "terminated"))
                    break
                if truncated and local_index + 1 < len(suffix_actions):
                    failure_reason = "restart environment truncated before requested suffix"
                    break
            success = bool(
                not failure_reason
                and len(trajectory) == len(suffix_actions) + 1
                and not any(bool(row.get("abnormal")) for row in trajectory)
            )
            result.update(
                {
                    "success": success,
                    "failure_reason": "" if success else failure_reason or "incomplete plant restart suffix",
                    "restart_trajectory": trajectory,
                    "restart_summary": {
                        "fresh_restart_actor": True,
                        "full_tsc_hidden_state_loaded_from_sprsina": True,
                        "controller_checkpoint_loaded": False,
                        "controller_state_reconstructed": False,
                        "exact_source_action_replay_requested": True,
                        "checkpoint_step": checkpoint_step,
                        "suffix_steps": len(suffix_actions),
                    },
                    "wall_time_s": float(time.time() - started),
                }
            )
            failed = not success
            return _json_safe(result)
        except Exception as exc:
            result.update(
                {
                    "success": False,
                    "failure_reason": repr(exc),
                    "traceback": traceback.format_exc(),
                    "wall_time_s": float(time.time() - started),
                }
            )
            return _json_safe(result)
        finally:
            self._cleanup(failed=failed, reason="stage4_2r1_restart")


_CAPTURE_ACTOR = None
_RESTART_ACTOR = None


def _capture_actor_class():
    global _CAPTURE_ACTOR
    if _CAPTURE_ACTOR is None:
        import ray

        @ray.remote(num_cpus=1, max_restarts=0)
        class Stage42R1CaptureActor:
            def __init__(self, payload, library, bundle, worker_id, selector_cfg, snapshot_root, checkpoint_cfg):
                self.worker = LocalPlantReplayWorker(
                    payload, library, bundle, worker_id, selector_cfg, snapshot_root, checkpoint_cfg
                )

            def evaluate(self, spec):
                return self.worker.evaluate_capture(spec)

            def close(self):
                self.worker.close()
                return True

        _CAPTURE_ACTOR = Stage42R1CaptureActor
    return _CAPTURE_ACTOR


def _restart_actor_class():
    global _RESTART_ACTOR
    if _RESTART_ACTOR is None:
        import ray

        @ray.remote(num_cpus=1, max_restarts=0)
        class Stage42R1RestartActor:
            def __init__(self, payload, library, bundle, worker_id, selector_cfg):
                self.worker = LocalPlantReplayWorker(payload, library, bundle, worker_id, selector_cfg)

            def evaluate(self, spec):
                return self.worker.evaluate_restart(spec)

            def close(self):
                self.worker.close()
                return True

        _RESTART_ACTOR = Stage42R1RestartActor
    return _RESTART_ACTOR


def run_source_audit(ctx: Stage42R1Context) -> dict[str, Any]:
    selected = _selected_source_cases(ctx)
    formal_rows = read_json(
        ctx.source_stage41r17_run / "stage4_1r17_formal_grid_confirmation" / "results.json"
    )
    formal_by = {
        (str(row["target_id"]), int(row["actual_delay_steps"]), float(row["actual_slew_scale"])): row
        for row in formal_rows
    }
    expected = {
        (target, delay, slew)
        for target in ctx.cfg["matrix"]["targets"]
        for delay in ctx.cfg["matrix"]["actual_delay_steps"]
        for slew in ctx.cfg["matrix"]["actual_slew_scales"]
    }
    r13_ctx = _r13_ctx(ctx)
    rows = []
    for key in sorted(selected, key=lambda item: (item[0], item[2], item[1])):
        result = selected[key]
        target, delay, slew = key
        horizon = _formal_horizon(slew)
        policy = r13._timing_policy(r13_ctx, slew, policy_id=f"r42r1_source_{target}_d{delay}_s{slew:.1f}")
        sliced = r13._slice_result(result, horizon)
        metrics = r8.tracking_metrics(r13_ctx.r12_ctx.r11_ctx.r10_ctx.r9_ctx.r8_ctx, sliced, policy)
        actions = _source_action_sequence(result, horizon=horizon)
        rows.append(
            {
                "target_id": target,
                "actual_delay_steps": delay,
                "actual_slew_scale": slew,
                "source_experiment_id": str(result["experiment_id"]),
                "source_controller_revision": str(result.get("controller_revision", "")),
                "formal_horizon_steps": horizon,
                "formal_arrival_deadline_step": max(policy["allowed_arrival_steps"]),
                "source_environment_success": bool(result.get("success")),
                "source_abnormal": any(bool(row.get("abnormal")) for row in result.get("trajectory") or []),
                "source_action_count": len(actions),
                "source_action_finite": bool(np.all(np.isfinite(np.asarray(actions, dtype=float)))),
                "trusted_calibration_model": bool((result.get("spec") or {}).get("trusted_calibration_model")),
                "calibration_token": (result.get("spec") or {}).get("calibration_token"),
                "formal_tracking_pass": bool(metrics.get("stage3_4_target_tracking_pass")),
                "formal_minimum_signed_margin": _as_float(metrics.get("stage3_4_tracking_minimum_signed_margin"), -math.inf),
                "official_formal_margin": _as_float(formal_by[key].get("oracle_minimum_signed_margin"), -math.inf),
                "controller_path": formal_by[key].get("controller_path"),
            }
        )
    tokens = {str(row["calibration_token"]) for row in rows if row.get("calibration_token")}
    minimum = min(rows, key=lambda row: row["formal_minimum_signed_margin"])
    passed = bool(
        set(selected) == expected
        and len(rows) == 18
        and all(bool(row["source_environment_success"]) for row in rows)
        and not any(bool(row["source_abnormal"]) for row in rows)
        and all(bool(row["source_action_finite"]) for row in rows)
        and all(int(row["source_action_count"]) == int(row["formal_horizon_steps"]) for row in rows)
        and all(bool(row["trusted_calibration_model"]) for row in rows)
        and all(bool(row["formal_tracking_pass"]) for row in rows)
        and all(math.isclose(float(row["formal_minimum_signed_margin"]), float(row["official_formal_margin"]), rel_tol=0.0, abs_tol=1e-12) for row in rows)
        and len(tokens) == 9
    )
    summary = {
        "schema_version": 1,
        "stage": STAGE,
        "phase": "source_audit",
        "source_stage4_1r17_run": str(ctx.source_stage41r17_run),
        "source_finished": bool(ctx.source_state.get("finished")),
        "source_stop_reason": str(ctx.source_state.get("stop_reason", "")),
        "source_formal_grid_status": ctx.source_verdict.get("formal_grid_confirmation_status"),
        "selected_expert_cases": len(rows),
        "expected_cases": 18,
        "modified_r17_cases": sum(str(row["controller_path"]).startswith("r17_one_sided_") for row in rows),
        "unchanged_source_cases": sum(str(row["controller_path"]) == "source_unchanged_r11_original_deadline" for row in rows),
        "environment_success_count": sum(bool(row["source_environment_success"]) for row in rows),
        "abnormal_rollout_count": sum(bool(row["source_abnormal"]) for row in rows),
        "formal_contract_pass_fraction": sum(bool(row["formal_tracking_pass"]) for row in rows) / len(rows) if rows else 0.0,
        "distinct_trusted_calibration_tokens": len(tokens),
        "minimum_formal_signed_margin": minimum["formal_minimum_signed_margin"],
        "minimum_margin_case": {
            "target_id": minimum["target_id"],
            "actual_delay_steps": minimum["actual_delay_steps"],
            "actual_slew_scale": minimum["actual_slew_scale"],
            "controller_path": minimum["controller_path"],
        },
        "razor_thin_source_margin_warning": bool(minimum["formal_minimum_signed_margin"] < 1e-4),
        "original_250_350_and_270_370_timing_unchanged": True,
        "r10_r11_long_horizons_are_auxiliary_only": True,
        "old_unrun_r11_based_stage4_2r1_not_reused": True,
        "plant_restart_only": True,
        "controller_checkpoint_replay_in_this_stage": False,
        "passed": passed,
        "interpretation": (
            "R17 genuinely restores the original finite 18-case timing grid, but the minimum "
            "source margin is razor-thin. R1 now isolates authentic TSC plant-state restart "
            "fidelity by replaying the exact expert actions; it does not yet test controller-state reconstruction."
        ),
    }
    write_csv(ctx.paths.source_audit / "expert_cases.csv", rows)
    atomic_write_json(ctx.paths.source_audit / "summary.json", summary)
    _update_state(ctx, source_audit_complete=True, source_audit_summary=summary)
    return summary


def build_capture_specs(ctx: Stage42R1Context) -> list[dict[str, Any]]:
    selected = _selected_source_cases(ctx)
    specs = []
    for key in sorted(selected, key=lambda item: (item[2], item[1], item[0])):
        target, delay, slew = key
        source = selected[key]
        horizon = _formal_horizon(slew)
        variant, _ = _materialize_variant(ctx, slew=slew, horizon=horizon)
        identity = {
            "revision": CONTROLLER_REVISION,
            "phase": "plant_checkpoint_capture",
            "target_id": target,
            "delay": delay,
            "slew": slew,
            "horizon": horizon,
            "checkpoint_step": CHECKPOINT_STEP,
            "source_experiment_id": source["experiment_id"],
            "selected_expert_digest": ctx.expert_fingerprint["digest"],
        }
        source_spec = source["spec"]
        specs.append(
            {
                "kind": "stage4_2r1_true_tsc_plant_checkpoint_capture",
                "controller_revision": CONTROLLER_REVISION,
                "experiment_id": _scenario_digest(identity),
                "phase": "plant_checkpoint_capture",
                "target_id": target,
                "target_R_offset_m": float(source_spec.get("target_R_offset_m", 0.0)),
                "target_Z_offset_m": float(source_spec.get("target_Z_offset_m", 0.0)),
                "target_Ip_offset_A": float(source_spec.get("target_Ip_offset_A", 0.0)),
                "action_delay_steps": delay,
                "controller_action_delay_steps": delay,
                "slew_scale": slew,
                "controller_slew_scale_estimate": slew,
                "environment_variant": variant,
                "horizon_steps": horizon,
                "checkpoint_step": CHECKPOINT_STEP,
                "source_experiment_id": str(source["experiment_id"]),
                "source_controller_revision": str(source.get("controller_revision", "")),
                "source_initial_action": _source_initial_action(source),
                "source_actions": _source_action_sequence(source, horizon=horizon),
                "trusted_calibration_model": bool(source_spec.get("trusted_calibration_model")),
                "calibration_token": source_spec.get("calibration_token"),
                "exact_source_action_replay": True,
                "plant_restart_only": True,
                "controller_checkpoint_replay": False,
            }
        )
    if len(specs) != int(ctx.cfg["matrix"]["expected_capture_rollouts"]):
        raise ValueError("Stage4.2R1 capture specification count mismatch")
    return specs


def _capture_snapshot_complete(path: Path) -> bool:
    if not _result_complete(path):
        return False
    try:
        result = read_json_gz(path)
        snapshot = result.get("restart_snapshot") or {}
        manifest_path = Path(str(snapshot.get("snapshot_manifest_path", "")))
        snapshot_dir = Path(str(snapshot.get("snapshot_dir", "")))
        if not manifest_path.is_file():
            return False
        manifest = read_json(manifest_path)
        return bool(
            snapshot.get("snapshot_files_valid")
            and snapshot.get("snapshot_wire_vector_exact_to_capture_state")
            and str(snapshot.get("snapshot_manifest_digest", "")) == str(manifest.get("digest", ""))
            and _validate_snapshot_inventory(snapshot_dir, manifest)
        )
    except Exception:
        return False


def _evaluate_capture_specs(
    ctx: Stage42R1Context, specs: Sequence[dict[str, Any]], *, backend: str, resume: bool
) -> list[dict[str, Any]]:
    raw_dir = ctx.paths.capture / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    by_variant: dict[str, list[dict[str, Any]]] = {}
    payloads: dict[str, dict[str, Any]] = {}
    for spec in specs:
        variant = str(spec["environment_variant"])
        _, payload = _materialize_variant(ctx, slew=float(spec["slew_scale"]), horizon=int(spec["horizon_steps"]))
        payloads[variant] = payload
        by_variant.setdefault(variant, []).append(spec)
    pending_by_variant = {
        variant: [spec for spec in rows if not (resume and _capture_snapshot_complete(raw_dir / f"{spec['experiment_id']}.json.gz"))]
        for variant, rows in by_variant.items()
    }
    pending_by_variant = {key: value for key, value in pending_by_variant.items() if value}
    library, bundle, selector = _library_bundle_selector(ctx)
    if backend == "serial":
        for variant, pending in pending_by_variant.items():
            worker = LocalPlantReplayWorker(
                payloads[variant], library, bundle, f"stage42r1_capture_{variant}_serial", selector,
                str(ctx.paths.restart_bank), ctx.cfg["checkpoint"]
            )
            try:
                for index, spec in enumerate(pending, 1):
                    atomic_write_json_gz(raw_dir / f"{spec['experiment_id']}.json.gz", worker.evaluate_capture(spec))
                    print(f"[Stage4.2R1 plant-capture {variant}] {index}/{len(pending)}", flush=True)
            finally:
                worker.close()
    elif backend == "ray" and pending_by_variant:
        import ray

        requested = int(os.environ.get("STAGE4_2R1_WORKERS", ctx.cfg["parallel"]["n_workers"]))
        total_pending = sum(len(rows) for rows in pending_by_variant.values())
        plan = ensure_ray_worker_plan(
            ray,
            requested_workers=requested,
            pending_tasks=total_pending,
            ray_tmpdir=os.environ.get("RAY_TMPDIR", ctx.cfg["parallel"].get("ray_tmpdir", "")) or None,
            log_prefix="[Stage4.2R1 plant-capture]",
        )
        allocation = r3.s40._allocate_variant_actor_counts(
            {variant: len(rows) for variant, rows in pending_by_variant.items()}, plan.actor_count
        )
        print("[Stage4.2R1 plant-capture] actor_allocation=" + json.dumps(allocation, sort_keys=True, separators=(",", ":")), flush=True)
        Actor = _capture_actor_class()
        actors_by_variant = {}
        all_actors = []
        for variant, count in allocation.items():
            actors = [
                Actor.remote(
                    payloads[variant], library, bundle, f"stage42r1_capture_{index:03d}", selector,
                    str(ctx.paths.restart_bank), ctx.cfg["checkpoint"]
                )
                for index in range(count)
            ]
            actors_by_variant[variant] = actors
            all_actors.extend(actors)
        refs = {}
        for variant, pending in pending_by_variant.items():
            actors = actors_by_variant[variant]
            for index, spec in enumerate(pending):
                refs[actors[index % len(actors)].evaluate.remote(spec)] = spec
        done = 0
        try:
            while refs:
                ready, _ = ray.wait(list(refs), num_returns=1, timeout=30.0)
                if not ready:
                    print(f"[Stage4.2R1 plant-capture] waiting {done}/{total_pending}", flush=True)
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
                        }
                    atomic_write_json_gz(raw_dir / f"{spec['experiment_id']}.json.gz", result)
                    done += 1
                    if done % 10 == 0 or not refs:
                        print(f"[Stage4.2R1 plant-capture] {done}/{total_pending}", flush=True)
        finally:
            s2._close_ray_actors(all_actors, timeout_s=float(ctx.cfg["storage"].get("actor_close_timeout_s", 1800.0)))
    elif backend not in {"serial", "ray"}:
        raise ValueError("backend must be serial or ray")
    return [read_json_gz(raw_dir / f"{spec['experiment_id']}.json.gz") for spec in specs]


def _source_case(ctx: Stage42R1Context, key: tuple[str, int, float]) -> dict[str, Any]:
    result = _selected_source_cases(ctx).get(key)
    if result is None:
        raise KeyError(f"selected source case missing: {key}")
    return result


def _capture_result_row(ctx: Stage42R1Context, result: Mapping[str, Any]) -> dict[str, Any]:
    key = _case_key(result)
    source = _source_case(ctx, key)
    horizon = int((result.get("spec") or {})["horizon_steps"])
    source_slice = {"trajectory": list(source.get("trajectory") or [])[: horizon + 1]}
    visible = _compare_arrays(
        _visible_array(result), _visible_array(source_slice), atol=float(ctx.cfg["checkpoint"]["capture_numeric_atol"])
    )
    source_actions = np.asarray((result.get("spec") or {})["source_actions"], dtype=float)
    capture_actions = np.asarray([row["action_norm_tsc"] for row in list(result.get("trajectory") or [])[1:]], dtype=float)
    action_compare = _compare_arrays(capture_actions, source_actions, atol=0.0)
    wire = _wire_array(result)
    snapshot = result.get("restart_snapshot") or {}
    manifest_path = Path(str(snapshot.get("snapshot_manifest_path", "")))
    snapshot_dir = Path(str(snapshot.get("snapshot_dir", "")))
    manifest = read_json(manifest_path) if manifest_path.is_file() else {}
    snapshot_valid = bool(
        manifest_path.is_file()
        and str(snapshot.get("snapshot_manifest_digest", "")) == str(manifest.get("digest", ""))
        and _validate_snapshot_inventory(snapshot_dir, manifest)
    )
    checkpoint_wire = wire[CHECKPOINT_STEP] if wire.shape[0] > CHECKPOINT_STEP else np.asarray([math.nan])
    snapshot_wire = (
        _snapshot_wire_vector_a(
            snapshot_dir,
            column_name=str(result.get("restart_snapshot", {}).get("wire_current_column", "cwire(ka)")),
            raw_to_a=float(result.get("restart_snapshot", {}).get("wire_current_raw_to_a", 1000.0)),
        )
        if snapshot_valid
        else np.asarray([math.nan])
    )
    snapshot_wire_compare = _compare_arrays(checkpoint_wire, snapshot_wire, atol=0.0)
    passed = bool(
        result.get("success")
        and visible["exact"]
        and visible["numeric"]
        and action_compare["exact"]
        and snapshot_valid
        and snapshot_wire_compare["exact"]
        and wire.shape[0] == horizon + 1
        and wire.shape[1] > 0
    )
    return {
        "experiment_id": result.get("experiment_id"),
        "source_experiment_id": source.get("experiment_id"),
        "target_id": key[0],
        "actual_delay_steps": key[1],
        "actual_slew_scale": key[2],
        "formal_horizon_steps": horizon,
        "environment_success": bool(result.get("success")),
        "failure_reason": str(result.get("failure_reason", "")),
        "capture_visible_exact_to_source": visible["exact"],
        "capture_visible_numeric_to_source": visible["numeric"],
        "capture_visible_maximum_abs_difference": visible["maximum_abs_difference"],
        "source_actions_exactly_replayed": action_compare["exact"],
        "source_action_maximum_abs_difference": action_compare["maximum_abs_difference"],
        "full_wire_current_vector_present": bool(wire.shape[1] > 0),
        "wire_current_count": int(wire.shape[1]) if wire.ndim == 2 else 0,
        "snapshot_dir": str(snapshot_dir),
        "snapshot_manifest_digest": snapshot.get("snapshot_manifest_digest"),
        "snapshot_files_valid": snapshot_valid,
        "snapshot_wire_exact_to_capture_checkpoint": snapshot_wire_compare["exact"],
        "snapshot_wire_maximum_abs_difference": snapshot_wire_compare["maximum_abs_difference"],
        "passed": passed,
    }


def _summarize_capture(ctx: Stage42R1Context, results: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    rows = [_capture_result_row(ctx, result) for result in results]
    expected = int(ctx.cfg["matrix"]["expected_capture_rollouts"])
    keys = {(row["target_id"], row["actual_delay_steps"], row["actual_slew_scale"]) for row in rows}
    expected_keys = set(_selected_source_cases(ctx))
    summary = {
        "schema_version": 1,
        "stage": STAGE,
        "phase": "plant_checkpoint_capture",
        "n_rollouts": len(rows),
        "expected_rollouts": expected,
        "coverage_complete": len(rows) == expected and keys == expected_keys,
        "environment_success_count": sum(bool(row["environment_success"]) for row in rows),
        "capture_visible_exact_fraction": sum(bool(row["capture_visible_exact_to_source"]) for row in rows) / len(rows) if rows else 0.0,
        "source_action_exact_fraction": sum(bool(row["source_actions_exactly_replayed"]) for row in rows) / len(rows) if rows else 0.0,
        "maximum_capture_visible_abs_difference": max((_as_float(row["capture_visible_maximum_abs_difference"], math.inf) for row in rows), default=math.inf),
        "maximum_source_action_abs_difference": max((_as_float(row["source_action_maximum_abs_difference"], math.inf) for row in rows), default=math.inf),
        "snapshot_valid_fraction": sum(bool(row["snapshot_files_valid"]) for row in rows) / len(rows) if rows else 0.0,
        "snapshot_wire_exact_fraction": sum(bool(row["snapshot_wire_exact_to_capture_checkpoint"]) for row in rows) / len(rows) if rows else 0.0,
        "full_wire_vector_fraction": sum(bool(row["full_wire_current_vector_present"]) for row in rows) / len(rows) if rows else 0.0,
        "distinct_snapshot_paths": len({row["snapshot_dir"] for row in rows}),
        "wire_current_count_min": min((int(row["wire_current_count"]) for row in rows), default=0),
        "wire_current_count_max": max((int(row["wire_current_count"]) for row in rows), default=0),
        "plant_capture_instrumentation_changed_source_trace": not all(bool(row["capture_visible_exact_to_source"]) for row in rows),
        "passed": False,
    }
    summary["passed"] = bool(
        summary["coverage_complete"]
        and summary["environment_success_count"] == expected
        and summary["capture_visible_exact_fraction"] == 1.0
        and summary["source_action_exact_fraction"] == 1.0
        and summary["maximum_capture_visible_abs_difference"] == 0.0
        and summary["maximum_source_action_abs_difference"] == 0.0
        and summary["snapshot_valid_fraction"] == 1.0
        and summary["snapshot_wire_exact_fraction"] == 1.0
        and summary["full_wire_vector_fraction"] == 1.0
        and summary["distinct_snapshot_paths"] == expected
        and summary["wire_current_count_min"] > 0
        and summary["wire_current_count_min"] == summary["wire_current_count_max"]
        and all(bool(row["passed"]) for row in rows)
    )
    write_csv(ctx.paths.capture / "results.csv", rows)
    atomic_write_json(ctx.paths.capture / "results.json", rows)
    atomic_write_json(ctx.paths.capture / "summary.json", summary)
    _update_state(ctx, capture_complete=True, capture_summary=summary)
    return summary


def run_capture(ctx: Stage42R1Context, *, backend: str, resume: bool) -> dict[str, Any]:
    specs = build_capture_specs(ctx)
    results = _evaluate_capture_specs(ctx, specs, backend=backend, resume=resume)
    return _summarize_capture(ctx, results)


def _capture_results_by_case(ctx: Stage42R1Context) -> dict[tuple[str, int, float], dict[str, Any]]:
    output = {}
    for path in sorted((ctx.paths.capture / "raw").glob("*.json.gz")):
        result = read_json_gz(path)
        key = _case_key(result)
        if key in output:
            raise ValueError(f"duplicate Stage4.2R1 capture case: {key}")
        output[key] = result
    return output


def _materialize_restart_variant(ctx: Stage42R1Context, capture: Mapping[str, Any]) -> tuple[str, dict[str, Any]]:
    key = _case_key(capture)
    snapshot = capture["restart_snapshot"]
    snapshot_dir = Path(str(snapshot["snapshot_dir"])).expanduser().resolve()
    horizon = int((capture.get("spec") or {})["horizon_steps"])
    suffix_steps = horizon - CHECKPOINT_STEP
    variant_id = f"r42r1_restart_{capture['experiment_id']}_d{key[1]}_s{key[2]:.3f}".replace(".", "p")
    if variant_id in ctx.materialized_variants:
        return variant_id, ctx.materialized_variants[variant_id]
    _, base_payload = _materialize_variant(ctx, slew=key[2], horizon=horizon)
    payload = copy.deepcopy(base_payload)
    env_cfg = copy.deepcopy(payload["env_cfg"])
    env_cfg["simulation_root"] = str(snapshot_dir.parent)
    env_cfg["start_folder"] = snapshot_dir.name
    env_cfg["tsc_timeout_s"] = float(ctx.cfg["runtime"]["tsc_timeout_s"])
    env_cfg["tsc_workspace_root"] = str(Path(os.environ.get("STAGE4_2R1_TSC_WORKSPACE_ROOT", ctx.cfg["storage"]["tsc_workspace_root"])).expanduser().resolve())
    env_cfg["run_root"] = str(Path(os.environ.get("STAGE4_2R1_TSC_RUN_ROOT", ctx.cfg["storage"]["tsc_run_root"])).expanduser().resolve())
    env_cfg["tsc_run_root"] = env_cfg["run_root"]
    env_cfg["runtime_only_fast_mode"] = True
    env_cfg["save_step_artifacts"] = False
    env_cfg["save_artifacts_every_n_steps"] = 0
    env_cfg["cleanup_episode_dir"] = True
    env_cfg["keep_failed_episode_dir"] = bool(ctx.cfg["storage"].get("keep_failed_episode_dir", False))
    env_cfg["keep_last_n_failed_episode_dirs"] = int(ctx.cfg["storage"].get("keep_last_n_failed_episode_dirs", 0))
    train_cfg = copy.deepcopy(payload["train_cfg"])
    env_path = ctx.paths.variants / f"env_{variant_id}.json"
    train_path = ctx.paths.variants / f"train_{variant_id}.json"
    train_cfg["env_config"] = str(env_path)
    train_cfg.setdefault("episode", {})["max_episode_steps"] = suffix_steps
    atomic_write_json(env_path, env_cfg)
    atomic_write_json(train_path, train_cfg)
    payload["env_cfg"] = env_cfg
    payload["train_cfg"] = train_cfg
    payload["variant_id"] = variant_id
    payload["start_folder"] = snapshot_dir.name
    payload["slew_scale"] = key[2]
    payload["stage4_1r4_horizon_steps"] = suffix_steps
    payload["stage4_2r1_restart_snapshot_dir"] = str(snapshot_dir)
    payload["stage4_2r1_snapshot_manifest_digest"] = str(snapshot["snapshot_manifest_digest"])
    ctx.materialized_variants[variant_id] = payload
    return variant_id, payload


def build_restart_specs(ctx: Stage42R1Context) -> list[dict[str, Any]]:
    captures = _capture_results_by_case(ctx)
    selected = _selected_source_cases(ctx)
    specs = []
    for key in sorted(captures, key=lambda item: (item[2], item[1], item[0])):
        capture = captures[key]
        raw_path = ctx.paths.capture / "raw" / f"{capture['experiment_id']}.json.gz"
        if not _capture_snapshot_complete(raw_path):
            raise ValueError(f"cannot build restart from incomplete capture: {key}")
        source = selected[key]
        horizon = _formal_horizon(key[2])
        variant, _ = _materialize_restart_variant(ctx, capture)
        actions = _source_action_sequence(source, horizon=horizon)
        identity = {
            "revision": CONTROLLER_REVISION,
            "phase": "plant_restart_replay",
            "target_id": key[0],
            "delay": key[1],
            "slew": key[2],
            "checkpoint_step": CHECKPOINT_STEP,
            "snapshot_digest": capture["restart_snapshot"]["snapshot_manifest_digest"],
            "source_experiment_id": source["experiment_id"],
        }
        source_spec = source["spec"]
        specs.append(
            {
                "kind": "stage4_2r1_true_tsc_plant_restart_action_replay",
                "controller_revision": CONTROLLER_REVISION,
                "experiment_id": _scenario_digest(identity),
                "phase": "plant_restart_replay",
                "target_id": key[0],
                "target_R_offset_m": float(source_spec.get("target_R_offset_m", 0.0)),
                "target_Z_offset_m": float(source_spec.get("target_Z_offset_m", 0.0)),
                "target_Ip_offset_A": float(source_spec.get("target_Ip_offset_A", 0.0)),
                "action_delay_steps": key[1],
                "controller_action_delay_steps": key[1],
                "slew_scale": key[2],
                "controller_slew_scale_estimate": key[2],
                "environment_variant": variant,
                "horizon_steps": horizon,
                "checkpoint_step": CHECKPOINT_STEP,
                "source_experiment_id": str(source["experiment_id"]),
                "capture_experiment_id": str(capture["experiment_id"]),
                "restart_snapshot_dir": str(capture["restart_snapshot"]["snapshot_dir"]),
                "restart_snapshot_manifest_path": str(capture["restart_snapshot"]["snapshot_manifest_path"]),
                "source_checkpoint_action": list(source["trajectory"][CHECKPOINT_STEP]["action_norm_tsc"]),
                "source_suffix_actions": actions[CHECKPOINT_STEP:],
                "trusted_calibration_model": bool(source_spec.get("trusted_calibration_model")),
                "calibration_token": source_spec.get("calibration_token"),
                "exact_source_action_replay": True,
                "fresh_restart_actor_required": True,
                "full_tsc_hidden_state_loaded_from_sprsina": True,
                "plant_restart_only": True,
                "controller_checkpoint_replay": False,
            }
        )
    if len(specs) != int(ctx.cfg["matrix"]["expected_restart_rollouts"]):
        raise ValueError("Stage4.2R1 restart specification count mismatch")
    return specs


def _evaluate_restart_specs(ctx: Stage42R1Context, specs: Sequence[dict[str, Any]], *, backend: str, resume: bool) -> list[dict[str, Any]]:
    raw_dir = ctx.paths.restart / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    payloads = {}
    by_variant = {}
    captures = _capture_results_by_case(ctx)
    for spec in specs:
        key = _case_key(spec)
        variant, payload = _materialize_restart_variant(ctx, captures[key])
        if variant != spec["environment_variant"]:
            raise ValueError("restart variant identity changed")
        payloads[variant] = payload
        by_variant.setdefault(variant, []).append(spec)
    pending_by_variant = {
        variant: [spec for spec in rows if not (resume and _result_complete(raw_dir / f"{spec['experiment_id']}.json.gz"))]
        for variant, rows in by_variant.items()
    }
    pending_by_variant = {key: value for key, value in pending_by_variant.items() if value}
    library, bundle, selector = _library_bundle_selector(ctx)
    if backend == "serial":
        for variant, pending in pending_by_variant.items():
            worker = LocalPlantReplayWorker(payloads[variant], library, bundle, f"stage42r1_restart_{variant}_serial", selector)
            try:
                for index, spec in enumerate(pending, 1):
                    atomic_write_json_gz(raw_dir / f"{spec['experiment_id']}.json.gz", worker.evaluate_restart(spec))
                    print(f"[Stage4.2R1 plant-restart {variant}] {index}/{len(pending)}", flush=True)
            finally:
                worker.close()
    elif backend == "ray" and pending_by_variant:
        import ray

        requested = int(os.environ.get("STAGE4_2R1_WORKERS", ctx.cfg["parallel"]["n_workers"]))
        total_pending = sum(len(rows) for rows in pending_by_variant.values())
        plan = ensure_ray_worker_plan(
            ray,
            requested_workers=requested,
            pending_tasks=total_pending,
            ray_tmpdir=os.environ.get("RAY_TMPDIR", ctx.cfg["parallel"].get("ray_tmpdir", "")) or None,
            log_prefix="[Stage4.2R1 plant-restart]",
        )
        allocation = r3.s40._allocate_variant_actor_counts(
            {variant: len(rows) for variant, rows in pending_by_variant.items()}, plan.actor_count
        )
        print("[Stage4.2R1 plant-restart] actor_allocation=" + json.dumps(allocation, sort_keys=True, separators=(",", ":")), flush=True)
        Actor = _restart_actor_class()
        actors_by_variant = {}
        all_actors = []
        for variant, count in allocation.items():
            actors = [
                Actor.remote(payloads[variant], library, bundle, f"stage42r1_restart_{index:03d}", selector)
                for index in range(count)
            ]
            actors_by_variant[variant] = actors
            all_actors.extend(actors)
        refs = {}
        for variant, pending in pending_by_variant.items():
            actors = actors_by_variant[variant]
            for index, spec in enumerate(pending):
                refs[actors[index % len(actors)].evaluate.remote(spec)] = spec
        done = 0
        try:
            while refs:
                ready, _ = ray.wait(list(refs), num_returns=1, timeout=30.0)
                if not ready:
                    print(f"[Stage4.2R1 plant-restart] waiting {done}/{total_pending}", flush=True)
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
                            "restart_trajectory": [],
                        }
                    atomic_write_json_gz(raw_dir / f"{spec['experiment_id']}.json.gz", result)
                    done += 1
                    if done % 10 == 0 or not refs:
                        print(f"[Stage4.2R1 plant-restart] {done}/{total_pending}", flush=True)
        finally:
            s2._close_ray_actors(all_actors, timeout_s=float(ctx.cfg["storage"].get("actor_close_timeout_s", 1800.0)))
    elif backend not in {"serial", "ray"}:
        raise ValueError("backend must be serial or ray")
    return [read_json_gz(raw_dir / f"{spec['experiment_id']}.json.gz") for spec in specs]


def _recombined_result(source: Mapping[str, Any], capture: Mapping[str, Any], restart: Mapping[str, Any], *, horizon: int) -> dict[str, Any]:
    prefix = copy.deepcopy(list(capture.get("trajectory") or [])[:CHECKPOINT_STEP])
    suffix = copy.deepcopy(list(restart.get("restart_trajectory") or []))
    trajectory = prefix + suffix
    if len(trajectory) != horizon + 1:
        raise ValueError("recombined restart trajectory length mismatch")
    output = copy.deepcopy(dict(source))
    output["trajectory"] = trajectory
    output["spec"] = copy.deepcopy(dict(source["spec"]))
    return output


def _restart_result_row(ctx: Stage42R1Context, result: Mapping[str, Any]) -> dict[str, Any]:
    key = _case_key(result)
    source = _source_case(ctx, key)
    capture = _capture_results_by_case(ctx)[key]
    horizon = int((result.get("spec") or {})["horizon_steps"])
    restart_visible = _visible_array(result, trajectory_key="restart_trajectory")
    capture_visible_suffix = _visible_array({"trajectory": list(capture["trajectory"])[CHECKPOINT_STEP : horizon + 1]})
    visible = _compare_arrays(restart_visible, capture_visible_suffix, atol=float(ctx.cfg["checkpoint"]["restart_numeric_atol"]))
    restart_wire = _wire_array(result, trajectory_key="restart_trajectory")
    capture_wire = _wire_array({"trajectory": list(capture["trajectory"])[CHECKPOINT_STEP : horizon + 1]})
    wire = _compare_arrays(restart_wire, capture_wire, atol=float(ctx.cfg["checkpoint"]["restart_numeric_atol"]))
    expected_actions = np.asarray((result.get("spec") or {})["source_suffix_actions"], dtype=float)
    actual_actions = np.asarray([row["action_norm_tsc"] for row in list(result.get("restart_trajectory") or [])[1:]], dtype=float)
    action = _compare_arrays(actual_actions, expected_actions, atol=0.0)
    initial_visible = _compare_arrays(restart_visible[:1], capture_visible_suffix[:1], atol=float(ctx.cfg["checkpoint"]["restart_numeric_atol"]))
    initial_wire = _compare_arrays(restart_wire[:1], capture_wire[:1], atol=float(ctx.cfg["checkpoint"]["restart_numeric_atol"]))
    recombined = _recombined_result(source, capture, result, horizon=horizon)
    source_slice = r13._slice_result(source, horizon)
    source_visible = _visible_array(source_slice)
    recombined_visible = _visible_array(recombined)
    recombined_compare = _compare_arrays(recombined_visible, source_visible, atol=float(ctx.cfg["checkpoint"]["restart_numeric_atol"]))
    r13_ctx = _r13_ctx(ctx)
    policy = r13._timing_policy(r13_ctx, key[2], policy_id=f"r42r1_restart_{key[0]}_d{key[1]}_s{key[2]:.1f}")
    metrics = r8.tracking_metrics(r13_ctx.r12_ctx.r11_ctx.r10_ctx.r9_ctx.r8_ctx, recombined, policy)
    formal_pass = bool(metrics.get("stage3_4_target_tracking_pass"))
    plant_fidelity = bool(
        result.get("success")
        and visible["exact"]
        and visible["numeric"]
        and wire["exact"]
        and wire["numeric"]
        and action["exact"]
        and initial_visible["exact"]
        and initial_wire["exact"]
        and recombined_compare["exact"]
    )
    passed = bool(plant_fidelity and formal_pass)
    return {
        "experiment_id": result.get("experiment_id"),
        "source_experiment_id": source.get("experiment_id"),
        "capture_experiment_id": (result.get("spec") or {}).get("capture_experiment_id"),
        "target_id": key[0],
        "actual_delay_steps": key[1],
        "actual_slew_scale": key[2],
        "formal_horizon_steps": horizon,
        "environment_success": bool(result.get("success")),
        "failure_reason": str(result.get("failure_reason", "")),
        "fresh_restart_actor": bool((result.get("restart_summary") or {}).get("fresh_restart_actor")),
        "full_tsc_hidden_state_loaded_from_sprsina": bool((result.get("restart_summary") or {}).get("full_tsc_hidden_state_loaded_from_sprsina")),
        "controller_checkpoint_loaded": bool((result.get("restart_summary") or {}).get("controller_checkpoint_loaded")),
        "restart_initial_visible_exact": initial_visible["exact"],
        "restart_initial_wire_exact": initial_wire["exact"],
        "restart_visible_suffix_exact": visible["exact"],
        "restart_wire_suffix_exact": wire["exact"],
        "restart_source_actions_exact": action["exact"],
        "restart_visible_maximum_abs_difference": visible["maximum_abs_difference"],
        "restart_wire_maximum_abs_difference": wire["maximum_abs_difference"],
        "restart_action_maximum_abs_difference": action["maximum_abs_difference"],
        "recombined_visible_exact_to_source": recombined_compare["exact"],
        "formal_contract_pass": formal_pass,
        "formal_minimum_signed_margin": _as_float(metrics.get("stage3_4_tracking_minimum_signed_margin"), -math.inf),
        "plant_restart_fidelity_pass": plant_fidelity,
        "passed": passed,
    }


def _summarize_restart(ctx: Stage42R1Context, results: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    rows = [_restart_result_row(ctx, result) for result in results]
    expected = int(ctx.cfg["matrix"]["expected_restart_rollouts"])
    keys = {(row["target_id"], row["actual_delay_steps"], row["actual_slew_scale"]) for row in rows}
    expected_keys = set(_selected_source_cases(ctx))
    minimum = min(rows, key=lambda row: row["formal_minimum_signed_margin"]) if rows else {}
    plant_fraction = sum(bool(row["plant_restart_fidelity_pass"]) for row in rows) / len(rows) if rows else 0.0
    formal_fraction = sum(bool(row["formal_contract_pass"]) for row in rows) / len(rows) if rows else 0.0
    summary = {
        "schema_version": 1,
        "stage": STAGE,
        "phase": "plant_restart_replay",
        "n_rollouts": len(rows),
        "expected_rollouts": expected,
        "coverage_complete": len(rows) == expected and keys == expected_keys,
        "environment_success_count": sum(bool(row["environment_success"]) for row in rows),
        "fresh_restart_actor_fraction": sum(bool(row["fresh_restart_actor"]) for row in rows) / len(rows) if rows else 0.0,
        "full_tsc_hidden_state_loaded_fraction": sum(bool(row["full_tsc_hidden_state_loaded_from_sprsina"]) for row in rows) / len(rows) if rows else 0.0,
        "controller_checkpoint_loaded_count": sum(bool(row["controller_checkpoint_loaded"]) for row in rows),
        "restart_initial_visible_exact_fraction": sum(bool(row["restart_initial_visible_exact"]) for row in rows) / len(rows) if rows else 0.0,
        "restart_initial_wire_exact_fraction": sum(bool(row["restart_initial_wire_exact"]) for row in rows) / len(rows) if rows else 0.0,
        "restart_visible_suffix_exact_fraction": sum(bool(row["restart_visible_suffix_exact"]) for row in rows) / len(rows) if rows else 0.0,
        "restart_wire_suffix_exact_fraction": sum(bool(row["restart_wire_suffix_exact"]) for row in rows) / len(rows) if rows else 0.0,
        "restart_source_action_exact_fraction": sum(bool(row["restart_source_actions_exact"]) for row in rows) / len(rows) if rows else 0.0,
        "maximum_restart_visible_abs_difference": max((_as_float(row["restart_visible_maximum_abs_difference"], math.inf) for row in rows), default=math.inf),
        "maximum_restart_wire_abs_difference": max((_as_float(row["restart_wire_maximum_abs_difference"], math.inf) for row in rows), default=math.inf),
        "maximum_restart_action_abs_difference": max((_as_float(row["restart_action_maximum_abs_difference"], math.inf) for row in rows), default=math.inf),
        "recombined_visible_exact_fraction": sum(bool(row["recombined_visible_exact_to_source"]) for row in rows) / len(rows) if rows else 0.0,
        "plant_restart_fidelity_pass_fraction": plant_fraction,
        "formal_contract_preservation_fraction": formal_fraction,
        "minimum_formal_signed_margin": minimum.get("formal_minimum_signed_margin"),
        "minimum_margin_case": {
            "target_id": minimum.get("target_id"),
            "actual_delay_steps": minimum.get("actual_delay_steps"),
            "actual_slew_scale": minimum.get("actual_slew_scale"),
        } if minimum else {},
        "plant_restart_fidelity_passed": bool(plant_fraction == 1.0),
        "formal_contract_preserved": bool(formal_fraction == 1.0),
        "passed": False,
    }
    summary["passed"] = bool(
        summary["coverage_complete"]
        and summary["environment_success_count"] == expected
        and summary["fresh_restart_actor_fraction"] == 1.0
        and summary["full_tsc_hidden_state_loaded_fraction"] == 1.0
        and summary["controller_checkpoint_loaded_count"] == 0
        and summary["restart_initial_visible_exact_fraction"] == 1.0
        and summary["restart_initial_wire_exact_fraction"] == 1.0
        and summary["restart_visible_suffix_exact_fraction"] == 1.0
        and summary["restart_wire_suffix_exact_fraction"] == 1.0
        and summary["restart_source_action_exact_fraction"] == 1.0
        and summary["maximum_restart_visible_abs_difference"] == 0.0
        and summary["maximum_restart_wire_abs_difference"] == 0.0
        and summary["maximum_restart_action_abs_difference"] == 0.0
        and summary["recombined_visible_exact_fraction"] == 1.0
        and summary["plant_restart_fidelity_pass_fraction"] == 1.0
        and summary["formal_contract_preservation_fraction"] == 1.0
        and all(bool(row["passed"]) for row in rows)
    )
    write_csv(ctx.paths.restart / "results.csv", rows)
    atomic_write_json(ctx.paths.restart / "results.json", rows)
    atomic_write_json(ctx.paths.restart / "summary.json", summary)
    _update_state(ctx, restart_replay_complete=True, restart_replay_summary=summary)
    return summary


def run_restart(ctx: Stage42R1Context, *, backend: str, resume: bool) -> dict[str, Any]:
    specs = build_restart_specs(ctx)
    results = _evaluate_restart_specs(ctx, specs, backend=backend, resume=resume)
    return _summarize_restart(ctx, results)


def analyze(
    ctx: Stage42R1Context,
    *,
    source_audit: Mapping[str, Any] | None = None,
    capture: Mapping[str, Any] | None = None,
    restart: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    source_audit = dict(source_audit or (read_json(ctx.paths.source_audit / "summary.json") if (ctx.paths.source_audit / "summary.json").is_file() else {}))
    capture = dict(capture or (read_json(ctx.paths.capture / "summary.json") if (ctx.paths.capture / "summary.json").is_file() else {}))
    restart = dict(restart or (read_json(ctx.paths.restart / "summary.json") if (ctx.paths.restart / "summary.json").is_file() else {}))
    source_pass = bool(source_audit.get("passed"))
    capture_pass = bool(capture.get("passed"))
    restart_pass = bool(restart.get("passed"))
    primary_pass = bool(source_pass and capture_pass and restart_pass)
    verdict = {
        "schema_version": 1,
        "stage": STAGE,
        "verdict": (
            "STAGE4_2R1_TRUE_TSC_PLANT_RESTART_ACTION_REPLAY_CERTIFIED"
            if primary_pass
            else "STAGE4_2R1_TRUE_TSC_PLANT_RESTART_ACTION_REPLAY_INCOMPLETE"
        ),
        "source_stage4_1r17_run": str(ctx.source_stage41r17_run),
        "source_audit_status": "passed" if source_pass else "failed",
        "plant_checkpoint_capture_status": "passed" if capture_pass else ("failed" if capture else "not_run"),
        "plant_restart_replay_status": "passed" if restart_pass else ("failed" if restart else "not_run"),
        "checkpoint_step": CHECKPOINT_STEP,
        "checkpoint_elapsed_ms": CHECKPOINT_STEP * DT_MS,
        "true_filesystem_tsc_restart_performed": bool(restart),
        "plant_restart_fidelity_passed": bool(restart.get("plant_restart_fidelity_passed")),
        "formal_contract_preserved": bool(restart.get("formal_contract_preserved")),
        "original_250_350_and_270_370_timing_unchanged": True,
        "controller_checkpoint_replay_validated": False,
        "cold_controller_restart_validated": False,
        "unseen_hidden_history_generalization_validated": False,
        "unseen_target_generalization_validated": False,
        "plant_parameter_robustness_validated": False,
        "continuous_parameter_change_validated": False,
        "measurement_noise_robustness_validated": False,
        "disturbance_recovery_validated": False,
        "deployment_robustness_validated": False,
        "finite_test_envelope_only": True,
        "primary_pass": primary_pass,
        "warning": (
            "Stage4.2R1 certifies only authentic TSC plant-state serialization and exact action-replay "
            "restart for the same finite clean 18-case R17 expert. It deliberately does not replay or "
            "reconstruct controller observer/integrator/queue state, and it does not validate unseen hidden "
            "histories, new targets, plant error, continuous actuator changes, noise, disturbances or deployment."
        ),
        "next_if_pass": (
            "Proceed to Stage4.2R2 persistent controller-checkpoint replay on the certified plant restart bank, "
            "then construct matched-visible/different-hidden-history tests. Do not start BC/DAgger/RL yet."
        ),
        "next_if_fail": (
            "Separate snapshot-file, full-wire-state, action-replay and formal-margin failures. Fix TSC plant "
            "serialization/restart fidelity before testing controller-state reconstruction; do not relax timing gates."
        ),
        "final_task": ctx.cfg["final_task"],
    }
    summary = {
        **verdict,
        "created_utc": utc_timestamp(),
        "phases": {
            "source_audit": source_audit,
            "plant_checkpoint_capture": capture,
            "plant_restart_replay": restart,
        },
    }
    atomic_write_json(ctx.paths.analysis / "stage4_2r1_verdict.json", verdict)
    atomic_write_json(ctx.paths.analysis / "stage4_2r1_summary.json", summary)
    stop_reason = "" if primary_pass else (
        "source_audit_failed" if not source_pass else "plant_checkpoint_capture_failed" if not capture_pass else "plant_restart_replay_failed"
    )
    _update_state(ctx, finished=True, stop_reason=stop_reason, primary_pass=primary_pass, verdict=verdict)
    return summary


def execute(ctx: Stage42R1Context, *, command: str, backend: str, resume: bool) -> dict[str, Any]:
    prepare(ctx, resume=resume)
    source_summary = run_source_audit(ctx)
    if command == "audit" or not source_summary.get("passed"):
        return analyze(ctx, source_audit=source_summary)
    capture_summary = run_capture(ctx, backend=backend, resume=resume)
    if command == "capture" or not capture_summary.get("passed"):
        return analyze(ctx, source_audit=source_summary, capture=capture_summary)
    restart_summary = run_restart(ctx, backend=backend, resume=resume)
    return analyze(ctx, source_audit=source_summary, capture=capture_summary, restart=restart_summary)


def self_test() -> dict[str, Any]:
    synthetic_states = []
    for step in range(WEAK_HORIZON + 1):
        synthetic_states.append(
            {
                "step_index": step,
                "time_ms": 1100 + step * 10,
                "R": 0.75 + step * 1e-6,
                "Z": -step * 1e-6,
                "Ip": 29779.724 + step,
                "vessel_current_total_a": float(step),
                "vessel_current_abs_sum_a": float(step + 1),
                "vessel_current_rms_a": float(step + 2),
                "vessel_current_max_abs_a": float(step + 3),
                "currents_a_tsc": [float(step)] * N_COILS,
                "currents_a_display": [float(step)] * N_COILS,
                "action_norm_tsc": ([0.0] * N_COILS if step == 0 else [step / 1000.0] * N_COILS),
                "action_norm_display": ([0.0] * N_COILS if step == 0 else [step / 1000.0] * N_COILS),
                "wire_currents_a": [float(step), -float(step), 0.5 * float(step)],
                "wire_current_count": 3,
                "abnormal": False,
            }
        )
    synthetic = {"trajectory": synthetic_states}
    actions = _source_action_sequence(synthetic, horizon=WEAK_HORIZON)
    action_ok = bool(len(actions) == WEAK_HORIZON and np.array_equal(np.asarray(actions[0]), np.asarray(synthetic_states[1]["action_norm_tsc"])))
    visible = _visible_array(synthetic)
    wire = _wire_array(synthetic)
    comparison = _compare_arrays(visible, visible, atol=1e-12)
    prefix = copy.deepcopy(synthetic_states[:CHECKPOINT_STEP])
    suffix = copy.deepcopy(synthetic_states[CHECKPOINT_STEP:])
    recombined = prefix + suffix
    recombination_ok = bool(len(recombined) == WEAK_HORIZON + 1 and recombined == synthetic_states)
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        required = ["inputa", "sprsina", "geqdsk", "outputa", "coil_currents.csv", "wire_currents.csv"]
        for name in required:
            (root / name).write_text("x\n", encoding="utf-8")
        cfg = {"required_snapshot_files": required, "optional_snapshot_files": []}
        inventory = _snapshot_file_inventory(root, cfg)
        inventory_ok = bool(inventory["passed"] and _validate_snapshot_inventory(root, inventory))
        (root / "sprsina").write_text("tampered\n", encoding="utf-8")
        tamper_detected = not _validate_snapshot_inventory(root, inventory)
    return {
        "schema_version": 1,
        "stage": STAGE,
        "controller_revision": CONTROLLER_REVISION,
        "package_revision": PACKAGE_REVISION,
        "passed": bool(
            action_ok
            and visible.shape == (WEAK_HORIZON + 1, 35)
            and wire.shape == (WEAK_HORIZON + 1, 3)
            and comparison["exact"]
            and recombination_ok
            and inventory_ok
            and tamper_detected
        ),
        "source_action_transition_mapping_passed": action_ok,
        "visible_state_width": int(visible.shape[1]),
        "full_wire_vector_preserved": bool(wire.shape[1] == 3),
        "exact_array_comparison_passed": comparison["exact"],
        "prefix_suffix_recombination_passed": recombination_ok,
        "snapshot_inventory_passed": inventory_ok,
        "snapshot_tamper_detected": tamper_detected,
        "checkpoint_step": CHECKPOINT_STEP,
        "expected_capture_rollouts": 18,
        "expected_restart_rollouts": 18,
        "maximum_true_tsc_rollouts": 36,
        "plant_restart_only": True,
        "controller_checkpoint_replay_validated": False,
    }


def _set_resource_limits() -> None:
    try:
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    except Exception:
        pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage4.2R1 true TSC plant restart action replay")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--source-stage4-1r17-run", type=Path)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--command", choices=("all", "audit", "capture", "restart"), default="all")
    parser.add_argument("--backend", choices=("ray", "serial"), default="ray")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    _set_resource_limits()
    if args.self_test:
        print(json.dumps(self_test(), indent=2, sort_keys=True))
        return
    missing = [
        name
        for name, value in (
            ("--config", args.config),
            ("--source-stage4-1r17-run", args.source_stage4_1r17_run),
            ("--run-dir", args.run_dir),
        )
        if value is None
    ]
    if missing:
        parser.error("the following arguments are required unless --self-test is used: " + ", ".join(missing))
    ctx = load_stage42r1_config(
        args.config,
        source_stage41r17_run=args.source_stage4_1r17_run,
        run_dir_override=args.run_dir,
    )
    payload = execute(ctx, command=args.command, backend=args.backend, resume=args.resume)
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
