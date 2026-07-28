"""Stage4.1R9 terminal-template MPC feedback hold validation.

Stage4.1R8 established two narrow facts in the finite digital-twin envelope:
trusted pair-level delay/slew calibration works on the 3x3 static bank, while an
open-loop "drain pending then zero increment" tail does not stabilize the plant.

R9 keeps the first 350 ms controller, observer, Stage3.4 target library and
175x105 real-TSC Jacobian frozen.  It changes only the post-350 ms architecture:
a continuously streaming, explicit-delay-queue terminal MPC reuses late-phase
Jacobian templates and closes feedback on measured R/Z/Ip and finite-difference
R/Z velocity.  Candidate policies are selected only on the nominal target and
then evaluated on a disjoint shifted-target holdout before trusted R8
calibration tokens are used for exact paired confirmation.

This remains a finite static digital-twin validation.  It is not true restart,
hardware pre-shot calibration, continuous parameter-change, plant-mismatch, or
deployment qualification.
"""
from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
import json
import math
import os
import resource
import shutil
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

from . import stage2_trajectory_optimization as s2
from . import stage4_1r3_control_aware_robustness as r3
from . import stage4_1r8_trusted_batch_calibration_queue_tail_closure as r8
from tsc_rzip_rllib.utils.ray_runtime import ensure_ray_worker_plan

atomic_write_json = r8.atomic_write_json
atomic_write_json_gz = r8.atomic_write_json_gz
read_json = r8.read_json
read_json_gz = r8.read_json_gz
utc_timestamp = r8.utc_timestamp
write_csv = r8.write_csv

SCHEMA_VERSION = 1
STAGE = "Stage4.1R9"
CONTROLLER_REVISION = "terminal_template_mpc_feedback_hold_v9"
EXPECTED_SOURCE_REVISION = "trusted_batch_calibration_queue_tail_closure_v8"
PACKAGE_REVISION = "r9_terminal_template_feedback_hold_v1"
MAIN_CONTROL_STEPS = 35
N_MODES = 3


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------


def _json_safe(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return [_json_safe(item) for item in value.tolist()]
    if isinstance(value, np.generic):
        return _json_safe(value.item())
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return bool(default)
    return bool(value)


def _as_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or isinstance(value, bool):
            return int(default)
        return int(value)
    except (TypeError, ValueError, OverflowError):
        return int(default)


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or isinstance(value, bool):
            return float(default)
        number = float(value)
        return number if math.isfinite(number) else float(default)
    except (TypeError, ValueError, OverflowError):
        return float(default)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _scenario_digest(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(
        _json_safe(dict(payload)),
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return "s41r9_" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:20]


def _array_digest(array: np.ndarray, prefix: str) -> str:
    arr = np.ascontiguousarray(np.asarray(array, dtype=np.float64))
    header = json.dumps(
        {"shape": arr.shape, "dtype": str(arr.dtype)}, sort_keys=True
    ).encode("utf-8")
    return f"{prefix}_" + hashlib.sha256(header + arr.tobytes()).hexdigest()[:20]


def _result_complete(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        payload = read_json_gz(path)
    except Exception:
        return False
    return bool(payload.get("success"))


def _available_memory_gb() -> float:
    try:
        with Path("/proc/meminfo").open("r", encoding="utf-8") as handle:
            fields = {
                row.split(":", 1)[0]: row.split(":", 1)[1].strip()
                for row in handle
                if ":" in row
            }
        return float(fields["MemAvailable"].split()[0]) / (1024.0 * 1024.0)
    except Exception:
        return math.inf


def _copy_json_payload(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Paths and source validation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Stage41R9Paths:
    run_dir: Path
    source_reference: Path
    source_audit: Path
    oracle_development: Path
    oracle_holdout: Path
    calibrated_confirmation: Path
    restart_audit: Path
    analysis: Path
    variants: Path
    state: Path
    manifest: Path

    @classmethod
    def from_run_dir(cls, run_dir: Path) -> "Stage41R9Paths":
        run_dir = run_dir.expanduser().resolve()
        return cls(
            run_dir=run_dir,
            source_reference=run_dir / "stage4_1r9_source_reference",
            source_audit=run_dir / "stage4_1r9_source_audit",
            oracle_development=run_dir / "stage4_1r9_oracle_development",
            oracle_holdout=run_dir / "stage4_1r9_oracle_holdout",
            calibrated_confirmation=run_dir / "stage4_1r9_calibrated_confirmation",
            restart_audit=run_dir / "stage4_1r9_restart_audit",
            analysis=run_dir / "stage4_1r9_analysis",
            variants=run_dir / "stage4_1r9_environment_variants",
            state=run_dir / "stage4_1r9_state.json",
            manifest=run_dir / "stage4_1r9_manifest.json",
        )


@dataclass
class Stage41R9Context:
    cfg: dict[str, Any]
    paths: Stage41R9Paths
    project_dir: Path
    source_stage41r8_run: Path
    source_manifest: dict[str, Any]
    source_state: dict[str, Any]
    source_cfg: dict[str, Any]
    source_verdict: dict[str, Any]
    source_stage41r7_run: Path
    r8_ctx: r8.Stage41R8Context
    source_fingerprint: dict[str, Any]


def _required_source_files(source: Path) -> list[Path]:
    required = [
        source / "stage4_1r8_manifest.json",
        source / "stage4_1r8_state.json",
        source / "stage4_1r8_config.resolved.json",
        source / "stage4_1r8_analysis" / "stage4_1r8_verdict.json",
        source / "stage4_1r8_source_audit" / "summary.json",
        source / "stage4_1r8_batch_source_replay" / "summary.json",
        source / "stage4_1r8_integrated_calibration" / "summary.json",
        source / "stage4_1r8_integrated_calibration" / "results.json",
        source / "stage4_1r8_oracle_queue_tail" / "summary.json",
        source / "stage4_1r8_oracle_queue_tail" / "results.json",
    ]
    required.extend(
        sorted((source / "stage4_1r8_integrated_calibration" / "raw").glob("*.json.gz"))
    )
    required.extend(
        sorted((source / "stage4_1r8_oracle_queue_tail" / "raw").glob("*.json.gz"))
    )
    return required


def _source_inventory(source: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    total = 0
    for path in _required_source_files(source):
        if not path.is_file():
            raise FileNotFoundError(f"required Stage4.1R8 source file missing: {path}")
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
        "n_files": len(rows),
        "total_bytes": total,
        "digest": hashlib.sha256(canonical).hexdigest(),
        "files": rows,
    }


def _resolve_recorded_run(project_dir: Path, recorded: str, run_root_name: str) -> Path:
    original = Path(recorded).expanduser()
    if original.is_dir():
        return original.resolve()
    candidate = project_dir / run_root_name / original.name
    if candidate.is_dir():
        return candidate.resolve()
    raise FileNotFoundError(
        f"recorded source run does not exist and no local basename match was found: "
        f"recorded={recorded!r} local={candidate}"
    )


def _validate_source_stage41r8(
    source: Path, cfg: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    source = source.expanduser().resolve()
    for path in _required_source_files(source):
        if not path.is_file():
            raise FileNotFoundError(f"required Stage4.1R8 source file missing: {path}")
    manifest = read_json(source / "stage4_1r8_manifest.json")
    state = read_json(source / "stage4_1r8_state.json")
    source_cfg = read_json(source / "stage4_1r8_config.resolved.json")
    verdict = read_json(source / "stage4_1r8_analysis" / "stage4_1r8_verdict.json")
    requirement = cfg["source_requirement"]
    if manifest.get("stage") != requirement["required_stage"]:
        raise ValueError("source Stage4.1R8 manifest stage mismatch")
    if manifest.get("controller_revision") != requirement["required_controller_revision"]:
        raise ValueError("source Stage4.1R8 controller revision mismatch")
    if source_cfg.get("controller_revision") != EXPECTED_SOURCE_REVISION:
        raise ValueError("source Stage4.1R8 resolved config revision mismatch")
    if bool(requirement.get("require_finished", True)) and not bool(state.get("finished")):
        raise ValueError("source Stage4.1R8 is not finished")
    required_stop = str(requirement.get("require_stop_reason", ""))
    if required_stop and str(state.get("stop_reason")) != required_stop:
        raise ValueError(
            f"source Stage4.1R8 stop_reason mismatch: "
            f"{state.get('stop_reason')!r} != {required_stop!r}"
        )
    phase_checks = {
        "source_audit_summary": "require_source_audit_passed",
        "source_replay_summary": "require_batch_source_replay_passed",
        "integrated_calibration_summary": "require_integrated_calibration_passed",
    }
    for state_key, requirement_key in phase_checks.items():
        if bool(requirement.get(requirement_key, True)) and not bool(
            (state.get(state_key) or {}).get("passed")
        ):
            raise ValueError(f"source Stage4.1R8 {state_key} did not pass")
    if bool(requirement.get("require_oracle_queue_tail_failed", True)) and bool(
        (state.get("oracle_queue_tail_summary") or {}).get("passed")
    ):
        raise ValueError("R9 expects the source R8 open-loop queue tail to have failed")
    if bool(requirement.get("require_calibrated_startup_not_executed", True)) and bool(
        state.get("calibrated_startup_complete")
    ):
        raise ValueError("R9 source requirement expects calibrated startup not to have run")
    calibration_raw = list(
        (source / "stage4_1r8_integrated_calibration" / "raw").glob("*.json.gz")
    )
    tail_raw = list(
        (source / "stage4_1r8_oracle_queue_tail" / "raw").glob("*.json.gz")
    )
    if len(calibration_raw) != int(requirement["require_raw_integrated_calibration_count"]):
        raise ValueError("source integrated calibration raw count mismatch")
    if len(tail_raw) != int(requirement["require_raw_oracle_queue_tail_count"]):
        raise ValueError("source oracle queue-tail raw count mismatch")
    return manifest, state, source_cfg, verdict


def validate_config(cfg: Mapping[str, Any]) -> None:
    if cfg.get("controller_revision") != CONTROLLER_REVISION:
        raise ValueError("Stage4.1R9 controller_revision mismatch")
    gate = cfg["gate"]
    if not math.isclose(float(gate["precise_tolerance_m"]), 0.03, abs_tol=1e-15):
        raise ValueError("R9 may not weaken the 30 mm position gate")
    if not math.isclose(
        float(gate["terminal_velocity_max_m_per_s"]), 0.1, abs_tol=1e-15
    ):
        raise ValueError("R9 may not weaken the 0.1 m/s terminal speed gate")
    terminal = cfg["terminal_feedback"]
    if int(terminal["main_control_steps"]) != MAIN_CONTROL_STEPS:
        raise ValueError("R9 must freeze the first 35 main-control steps")
    horizon = int(terminal["horizon_steps"])
    tail = int(terminal["tail_feedback_steps"])
    if horizon != MAIN_CONTROL_STEPS + tail:
        raise ValueError("terminal horizon must equal 35 + tail_feedback_steps")
    delays = [int(value) for value in terminal["actual_delay_steps"]]
    slews = [float(value) for value in terminal["actual_slew_scales"]]
    if delays != [0, 1, 2] or slews != [0.9, 1.0, 1.1]:
        raise ValueError("R9 finite actuator bank must remain the frozen 3x3 grid")
    candidates = list(terminal["candidate_bank"])
    if len(candidates) < 2:
        raise ValueError("terminal candidate bank must contain at least two policies")
    ids = [str(row["policy_id"]) for row in candidates]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate terminal policy_id")
    max_delay = max(delays)
    for row in candidates:
        template = int(row["template_step"])
        if template < 0 or template + max_delay >= MAIN_CONTROL_STEPS:
            raise ValueError(
                f"template_step={template} leaves no free delayed terminal action"
            )
        if float(row["controller_scale"]) <= 0.0:
            raise ValueError("terminal controller_scale must be positive")
        if float(row["velocity_measurement_gain"]) <= 0.0:
            raise ValueError("terminal velocity gain must be positive")
    development = terminal["development_target"]
    holdout = terminal["holdout_target"]
    if str(development["target_id"]) == str(holdout["target_id"]):
        raise ValueError("development and holdout targets must be disjoint")
    if cfg["calibrated_confirmation"].get("online_handover_enabled"):
        raise ValueError("R9 primary confirmation must not use online handover")
    if not bool(cfg.get("finite_test_envelope_only", False)):
        raise ValueError("R9 must remain explicitly finite-envelope only")


def load_stage41r9_config(
    config_path: Path,
    *,
    source_stage41r8_run: Path,
    run_dir_override: Path | None = None,
) -> Stage41R9Context:
    config_path = config_path.expanduser().resolve()
    cfg = read_json(config_path)
    validate_config(cfg)
    project_dir = config_path.parents[1]
    source_stage41r8_run = source_stage41r8_run.expanduser().resolve()
    manifest, state, source_cfg, verdict = _validate_source_stage41r8(
        source_stage41r8_run, cfg
    )
    source_stage41r7_run = _resolve_recorded_run(
        project_dir, str(manifest["source_stage4_1r7_run"]), "stage4_1r7_runs"
    )
    if run_dir_override is None:
        root = project_dir / str(cfg.get("output_root", "stage4_1r9_runs"))
        run_dir = root / f"{cfg.get('run_name', 'stage4_1r9')}_{utc_timestamp()}"
    else:
        run_dir = run_dir_override.expanduser().resolve()
    paths = Stage41R9Paths.from_run_dir(run_dir)

    # R8 is loaded only as the complete frozen dependency chain that resolves
    # R7/R6/R5/R4/R3, the source library and the real 175x105 Jacobian.
    r8_config_path = project_dir / "configs" / "stage4_1r8_trusted_batch_calibration_queue_tail_closure_410ms.json"
    if not r8_config_path.is_file():
        raise FileNotFoundError(f"packaged R8 dependency config missing: {r8_config_path}")
    r8_ctx = r8.load_stage41r8_config(
        r8_config_path,
        source_stage41r7_run=source_stage41r7_run,
        run_dir_override=run_dir,
    )
    storage = cfg["storage"]
    env_cfg = copy.deepcopy(
        r8_ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.source_env_cfg
    )
    env_cfg["tsc_timeout_s"] = float(cfg["runtime"]["tsc_timeout_s"])
    env_cfg["tsc_workspace_root"] = str(
        Path(
            os.environ.get(
                "STAGE4_1R9_TSC_WORKSPACE_ROOT", storage["tsc_workspace_root"]
            )
        )
        .expanduser()
        .resolve()
    )
    env_cfg["run_root"] = str(
        Path(
            os.environ.get("STAGE4_1R9_TSC_RUN_ROOT", storage["tsc_run_root"])
        )
        .expanduser()
        .resolve()
    )
    env_cfg["tsc_run_root"] = env_cfg["run_root"]
    env_cfg["keep_tsc_workspace"] = False
    env_cfg["cleanup_episode_dir"] = True
    env_cfg["keep_failed_episode_dir"] = bool(
        storage.get("keep_failed_episode_dir", False)
    )
    env_cfg["keep_last_n_failed_episode_dirs"] = int(
        storage.get("keep_last_n_failed_episode_dirs", 0)
    )
    train_cfg = copy.deepcopy(
        r8_ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.source_train_cfg
    )
    train_cfg["env_config"] = str(paths.run_dir / "env_config.resolved.json")
    base34 = r8_ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.base34
    base34.env_cfg = env_cfg
    base34.train_cfg = train_cfg
    return Stage41R9Context(
        cfg=cfg,
        paths=paths,
        project_dir=project_dir,
        source_stage41r8_run=source_stage41r8_run,
        source_manifest=manifest,
        source_state=state,
        source_cfg=source_cfg,
        source_verdict=verdict,
        source_stage41r7_run=source_stage41r7_run,
        r8_ctx=r8_ctx,
        source_fingerprint=_source_inventory(source_stage41r8_run),
    )


# ---------------------------------------------------------------------------
# Run state, preflight and preparation
# ---------------------------------------------------------------------------


def runtime_preflight(ctx: Stage41R9Context) -> dict[str, Any]:
    requested = int(
        os.environ.get("STAGE4_1R9_WORKERS", ctx.cfg["parallel"]["n_workers"])
    )
    logical = int(os.cpu_count() or 1)
    reserve = int(ctx.cfg["parallel"].get("reserve_logical_cpus", 16))
    ceiling = max(1, logical - reserve)
    if requested > ceiling:
        raise RuntimeError(
            f"Stage4.1R9 requests {requested} workers but safe ceiling is {ceiling} "
            f"({logical} visible, reserve={reserve}); no silent fallback is allowed"
        )
    memory = _available_memory_gb()
    configured = int(ctx.cfg["parallel"]["n_workers"])
    minimum = (
        float(ctx.cfg["parallel"].get("minimum_available_memory_gb", 72.0))
        * requested
        / configured
    )
    if math.isfinite(memory) and memory < minimum:
        raise RuntimeError(
            f"Stage4.1R9 requires {minimum:.1f} GiB available memory; "
            f"{memory:.1f} GiB visible"
        )
    soft_fd, hard_fd = resource.getrlimit(resource.RLIMIT_NOFILE)
    required_fd = max(1024, requested * 16)
    if soft_fd < required_fd:
        raise RuntimeError(
            f"open-file soft limit {soft_fd} is below required {required_fd}"
        )
    return {
        "requested_workers": requested,
        "logical_cpus": logical,
        "reserved_logical_cpus": reserve,
        "safe_worker_ceiling": ceiling,
        "available_memory_gb": None if not math.isfinite(memory) else memory,
        "open_file_soft_limit": soft_fd,
        "open_file_hard_limit": hard_fd,
    }


def initial_state() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "controller_revision": CONTROLLER_REVISION,
        "prepared": True,
        "source_audit_complete": False,
        "oracle_development_complete": False,
        "oracle_holdout_complete": False,
        "calibrated_confirmation_complete": False,
        "restart_audit_complete": False,
        "finished": False,
        "stop_reason": "",
        "updated_utc": utc_timestamp(),
    }


def _update_state(ctx: Stage41R9Context, **values: Any) -> dict[str, Any]:
    state = read_json(ctx.paths.state) if ctx.paths.state.exists() else initial_state()
    state.update(_json_safe(values))
    state["updated_utc"] = utc_timestamp()
    atomic_write_json(ctx.paths.state, state)
    return state


def initialize_run(ctx: Stage41R9Context, preflight: Mapping[str, Any]) -> None:
    for path in (
        ctx.paths.run_dir,
        ctx.paths.source_reference,
        ctx.paths.source_audit,
        ctx.paths.oracle_development,
        ctx.paths.oracle_holdout,
        ctx.paths.calibrated_confirmation,
        ctx.paths.restart_audit,
        ctx.paths.analysis,
        ctx.paths.variants,
    ):
        path.mkdir(parents=True, exist_ok=True)
    atomic_write_json(
        ctx.paths.run_dir / "stage4_1r9_config.resolved.json", ctx.cfg
    )
    atomic_write_json(
        ctx.paths.run_dir / "env_config.resolved.json",
        ctx.r8_ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.source_env_cfg,
    )
    atomic_write_json(
        ctx.paths.run_dir / "train_config.resolved.json",
        ctx.r8_ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.source_train_cfg,
    )
    reference_files = {
        "stage4_1r8_manifest.json": ctx.source_manifest,
        "stage4_1r8_state.json": ctx.source_state,
        "stage4_1r8_config.resolved.json": ctx.source_cfg,
        "stage4_1r8_verdict.json": ctx.source_verdict,
        "source_content_inventory.json": ctx.source_fingerprint,
    }
    for name, payload in reference_files.items():
        atomic_write_json(ctx.paths.source_reference / name, payload)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "controller_revision": CONTROLLER_REVISION,
        "package_revision": PACKAGE_REVISION,
        "created_utc": utc_timestamp(),
        "source_stage4_1r8_run": str(ctx.source_stage41r8_run),
        "source_stage4_1r7_run": str(ctx.source_stage41r7_run),
        "source_fingerprint": ctx.source_fingerprint,
        "workers": dict(preflight),
        "first_350ms_main_controller_changed": False,
        "observer_changed_in_first_350ms": False,
        "target_library_changed": False,
        "jacobian_changed": False,
        "post_350ms_terminal_feedback_added": True,
        "terminal_queue_semantics": "continuous_streaming_explicit_delay_queue",
        "candidate_selection_target": ctx.cfg["terminal_feedback"][
            "development_target"
        ]["target_id"],
        "disjoint_holdout_target": ctx.cfg["terminal_feedback"]["holdout_target"][
            "target_id"
        ],
        "finite_test_envelope_only": True,
        "hardware_pre_shot_calibration_validated": False,
        "true_restart_validation_performed": False,
        "continuous_parameter_change_validated": False,
        "deployment_robustness_validated": False,
        "final_task": ctx.cfg["final_task"],
    }
    if ctx.paths.manifest.exists():
        old = read_json(ctx.paths.manifest)
        for key in (
            "controller_revision",
            "source_stage4_1r8_run",
            "source_fingerprint",
        ):
            if old.get(key) != manifest.get(key):
                raise ValueError(f"resume manifest mismatch for {key}")
    else:
        atomic_write_json(ctx.paths.manifest, manifest)
    if not ctx.paths.state.exists():
        atomic_write_json(ctx.paths.state, initial_state())


def prepare(ctx: Stage41R9Context) -> dict[str, Any]:
    preflight = runtime_preflight(ctx)
    initialize_run(ctx, preflight)
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "run_dir": str(ctx.paths.run_dir),
        "source_stage4_1r8_run": str(ctx.source_stage41r8_run),
        "source_fingerprint_digest": ctx.source_fingerprint["digest"],
        "preflight": preflight,
        "prepared": True,
    }


# ---------------------------------------------------------------------------
# Source R8 forensic audit
# ---------------------------------------------------------------------------


def _physics_prefix(result: Mapping[str, Any], state_count: int = 36) -> np.ndarray:
    trajectory = list(result.get("trajectory") or [])[:state_count]
    return np.asarray(
        [
            [
                row["R"],
                row["Z"],
                row["Ip"],
                *row["currents_a_tsc"],
                *row["action_norm_tsc"],
            ]
            for row in trajectory
        ],
        dtype=float,
    )


def _issued_prefix(result: Mapping[str, Any], count: int = 35) -> np.ndarray:
    return np.asarray(
        [
            row.get("issued_mode_coefficients", [0.0, 0.0, 0.0])
            for row in list(result.get("control_trace") or [])[:count]
        ],
        dtype=float,
    )


def _speed_at_state(trajectory: Sequence[Mapping[str, Any]], index: int, dt_s: float) -> float:
    if index <= 0 or index >= len(trajectory):
        return math.nan
    d_r = float(trajectory[index]["R"]) - float(trajectory[index - 1]["R"])
    d_z = float(trajectory[index]["Z"]) - float(trajectory[index - 1]["Z"])
    return math.hypot(d_r, d_z) / max(float(dt_s), 1e-12)


def _best_endpoint_evaluation(row: Mapping[str, Any]) -> Mapping[str, Any]:
    target = _as_int(row.get("stage3_4_best_endpoint_step"), -1)
    evaluations = list(row.get("stage3_4_endpoint_evaluations") or [])
    for evaluation in evaluations:
        if _as_int(evaluation.get("endpoint_step"), -2) == target:
            return evaluation
    if evaluations:
        return min(
            evaluations,
            key=lambda item: _as_float(item.get("minimum_signed_margin"), -1e12),
        )
    return {}


def _source_tail_raw_by_key(ctx: Stage41R9Context) -> dict[tuple[str, str, int, float], dict[str, Any]]:
    output: dict[tuple[str, str, int, float], dict[str, Any]] = {}
    for path in sorted(
        (ctx.source_stage41r8_run / "stage4_1r8_oracle_queue_tail" / "raw").glob(
            "*.json.gz"
        )
    ):
        result = read_json_gz(path)
        spec = result["spec"]
        key = (
            str(spec["queue_tail_policy_id"]),
            str(spec["target_id"]),
            int(spec["action_delay_steps"]),
            float(spec["slew_scale"]),
        )
        if key in output:
            raise ValueError(f"duplicate R8 source tail raw case: {key}")
        output[key] = result
    return output


def _source_h41_by_case(ctx: Stage41R9Context) -> dict[tuple[str, int, float], dict[str, Any]]:
    raw = _source_tail_raw_by_key(ctx)
    return {
        (target, delay, slew): result
        for (policy, target, delay, slew), result in raw.items()
        if policy == "drain_pending_h41"
    }


def source_calibration_tokens(
    ctx: Stage41R9Context,
) -> dict[tuple[int, float], dict[str, Any]]:
    rows = read_json(
        ctx.source_stage41r8_run
        / "stage4_1r8_integrated_calibration"
        / "results.json"
    )
    output: dict[tuple[int, float], dict[str, Any]] = {}
    for row in rows:
        key = (int(row["actual_delay_steps"]), float(row["actual_slew_scale"]))
        if key in output:
            raise ValueError(f"duplicate Stage4.1R8 calibration token: {key}")
        output[key] = copy.deepcopy(row)
    return output


def run_source_audit(ctx: Stage41R9Context) -> dict[str, Any]:
    source_state = ctx.source_state
    source_results = read_json(
        ctx.source_stage41r8_run
        / "stage4_1r8_oracle_queue_tail"
        / "results.json"
    )
    raw_by_key = _source_tail_raw_by_key(ctx)
    policies = ("drain_pending_h37", "drain_pending_h39", "drain_pending_h41")
    targets = ("nominal", "RZ_p10_m10")
    expected_cases = {
        (policy, target, delay, slew)
        for policy in policies
        for target in targets
        for delay in (0, 1, 2)
        for slew in (0.9, 1.0, 1.1)
    }
    raw_coverage = set(raw_by_key) == expected_cases and len(raw_by_key) == 54
    raw_success = all(bool(row.get("success")) for row in raw_by_key.values())
    raw_abnormal_count = sum(
        any(bool(state.get("abnormal", False)) for state in row.get("trajectory") or [])
        for row in raw_by_key.values()
    )
    raw_failure_reason_count = sum(
        bool(str(row.get("failure_reason", "")).strip()) for row in raw_by_key.values()
    )
    nonfinite_count = 0
    for result in raw_by_key.values():
        for state in result.get("trajectory") or []:
            numeric = [state.get("R"), state.get("Z"), state.get("Ip")]
            numeric.extend(state.get("currents_a_tsc") or [])
            if any(not math.isfinite(float(value)) for value in numeric):
                nonfinite_count += 1
                break

    policy_recomputed: list[dict[str, Any]] = []
    for policy in policies:
        subset = [row for row in source_results if row.get("policy_id") == policy]
        policy_recomputed.append(
            {
                "policy_id": policy,
                "n_rollouts": len(subset),
                "tracking_fraction": sum(
                    bool(row.get("stage3_4_target_tracking_pass")) for row in subset
                )
                / max(len(subset), 1),
                "minimum_signed_margin": min(
                    (
                        _as_float(
                            row.get("stage3_4_tracking_minimum_signed_margin"),
                            -1e12,
                        )
                        for row in subset
                    ),
                    default=-1e12,
                ),
            }
        )

    prefix_exact = True
    prefix_numeric_max = 0.0
    prefix_comparisons = 0
    for target in targets:
        for delay in (0, 1, 2):
            for slew in (0.9, 1.0, 1.1):
                reference = raw_by_key[
                    ("drain_pending_h41", target, delay, slew)
                ]
                ref_physics = _physics_prefix(reference)
                ref_issued = _issued_prefix(reference)
                for policy in ("drain_pending_h37", "drain_pending_h39"):
                    candidate = raw_by_key[(policy, target, delay, slew)]
                    arrays = (
                        (_physics_prefix(candidate), ref_physics),
                        (_issued_prefix(candidate), ref_issued),
                    )
                    for left, right in arrays:
                        prefix_comparisons += 1
                        if left.shape != right.shape:
                            prefix_exact = False
                            prefix_numeric_max = math.inf
                        else:
                            prefix_exact = bool(prefix_exact and np.array_equal(left, right))
                            if left.size:
                                prefix_numeric_max = max(
                                    prefix_numeric_max,
                                    float(np.max(np.abs(left - right))),
                                )

    failed_rows = [
        row for row in source_results
        if not bool(row.get("stage3_4_target_tracking_pass"))
    ]
    final_speed_limited = 0
    limiting_rows: list[dict[str, Any]] = []
    for row in failed_rows:
        evaluation = _best_endpoint_evaluation(row)
        margins = {
            "position": _as_float(evaluation.get("position_signed_margin"), math.inf),
            "endpoint_speed": _as_float(
                evaluation.get("endpoint_speed_signed_margin"), math.inf
            ),
            "endpoint_late_speed": _as_float(
                evaluation.get("endpoint_late_speed_signed_margin"), math.inf
            ),
            "post_speed": _as_float(
                evaluation.get("post_speed_signed_margin"), math.inf
            ),
            "final_speed": _as_float(
                evaluation.get("final_speed_signed_margin"), math.inf
            ),
            "ip": _as_float(evaluation.get("ip_signed_margin"), math.inf),
        }
        limiting = min(margins, key=margins.get)
        if limiting == "final_speed":
            final_speed_limited += 1
        limiting_rows.append(
            {
                "policy_id": row["policy_id"],
                "target_id": row["target_id"],
                "actual_delay_steps": row["actual_action_delay_steps"],
                "actual_slew_scale": row["actual_slew_scale"],
                "limiting_metric": limiting,
                "minimum_signed_margin": margins[limiting],
                "final_speed_m_per_s": row.get("stage3_4_final_velocity_m_per_s"),
            }
        )

    dt_s = float(ctx.cfg["terminal_feedback"]["dt_s"])
    speed_growth: list[dict[str, Any]] = []
    for (policy, target, delay, slew), result in sorted(raw_by_key.items()):
        if policy != "drain_pending_h41":
            continue
        trajectory = result["trajectory"]
        speed_growth.append(
            {
                "target_id": target,
                "actual_delay_steps": delay,
                "actual_slew_scale": slew,
                "speed_350ms_m_per_s": _speed_at_state(trajectory, 35, dt_s),
                "speed_370ms_m_per_s": _speed_at_state(trajectory, 37, dt_s),
                "speed_390ms_m_per_s": _speed_at_state(trajectory, 39, dt_s),
                "speed_410ms_m_per_s": _speed_at_state(trajectory, 41, dt_s),
            }
        )

    tokens = source_calibration_tokens(ctx)
    expected_tokens = {
        (delay, slew)
        for delay in (0, 1, 2)
        for slew in (0.9, 1.0, 1.1)
    }
    token_coverage = set(tokens) == expected_tokens and len(tokens) == 9
    all_tokens_trusted = token_coverage and all(
        bool(row.get("success"))
        and bool(row.get("batch_trusted"))
        and bool(row.get("batch_trusted_correct"))
        and not bool(row.get("batch_wrong_accept"))
        and int(row.get("batch_selected_delay_steps")) == key[0]
        and math.isclose(
            float(row.get("batch_selected_slew_scale")),
            key[1],
            abs_tol=1e-12,
        )
        for key, row in tokens.items()
    )

    source_summary = source_state.get("oracle_queue_tail_summary") or {}
    source_policy_map = {
        row["policy_id"]: row
        for row in source_summary.get("policy_summaries") or []
    }
    summary_match = all(
        policy in source_policy_map
        and math.isclose(
            recomputed["tracking_fraction"],
            float(source_policy_map[policy]["tracking_fraction"]),
            abs_tol=1e-15,
        )
        and math.isclose(
            recomputed["minimum_signed_margin"],
            float(source_policy_map[policy]["minimum_signed_margin"]),
            abs_tol=1e-12,
        )
        for policy, recomputed in (
            (row["policy_id"], row) for row in policy_recomputed
        )
    )
    passed = bool(
        raw_coverage
        and raw_success
        and raw_abnormal_count == 0
        and raw_failure_reason_count == 0
        and nonfinite_count == 0
        and prefix_exact
        and prefix_numeric_max == 0.0
        and len(failed_rows) == 47
        and final_speed_limited == len(failed_rows)
        and summary_match
        and token_coverage
        and all_tokens_trusted
        and bool((source_state.get("source_audit_summary") or {}).get("passed"))
        and bool((source_state.get("source_replay_summary") or {}).get("passed"))
        and bool(
            (source_state.get("integrated_calibration_summary") or {}).get("passed")
        )
        and not bool(
            (source_state.get("oracle_queue_tail_summary") or {}).get("passed")
        )
        and not bool(source_state.get("calibrated_startup_complete"))
    )
    summary = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "phase": "source_audit",
        "source_stage4_1r8_run": str(ctx.source_stage41r8_run),
        "source_finished": bool(source_state.get("finished")),
        "source_stop_reason": source_state.get("stop_reason"),
        "raw_tail_rollouts": len(raw_by_key),
        "raw_tail_coverage_complete": raw_coverage,
        "raw_environment_success_count": sum(
            bool(row.get("success")) for row in raw_by_key.values()
        ),
        "raw_abnormal_rollout_count": raw_abnormal_count,
        "raw_failure_reason_count": raw_failure_reason_count,
        "raw_nonfinite_rollout_count": nonfinite_count,
        "first_350ms_prefix_exact_across_r8_policies": prefix_exact,
        "first_350ms_prefix_max_abs_difference": prefix_numeric_max,
        "prefix_array_comparisons": prefix_comparisons,
        "r8_policy_recomputed": policy_recomputed,
        "r8_failed_tracking_rollouts": len(failed_rows),
        "r8_failed_rollouts_limited_by_final_speed": final_speed_limited,
        "r8_open_loop_tail_failure_is_terminal_control_not_runtime": bool(
            len(failed_rows) == 47 and final_speed_limited == len(failed_rows)
        ),
        "source_calibration_token_count": len(tokens),
        "source_calibration_tokens_all_trusted_correct": all_tokens_trusted,
        "source_calibrated_startup_status": "not_run",
        "passed": passed,
        "interpretation": (
            "R8 ran successfully and its finite 3x3 batch calibration closed. "
            "The queue bookkeeping was correct, but the post-350ms policy was open-loop; "
            "all 47 tracking failures were limited by final speed. R9 must add terminal feedback, "
            "not weaken the gate or proceed to RL."
        ),
    }
    atomic_write_json(ctx.paths.source_audit / "summary.json", summary)
    write_csv(ctx.paths.source_audit / "r8_limiting_metrics.csv", limiting_rows)
    write_csv(ctx.paths.source_audit / "r8_speed_growth.csv", speed_growth)
    _update_state(
        ctx,
        source_audit_complete=True,
        source_audit_summary=summary,
    )
    return summary


# ---------------------------------------------------------------------------
# Streaming delay queue and terminal measurement
# ---------------------------------------------------------------------------


def _initial_stream_queue(
    control_trace: Sequence[Mapping[str, Any]], delay_steps: int
) -> list[dict[str, Any]]:
    if len(control_trace) != MAIN_CONTROL_STEPS:
        raise ValueError(
            f"expected {MAIN_CONTROL_STEPS} main control rows, got {len(control_trace)}"
        )
    delay = max(0, int(delay_steps))
    if delay > MAIN_CONTROL_STEPS:
        raise ValueError("delay exceeds available main-control history")
    output: list[dict[str, Any]] = []
    for index in range(MAIN_CONTROL_STEPS - delay, MAIN_CONTROL_STEPS):
        row = control_trace[index]
        output.append(
            {
                "origin": "main_control",
                "origin_index": index,
                "command": np.asarray(
                    row["issued_mode_coefficients"], dtype=float
                ).reshape(N_MODES),
                "desired_physical": np.asarray(
                    row.get(
                        "issued_desired_physical_mode_coefficients",
                        row.get(
                            "desired_physical_mode_coefficients",
                            row["issued_mode_coefficients"],
                        ),
                    ),
                    dtype=float,
                ).reshape(N_MODES),
            }
        )
    return output


def _stream_queue_apply(
    queue: Sequence[Mapping[str, Any]],
    issued_item: Mapping[str, Any],
    delay_steps: int,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    delay = max(0, int(delay_steps))
    copied = [
        {
            "origin": str(item["origin"]),
            "origin_index": int(item["origin_index"]),
            "command": np.asarray(item["command"], dtype=float).reshape(N_MODES),
            "desired_physical": np.asarray(
                item["desired_physical"], dtype=float
            ).reshape(N_MODES),
        }
        for item in queue
    ]
    issued = {
        "origin": str(issued_item["origin"]),
        "origin_index": int(issued_item["origin_index"]),
        "command": np.asarray(issued_item["command"], dtype=float).reshape(N_MODES),
        "desired_physical": np.asarray(
            issued_item["desired_physical"], dtype=float
        ).reshape(N_MODES),
    }
    if delay == 0:
        if copied:
            raise ValueError("delay=0 streaming queue must be empty")
        return issued, []
    if len(copied) != delay:
        raise ValueError(
            f"streaming queue length {len(copied)} does not match delay {delay}"
        )
    copied.append(issued)
    applied = copied.pop(0)
    if len(copied) != delay:
        raise AssertionError("streaming queue length invariant broken")
    return applied, copied


def _terminal_measurement(
    trajectory: Sequence[Mapping[str, Any]],
    target: np.ndarray,
    dt_s: float,
) -> np.ndarray:
    if len(trajectory) < 2:
        raise ValueError("terminal feedback requires at least two trajectory states")
    current = trajectory[-1]
    previous = trajectory[-2]
    velocity_r = (float(current["R"]) - float(previous["R"])) / max(dt_s, 1e-12)
    velocity_z = (float(current["Z"]) - float(previous["Z"])) / max(dt_s, 1e-12)
    return np.asarray(
        [
            float(current["R"]) - float(target[0]),
            float(current["Z"]) - float(target[1]),
            velocity_r,
            velocity_z,
            float(current["Ip"]) - float(target[2]),
        ],
        dtype=float,
    )


def _queue_origins(queue: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "origin": str(item["origin"]),
            "origin_index": int(item["origin_index"]),
        }
        for item in queue
    ]


# ---------------------------------------------------------------------------
# R9 TSC worker
# ---------------------------------------------------------------------------


class LocalStage41R9Worker:
    def __init__(
        self,
        payload: dict[str, Any],
        library: dict[str, Any],
        bundle: dict[str, Any],
        worker_id: str,
        selector_cfg: dict[str, Any],
    ):
        self.r8_worker = r8.LocalStage41R8Worker(
            payload, library, bundle, worker_id, selector_cfg
        )
        self.base_worker = self.r8_worker.base_worker
        self.bundle = bundle
        self.horizon_steps = int(payload.get("stage4_1r4_horizon_steps", 35))

    def _cleanup_episode(self, *, failed: bool, reason: str) -> None:
        runner = getattr(self.base_worker.env, "runner", None)
        if runner is not None:
            runner.cleanup_episode_workspace(failed=failed, reason=reason)

    def close(self) -> None:
        self.r8_worker.close()

    def evaluate(self, spec: dict[str, Any]) -> dict[str, Any]:
        return self._run_terminal_feedback(spec)

    def _run_terminal_feedback(self, spec: dict[str, Any]) -> dict[str, Any]:
        started = time.time()
        failed = True
        result: dict[str, Any]
        try:
            internal = copy.deepcopy(spec)
            internal["_defer_cleanup"] = True
            internal["extended_horizon"] = False
            internal["tail_hold_steps"] = 0
            internal["tail_action_policy"] = "none"
            result = self.base_worker.evaluate(internal)
            result["spec"] = copy.deepcopy(spec)
            if not result.get("success"):
                result["controller_revision"] = CONTROLLER_REVISION
                result["stage4_1r9_controller_revision"] = CONTROLLER_REVISION
                return _json_safe(result)
            control_trace = list(result.get("control_trace") or [])
            trajectory = list(result.get("trajectory") or [])
            if len(control_trace) != MAIN_CONTROL_STEPS:
                raise ValueError("main control trace length mismatch")
            if len(trajectory) != MAIN_CONTROL_STEPS + 1:
                raise ValueError("main trajectory prefix length mismatch")

            horizon = int(spec["horizon_steps"])
            tail_steps = int(spec["tail_feedback_steps"])
            if horizon != self.horizon_steps:
                raise ValueError("environment horizon/payload mismatch")
            if horizon != MAIN_CONTROL_STEPS + tail_steps:
                raise ValueError("R9 horizon must equal 35 plus tail feedback steps")

            actual_delay = int(spec["action_delay_steps"])
            modeled_delay = int(spec["controller_action_delay_steps"])
            actual_slew = float(spec["slew_scale"])
            modeled_slew = float(spec["controller_slew_scale_estimate"])
            trusted = bool(spec.get("trusted_calibration_model", False))
            if trusted and (
                actual_delay != modeled_delay
                or not math.isclose(actual_slew, modeled_slew, abs_tol=1e-12)
            ):
                raise ValueError(
                    "trusted finite-envelope R9 spec has actual/modeled actuator mismatch"
                )

            queue = _initial_stream_queue(control_trace, actual_delay)
            template_step = int(spec["terminal_template_step"])
            controller_scale = float(spec["terminal_controller_scale"])
            model_scale = float(spec.get("terminal_controller_model_scale", 1.0))
            velocity_gain = float(spec["terminal_velocity_measurement_gain"])
            position_gain = float(spec.get("terminal_position_measurement_gain", 1.0))
            ip_gain = float(spec.get("terminal_ip_measurement_gain", 1.0))
            if template_step + modeled_delay >= MAIN_CONTROL_STEPS:
                raise ValueError("terminal template leaves no free delayed control step")

            target = np.asarray(
                [
                    float(self.base_worker.cfg["target"]["R"])
                    + float(spec.get("target_R_offset_m", 0.0)),
                    float(self.base_worker.cfg["target"]["Z"])
                    + float(spec.get("target_Z_offset_m", 0.0)),
                    float(self.base_worker.cfg["target"]["Ip"])
                    + float(spec.get("target_Ip_offset_A", 0.0)),
                ],
                dtype=float,
            )
            scales_cfg = self.base_worker.cfg["identification"]["output_scales"]
            measurement_scales = np.asarray(
                [
                    scales_cfg["R_m"],
                    scales_cfg["Z_m"],
                    scales_cfg["vR_m_per_s"],
                    scales_cfg["vZ_m_per_s"],
                    scales_cfg["Ip_A"],
                ],
                dtype=float,
            )
            dt_s = float(self.base_worker.env_cfg["dt_ms"]) / 1000.0
            nominal_physical = np.zeros((MAIN_CONTROL_STEPS, N_MODES), dtype=float)
            nominal_feature = np.zeros(MAIN_CONTROL_STEPS * 5, dtype=float)
            integral = np.zeros(5, dtype=float)
            if spec.get("terminal_initial_previous_correction") == "last_issued_desired_physical":
                previous_correction = np.asarray(
                    control_trace[-1].get(
                        "issued_desired_physical_mode_coefficients",
                        control_trace[-1].get(
                            "desired_physical_mode_coefficients",
                            control_trace[-1]["issued_mode_coefficients"],
                        ),
                    ),
                    dtype=float,
                ).reshape(N_MODES)
            else:
                previous_correction = np.zeros(N_MODES, dtype=float)

            actual_gain = np.asarray(
                spec.get("actuator_gain_by_mode", [1.0, 1.0, 1.0]), dtype=float
            ).reshape(N_MODES)
            controller_gain = np.asarray(
                spec.get("controller_gain_estimate_by_mode", [1.0, 1.0, 1.0]),
                dtype=float,
            ).reshape(N_MODES)
            actuator_bias = np.asarray(
                spec.get("actuator_bias_by_mode", [0.0, 0.0, 0.0]), dtype=float
            ).reshape(N_MODES)

            tail_trace: list[dict[str, Any]] = []
            failure_reason = ""
            streaming_consistent = True
            for tail_index in range(tail_steps):
                measurement_physical = _terminal_measurement(
                    trajectory, target, dt_s
                )
                measurement_normalized = measurement_physical / measurement_scales
                measurement_for_solver = measurement_normalized.copy()
                measurement_for_solver[:2] *= position_gain
                measurement_for_solver[2:4] *= velocity_gain
                measurement_for_solver[4] *= ip_gain
                modeled_pending = [
                    np.asarray(item["desired_physical"], dtype=float)
                    for item in queue[:modeled_delay]
                ]
                if len(modeled_pending) != modeled_delay:
                    raise ValueError(
                        "modeled pending queue length does not match calibrated delay"
                    )
                solve = r3.solve_delay_aware_physical_correction(
                    self.base_worker.stub,
                    self.bundle,
                    current_step=template_step,
                    modeled_action_delay_steps=modeled_delay,
                    modeled_pending_physical_coefficients=modeled_pending,
                    nominal_physical_coefficients=nominal_physical,
                    nominal_feature=nominal_feature,
                    measurement_normalized=measurement_for_solver,
                    integral_normalized=integral,
                    previous_correction=previous_correction,
                    controller_scale=controller_scale,
                    controller_model_scale=model_scale,
                )
                correction = np.asarray(
                    solve["first_correction"], dtype=float
                ).reshape(N_MODES)
                desired_physical = np.clip(
                    correction,
                    self.base_worker.lower_mode,
                    self.base_worker.upper_mode,
                )
                currents_before = np.asarray(
                    self.base_worker.env.last_state["currents_a_tsc"], dtype=float
                )
                scheduled = self.base_worker.scheduler.solve_command(
                    desired_physical,
                    currents_before,
                    controller_gain,
                    modeled_slew,
                    enabled=True,
                )
                issued_command = np.asarray(
                    scheduled["command"], dtype=float
                ).reshape(N_MODES)
                issued_item = {
                    "origin": "terminal_feedback",
                    "origin_index": tail_index,
                    "command": issued_command,
                    "desired_physical": desired_physical,
                }
                queue_before = _queue_origins(queue)
                applied_item, queue = _stream_queue_apply(
                    queue, issued_item, actual_delay
                )
                if len(queue) != actual_delay:
                    streaming_consistent = False
                applied_command = np.asarray(
                    applied_item["command"], dtype=float
                ).reshape(N_MODES)
                effective = actual_gain * applied_command + actuator_bias
                action = self.base_worker._mode_action(effective, currents_before)
                _, _, terminated, truncated, info = self.base_worker.env.step(action)
                state_index = MAIN_CONTROL_STEPS + tail_index + 1
                trajectory.append(
                    r3.base._state_record(
                        self.base_worker.env, state_index, action
                    )
                )
                currents_after = np.asarray(
                    self.base_worker.env.last_state["currents_a_tsc"], dtype=float
                )
                tail_trace.append(
                    {
                        "tail_index": tail_index,
                        "environment_step": state_index - 1,
                        "template_step": template_step,
                        "measurement_physical": measurement_physical.tolist(),
                        "measurement_normalized": measurement_normalized.tolist(),
                        "measurement_for_solver": measurement_for_solver.tolist(),
                        "modeled_delay_steps": modeled_delay,
                        "actual_delay_steps": actual_delay,
                        "queue_before": queue_before,
                        "queue_after": _queue_origins(queue),
                        "issued_origin": {
                            "origin": "terminal_feedback",
                            "origin_index": tail_index,
                        },
                        "applied_origin": {
                            "origin": str(applied_item["origin"]),
                            "origin_index": int(applied_item["origin_index"]),
                        },
                        "issued_desired_physical_mode_coefficients": desired_physical.tolist(),
                        "issued_mode_coefficients": issued_command.tolist(),
                        "applied_desired_physical_mode_coefficients": np.asarray(
                            applied_item["desired_physical"], dtype=float
                        ).tolist(),
                        "applied_mode_coefficients": applied_command.tolist(),
                        "effective_mode_coefficients": effective.tolist(),
                        "mode_correction_physical": correction.tolist(),
                        "previous_correction_physical": previous_correction.tolist(),
                        "solver_success": bool(solve.get("solver_success", False)),
                        "solver_status": int(solve.get("solver_status", 0)),
                        "solver_cost": float(solve.get("solver_cost", 0.0)),
                        "solver_optimality": float(
                            solve.get("solver_optimality", 0.0)
                        ),
                        "solver_effect_step": int(solve.get("effect_step", -1)),
                        "solver_fixed_pending_steps": int(
                            solve.get("fixed_pending_steps", modeled_delay)
                        ),
                        "predicted_normalized_residual_rms": float(
                            solve.get("predicted_normalized_residual_rms", 0.0)
                        ),
                        "scheduler_predicted_mismatch_rms_a": float(
                            scheduled["mismatch_rms_a"]
                        ),
                        "scheduler_predicted_mismatch_max_abs_a": float(
                            scheduled["mismatch_max_abs_a"]
                        ),
                        "currents_before_A": currents_before.tolist(),
                        "currents_after_A": currents_after.tolist(),
                        "actual_current_delta_A": (
                            currents_after - currents_before
                        ).tolist(),
                        "action_norm_tsc": np.asarray(action, dtype=float).tolist(),
                    }
                )
                previous_correction = desired_physical.copy()
                if terminated:
                    failure_reason = str(
                        info.get("failure_reason", "terminal feedback terminated")
                    )
                    break
                if truncated and state_index < horizon:
                    failure_reason = (
                        "environment truncated before terminal-feedback horizon"
                    )
                    break

            result["trajectory"] = trajectory
            result["terminal_feedback_trace"] = tail_trace
            # Compatibility alias used only by generic trace comparison.
            result["tail_queue_trace"] = tail_trace
            pending_norms = [
                float(np.linalg.norm(np.asarray(item["command"], dtype=float)))
                for item in queue
            ]
            pending_desired_norms = [
                float(
                    np.linalg.norm(
                        np.asarray(item["desired_physical"], dtype=float)
                    )
                )
                for item in queue
            ]
            last5 = np.asarray(
                [
                    row["issued_desired_physical_mode_coefficients"]
                    for row in tail_trace[-5:]
                ],
                dtype=float,
            )
            last5_rms = (
                float(np.sqrt(np.mean(last5**2))) if last5.size else 0.0
            )
            result["terminal_feedback_summary"] = {
                "policy_id": spec["terminal_policy_id"],
                "template_step": template_step,
                "horizon_steps": horizon,
                "tail_feedback_steps": tail_steps,
                "actual_delay_steps": actual_delay,
                "modeled_delay_steps": modeled_delay,
                "continuous_streaming_queue": True,
                "initial_pending_count": actual_delay,
                "final_pending_count": len(queue),
                "final_pending_origins": _queue_origins(queue),
                "maximum_final_pending_command_norm": max(
                    pending_norms, default=0.0
                ),
                "maximum_final_pending_desired_physical_norm": max(
                    pending_desired_norms, default=0.0
                ),
                "last5_issued_desired_rms": last5_rms,
                "streaming_queue_consistent": streaming_consistent,
                "pending_queue_bypassed": False,
                "terminal_feedback_uses_direct_measured_RZI_and_finite_difference_velocity": True,
                "terminal_feedback_observer_noise_robustness_validated": False,
            }
            success = bool(
                not failure_reason
                and len(trajectory) == horizon + 1
                and len(tail_trace) == tail_steps
                and not any(
                    bool(row.get("abnormal", False)) for row in trajectory
                )
                and streaming_consistent
                and len(queue) == actual_delay
            )
            result["success"] = success
            result["failure_reason"] = (
                "" if success else failure_reason or "incomplete terminal feedback"
            )
            result["wall_time_s"] = float(time.time() - started)
            result["controller_revision"] = CONTROLLER_REVISION
            result["stage4_1r9_controller_revision"] = CONTROLLER_REVISION
            failed = not success
            return _json_safe(result)
        except Exception as exc:
            failed = True
            return _json_safe(
                {
                    "schema_version": SCHEMA_VERSION,
                    "controller_revision": CONTROLLER_REVISION,
                    "experiment_id": spec.get("experiment_id", "unknown"),
                    "spec": copy.deepcopy(spec),
                    "success": False,
                    "failure_reason": repr(exc),
                    "traceback": traceback.format_exc(),
                    "wall_time_s": float(time.time() - started),
                    "trajectory": [],
                    "control_trace": [],
                    "terminal_feedback_trace": [],
                    "tail_queue_trace": [],
                }
            )
        finally:
            self._cleanup_episode(
                failed=failed, reason="stage4_1r9_terminal_feedback"
            )


_RAY_ACTOR = None


def _ray_actor_class():
    global _RAY_ACTOR
    if _RAY_ACTOR is None:
        import ray

        @ray.remote(num_cpus=1)
        class Stage41R9Actor:
            def __init__(
                self,
                payload: dict[str, Any],
                library: dict[str, Any],
                bundle: dict[str, Any],
                worker_id: str,
                selector_cfg: dict[str, Any],
            ):
                self.worker = LocalStage41R9Worker(
                    payload, library, bundle, worker_id, selector_cfg
                )

            def evaluate(self, spec: dict[str, Any]) -> dict[str, Any]:
                return self.worker.evaluate(spec)

            def close(self) -> bool:
                self.worker.close()
                return True

        _RAY_ACTOR = Stage41R9Actor
    return _RAY_ACTOR


def materialize_variant(
    ctx: Stage41R9Context, *, slew_scale: float, horizon_steps: int
) -> tuple[str, dict[str, Any]]:
    return r8.materialize_variant(
        ctx.r8_ctx,
        slew_scale=float(slew_scale),
        horizon_steps=int(horizon_steps),
    )


def evaluate_specs(
    ctx: Stage41R9Context,
    specs: Sequence[dict[str, Any]],
    *,
    output_dir: Path,
    backend: str,
    resume: bool,
) -> list[dict[str, Any]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    variants = ctx.r8_ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.variants
    by_variant: dict[str, list[dict[str, Any]]] = {}
    for spec in specs:
        variant = str(spec["environment_variant"])
        if variant not in variants:
            raise KeyError(f"unmaterialized environment variant {variant}")
        by_variant.setdefault(variant, []).append(spec)
    pending_by_variant: dict[str, list[dict[str, Any]]] = {}
    for variant, rows in by_variant.items():
        pending = [
            row
            for row in rows
            if not (
                resume
                and _result_complete(
                    output_dir / f"{row['experiment_id']}.json.gz"
                )
            )
        ]
        if pending:
            pending_by_variant[variant] = pending
    library = ctx.r8_ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.source_library
    bundle = ctx.r8_ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.source_bundle
    selector_cfg = ctx.r8_ctx.cfg["batch_selector"]
    if backend == "serial":
        for variant, pending in pending_by_variant.items():
            worker = LocalStage41R9Worker(
                variants[variant],
                library,
                bundle,
                f"stage41r9_{variant}_serial",
                selector_cfg,
            )
            try:
                for index, spec in enumerate(pending, 1):
                    atomic_write_json_gz(
                        output_dir / f"{spec['experiment_id']}.json.gz",
                        worker.evaluate(spec),
                    )
                    print(
                        f"[Stage4.1R9 {variant}] {index}/{len(pending)}",
                        flush=True,
                    )
            finally:
                worker.close()
    elif backend == "ray" and pending_by_variant:
        import ray

        requested = int(
            os.environ.get(
                "STAGE4_1R9_WORKERS", ctx.cfg["parallel"]["n_workers"]
            )
        )
        total_pending = sum(len(rows) for rows in pending_by_variant.values())
        plan = ensure_ray_worker_plan(
            ray,
            requested_workers=requested,
            pending_tasks=total_pending,
            ray_tmpdir=os.environ.get(
                "RAY_TMPDIR", ctx.cfg["parallel"].get("ray_tmpdir", "")
            )
            or None,
            log_prefix="[Stage4.1R9 mixed-variant]",
        )
        allocation = r3.s40._allocate_variant_actor_counts(
            {
                variant: len(rows)
                for variant, rows in pending_by_variant.items()
            },
            plan.actor_count,
        )
        print(
            "[Stage4.1R9 mixed-variant] actor_allocation="
            + json.dumps(allocation, sort_keys=True, separators=(",", ":")),
            flush=True,
        )
        Actor = _ray_actor_class()
        actors_by_variant: dict[str, list[Any]] = {}
        all_actors: list[Any] = []
        for variant, count in allocation.items():
            actors = [
                Actor.remote(
                    variants[variant],
                    library,
                    bundle,
                    f"stage41r9_{variant}_{index:03d}",
                    selector_cfg,
                )
                for index in range(count)
            ]
            actors_by_variant[variant] = actors
            all_actors.extend(actors)
        refs: dict[Any, dict[str, Any]] = {}
        for variant, pending in pending_by_variant.items():
            actors = actors_by_variant[variant]
            for index, spec in enumerate(pending):
                refs[actors[index % len(actors)].evaluate.remote(spec)] = spec
        done = 0
        try:
            while refs:
                ready, _ = ray.wait(
                    list(refs), num_returns=1, timeout=30.0
                )
                if not ready:
                    print(
                        f"[Stage4.1R9 mixed-variant] "
                        f"waiting {done}/{total_pending}",
                        flush=True,
                    )
                    continue
                for ref in ready:
                    spec = refs.pop(ref)
                    try:
                        result = ray.get(ref)
                    except Exception as exc:
                        result = {
                            "schema_version": SCHEMA_VERSION,
                            "controller_revision": CONTROLLER_REVISION,
                            "experiment_id": spec["experiment_id"],
                            "spec": spec,
                            "success": False,
                            "failure_reason": repr(exc),
                            "traceback": traceback.format_exc(),
                            "trajectory": [],
                        }
                    atomic_write_json_gz(
                        output_dir / f"{spec['experiment_id']}.json.gz",
                        result,
                    )
                    done += 1
                    if done % 10 == 0 or not refs:
                        print(
                            f"[Stage4.1R9 mixed-variant] "
                            f"{done}/{total_pending}",
                            flush=True,
                        )
        finally:
            s2._close_ray_actors(
                all_actors,
                timeout_s=float(
                    ctx.cfg["storage"].get("actor_close_timeout_s", 1800.0)
                ),
            )
    elif backend not in {"serial", "ray"}:
        raise ValueError("backend must be 'ray' or 'serial'")
    return [
        read_json_gz(output_dir / f"{spec['experiment_id']}.json.gz")
        for spec in specs
    ]


# ---------------------------------------------------------------------------
# Specs, metrics and trace comparisons
# ---------------------------------------------------------------------------


def _make_spec(
    *,
    phase: str,
    scenario: str,
    category: str,
    target: Mapping[str, Any],
    controller_scale: float,
    environment_variant: str,
    extra: Mapping[str, Any],
) -> dict[str, Any]:
    identity = {
        "revision": CONTROLLER_REVISION,
        "phase": phase,
        "scenario": scenario,
        "category": category,
        "target": dict(target),
        "controller_scale": controller_scale,
        "environment_variant": environment_variant,
        "extra": dict(extra),
    }
    return {
        "kind": "stage4_1r9_terminal_template_mpc_feedback_hold",
        "controller_revision": CONTROLLER_REVISION,
        "experiment_id": _scenario_digest(identity),
        "phase": phase,
        "scenario": scenario,
        "category": category,
        "target_id": str(target["target_id"]),
        "target_R_offset_m": float(target.get("R_offset_m", 0.0)),
        "target_Z_offset_m": float(target.get("Z_offset_m", 0.0)),
        "target_Ip_offset_A": float(target.get("Ip_offset_A", 0.0)),
        "controller_scale": float(controller_scale),
        "environment_variant": environment_variant,
        **copy.deepcopy(dict(extra)),
    }


def _target_task(spec: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "task_id": str(spec.get("scenario", spec.get("experiment_id"))),
        "R_offset_m": float(spec.get("target_R_offset_m", 0.0)),
        "Z_offset_m": float(spec.get("target_Z_offset_m", 0.0)),
        "Ip_offset_A": float(spec.get("target_Ip_offset_A", 0.0)),
        "final": False,
        "mandatory": False,
        "parents": [],
        "category": str(spec.get("category", "r9")),
    }


def _terminal_policy_lookup(ctx: Stage41R9Context) -> dict[str, dict[str, Any]]:
    return {
        str(row["policy_id"]): copy.deepcopy(row)
        for row in ctx.cfg["terminal_feedback"]["candidate_bank"]
    }


def _main_extra(
    ctx: Stage41R9Context,
    *,
    actual_delay: int,
    actual_slew: float,
    modeled_delay: int,
    modeled_slew: float,
    policy: Mapping[str, Any],
    calibration_token: str | None,
    trusted: bool,
    controller_variant: str,
) -> dict[str, Any]:
    terminal_cfg = ctx.cfg["terminal_feedback"]
    generic_policy = {
        "horizon_steps": int(terminal_cfg["horizon_steps"]),
        "tail_steps": int(terminal_cfg["tail_feedback_steps"]),
        "tail_policy": "continuous_streaming_terminal_feedback",
        "policy_id": str(policy["policy_id"]),
    }
    extra = r8._main_extra(
        ctx.r8_ctx,
        actual_delay=int(actual_delay),
        actual_slew=float(actual_slew),
        modeled_delay=int(modeled_delay),
        modeled_slew=float(modeled_slew),
        policy=generic_policy,
        variant=controller_variant,
        monitor_enabled=False,
        calibration_token=calibration_token,
        trusted=trusted,
    )
    extra.update(
        {
            "horizon_steps": int(terminal_cfg["horizon_steps"]),
            "tail_feedback_steps": int(
                terminal_cfg["tail_feedback_steps"]
            ),
            "tail_steps": int(terminal_cfg["tail_feedback_steps"]),
            "tail_policy": "continuous_streaming_terminal_feedback",
            "terminal_policy_id": str(policy["policy_id"]),
            "terminal_template_step": int(policy["template_step"]),
            "terminal_controller_scale": float(policy["controller_scale"]),
            "terminal_velocity_measurement_gain": float(
                policy["velocity_measurement_gain"]
            ),
            "terminal_position_measurement_gain": float(
                terminal_cfg["position_measurement_gain"]
            ),
            "terminal_ip_measurement_gain": float(
                terminal_cfg["ip_measurement_gain"]
            ),
            "terminal_controller_model_scale": float(
                terminal_cfg["controller_model_scale"]
            ),
            "terminal_integral_mode": str(terminal_cfg["integral_mode"]),
            "terminal_nominal_physical_mode": str(
                terminal_cfg["terminal_nominal_physical_mode"]
            ),
            "terminal_initial_previous_correction": str(
                terminal_cfg["initial_previous_correction"]
            ),
            "controller_variant": controller_variant,
            "adaptive_handover": {"enabled": False},
            "adaptive_delay_slew_estimator": None,
        }
    )
    extra.pop("adaptive_delay_slew_estimator", None)
    return extra


def _trace_arrays(
    result: Mapping[str, Any],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    physics = np.asarray(
        [
            [
                row["R"],
                row["Z"],
                row["Ip"],
                *row["currents_a_tsc"],
                *row["action_norm_tsc"],
            ]
            for row in result.get("trajectory") or []
        ],
        dtype=float,
    )
    main_issued = np.asarray(
        [
            row.get("issued_mode_coefficients", [0.0, 0.0, 0.0])
            for row in result.get("control_trace") or []
        ],
        dtype=float,
    )
    terminal_issued = np.asarray(
        [
            row.get(
                "issued_mode_coefficients",
                row.get("command_mode_coefficients", [0.0, 0.0, 0.0]),
            )
            for row in result.get("terminal_feedback_trace") or []
        ],
        dtype=float,
    )
    terminal_applied = np.asarray(
        [
            row.get(
                "applied_mode_coefficients",
                row.get("command_mode_coefficients", [0.0, 0.0, 0.0]),
            )
            for row in result.get("terminal_feedback_trace") or []
        ],
        dtype=float,
    )
    return physics, main_issued, terminal_issued, terminal_applied


def _compare_results(
    left: Mapping[str, Any],
    right: Mapping[str, Any],
    *,
    atol: float,
    prefix_only: bool = False,
) -> dict[str, Any]:
    if prefix_only:
        arrays = (
            (_physics_prefix(left), _physics_prefix(right), "physics"),
            (_issued_prefix(left), _issued_prefix(right), "main_issued"),
        )
    else:
        left_arrays = _trace_arrays(left)
        right_arrays = _trace_arrays(right)
        names = ("physics", "main_issued", "terminal_issued", "terminal_applied")
        arrays = tuple(
            (a, b, name)
            for a, b, name in zip(left_arrays, right_arrays, names)
        )
    exact = True
    numeric = True
    maxima: dict[str, float] = {}
    for a, b, name in arrays:
        if a.shape != b.shape:
            exact = False
            numeric = False
            maxima[name] = math.inf
            continue
        maxima[name] = (
            float(np.max(np.abs(a - b))) if a.size else 0.0
        )
        exact = bool(exact and np.array_equal(a, b))
        numeric = bool(
            numeric
            and np.allclose(a, b, rtol=0.0, atol=float(atol), equal_nan=False)
        )
    return {
        "exact_equal": exact,
        "numeric_equal": numeric,
        "max_abs_difference": max(maxima.values(), default=0.0),
        "component_max_abs_difference": maxima,
    }


def _source_prefix_comparison(
    ctx: Stage41R9Context, result: Mapping[str, Any], *, atol: float
) -> dict[str, Any]:
    spec = result["spec"]
    source = _source_h41_by_case(ctx).get(
        (
            str(spec["target_id"]),
            int(spec["action_delay_steps"]),
            float(spec["slew_scale"]),
        )
    )
    if source is None:
        return {
            "source_available": False,
            "exact_equal": False,
            "numeric_equal": False,
            "max_abs_difference": math.inf,
        }
    comparison = _compare_results(
        result, source, atol=atol, prefix_only=True
    )
    comparison["source_available"] = True
    return comparison


def feedback_result_row(
    ctx: Stage41R9Context,
    result: Mapping[str, Any],
    *,
    phase: str,
) -> dict[str, Any]:
    spec = result.get("spec") or {}
    terminal = result.get("terminal_feedback_summary") or {}
    task = _target_task(spec)
    allowed = [
        int(value)
        for value in ctx.cfg["terminal_feedback"]["allowed_arrival_steps"]
    ]
    metric_policy = {
        "horizon_steps": int(ctx.cfg["terminal_feedback"]["horizon_steps"]),
        "allowed_arrival_steps": allowed,
    }
    metrics = r8.tracking_metrics(ctx.r8_ctx, result, metric_policy)
    trajectory = list(result.get("trajectory") or [])
    full_actions = np.asarray(
        [row.get("action_norm_tsc", [0.0] * 14) for row in trajectory[1:]],
        dtype=float,
    )
    terminal_trace = list(result.get("terminal_feedback_trace") or [])
    terminal_actions = np.asarray(
        [row.get("action_norm_tsc", [0.0] * 14) for row in terminal_trace],
        dtype=float,
    )
    issued = np.asarray(
        [
            row.get("issued_desired_physical_mode_coefficients", [0.0] * 3)
            for row in terminal_trace
        ],
        dtype=float,
    )
    physics, main_issued, terminal_issued, terminal_applied = _trace_arrays(
        result
    )
    prefix = _source_prefix_comparison(
        ctx,
        result,
        atol=float(ctx.cfg["terminal_feedback"]["prefix_numeric_atol"]),
    )
    row = {
        "experiment_id": result.get("experiment_id"),
        "phase": phase,
        "scenario": spec.get("scenario"),
        "target_id": spec.get("target_id"),
        "policy_id": spec.get("terminal_policy_id"),
        "controller_variant": spec.get("controller_variant"),
        "actual_action_delay_steps": spec.get("action_delay_steps"),
        "controller_action_delay_steps": spec.get(
            "controller_action_delay_steps"
        ),
        "actual_slew_scale": spec.get("slew_scale"),
        "controller_slew_scale_estimate": spec.get(
            "controller_slew_scale_estimate"
        ),
        "calibration_token": spec.get("calibration_token"),
        "trusted_calibration_model": bool(
            spec.get("trusted_calibration_model", False)
        ),
        "success": bool(result.get("success")),
        "failure_reason": result.get("failure_reason", ""),
        "terminal_template_step": spec.get("terminal_template_step"),
        "terminal_controller_scale": spec.get("terminal_controller_scale"),
        "terminal_velocity_measurement_gain": spec.get(
            "terminal_velocity_measurement_gain"
        ),
        "continuous_streaming_queue": bool(
            terminal.get("continuous_streaming_queue", False)
        ),
        "streaming_queue_consistent": bool(
            terminal.get("streaming_queue_consistent", False)
        ),
        "pending_queue_bypassed": bool(
            terminal.get("pending_queue_bypassed", True)
        ),
        "initial_pending_count": terminal.get("initial_pending_count"),
        "final_pending_count": terminal.get("final_pending_count"),
        "maximum_final_pending_command_norm": terminal.get(
            "maximum_final_pending_command_norm"
        ),
        "maximum_final_pending_desired_physical_norm": terminal.get(
            "maximum_final_pending_desired_physical_norm"
        ),
        "last5_issued_desired_rms": terminal.get(
            "last5_issued_desired_rms"
        ),
        "first_350ms_prefix_source_available": bool(
            prefix.get("source_available", False)
        ),
        "first_350ms_prefix_exact": bool(prefix.get("exact_equal", False)),
        "first_350ms_prefix_numeric_equal": bool(
            prefix.get("numeric_equal", False)
        ),
        "first_350ms_prefix_max_abs_difference": prefix.get(
            "max_abs_difference"
        ),
        "physics_signature": _array_digest(physics, "physics"),
        "main_issued_signature": _array_digest(main_issued, "maincmd"),
        "terminal_issued_signature": _array_digest(
            terminal_issued, "terminalissued"
        ),
        "terminal_applied_signature": _array_digest(
            terminal_applied, "terminalapplied"
        ),
        "n_trajectory_steps": len(trajectory),
        "full_action_rms": (
            float(np.sqrt(np.mean(full_actions**2)))
            if full_actions.size
            else 0.0
        ),
        "terminal_action_rms": (
            float(np.sqrt(np.mean(terminal_actions**2)))
            if terminal_actions.size
            else 0.0
        ),
        "terminal_issued_desired_rms": (
            float(np.sqrt(np.mean(issued**2))) if issued.size else 0.0
        ),
        "wall_time_s": result.get("wall_time_s"),
        **metrics,
    }
    return _json_safe(row)


def _expected_case_keys(
    targets: Sequence[Mapping[str, Any]],
) -> set[tuple[str, int, float]]:
    return {
        (str(target["target_id"]), delay, slew)
        for target in targets
        for delay in (0, 1, 2)
        for slew in (0.9, 1.0, 1.1)
    }


def build_oracle_development_specs(
    ctx: Stage41R9Context,
) -> list[dict[str, Any]]:
    terminal = ctx.cfg["terminal_feedback"]
    target = terminal["development_target"]
    source_scale = float(
        ctx.r8_ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.source_scale
    )
    specs: list[dict[str, Any]] = []
    for slew in terminal["actual_slew_scales"]:
        variant_id, _ = materialize_variant(
            ctx,
            slew_scale=float(slew),
            horizon_steps=int(terminal["horizon_steps"]),
        )
        for delay in terminal["actual_delay_steps"]:
            for policy in terminal["candidate_bank"]:
                extra = _main_extra(
                    ctx,
                    actual_delay=int(delay),
                    actual_slew=float(slew),
                    modeled_delay=int(delay),
                    modeled_slew=float(slew),
                    policy=policy,
                    calibration_token=None,
                    trusted=True,
                    controller_variant="r9_oracle_development",
                )
                specs.append(
                    _make_spec(
                        phase="oracle_development",
                        scenario=(
                            f"{policy['policy_id']}__{target['target_id']}"
                            f"__d{delay}__s{float(slew):.1f}"
                        ),
                        category="oracle_development",
                        target=target,
                        controller_scale=source_scale,
                        environment_variant=variant_id,
                        extra=extra,
                    )
                )
    return specs


def _policy_summary(
    ctx: Stage41R9Context,
    policy_id: str,
    subset: Sequence[Mapping[str, Any]],
    expected_cases: set[tuple[str, int, float]],
) -> dict[str, Any]:
    observed = {
        (
            str(row["target_id"]),
            int(row["actual_action_delay_steps"]),
            float(row["actual_slew_scale"]),
        )
        for row in subset
    }
    coverage = len(subset) == len(expected_cases) and observed == expected_cases
    tracking_fraction = sum(
        bool(row.get("stage3_4_target_tracking_pass")) for row in subset
    ) / max(len(subset), 1)
    minimum_margin = min(
        (
            _as_float(
                row.get("stage3_4_tracking_minimum_signed_margin"), -1e12
            )
            for row in subset
        ),
        default=-1e12,
    )
    mean_margin = (
        float(
            np.mean(
                [
                    _as_float(
                        row.get(
                            "stage3_4_tracking_minimum_signed_margin"
                        ),
                        -1e12,
                    )
                    for row in subset
                ]
            )
        )
        if subset
        else -1e12
    )
    prefix_fraction = sum(
        bool(row.get("first_350ms_prefix_exact")) for row in subset
    ) / max(len(subset), 1)
    terminal = ctx.cfg["terminal_feedback"]
    max_pending = max(
        (
            _as_float(
                row.get(
                    "maximum_final_pending_desired_physical_norm"
                ),
                math.inf,
            )
            for row in subset
        ),
        default=math.inf,
    )
    max_last5 = max(
        (
            _as_float(row.get("last5_issued_desired_rms"), math.inf)
            for row in subset
        ),
        default=math.inf,
    )
    all_streaming = all(
        bool(row.get("continuous_streaming_queue"))
        and bool(row.get("streaming_queue_consistent"))
        and not bool(row.get("pending_queue_bypassed"))
        for row in subset
    )
    passed = bool(
        coverage
        and all(bool(row.get("success")) for row in subset)
        and tracking_fraction
        >= float(terminal["minimum_tracking_fraction"])
        and minimum_margin >= float(terminal["minimum_signed_margin"])
        and (
            not bool(terminal.get("require_exact_first_350ms_prefix", True))
            or prefix_fraction >= 1.0 - 1e-12
        )
        and (
            not bool(
                terminal.get("require_streaming_queue_consistency", True)
            )
            or all_streaming
        )
        and max_pending
        <= float(terminal["maximum_terminal_pending_command_norm"])
        and max_last5
        <= float(terminal["maximum_last5_issued_desired_rms"])
    )
    return {
        "policy_id": policy_id,
        "n_rollouts": len(subset),
        "coverage_complete": coverage,
        "all_environment_success": all(
            bool(row.get("success")) for row in subset
        ),
        "tracking_fraction": tracking_fraction,
        "minimum_signed_margin": minimum_margin,
        "mean_signed_margin": mean_margin,
        "first_350ms_prefix_exact_fraction": prefix_fraction,
        "all_streaming_queues_consistent": all_streaming,
        "maximum_terminal_pending_desired_physical_norm": max_pending,
        "maximum_last5_issued_desired_rms": max_last5,
        "mean_terminal_action_rms": (
            float(
                np.mean(
                    [
                        _as_float(row.get("terminal_action_rms"), 0.0)
                        for row in subset
                    ]
                )
            )
            if subset
            else math.inf
        ),
        "passed": passed,
    }


def summarize_oracle_development(
    ctx: Stage41R9Context, rows: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    terminal = ctx.cfg["terminal_feedback"]
    target = terminal["development_target"]
    expected_cases = _expected_case_keys([target])
    policies = _terminal_policy_lookup(ctx)
    summaries = [
        _policy_summary(
            ctx,
            policy_id,
            [row for row in rows if str(row.get("policy_id")) == policy_id],
            expected_cases,
        )
        for policy_id in policies
    ]
    coverage = bool(
        len(rows) == len(expected_cases) * len(policies)
        and all(item["coverage_complete"] for item in summaries)
    )
    passing = [item for item in summaries if item["passed"]]
    selected = None
    if coverage and passing:
        selected = max(
            passing,
            key=lambda item: (
                float(item["minimum_signed_margin"]),
                float(item["mean_signed_margin"]),
                -float(item["mean_terminal_action_rms"]),
                str(item["policy_id"]),
            ),
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "phase": "oracle_development",
        "development_target_id": target["target_id"],
        "holdout_target_id": terminal["holdout_target"]["target_id"],
        "candidate_selection_uses_holdout": False,
        "n_rollouts": len(rows),
        "expected_rollouts": len(expected_cases) * len(policies),
        "coverage_complete": coverage,
        "policy_summaries": summaries,
        "selected_policy_id": None if selected is None else selected["policy_id"],
        "selected_policy_minimum_signed_margin": (
            None if selected is None else selected["minimum_signed_margin"]
        ),
        "passed": bool(coverage and selected is not None),
    }


def run_oracle_development(
    ctx: Stage41R9Context, *, backend: str, resume: bool
) -> dict[str, Any]:
    specs = build_oracle_development_specs(ctx)
    raw_dir = ctx.paths.oracle_development / "raw"
    results = evaluate_specs(
        ctx, specs, output_dir=raw_dir, backend=backend, resume=resume
    )
    rows = [
        feedback_result_row(ctx, result, phase="oracle_development")
        for result in results
    ]
    summary = summarize_oracle_development(ctx, rows)
    atomic_write_json(ctx.paths.oracle_development / "results.json", rows)
    atomic_write_json(ctx.paths.oracle_development / "summary.json", summary)
    write_csv(ctx.paths.oracle_development / "results.csv", rows)
    _update_state(
        ctx,
        oracle_development_complete=True,
        oracle_development_summary=summary,
    )
    return summary


def _selected_policy(ctx: Stage41R9Context) -> dict[str, Any] | None:
    path = ctx.paths.oracle_development / "summary.json"
    if not path.is_file():
        return None
    summary = read_json(path)
    policy_id = summary.get("selected_policy_id")
    if policy_id is None:
        return None
    return _terminal_policy_lookup(ctx).get(str(policy_id))


def build_oracle_holdout_specs(
    ctx: Stage41R9Context,
) -> list[dict[str, Any]]:
    policy = _selected_policy(ctx)
    if policy is None:
        return []
    terminal = ctx.cfg["terminal_feedback"]
    target = terminal["holdout_target"]
    source_scale = float(
        ctx.r8_ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.source_scale
    )
    specs: list[dict[str, Any]] = []
    for slew in terminal["actual_slew_scales"]:
        variant_id, _ = materialize_variant(
            ctx,
            slew_scale=float(slew),
            horizon_steps=int(terminal["horizon_steps"]),
        )
        for delay in terminal["actual_delay_steps"]:
            extra = _main_extra(
                ctx,
                actual_delay=int(delay),
                actual_slew=float(slew),
                modeled_delay=int(delay),
                modeled_slew=float(slew),
                policy=policy,
                calibration_token=None,
                trusted=True,
                controller_variant="r9_oracle_holdout",
            )
            specs.append(
                _make_spec(
                    phase="oracle_holdout",
                    scenario=(
                        f"{policy['policy_id']}__{target['target_id']}"
                        f"__d{delay}__s{float(slew):.1f}"
                    ),
                    category="oracle_holdout",
                    target=target,
                    controller_scale=source_scale,
                    environment_variant=variant_id,
                    extra=extra,
                )
            )
    return specs


def summarize_oracle_holdout(
    ctx: Stage41R9Context, rows: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    policy = _selected_policy(ctx)
    target = ctx.cfg["terminal_feedback"]["holdout_target"]
    expected = _expected_case_keys([target])
    policy_id = None if policy is None else str(policy["policy_id"])
    summary = _policy_summary(
        ctx,
        policy_id or "none",
        rows,
        expected,
    )
    development = read_json(
        ctx.paths.oracle_development / "summary.json"
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "phase": "oracle_holdout",
        "selected_policy_id": policy_id,
        "selection_target_id": development.get("development_target_id"),
        "holdout_target_id": target["target_id"],
        "holdout_was_not_used_for_candidate_selection": True,
        "n_rollouts": len(rows),
        "expected_rollouts": len(expected),
        "coverage_complete": summary["coverage_complete"],
        "all_environment_success": summary["all_environment_success"],
        "tracking_fraction": summary["tracking_fraction"],
        "minimum_signed_margin": summary["minimum_signed_margin"],
        "mean_signed_margin": summary["mean_signed_margin"],
        "first_350ms_prefix_exact_fraction": summary[
            "first_350ms_prefix_exact_fraction"
        ],
        "all_streaming_queues_consistent": summary[
            "all_streaming_queues_consistent"
        ],
        "maximum_terminal_pending_desired_physical_norm": summary[
            "maximum_terminal_pending_desired_physical_norm"
        ],
        "maximum_last5_issued_desired_rms": summary[
            "maximum_last5_issued_desired_rms"
        ],
        "passed": bool(
            development.get("passed")
            and policy is not None
            and summary["passed"]
        ),
    }


def run_oracle_holdout(
    ctx: Stage41R9Context, *, backend: str, resume: bool
) -> dict[str, Any]:
    specs = build_oracle_holdout_specs(ctx)
    if not specs:
        summary = {
            "schema_version": SCHEMA_VERSION,
            "stage": STAGE,
            "phase": "oracle_holdout",
            "status": "not_run_no_selected_development_policy",
            "passed": False,
        }
        atomic_write_json(ctx.paths.oracle_holdout / "summary.json", summary)
        _update_state(
            ctx,
            oracle_holdout_complete=False,
            oracle_holdout_summary=summary,
        )
        return summary
    raw_dir = ctx.paths.oracle_holdout / "raw"
    results = evaluate_specs(
        ctx, specs, output_dir=raw_dir, backend=backend, resume=resume
    )
    rows = [
        feedback_result_row(ctx, result, phase="oracle_holdout")
        for result in results
    ]
    summary = summarize_oracle_holdout(ctx, rows)
    atomic_write_json(ctx.paths.oracle_holdout / "results.json", rows)
    atomic_write_json(ctx.paths.oracle_holdout / "summary.json", summary)
    write_csv(ctx.paths.oracle_holdout / "results.csv", rows)
    _update_state(
        ctx,
        oracle_holdout_complete=True,
        oracle_holdout_summary=summary,
    )
    return summary


def _oracle_rows_by_case(
    ctx: Stage41R9Context,
) -> dict[tuple[str, int, float], dict[str, Any]]:
    selected = _selected_policy(ctx)
    if selected is None:
        return {}
    policy_id = str(selected["policy_id"])
    rows: list[dict[str, Any]] = []
    for path in (
        ctx.paths.oracle_development / "results.json",
        ctx.paths.oracle_holdout / "results.json",
    ):
        if path.is_file():
            rows.extend(read_json(path))
    output: dict[tuple[str, int, float], dict[str, Any]] = {}
    for row in rows:
        if str(row.get("policy_id")) != policy_id:
            continue
        key = (
            str(row["target_id"]),
            int(row["actual_action_delay_steps"]),
            float(row["actual_slew_scale"]),
        )
        if key in output:
            raise ValueError(f"duplicate selected oracle row: {key}")
        output[key] = row
    return output


def _oracle_raw_path_for_row(
    ctx: Stage41R9Context, row: Mapping[str, Any]
) -> Path:
    phase = str(row["phase"])
    root = (
        ctx.paths.oracle_development
        if phase == "oracle_development"
        else ctx.paths.oracle_holdout
    )
    return root / "raw" / f"{row['experiment_id']}.json.gz"


def build_calibrated_confirmation_specs(
    ctx: Stage41R9Context,
) -> list[dict[str, Any]]:
    policy = _selected_policy(ctx)
    holdout = (
        read_json(ctx.paths.oracle_holdout / "summary.json")
        if (ctx.paths.oracle_holdout / "summary.json").is_file()
        else {}
    )
    if policy is None or not bool(holdout.get("passed")):
        return []
    terminal = ctx.cfg["terminal_feedback"]
    confirmation = ctx.cfg["calibrated_confirmation"]
    tokens = source_calibration_tokens(ctx)
    source_scale = float(
        ctx.r8_ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.source_scale
    )
    specs: list[dict[str, Any]] = []
    for slew in terminal["actual_slew_scales"]:
        variant_id, _ = materialize_variant(
            ctx,
            slew_scale=float(slew),
            horizon_steps=int(terminal["horizon_steps"]),
        )
        for delay in terminal["actual_delay_steps"]:
            token = tokens.get((int(delay), float(slew)))
            if token is None:
                raise ValueError(f"missing R8 calibration token {(delay, slew)}")
            trusted = bool(
                token.get("success")
                and token.get("batch_trusted")
                and token.get("batch_trusted_correct")
                and not token.get("batch_wrong_accept")
            )
            if not trusted:
                raise RuntimeError(
                    "untrusted Stage4.1R8 calibration token cannot start "
                    f"Stage4.1R9 main control: delay={delay} slew={slew}"
                )
            modeled_delay = int(token["batch_selected_delay_steps"])
            modeled_slew = float(token["batch_selected_slew_scale"])
            if modeled_delay != int(delay) or not math.isclose(
                modeled_slew, float(slew), abs_tol=1e-12
            ):
                raise RuntimeError(
                    "trusted calibration token does not match the actual finite-envelope "
                    f"pair: actual=({delay}, {slew}) selected=({modeled_delay}, {modeled_slew})"
                )
            for target in confirmation["targets"]:
                extra = _main_extra(
                    ctx,
                    actual_delay=int(delay),
                    actual_slew=float(slew),
                    modeled_delay=modeled_delay,
                    modeled_slew=modeled_slew,
                    policy=policy,
                    calibration_token=str(token["experiment_id"]),
                    trusted=trusted,
                    controller_variant="r9_calibrated_confirmation",
                )
                specs.append(
                    _make_spec(
                        phase="calibrated_confirmation",
                        scenario=(
                            f"{policy['policy_id']}__{target['target_id']}"
                            f"__d{delay}__s{float(slew):.1f}"
                        ),
                        category="calibrated_confirmation",
                        target=target,
                        controller_scale=source_scale,
                        environment_variant=variant_id,
                        extra=extra,
                    )
                )
    return specs


def _full_trace_comparison(
    ctx: Stage41R9Context,
    calibrated_row: Mapping[str, Any],
    oracle_row: Mapping[str, Any],
    *,
    atol: float,
) -> dict[str, Any]:
    calibrated_path = (
        ctx.paths.calibrated_confirmation
        / "raw"
        / f"{calibrated_row['experiment_id']}.json.gz"
    )
    oracle_path = _oracle_raw_path_for_row(ctx, oracle_row)
    if not calibrated_path.is_file() or not oracle_path.is_file():
        return {
            "raw_files_available": False,
            "exact_equal": False,
            "numeric_equal": False,
            "max_abs_difference": math.inf,
        }
    comparison = _compare_results(
        read_json_gz(calibrated_path),
        read_json_gz(oracle_path),
        atol=atol,
        prefix_only=False,
    )
    comparison["raw_files_available"] = True
    return comparison


def summarize_calibrated_confirmation(
    ctx: Stage41R9Context, rows: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    cfg = ctx.cfg["calibrated_confirmation"]
    expected = _expected_case_keys(cfg["targets"])
    observed = {
        (
            str(row["target_id"]),
            int(row["actual_action_delay_steps"]),
            float(row["actual_slew_scale"]),
        )
        for row in rows
    }
    oracle = _oracle_rows_by_case(ctx)
    comparisons: list[dict[str, Any]] = []
    atol = float(cfg["numeric_trace_equivalence_atol"])
    for row in rows:
        key = (
            str(row["target_id"]),
            int(row["actual_action_delay_steps"]),
            float(row["actual_slew_scale"]),
        )
        oracle_row = oracle.get(key)
        comparison = (
            _full_trace_comparison(
                ctx, row, oracle_row, atol=atol
            )
            if oracle_row is not None
            else {
                "raw_files_available": False,
                "exact_equal": False,
                "numeric_equal": False,
                "max_abs_difference": math.inf,
            }
        )
        comparisons.append(
            {
                "target_id": key[0],
                "actual_delay_steps": key[1],
                "actual_slew_scale": key[2],
                "exact_trace_equal_to_oracle": bool(
                    comparison["exact_equal"]
                ),
                "numeric_trace_equal_to_oracle": bool(
                    comparison["numeric_equal"]
                ),
                "maximum_trace_abs_difference": comparison[
                    "max_abs_difference"
                ],
                "calibrated_margin": row.get(
                    "stage3_4_tracking_minimum_signed_margin"
                ),
                "oracle_margin": (
                    None
                    if oracle_row is None
                    else oracle_row.get(
                        "stage3_4_tracking_minimum_signed_margin"
                    )
                ),
            }
        )
    coverage = len(rows) == len(expected) and observed == expected
    exact_fraction = sum(
        bool(row["exact_trace_equal_to_oracle"]) for row in comparisons
    ) / max(len(comparisons), 1)
    numeric_fraction = sum(
        bool(row["numeric_trace_equal_to_oracle"]) for row in comparisons
    ) / max(len(comparisons), 1)
    tokens = {
        str(row.get("calibration_token"))
        for row in rows
        if row.get("calibration_token")
    }
    untrusted = sum(
        not bool(row.get("trusted_calibration_model")) for row in rows
    )
    passed = bool(
        coverage
        and len(oracle) == len(expected)
        and len(tokens) == 9
        and untrusted == 0
        and all(bool(row.get("success")) for row in rows)
        and all(
            bool(row.get("stage3_4_target_tracking_pass")) for row in rows
        )
        and all(
            bool(row.get("streaming_queue_consistent"))
            and not bool(row.get("pending_queue_bypassed"))
            for row in rows
        )
        and exact_fraction
        >= float(cfg["minimum_trace_equivalence_fraction"])
        and numeric_fraction >= 1.0 - 1e-12
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "phase": "calibrated_confirmation",
        "n_rollouts": len(rows),
        "expected_rollouts": len(expected),
        "coverage_complete": coverage,
        "n_successful": sum(bool(row.get("success")) for row in rows),
        "tracking_pass_fraction": sum(
            bool(row.get("stage3_4_target_tracking_pass")) for row in rows
        )
        / max(len(rows), 1),
        "distinct_calibration_tokens": len(tokens),
        "untrusted_main_start_count": untrusted,
        "exact_trace_equivalence_fraction": exact_fraction,
        "numeric_trace_equivalence_fraction": numeric_fraction,
        "numeric_trace_equivalence_atol": atol,
        "maximum_trace_abs_difference": max(
            (
                _as_float(
                    row.get("maximum_trace_abs_difference"), math.inf
                )
                for row in comparisons
            ),
            default=math.inf,
        ),
        "comparisons": comparisons,
        "passed": passed,
    }


def run_calibrated_confirmation(
    ctx: Stage41R9Context, *, backend: str, resume: bool
) -> dict[str, Any]:
    specs = build_calibrated_confirmation_specs(ctx)
    if not specs:
        summary = {
            "schema_version": SCHEMA_VERSION,
            "stage": STAGE,
            "phase": "calibrated_confirmation",
            "status": "not_run_oracle_holdout_not_closed",
            "passed": False,
        }
        atomic_write_json(
            ctx.paths.calibrated_confirmation / "summary.json", summary
        )
        _update_state(
            ctx,
            calibrated_confirmation_complete=False,
            calibrated_confirmation_summary=summary,
        )
        return summary
    raw_dir = ctx.paths.calibrated_confirmation / "raw"
    results = evaluate_specs(
        ctx, specs, output_dir=raw_dir, backend=backend, resume=resume
    )
    rows = [
        feedback_result_row(
            ctx, result, phase="calibrated_confirmation"
        )
        for result in results
    ]
    summary = summarize_calibrated_confirmation(ctx, rows)
    atomic_write_json(
        ctx.paths.calibrated_confirmation / "results.json", rows
    )
    atomic_write_json(
        ctx.paths.calibrated_confirmation / "summary.json", summary
    )
    write_csv(ctx.paths.calibrated_confirmation / "results.csv", rows)
    _update_state(
        ctx,
        calibrated_confirmation_complete=True,
        calibrated_confirmation_summary=summary,
    )
    return summary


# ---------------------------------------------------------------------------
# Restart availability audit and verdict
# ---------------------------------------------------------------------------


def run_restart_audit(ctx: Stage41R9Context) -> dict[str, Any]:
    folders = [
        str(value) for value in ctx.cfg["restart_audit"]["candidate_folders"]
    ]
    available: list[str] = []
    roots = {
        ctx.source_stage41r8_run,
        ctx.source_stage41r7_run,
        ctx.project_dir,
    }
    for name in folders:
        found = False
        for root in roots:
            for candidate in (
                root / name,
                root / "restart" / name,
                root / "restarts" / name,
            ):
                if candidate.is_dir():
                    found = True
                    break
            if found:
                break
        if found:
            available.append(name)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "phase": "restart_audit",
        "candidate_folders": folders,
        "available_folders": available,
        "true_restart_validation_available": len(available)
        >= int(ctx.cfg["restart_audit"]["minimum_distinct_folders"]),
        "true_restart_validation_performed": False,
        "availability_requirement_for_stage4_1r9": False,
        "audit_completed": True,
        "passed": True,
    }
    atomic_write_json(ctx.paths.restart_audit / "summary.json", summary)
    _update_state(
        ctx,
        restart_audit_complete=True,
        restart_audit_summary=summary,
    )
    return summary


def _phase_status(
    state: Mapping[str, Any], complete_key: str, summary_key: str
) -> str:
    if not bool(state.get(complete_key)):
        return "not_run"
    return "passed" if bool((state.get(summary_key) or {}).get("passed")) else "failed"


def analyze(ctx: Stage41R9Context) -> dict[str, Any]:
    state = read_json(ctx.paths.state)
    source = state.get("source_audit_summary") or {}
    development = state.get("oracle_development_summary") or {}
    holdout = state.get("oracle_holdout_summary") or {}
    confirmation = state.get("calibrated_confirmation_summary") or {}
    restart = state.get("restart_audit_summary") or {}
    primary_pass = bool(
        source.get("passed")
        and development.get("passed")
        and holdout.get("passed")
        and confirmation.get("passed")
    )
    verdict = (
        "STAGE4_1R9_FINITE_TRUSTED_CALIBRATION_TERMINAL_FEEDBACK_HOLD_CLOSURE"
        if primary_pass
        else "STAGE4_1R9_TERMINAL_FEEDBACK_HOLD_CLOSURE_INCOMPLETE"
    )
    summary = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "created_utc": utc_timestamp(),
        "verdict": verdict,
        "source_stage4_1r8_run": str(ctx.source_stage41r8_run),
        "source_audit_status": _phase_status(
            state, "source_audit_complete", "source_audit_summary"
        ),
        "oracle_development_status": _phase_status(
            state,
            "oracle_development_complete",
            "oracle_development_summary",
        ),
        "oracle_holdout_status": _phase_status(
            state, "oracle_holdout_complete", "oracle_holdout_summary"
        ),
        "calibrated_confirmation_status": _phase_status(
            state,
            "calibrated_confirmation_complete",
            "calibrated_confirmation_summary",
        ),
        "selected_terminal_policy": development.get("selected_policy_id"),
        "finite_terminal_feedback_envelope_validated": primary_pass,
        "first_350ms_main_mpc_frozen": True,
        "continuous_streaming_delay_queue_used": True,
        "open_loop_zero_tail_reused_as_success": False,
        "untrusted_default_main_start_allowed": False,
        "candidate_selection_target": ctx.cfg["terminal_feedback"][
            "development_target"
        ]["target_id"],
        "disjoint_holdout_target": ctx.cfg["terminal_feedback"][
            "holdout_target"
        ]["target_id"],
        "terminal_measurement_noise_robustness_validated": False,
        "true_restart_validation_available": bool(
            restart.get("true_restart_validation_available", False)
        ),
        "true_restart_validation_performed": False,
        "hardware_pre_shot_calibration_validated": False,
        "continuous_parameter_change_validated": False,
        "plant_parameter_robustness_validated": False,
        "unseen_hidden_state_robustness_validated": False,
        "deployment_robustness_validated": False,
        "finite_test_envelope_only": True,
        "warning": (
            "R9 can only test a clean-measurement terminal feedback architecture "
            "inside the same finite static digital twin. It does not validate true "
            "restart state, hidden vessel/eddy history, continuous actuator changes, "
            "plant-model error, noisy terminal sensing, or hardware deployment."
        ),
        "next_if_pass": (
            "Stage4.2 true restart and plant/actuator-parameter robustness. "
            "Do not start BC/DAgger/RL yet."
        ),
        "next_if_fail": (
            "Identify a dedicated terminal local model with bounded TSC probes and "
            "redesign the terminal regulator. Do not weaken the tracking gate and "
            "do not hand the 14-coil problem back to RL."
        ),
        "final_task": ctx.cfg["final_task"],
        "phases": {
            "source_audit": source,
            "oracle_development": development,
            "oracle_holdout": holdout,
            "calibrated_confirmation": confirmation,
            "restart_audit": restart,
        },
    }
    verdict_payload = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "verdict": verdict,
        "primary_pass": primary_pass,
        "selected_terminal_policy": development.get("selected_policy_id"),
        "next_if_pass": summary["next_if_pass"],
        "next_if_fail": summary["next_if_fail"],
        "final_task": ctx.cfg["final_task"],
    }
    atomic_write_json(ctx.paths.analysis / "stage4_1r9_summary.json", summary)
    atomic_write_json(
        ctx.paths.analysis / "stage4_1r9_verdict.json", verdict_payload
    )
    _update_state(
        ctx,
        finished=True,
        stop_reason="" if primary_pass else state.get("stop_reason", ""),
        verdict=verdict,
    )
    return summary


def execute(
    ctx: Stage41R9Context,
    *,
    command: str,
    backend: str,
    resume: bool,
) -> dict[str, Any]:
    prepared = prepare(ctx)
    if command == "prepare":
        return prepared
    source = run_source_audit(ctx)
    if command == "audit":
        return source
    if not source.get("passed"):
        _update_state(
            ctx, finished=True, stop_reason="source_audit_failed"
        )
        run_restart_audit(ctx)
        return analyze(ctx)
    if command in {"all", "oracle"}:
        development = run_oracle_development(
            ctx, backend=backend, resume=resume
        )
        if command == "oracle" and not development.get("passed"):
            return development
        if not development.get("passed"):
            _update_state(
                ctx,
                finished=True,
                stop_reason="oracle_development_failed",
            )
            run_restart_audit(ctx)
            return analyze(ctx)
        holdout = run_oracle_holdout(
            ctx, backend=backend, resume=resume
        )
        if command == "oracle":
            return holdout
        if not holdout.get("passed"):
            _update_state(
                ctx, finished=True, stop_reason="oracle_holdout_failed"
            )
            run_restart_audit(ctx)
            return analyze(ctx)
    if command in {"all", "startup"}:
        confirmation = run_calibrated_confirmation(
            ctx, backend=backend, resume=resume
        )
        if command == "startup":
            return confirmation
        if not confirmation.get("passed"):
            _update_state(
                ctx,
                finished=True,
                stop_reason="calibrated_confirmation_failed",
            )
    run_restart_audit(ctx)
    return analyze(ctx)


# ---------------------------------------------------------------------------
# Self-test and CLI
# ---------------------------------------------------------------------------


def self_test() -> dict[str, Any]:
    fake_trace = []
    for index in range(MAIN_CONTROL_STEPS):
        fake_trace.append(
            {
                "issued_mode_coefficients": [
                    float(index),
                    -float(index),
                    0.1 * index,
                ],
                "issued_desired_physical_mode_coefficients": [
                    0.01 * index,
                    -0.01 * index,
                    0.001 * index,
                ],
            }
        )
    queue = _initial_stream_queue(fake_trace, 2)
    issued = {
        "origin": "terminal_feedback",
        "origin_index": 0,
        "command": np.asarray([100.0, 0.0, 0.0]),
        "desired_physical": np.asarray([1.0, 0.0, 0.0]),
    }
    applied, queue_after = _stream_queue_apply(queue, issued, 2)
    queue_ok = bool(
        applied["origin"] == "main_control"
        and applied["origin_index"] == 33
        and len(queue_after) == 2
        and queue_after[0]["origin_index"] == 34
        and queue_after[1]["origin"] == "terminal_feedback"
    )
    trajectory = [
        {"R": 1.0, "Z": -1.0, "Ip": 100.0},
        {"R": 1.001, "Z": -1.002, "Ip": 102.0},
    ]
    measurement = _terminal_measurement(
        trajectory, np.asarray([1.0, -1.0, 100.0]), 0.01
    )
    measurement_ok = bool(
        np.allclose(measurement, [0.001, -0.002, 0.1, -0.2, 2.0])
    )
    config_path = (
        Path(__file__).resolve().parents[2]
        / "configs"
        / "stage4_1r9_terminal_template_mpc_feedback_hold_550ms.json"
    )
    config_ok = False
    if config_path.is_file():
        cfg = json.loads(config_path.read_text(encoding="utf-8"))
        validate_config(cfg)
        config_ok = True
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "queue_streaming_semantics_passed": queue_ok,
        "terminal_measurement_passed": measurement_ok,
        "config_guardrails_passed": config_ok,
        "passed": bool(queue_ok and measurement_ok and config_ok),
    }


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Stage4.1R9 terminal-template MPC feedback hold"
    )
    parser.add_argument(
        "--config",
        default=(
            "configs/"
            "stage4_1r9_terminal_template_mpc_feedback_hold_550ms.json"
        ),
    )
    parser.add_argument("--source-stage4-1r8-run")
    parser.add_argument("--run-dir")
    parser.add_argument("--backend", choices=["ray", "serial"], default="ray")
    parser.add_argument(
        "--command",
        choices=[
            "all",
            "prepare",
            "audit",
            "oracle",
            "startup",
            "analyze",
        ],
        default="all",
    )
    parser.add_argument("--resume", dest="resume", action="store_true")
    parser.add_argument("--no-resume", dest="resume", action="store_false")
    parser.set_defaults(resume=False)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        payload = self_test()
        print(json.dumps(_json_safe(payload), indent=2, allow_nan=False))
        if not payload["passed"]:
            raise SystemExit(1)
        return
    if not args.source_stage4_1r8_run:
        parser.error("--source-stage4-1r8-run is required")
    if not args.run_dir:
        parser.error("--run-dir is required")
    ctx = load_stage41r9_config(
        Path(args.config),
        source_stage41r8_run=Path(args.source_stage4_1r8_run),
        run_dir_override=Path(args.run_dir),
    )
    if args.command == "analyze":
        prepare(ctx)
        payload = analyze(ctx)
    else:
        payload = execute(
            ctx,
            command=args.command,
            backend=args.backend,
            resume=bool(args.resume),
        )
    print(json.dumps(_json_safe(payload), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
