"""Stage4.1R8 trusted batch calibration and queue-tail closure.

This stage is deliberately narrower than deployment robustness.  It fixes two
concrete Stage4.1R7 defects before any restart/plant-uncertainty expansion:

1. a completed calibration episode must not silently fall back to the initial
   (delay=0, slew=1.0) model when the online confidence lock was absent;
2. the 350 ms controller's finite action-delay queue must be drained before
   zero-current-increment tail actions are applied.

The main controller, observer, Stage3.4 target library, and 175x105 Jacobian are
otherwise frozen.  The output is still a finite digital-twin envelope and is
not hardware, true-restart, continuous-parameter, or deployment validation.
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
from types import SimpleNamespace
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

from . import stage2_trajectory_optimization as s2
from . import stage3_2_margin_long_hold_mpc as s32
from . import stage3_4_late_arrival_continuation_mpc as s34
from . import stage4_1r3_control_aware_robustness as r3
from . import stage4_1r4_targeted_closure as r4
from . import stage4_1r7_precontrol_calibration_queue_startup as r7
from tsc_rzip_rllib.utils.ray_runtime import ensure_ray_worker_plan

atomic_write_json = r7.atomic_write_json
atomic_write_json_gz = r7.atomic_write_json_gz
read_json = r7.read_json
read_json_gz = r7.read_json_gz
utc_timestamp = r7.utc_timestamp
write_csv = r7.write_csv

SCHEMA_VERSION = 1
STAGE = "Stage4.1R8"
CONTROLLER_REVISION = "trusted_batch_calibration_queue_tail_closure_v8"
EXPECTED_SOURCE_REVISION = "precontrol_calibration_queue_consistent_startup_v7"
PACKAGE_REVISION = "r8_batch_trust_queue_tail_v1"
MAIN_CONTROL_STEPS = 35
N_COILS = 14


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
        result = float(value)
        return result if math.isfinite(result) else float(default)
    except (TypeError, ValueError, OverflowError):
        return float(default)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _scenario_digest(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(_json_safe(dict(payload)), sort_keys=True, separators=(",", ":"), allow_nan=False)
    return "s41r8_" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:20]


def _array_digest(array: np.ndarray, prefix: str) -> str:
    arr = np.ascontiguousarray(np.asarray(array, dtype=np.float64))
    header = json.dumps({"shape": arr.shape, "dtype": str(arr.dtype)}, sort_keys=True).encode("utf-8")
    return f"{prefix}_" + hashlib.sha256(header + arr.tobytes()).hexdigest()[:20]


def _result_complete(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        payload = read_json_gz(path)
    except Exception:
        return False
    return bool(payload.get("success", False)) and bool(payload.get("experiment_id"))


def _read_json_gz_direct(path: Path) -> dict[str, Any]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise TypeError(f"expected object in {path}")
    return payload


def _candidate_key(delay: int, slew: float) -> str:
    return f"d{int(delay)}_s{float(slew):.3f}"


def _candidate_tuple(key: str) -> tuple[int, float]:
    try:
        left, right = str(key).split("_s", 1)
        return int(left[1:]), float(right)
    except Exception as exc:
        raise ValueError(f"invalid delay/slew candidate key {key!r}") from exc


def _available_memory_gb() -> float:
    try:
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            if line.startswith("MemAvailable:"):
                return float(line.split()[1]) / (1024.0 * 1024.0)
    except Exception:
        pass
    return math.nan


# ---------------------------------------------------------------------------
# Paths and source context
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Stage41R8Paths:
    run_dir: Path
    state: Path
    manifest: Path
    source_reference: Path
    source_audit: Path
    source_replay: Path
    integrated_calibration: Path
    oracle_queue_tail: Path
    calibrated_startup: Path
    restart_audit: Path
    analysis: Path
    variants: Path

    @classmethod
    def from_run_dir(cls, run_dir: Path) -> "Stage41R8Paths":
        run_dir = run_dir.resolve()
        return cls(
            run_dir=run_dir,
            state=run_dir / "stage4_1r8_state.json",
            manifest=run_dir / "stage4_1r8_manifest.json",
            source_reference=run_dir / "source_stage4_1r7_reference",
            source_audit=run_dir / "stage4_1r8_source_audit",
            source_replay=run_dir / "stage4_1r8_batch_source_replay",
            integrated_calibration=run_dir / "stage4_1r8_integrated_calibration",
            oracle_queue_tail=run_dir / "stage4_1r8_oracle_queue_tail",
            calibrated_startup=run_dir / "stage4_1r8_calibrated_startup",
            restart_audit=run_dir / "stage4_1r8_restart_audit",
            analysis=run_dir / "stage4_1r8_analysis",
            variants=run_dir / "stage4_1r8_environment_variants",
        )


@dataclass
class Stage41R8Context:
    cfg: dict[str, Any]
    paths: Stage41R8Paths
    project_dir: Path
    source_stage41r7_run: Path
    source_manifest: dict[str, Any]
    source_state: dict[str, Any]
    source_cfg: dict[str, Any]
    source_verdict: dict[str, Any]
    source_stage41r6_run: Path
    r7_ctx: r7.Stage41R7Context
    source_fingerprint: dict[str, Any]


def _required_source_files(run_dir: Path) -> list[Path]:
    files = [
        run_dir / "stage4_1r7_manifest.json",
        run_dir / "stage4_1r7_state.json",
        run_dir / "stage4_1r7_config.resolved.json",
        run_dir / "stage4_1r7_analysis" / "stage4_1r7_verdict.json",
        run_dir / "stage4_1r7_precontrol_calibration" / "summary.json",
        run_dir / "stage4_1r7_precontrol_calibration" / "results.json",
        run_dir / "stage4_1r7_queue_consistent_startup" / "summary.json",
        run_dir / "stage4_1r7_queue_consistent_startup" / "results.json",
        run_dir / "stage4_1r7_paired_confirmation" / "summary.json",
        run_dir / "stage4_1r7_paired_confirmation" / "results.json",
    ]
    for phase in (
        "stage4_1r7_precontrol_calibration",
        "stage4_1r7_queue_consistent_startup",
        "stage4_1r7_paired_confirmation",
    ):
        files.extend(sorted((run_dir / phase / "raw").glob("*.json.gz")))
    return files


def _source_inventory(run_dir: Path) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    for path in _required_source_files(run_dir):
        if not path.is_file():
            raise FileNotFoundError(path)
        entries.append({
            "relative_path": path.relative_to(run_dir).as_posix(),
            "size_bytes": path.stat().st_size,
            "sha256": _sha256_file(path),
        })
    canonical = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {
        "schema_version": 1,
        "n_files": len(entries),
        "total_bytes": sum(int(item["size_bytes"]) for item in entries),
        "digest": _sha256_bytes(canonical),
        "files": entries,
    }


def _resolve_source_r6(project_dir: Path, source_manifest: Mapping[str, Any]) -> Path:
    raw = str(source_manifest.get("source_stage4_1r6_run", "")).strip()
    if not raw:
        raise ValueError("Stage4.1R7 manifest has no source_stage4_1r6_run")
    path = Path(raw).expanduser()
    if not path.exists():
        fallback = project_dir / "stage4_1r6_runs" / path.name
        if fallback.exists():
            path = fallback
    path = path.resolve()
    for relative in (
        "stage4_1r6_manifest.json",
        "stage4_1r6_state.json",
        "stage4_1r6_config.resolved.json",
    ):
        if not (path / relative).is_file():
            raise FileNotFoundError(f"source Stage4.1R6 is incomplete: {path / relative}")
    return path


def _validate_source_stage41r7(run_dir: Path, cfg: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    for path in _required_source_files(run_dir):
        if not path.is_file():
            raise FileNotFoundError(f"required Stage4.1R7 source file is missing: {path}")
    manifest = read_json(run_dir / "stage4_1r7_manifest.json")
    state = read_json(run_dir / "stage4_1r7_state.json")
    source_cfg = read_json(run_dir / "stage4_1r7_config.resolved.json")
    verdict = read_json(run_dir / "stage4_1r7_analysis" / "stage4_1r7_verdict.json")
    req = cfg["source_requirement"]
    if manifest.get("stage") != req["required_stage"]:
        raise ValueError(f"source stage mismatch: {manifest.get('stage')!r}")
    if manifest.get("controller_revision") != req["required_controller_revision"]:
        raise ValueError("source Stage4.1R7 controller revision mismatch")
    if bool(req.get("require_finished", True)) and state.get("finished") is not True:
        raise ValueError("source Stage4.1R7 run is not finished")
    if bool(req.get("require_source_audit_passed", True)) and not bool(
        (state.get("source_audit_summary") or {}).get("passed", False)
    ):
        raise ValueError("source Stage4.1R7 source audit did not pass")
    if bool(req.get("require_precontrol_calibration_passed", True)) and not bool(
        (state.get("calibration_summary") or {}).get("passed", False)
    ):
        raise ValueError("source Stage4.1R7 pre-control calibration did not pass")
    if bool(req.get("require_queue_consistent_startup_passed", True)) and not bool(
        (state.get("startup_summary") or {}).get("precalibrated_startup_passed", False)
    ):
        raise ValueError("source Stage4.1R7 queue-consistent startup did not pass")
    if not bool(req.get("allow_paired_confirmation_failure", False)) and not bool(
        (state.get("confirmation_summary") or {}).get("passed", False)
    ):
        raise ValueError("source Stage4.1R7 paired confirmation did not pass")
    expected_counts = {
        "stage4_1r7_precontrol_calibration": int(req["require_raw_precontrol_calibration_count"]),
        "stage4_1r7_queue_consistent_startup": int(req["require_raw_startup_count"]),
        "stage4_1r7_paired_confirmation": int(req["require_raw_paired_confirmation_count"]),
    }
    for phase, expected in expected_counts.items():
        observed = len(list((run_dir / phase / "raw").glob("*.json.gz")))
        if observed != expected:
            raise ValueError(f"source {phase} raw count {observed} != expected {expected}")
    return manifest, state, source_cfg, verdict


def load_stage41r8_config(
    config_path: Path,
    *,
    source_stage41r7_run: Path,
    run_dir_override: Path | None = None,
) -> Stage41R8Context:
    config_path = config_path.expanduser().resolve()
    cfg = read_json(config_path)
    if cfg.get("controller_revision") != CONTROLLER_REVISION:
        raise ValueError("Stage4.1R8 controller_revision mismatch")
    project_dir = config_path.parents[1]
    source_stage41r7_run = source_stage41r7_run.expanduser().resolve()
    manifest, state, source_cfg, verdict = _validate_source_stage41r7(source_stage41r7_run, cfg)
    source_r6 = _resolve_source_r6(project_dir, manifest)
    if run_dir_override is None:
        root = project_dir / str(cfg.get("output_root", "stage4_1r8_runs"))
        run_dir = root / f"{cfg.get('run_name', 'stage4_1r8')}_{utc_timestamp()}"
    else:
        run_dir = run_dir_override.expanduser().resolve()
    paths = Stage41R8Paths.from_run_dir(run_dir)
    r7_ctx = r7.load_stage41r7_config(
        source_stage41r7_run / "stage4_1r7_config.resolved.json",
        source_stage41r6_run=source_r6,
        run_dir_override=run_dir,
    )
    storage = cfg["storage"]
    env_cfg = copy.deepcopy(r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.source_env_cfg)
    env_cfg["tsc_timeout_s"] = float(cfg["runtime"]["tsc_timeout_s"])
    env_cfg["tsc_workspace_root"] = str(
        Path(os.environ.get("STAGE4_1R8_TSC_WORKSPACE_ROOT", storage["tsc_workspace_root"]))
        .expanduser().resolve()
    )
    env_cfg["run_root"] = str(
        Path(os.environ.get("STAGE4_1R8_TSC_RUN_ROOT", storage["tsc_run_root"]))
        .expanduser().resolve()
    )
    # Compatibility alias for wrappers that expose the storage field name.
    env_cfg["tsc_run_root"] = env_cfg["run_root"]
    env_cfg["keep_tsc_workspace"] = False
    env_cfg["cleanup_episode_dir"] = True
    env_cfg["keep_failed_episode_dir"] = bool(storage.get("keep_failed_episode_dir", False))
    env_cfg["keep_last_n_failed_episode_dirs"] = int(storage.get("keep_last_n_failed_episode_dirs", 0))
    train_cfg = r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.source_train_cfg
    train_cfg["env_config"] = str(paths.run_dir / "env_config.resolved.json")
    r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.base34.env_cfg = env_cfg
    r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.base34.train_cfg = train_cfg
    return Stage41R8Context(
        cfg=cfg,
        paths=paths,
        project_dir=project_dir,
        source_stage41r7_run=source_stage41r7_run,
        source_manifest=manifest,
        source_state=state,
        source_cfg=source_cfg,
        source_verdict=verdict,
        source_stage41r6_run=source_r6,
        r7_ctx=r7_ctx,
        source_fingerprint=_source_inventory(source_stage41r7_run),
    )


def validate_config(ctx: Stage41R8Context) -> None:
    cfg = ctx.cfg
    selector = cfg["batch_selector"]
    if sorted(map(int, selector["delay_candidates"])) != [0, 1, 2]:
        raise ValueError("R8 finite delay bank must remain [0,1,2]")
    if sorted(map(float, selector["slew_candidates"])) != [0.9, 1.0, 1.1]:
        raise ValueError("R8 finite slew bank must remain [0.9,1.0,1.1]")
    if float(selector["minimum_full_delta_log_likelihood"]) <= 0.0:
        raise ValueError("batch full likelihood threshold must be positive")
    if float(selector["minimum_split_delta_log_likelihood"]) <= 0.0:
        raise ValueError("batch split likelihood threshold must be positive")
    cal = cfg["integrated_calibration"]
    plan = np.asarray(cal["mode_command_plan"], dtype=float)
    if plan.shape != (10, 3) or not np.all(np.isfinite(plan)):
        raise ValueError("integrated calibration plan must have shape (10,3)")
    if not np.allclose(plan.sum(axis=0), 0.0, atol=1e-12):
        raise ValueError("integrated calibration plan must be zero-net in all three modes")
    if not np.allclose(plan[-2:], 0.0, atol=1e-12):
        raise ValueError("last two calibration commands must flush the delay bank with zeros")
    policies = cfg["oracle_queue_tail"]["policies"]
    if not policies:
        raise ValueError("at least one queue-tail policy is required")
    seen: set[str] = set()
    for policy in policies:
        pid = str(policy["policy_id"])
        if pid in seen:
            raise ValueError(f"duplicate queue-tail policy {pid}")
        seen.add(pid)
        horizon = int(policy["horizon_steps"])
        tail_steps = int(policy["tail_steps"])
        if horizon != MAIN_CONTROL_STEPS + tail_steps:
            raise ValueError(f"policy {pid}: horizon must equal 35 + tail_steps")
        if tail_steps < max(map(int, cfg["oracle_queue_tail"]["actual_delay_steps"])):
            raise ValueError(f"policy {pid}: tail is too short to drain the maximum delay queue")
        arrivals = list(map(int, policy["allowed_arrival_steps"]))
        if not arrivals or max(arrivals) > horizon:
            raise ValueError(f"policy {pid}: invalid arrival steps")
    if float(cal.get("maximum_final_max_abs_coil_residual_A", 0.0)) <= 0.0:
        raise ValueError("integrated calibration final coil-current residual limit must be positive")
    if not bool(cfg["calibrated_startup"].get("require_zero_untrusted_main_starts", True)):
        raise ValueError("R8 must never launch main control from an untrusted calibration")
    if float(cfg["calibrated_startup"].get("numeric_trace_equivalence_atol", -1.0)) < 0.0:
        raise ValueError("numeric trace-equivalence tolerance must be non-negative")


def runtime_preflight(ctx: Stage41R8Context) -> dict[str, Any]:
    requested = int(os.environ.get("STAGE4_1R8_WORKERS", ctx.cfg["parallel"]["n_workers"]))
    logical = int(os.cpu_count() or 1)
    reserve = int(ctx.cfg["parallel"].get("reserve_logical_cpus", 16))
    ceiling = max(1, logical - reserve)
    if requested > ceiling:
        raise RuntimeError(
            f"Stage4.1R8 requests {requested} workers but safe ceiling is {ceiling} "
            f"({logical} visible, reserve={reserve}); no silent fallback is allowed"
        )
    memory = _available_memory_gb()
    configured = int(ctx.cfg["parallel"]["n_workers"])
    minimum = float(ctx.cfg["parallel"].get("minimum_available_memory_gb", 72.0)) * requested / configured
    if math.isfinite(memory) and memory < minimum:
        raise RuntimeError(f"Stage4.1R8 requires {minimum:.1f} GiB available memory; {memory:.1f} GiB visible")
    soft_fd, hard_fd = resource.getrlimit(resource.RLIMIT_NOFILE)
    required_fd = max(1024, requested * 16)
    if soft_fd < required_fd:
        raise RuntimeError(f"open-file soft limit {soft_fd} is below required {required_fd}")
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
        "source_replay_complete": False,
        "integrated_calibration_complete": False,
        "oracle_queue_tail_complete": False,
        "calibrated_startup_complete": False,
        "restart_audit_complete": False,
        "finished": False,
        "stop_reason": "",
        "updated_utc": utc_timestamp(),
    }


def _update_state(ctx: Stage41R8Context, **values: Any) -> dict[str, Any]:
    state = read_json(ctx.paths.state) if ctx.paths.state.exists() else initial_state()
    state.update(_json_safe(values))
    state["updated_utc"] = utc_timestamp()
    atomic_write_json(ctx.paths.state, state)
    return state


def initialize_run(ctx: Stage41R8Context, preflight: Mapping[str, Any]) -> None:
    for path in (
        ctx.paths.run_dir,
        ctx.paths.source_reference,
        ctx.paths.source_audit,
        ctx.paths.source_replay,
        ctx.paths.integrated_calibration,
        ctx.paths.oracle_queue_tail,
        ctx.paths.calibrated_startup,
        ctx.paths.restart_audit,
        ctx.paths.analysis,
        ctx.paths.variants,
    ):
        path.mkdir(parents=True, exist_ok=True)
    atomic_write_json(ctx.paths.run_dir / "stage4_1r8_config.resolved.json", ctx.cfg)
    atomic_write_json(
        ctx.paths.run_dir / "env_config.resolved.json",
        ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.source_env_cfg,
    )
    atomic_write_json(
        ctx.paths.run_dir / "train_config.resolved.json",
        ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.source_train_cfg,
    )
    reference_files = {
        "stage4_1r7_manifest.json": ctx.source_manifest,
        "stage4_1r7_state.json": ctx.source_state,
        "stage4_1r7_config.resolved.json": ctx.source_cfg,
        "stage4_1r7_verdict.json": ctx.source_verdict,
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
        "source_stage4_1r7_run": str(ctx.source_stage41r7_run),
        "source_stage4_1r6_run": str(ctx.source_stage41r6_run),
        "source_fingerprint": ctx.source_fingerprint,
        "workers": dict(preflight),
        "main_controller_changed": False,
        "observer_changed": False,
        "target_library_changed": False,
        "jacobian_changed": False,
        "calibration_selector_changed": True,
        "tail_queue_semantics_changed": True,
        "untrusted_default_main_start_forbidden": True,
        "finite_test_envelope_only": True,
        "hardware_pre_shot_calibration_validated": False,
        "true_restart_validation_performed": False,
        "continuous_parameter_change_validated": False,
        "deployment_robustness_validated": False,
        "final_task": ctx.cfg["final_task"],
    }
    if ctx.paths.manifest.exists():
        old = read_json(ctx.paths.manifest)
        for key in ("controller_revision", "source_stage4_1r7_run"):
            if str(old.get(key)) != str(manifest.get(key)):
                raise ValueError(f"resume manifest mismatch for {key}")
        old_digest = (old.get("source_fingerprint") or {}).get("digest")
        if old_digest != ctx.source_fingerprint.get("digest"):
            raise ValueError("Stage4.1R7 source fingerprint changed since the R8 run was prepared")
    atomic_write_json(ctx.paths.manifest, manifest)
    if not ctx.paths.state.exists():
        atomic_write_json(ctx.paths.state, initial_state())


# ---------------------------------------------------------------------------
# Trusted batch finite-bank selector
# ---------------------------------------------------------------------------


def _score_split(
    residual_rows: Sequence[Mapping[str, float]],
    indices: Sequence[int],
    *,
    noise_sigma_a: float,
    nominal_max_delta_a: float,
    n_coils: int,
) -> dict[str, Any]:
    if not indices:
        raise ValueError("empty evidence split")
    keys = sorted(residual_rows[0])
    scores = {
        key: float(sum(float(residual_rows[index][key]) ** 2 for index in indices))
        for key in keys
    }
    ordered = sorted(keys, key=lambda key: (scores[key], _candidate_tuple(key)[0], abs(_candidate_tuple(key)[1] - 1.0)))
    best = ordered[0]
    second = ordered[1] if len(ordered) > 1 else ordered[0]
    best_score = scores[best]
    second_score = scores[second]
    score_gap = second_score - best_score
    ratio = 1.0e12 if best_score <= 1e-30 and second_score > best_score else second_score / max(best_score, 1e-30)
    if noise_sigma_a > 0.0:
        delta_log_likelihood = (
            score_gap * float(n_coils) * float(nominal_max_delta_a) ** 2
            / (2.0 * float(noise_sigma_a) ** 2)
        )
    else:
        delta_log_likelihood = math.inf if score_gap > 0.0 else 0.0
    return {
        "indices": list(map(int, indices)),
        "best_key": best,
        "second_key": second,
        "best_delay_steps": _candidate_tuple(best)[0],
        "best_slew_scale": _candidate_tuple(best)[1],
        "best_score": best_score,
        "second_best_score": second_score,
        "score_gap": score_gap,
        "score_ratio": float(min(ratio, 1.0e12)),
        "delta_log_likelihood": float(min(delta_log_likelihood, 1.0e12)),
        "scores": scores,
    }


def trusted_batch_select_from_residuals(
    residual_rows: Sequence[Mapping[str, float]],
    *,
    noise_sigma_a: float,
    nominal_max_delta_a: float,
    selector_cfg: Mapping[str, Any],
) -> dict[str, Any]:
    if not residual_rows:
        return {
            "selector_revision": selector_cfg.get("selector_revision"),
            "trusted": False,
            "rejection_reasons": ["empty_residual_evidence"],
            "selected_delay_steps": None,
            "selected_slew_scale": None,
        }
    expected = {
        _candidate_key(delay, slew)
        for delay in map(int, selector_cfg["delay_candidates"])
        for slew in map(float, selector_cfg["slew_candidates"])
    }
    for index, row in enumerate(residual_rows):
        if set(row) != expected:
            raise ValueError(f"residual candidate bank mismatch at row {index}")
        if not all(math.isfinite(float(value)) and float(value) >= 0.0 for value in row.values()):
            raise ValueError(f"non-finite/negative residual at row {index}")
    n = len(residual_rows)
    midpoint = n // 2
    split_indices = {
        "full": list(range(n)),
        "first_half": list(range(0, midpoint)),
        "second_half": list(range(midpoint, n)),
        "odd": list(range(1, n, 2)),
        "even": list(range(0, n, 2)),
    }
    if not split_indices["first_half"] or not split_indices["second_half"]:
        raise ValueError("batch selector requires at least two observations")
    splits = {
        name: _score_split(
            residual_rows,
            indices,
            noise_sigma_a=float(noise_sigma_a),
            nominal_max_delta_a=float(nominal_max_delta_a),
            n_coils=int(selector_cfg.get("nominal_coil_count", N_COILS)),
        )
        for name, indices in split_indices.items()
    }
    full_best = str(splits["full"]["best_key"])
    consensus = all(str(row["best_key"]) == full_best for row in splits.values())
    loo_best: list[str] = []
    if n > 2:
        for dropped in range(n):
            indices = [index for index in range(n) if index != dropped]
            loo = _score_split(
                residual_rows,
                indices,
                noise_sigma_a=float(noise_sigma_a),
                nominal_max_delta_a=float(nominal_max_delta_a),
                n_coils=int(selector_cfg.get("nominal_coil_count", N_COILS)),
            )
            loo_best.append(str(loo["best_key"]))
    loo_consensus = all(value == full_best for value in loo_best)
    rejection_reasons: list[str] = []
    if bool(selector_cfg.get("require_full_first_second_odd_even_consensus", True)) and not consensus:
        rejection_reasons.append("split_best_disagreement")
    if bool(selector_cfg.get("require_leave_one_out_consensus", True)) and not loo_consensus:
        rejection_reasons.append("leave_one_out_best_disagreement")
    if float(noise_sigma_a) > 0.0:
        if float(splits["full"]["delta_log_likelihood"]) < float(
            selector_cfg["minimum_full_delta_log_likelihood"]
        ):
            rejection_reasons.append("full_likelihood_gap_below_threshold")
        for name in ("first_half", "second_half", "odd", "even"):
            if float(splits[name]["delta_log_likelihood"]) < float(
                selector_cfg["minimum_split_delta_log_likelihood"]
            ):
                rejection_reasons.append(f"{name}_likelihood_gap_below_threshold")
    else:
        if float(splits["full"]["score_ratio"]) < float(selector_cfg["minimum_clean_score_ratio"]):
            rejection_reasons.append("clean_score_ratio_below_threshold")
        if float(splits["full"]["score_gap"]) < float(selector_cfg["minimum_clean_absolute_score_gap"]):
            rejection_reasons.append("clean_score_gap_below_threshold")
    trusted = not rejection_reasons
    delay, slew = _candidate_tuple(full_best)
    return _json_safe({
        "selector_revision": selector_cfg.get("selector_revision"),
        "observations": n,
        "noise_sigma_A": float(noise_sigma_a),
        "nominal_max_delta_A": float(nominal_max_delta_a),
        "ranked_best_delay_steps": delay,
        "ranked_best_slew_scale": slew,
        "trusted": trusted,
        "selected_delay_steps": delay if trusted else None,
        "selected_slew_scale": slew if trusted else None,
        "rejection_reasons": rejection_reasons,
        "split_consensus": consensus,
        "leave_one_out_consensus": loo_consensus,
        "leave_one_out_best_keys": loo_best,
        "splits": splits,
    })


def batch_select_calibration_result(
    result: Mapping[str, Any],
    *,
    selector_cfg: Mapping[str, Any],
    nominal_max_delta_a: float,
) -> dict[str, Any]:
    trace = list(result.get("calibration_trace") or [])
    residual_rows: list[dict[str, float]] = []
    for index, row in enumerate(trace):
        update = row.get("estimator_update") or {}
        residuals = update.get("instantaneous_residuals")
        if not isinstance(residuals, dict):
            raise ValueError(f"calibration trace row {index} has no instantaneous residual bank")
        residual_rows.append({str(key): float(value) for key, value in residuals.items()})
    spec = result.get("spec") or {}
    selector = trusted_batch_select_from_residuals(
        residual_rows,
        noise_sigma_a=float(spec.get("coil_current_measurement_noise_A", 0.0)),
        nominal_max_delta_a=float(nominal_max_delta_a),
        selector_cfg=selector_cfg,
    )
    actual_delay = int(spec.get("action_delay_steps", result.get("actual_delay_steps", 0)))
    actual_slew = float(spec.get("slew_scale", result.get("actual_slew_scale", 1.0)))
    ranked_correct = bool(
        int(selector["ranked_best_delay_steps"]) == actual_delay
        and math.isclose(float(selector["ranked_best_slew_scale"]), actual_slew, abs_tol=1e-12)
    )
    trusted_correct = bool(
        selector["trusted"]
        and int(selector["selected_delay_steps"]) == actual_delay
        and math.isclose(float(selector["selected_slew_scale"]), actual_slew, abs_tol=1e-12)
    )
    selector.update({
        "actual_delay_steps": actual_delay,
        "actual_slew_scale": actual_slew,
        "ranked_model_correct": ranked_correct,
        "trusted_model_correct": trusted_correct,
        "wrong_accept": bool(selector["trusted"] and not trusted_correct),
    })
    return selector


# ---------------------------------------------------------------------------
# Source audit and source-noise replay
# ---------------------------------------------------------------------------


def _phase_raw_paths(ctx: Stage41R8Context, phase: str) -> list[Path]:
    return sorted((ctx.source_stage41r7_run / phase / "raw").glob("*.json.gz"))


def _load_source_calibration_traces(ctx: Stage41R8Context) -> tuple[list[dict[str, Any]], dict[tuple[int, float], dict[str, Any]]]:
    noisy: list[dict[str, Any]] = []
    clean_by_pair: dict[tuple[int, float], dict[str, Any]] = {}
    seen_noisy: set[tuple[int, float, int]] = set()
    for path in _phase_raw_paths(ctx, "stage4_1r7_precontrol_calibration"):
        result = _read_json_gz_direct(path)
        spec = result["spec"]
        pair = (int(spec["action_delay_steps"]), float(spec["slew_scale"]))
        sigma = float(spec.get("coil_current_measurement_noise_A", 0.0))
        if sigma == 0.0:
            clean_by_pair[pair] = result
        else:
            seed = int(spec.get("coil_current_measurement_seed", 0))
            key = (pair[0], pair[1], seed)
            if key not in seen_noisy:
                seen_noisy.add(key)
                noisy.append(result)
    for path in _phase_raw_paths(ctx, "stage4_1r7_paired_confirmation"):
        outer = _read_json_gz_direct(path)
        result = outer.get("paired_calibration_result") or {}
        if not result:
            continue
        spec = result["spec"]
        pair = (int(spec["action_delay_steps"]), float(spec["slew_scale"]))
        seed = int(spec.get("coil_current_measurement_seed", 0))
        key = (pair[0], pair[1], seed)
        if key in seen_noisy:
            continue
        seen_noisy.add(key)
        noisy.append(result)
    noisy.sort(key=lambda result: (
        int(result["spec"]["action_delay_steps"]),
        float(result["spec"]["slew_scale"]),
        int(result["spec"].get("coil_current_measurement_seed", 0)),
    ))
    return noisy, clean_by_pair


def _oracle_source_rows(ctx: Stage41R8Context) -> list[dict[str, Any]]:
    rows = read_json(ctx.source_stage41r7_run / "stage4_1r7_queue_consistent_startup" / "results.json")
    return [row for row in rows if str(row.get("controller_variant")) == "oracle"]


def _source_startup_raw_by_case(ctx: Stage41R8Context) -> dict[tuple[str, int, float, str], dict[str, Any]]:
    output: dict[tuple[str, int, float, str], dict[str, Any]] = {}
    for path in _phase_raw_paths(ctx, "stage4_1r7_queue_consistent_startup"):
        result = _read_json_gz_direct(path)
        spec = result["spec"]
        key = (
            str(spec["target_id"]),
            int(spec["action_delay_steps"]),
            float(spec["slew_scale"]),
            str(spec["controller_variant"]),
        )
        output[key] = result
    return output


def run_source_audit(ctx: Stage41R8Context) -> dict[str, Any]:
    source_state = ctx.source_state
    startup = source_state.get("startup_summary") or {}
    confirmation = source_state.get("confirmation_summary") or {}
    oracle_rows = _oracle_source_rows(ctx)
    oracle_feasible = sum(bool(row.get("stage3_4_target_tracking_pass")) for row in oracle_rows)
    oracle_total = len(oracle_rows)
    paired_expected_groups = int((confirmation or {}).get("distinct_groups_confirmed", 0))
    paired_gate_structurally_possible = bool(oracle_feasible == oracle_total)
    raw_by_case = _source_startup_raw_by_case(ctx)
    dropped_examples: list[dict[str, Any]] = []
    total_pending_dropped = 0
    for (target, delay, slew, variant), result in sorted(raw_by_case.items()):
        if variant != "oracle" or not math.isclose(slew, 0.9, abs_tol=1e-12) or delay <= 0:
            continue
        trace = list(result.get("control_trace") or [])
        if len(trace) != MAIN_CONTROL_STEPS:
            continue
        pending_indices = list(range(MAIN_CONTROL_STEPS - delay, MAIN_CONTROL_STEPS))
        pending = [np.asarray(trace[index]["issued_mode_coefficients"], dtype=float) for index in pending_indices]
        tail_actions = [
            np.asarray(row.get("action_norm_tsc", np.zeros(N_COILS)), dtype=float)
            for row in (result.get("trajectory") or [])[MAIN_CONTROL_STEPS + 1 :]
        ]
        zero_tail = bool(tail_actions and all(np.max(np.abs(action)) <= 1e-15 for action in tail_actions))
        nonzero_pending = sum(float(np.linalg.norm(command)) > 1e-12 for command in pending)
        if zero_tail and nonzero_pending:
            total_pending_dropped += nonzero_pending
            dropped_examples.append({
                "target_id": target,
                "actual_delay_steps": delay,
                "actual_slew_scale": slew,
                "pending_source_steps": pending_indices,
                "pending_command_norms": [float(np.linalg.norm(command)) for command in pending],
                "legacy_tail_actions_zero": True,
                "dropped_pending_command_count": nonzero_pending,
            })
    action_metric_zero_count = 0
    raw_nonzero_action_count = 0
    source_rows = read_json(ctx.source_stage41r7_run / "stage4_1r7_queue_consistent_startup" / "results.json")
    for row in source_rows:
        if math.isclose(float(row.get("action_rms", 0.0)), 0.0, abs_tol=1e-15):
            action_metric_zero_count += 1
    for result in raw_by_case.values():
        actions = np.asarray(
            [row.get("action_norm_tsc", []) for row in (result.get("trajectory") or [])[1:]],
            dtype=float,
        )
        if actions.size and float(np.sqrt(np.mean(actions**2))) > 1e-12:
            raw_nonzero_action_count += 1
    noisy, _ = _load_source_calibration_traces(ctx)
    online_untrusted_default = 0
    online_ranked_actual_but_unlocked = 0
    for result in noisy:
        spec = result["spec"]
        estimator = result.get("adaptive_estimator_summary") or {}
        actual = (int(spec["action_delay_steps"]), float(spec["slew_scale"]))
        selected = (
            _as_int(estimator.get("selected_delay_steps"), -999),
            _as_float(estimator.get("selected_slew_scale"), -999.0),
        )
        ranked = (
            _as_int(estimator.get("best_delay_steps"), -999),
            _as_float(estimator.get("best_slew_scale"), -999.0),
        )
        no_lock = estimator.get("first_confident_lock_step") is None
        if no_lock and selected == (0, 1.0):
            online_untrusted_default += 1
        if no_lock and ranked[0] == actual[0] and math.isclose(ranked[1], actual[1], abs_tol=1e-12):
            online_ranked_actual_but_unlocked += 1
    summary = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "phase": "source_audit",
        "source_stage4_1r7_run": str(ctx.source_stage41r7_run),
        "source_finished": bool(source_state.get("finished", False)),
        "source_stop_reason": source_state.get("stop_reason"),
        "source_precontrol_calibration_passed": bool((source_state.get("calibration_summary") or {}).get("passed", False)),
        "source_queue_startup_passed": bool(startup.get("precalibrated_startup_passed", False)),
        "source_paired_confirmation_passed": bool(confirmation.get("passed", False)),
        "oracle_feasible_cases": oracle_feasible,
        "oracle_total_cases": oracle_total,
        "paired_distinct_groups": paired_expected_groups,
        "paired_all_group_gate_structurally_possible": paired_gate_structurally_possible,
        "paired_gate_conflated_oracle_infeasibility": bool(not paired_gate_structurally_possible and paired_expected_groups == oracle_total),
        "legacy_weak_slew_pending_commands_dropped": total_pending_dropped,
        "legacy_weak_slew_pending_drop_examples": dropped_examples,
        "flattened_action_rms_zero_rows": action_metric_zero_count,
        "raw_nonzero_action_rollouts": raw_nonzero_action_count,
        "unique_noisy_calibration_traces": len(noisy),
        "online_no_lock_default_retained_count": online_untrusted_default,
        "online_no_lock_but_actual_ranked_best_count": online_ranked_actual_but_unlocked,
        "passed": bool(
            oracle_total == 18
            and oracle_feasible == 14
            and paired_expected_groups == 18
            and not paired_gate_structurally_possible
            and total_pending_dropped == 6
            and action_metric_zero_count == 108
            and raw_nonzero_action_count == 108
            and len(noisy) == 27
            and online_untrusted_default == 3
            and online_ranked_actual_but_unlocked == 3
        ),
        "interpretation": (
            "R7 completed without a runtime crash. Its final failure mixes an impossible all-group gate, "
            "three untrusted-default starts, and a legacy tail that bypassed non-empty delay queues."
        ),
    }
    atomic_write_json(ctx.paths.source_audit / "summary.json", summary)
    _update_state(ctx, source_audit_complete=True, source_audit_summary=summary)
    return summary


def _build_scheduler_from_payload(payload: Mapping[str, Any]) -> r3.PhysicalCoilScheduler:
    cfg = payload["stage4_1_cfg"]
    scheduler_cfg = cfg["controller_upgrade"]["gain_slew_scheduling"]
    return r3.PhysicalCoilScheduler(
        modes_tsc=np.asarray(payload["modes_tsc"], dtype=float),
        nominal_max_delta_a=float(payload["nominal_max_delta_a"]),
        command_max_delta_a=float(payload["max_delta_a"]),
        min_current=np.asarray(payload["min_current_tsc"], dtype=float),
        max_current=np.asarray(payload["max_current_tsc"], dtype=float),
        lower_mode=np.asarray(payload["cfg"]["trajectory"]["coefficient_lower"], dtype=float),
        upper_mode=np.asarray(payload["cfg"]["trajectory"]["coefficient_upper"], dtype=float),
        regularization=float(scheduler_cfg.get("physical_inverse_regularization", 1e-4)),
    )


def _residual_bank_for_observed(
    *,
    scheduler: r3.PhysicalCoilScheduler,
    step: int,
    observed_delta_a: np.ndarray,
    currents_before_a: np.ndarray,
    issued_commands: Sequence[np.ndarray],
    selector_cfg: Mapping[str, Any],
) -> dict[str, float]:
    scale = max(float(scheduler.nominal_max_delta_a), 1.0)
    output: dict[str, float] = {}
    for delay in map(int, selector_cfg["delay_candidates"]):
        issue_index = int(step) - delay
        command = np.zeros(3, dtype=float) if issue_index < 0 else np.asarray(issued_commands[issue_index], dtype=float)
        for slew in map(float, selector_cfg["slew_candidates"]):
            predicted = scheduler.predicted_delta_a(command, currents_before_a, np.ones(3), slew)
            output[_candidate_key(delay, slew)] = float(
                np.sqrt(np.mean(((predicted - observed_delta_a) / scale) ** 2))
            )
    return output


def _monte_carlo_pair(
    ctx: Stage41R8Context,
    clean_result: Mapping[str, Any],
    *,
    noise_sigma_a: float,
    trials: int,
    seed_base: int,
) -> list[dict[str, Any]]:
    spec = clean_result["spec"]
    actual_delay = int(spec["action_delay_steps"])
    actual_slew = float(spec["slew_scale"])
    _, payload = r7.materialize_variant(ctx.r7_ctx, slew_scale=actual_slew, horizon_steps=35)
    scheduler = _build_scheduler_from_payload(payload)
    trace = list(clean_result["calibration_trace"])
    trajectory = list(clean_result["trajectory"])
    issued = [np.asarray(row["issued_mode_coefficients"], dtype=float) for row in trace]
    actual_deltas = [np.asarray(row["actual_current_delta_A"], dtype=float) for row in trace]
    currents_before = [np.asarray(trajectory[index]["currents_a_tsc"], dtype=float) for index in range(len(trace))]
    output: list[dict[str, Any]] = []
    pair_seed = int(seed_base) + 1000 * actual_delay + 100 * int(round(10 * actual_slew))
    for trial in range(int(trials)):
        rng = np.random.default_rng(pair_seed + trial)
        residual_rows: list[dict[str, float]] = []
        for step in range(len(trace)):
            observed = actual_deltas[step] + rng.normal(0.0, float(noise_sigma_a), size=N_COILS)
            residual_rows.append(_residual_bank_for_observed(
                scheduler=scheduler,
                step=step,
                observed_delta_a=observed,
                currents_before_a=currents_before[step],
                issued_commands=issued[: step + 1],
                selector_cfg=ctx.cfg["batch_selector"],
            ))
        selected = trusted_batch_select_from_residuals(
            residual_rows,
            noise_sigma_a=float(noise_sigma_a),
            nominal_max_delta_a=float(scheduler.nominal_max_delta_a),
            selector_cfg=ctx.cfg["batch_selector"],
        )
        ranked_correct = bool(
            int(selected["ranked_best_delay_steps"]) == actual_delay
            and math.isclose(float(selected["ranked_best_slew_scale"]), actual_slew, abs_tol=1e-12)
        )
        trusted_correct = bool(
            selected["trusted"]
            and int(selected["selected_delay_steps"]) == actual_delay
            and math.isclose(float(selected["selected_slew_scale"]), actual_slew, abs_tol=1e-12)
        )
        output.append({
            "actual_delay_steps": actual_delay,
            "actual_slew_scale": actual_slew,
            "trial": trial,
            "seed": pair_seed + trial,
            "trusted": bool(selected["trusted"]),
            "ranked_model_correct": ranked_correct,
            "trusted_model_correct": trusted_correct,
            "wrong_accept": bool(selected["trusted"] and not trusted_correct),
            "ranked_best_delay_steps": selected["ranked_best_delay_steps"],
            "ranked_best_slew_scale": selected["ranked_best_slew_scale"],
            "full_delta_log_likelihood": selected["splits"]["full"]["delta_log_likelihood"],
            "minimum_split_delta_log_likelihood": min(
                selected["splits"][name]["delta_log_likelihood"]
                for name in ("first_half", "second_half", "odd", "even")
            ),
            "rejection_reasons": selected["rejection_reasons"],
        })
    return output


def run_source_replay(ctx: Stage41R8Context) -> dict[str, Any]:
    noisy, clean_by_pair = _load_source_calibration_traces(ctx)
    nominal_max_delta = float(
        ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.source_env_cfg["current_slew_a_per_ms"]
    ) * float(ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.source_env_cfg["dt_ms"])
    rows: list[dict[str, Any]] = []
    for result in noisy:
        selected = batch_select_calibration_result(
            result,
            selector_cfg=ctx.cfg["batch_selector"],
            nominal_max_delta_a=nominal_max_delta,
        )
        spec = result["spec"]
        online = result.get("adaptive_estimator_summary") or {}
        rows.append({
            "experiment_id": result.get("experiment_id"),
            "actual_delay_steps": int(spec["action_delay_steps"]),
            "actual_slew_scale": float(spec["slew_scale"]),
            "noise_seed": int(spec.get("coil_current_measurement_seed", 0)),
            "online_selected_delay_steps": online.get("selected_delay_steps"),
            "online_selected_slew_scale": online.get("selected_slew_scale"),
            "online_first_confident_lock_step": online.get("first_confident_lock_step"),
            "online_final_confident": online.get("confident"),
            "batch_ranked_delay_steps": selected["ranked_best_delay_steps"],
            "batch_ranked_slew_scale": selected["ranked_best_slew_scale"],
            "batch_trusted": selected["trusted"],
            "batch_selected_delay_steps": selected["selected_delay_steps"],
            "batch_selected_slew_scale": selected["selected_slew_scale"],
            "batch_ranked_correct": selected["ranked_model_correct"],
            "batch_trusted_correct": selected["trusted_model_correct"],
            "batch_wrong_accept": selected["wrong_accept"],
            "full_delta_log_likelihood": selected["splits"]["full"]["delta_log_likelihood"],
            "minimum_split_delta_log_likelihood": min(
                selected["splits"][name]["delta_log_likelihood"]
                for name in ("first_half", "second_half", "odd", "even")
            ),
            "rejection_reasons": selected["rejection_reasons"],
        })
    replay_cfg = ctx.cfg["source_replay"]
    mc_cfg = replay_cfg["monte_carlo"]
    if set(clean_by_pair) != {(delay, slew) for delay in (0, 1, 2) for slew in (0.9, 1.0, 1.1)}:
        raise RuntimeError("source Stage4.1R7 does not contain exactly one clean calibration for every pair")
    primary_rows: list[dict[str, Any]] = []
    diagnostic_rows: list[dict[str, Any]] = []
    for pair, result in sorted(clean_by_pair.items()):
        primary_rows.extend(_monte_carlo_pair(
            ctx,
            result,
            noise_sigma_a=float(mc_cfg["primary_noise_sigma_A"]),
            trials=int(mc_cfg["primary_trials_per_pair"]),
            seed_base=int(mc_cfg["primary_seed_base"]),
        ))
        diagnostic_rows.extend(_monte_carlo_pair(
            ctx,
            result,
            noise_sigma_a=float(mc_cfg["diagnostic_noise_sigma_A"]),
            trials=int(mc_cfg["diagnostic_trials_per_pair"]),
            seed_base=int(mc_cfg["diagnostic_seed_base"]),
        ))
    write_csv(ctx.paths.source_replay / "source_trace_replay.csv", rows)
    atomic_write_json(ctx.paths.source_replay / "source_trace_replay.json", rows)
    write_csv(ctx.paths.source_replay / "monte_carlo_primary.csv", primary_rows)
    atomic_write_json(ctx.paths.source_replay / "monte_carlo_primary.json", primary_rows)
    write_csv(ctx.paths.source_replay / "monte_carlo_diagnostic.csv", diagnostic_rows)
    atomic_write_json(ctx.paths.source_replay / "monte_carlo_diagnostic.json", diagnostic_rows)

    def summarize_mc(items: Sequence[Mapping[str, Any]], profile_id: str) -> dict[str, Any]:
        n = len(items)
        accepted = sum(bool(row["trusted"]) for row in items)
        wrong = sum(bool(row["wrong_accept"]) for row in items)
        correct = sum(bool(row["trusted_model_correct"]) for row in items)
        return {
            "profile_id": profile_id,
            "trials": n,
            "accepted": accepted,
            "trusted_correct": correct,
            "wrong_accept_count": wrong,
            "acceptance_fraction": accepted / max(n, 1),
            "trusted_correct_fraction": correct / max(n, 1),
            "zero_wrong_accept_rule_of_three_95pct_upper": 3.0 / max(n, 1) if wrong == 0 else None,
            "minimum_full_delta_log_likelihood": min(
                (_as_float(row.get("full_delta_log_likelihood"), 0.0) for row in items), default=0.0
            ),
            "minimum_split_delta_log_likelihood": min(
                (_as_float(row.get("minimum_split_delta_log_likelihood"), 0.0) for row in items), default=0.0
            ),
        }

    primary_summary = summarize_mc(primary_rows, str(mc_cfg["primary_profile_id"]))
    diagnostic_summary = summarize_mc(diagnostic_rows, str(mc_cfg["diagnostic_profile_id"]))
    summary = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "phase": "batch_source_replay",
        "unique_source_noisy_traces": len(rows),
        "source_batch_ranked_correct_fraction": sum(bool(row["batch_ranked_correct"]) for row in rows) / max(len(rows), 1),
        "source_batch_trusted_fraction": sum(bool(row["batch_trusted"]) for row in rows) / max(len(rows), 1),
        "source_batch_trusted_correct_fraction": sum(bool(row["batch_trusted_correct"]) for row in rows) / max(len(rows), 1),
        "source_batch_wrong_accept_count": sum(bool(row["batch_wrong_accept"]) for row in rows),
        "source_online_no_lock_count": sum(row["online_first_confident_lock_step"] is None for row in rows),
        "primary_monte_carlo": primary_summary,
        "diagnostic_monte_carlo": diagnostic_summary,
    }
    summary["passed"] = bool(
        len(rows) == int(replay_cfg["expected_unique_noisy_traces"])
        and (not bool(replay_cfg.get("require_all_batch_best_correct", True)) or all(bool(row["batch_ranked_correct"]) for row in rows))
        and (not bool(replay_cfg.get("require_all_batch_trusted", True)) or all(bool(row["batch_trusted"]) for row in rows))
        and int(summary["source_batch_wrong_accept_count"]) <= int(replay_cfg["maximum_wrong_accept_count"])
        and float(primary_summary["acceptance_fraction"]) >= float(mc_cfg["minimum_primary_acceptance_fraction"])
        and int(primary_summary["wrong_accept_count"]) <= int(mc_cfg["maximum_primary_wrong_accept_count"])
        and int(diagnostic_summary["wrong_accept_count"]) <= int(mc_cfg["maximum_diagnostic_wrong_accept_count"])
    )
    atomic_write_json(ctx.paths.source_replay / "summary.json", summary)
    _update_state(ctx, source_replay_complete=True, source_replay_summary=summary)
    return summary


# ---------------------------------------------------------------------------
# R8 worker: integrated calibration and queue-correct tail
# ---------------------------------------------------------------------------


def _tail_queue_plan(control_trace: Sequence[Mapping[str, Any]], actual_delay: int, tail_steps: int) -> list[dict[str, Any]]:
    if len(control_trace) != MAIN_CONTROL_STEPS:
        raise ValueError(f"expected {MAIN_CONTROL_STEPS} main control trace rows")
    delay = max(0, int(actual_delay))
    pending_indices = list(range(MAIN_CONTROL_STEPS - delay, MAIN_CONTROL_STEPS))
    pending = [
        (index, np.asarray(control_trace[index]["issued_mode_coefficients"], dtype=float).reshape(3))
        for index in pending_indices
    ]
    plan: list[dict[str, Any]] = []
    for tail_index in range(int(tail_steps)):
        if pending:
            source_index, command = pending.pop(0)
            source = "pending_issued_command"
        else:
            source_index, command = None, np.zeros(3, dtype=float)
            source = "zero_current_increment_after_queue_empty"
        plan.append({
            "tail_index": tail_index,
            "source": source,
            "source_control_step": source_index,
            "command_mode_coefficients": command,
            "pending_count_after_pop": len(pending),
        })
    if pending:
        raise RuntimeError(
            f"tail_steps={tail_steps} did not drain delay={delay}; {len(pending)} commands remain"
        )
    return plan


class LocalStage41R8Worker:
    def __init__(self, payload: dict[str, Any], library: dict[str, Any], bundle: dict[str, Any], worker_id: str, selector_cfg: dict[str, Any]):
        self.r7_worker = r7.LocalStage41R7Worker(payload, library, bundle, worker_id)
        self.base_worker = self.r7_worker.base_worker
        self.selector_cfg = copy.deepcopy(selector_cfg)
        self.horizon_steps = int(payload.get("stage4_1r4_horizon_steps", 35))

    def _cleanup_episode(self, *, failed: bool, reason: str) -> None:
        runner = getattr(self.base_worker.env, "runner", None)
        if runner is not None:
            runner.cleanup_episode_workspace(failed=failed, reason=reason)

    def _run_integrated_calibration(self, spec: dict[str, Any]) -> dict[str, Any]:
        result = self.r7_worker._run_calibration(spec)
        result["controller_revision"] = CONTROLLER_REVISION
        result["stage4_1r8_controller_revision"] = CONTROLLER_REVISION
        if result.get("success"):
            selector = batch_select_calibration_result(
                result,
                selector_cfg=self.selector_cfg,
                nominal_max_delta_a=float(self.base_worker.nominal_max_delta_a),
            )
        else:
            selector = {
                "selector_revision": self.selector_cfg.get("selector_revision"),
                "trusted": False,
                "selected_delay_steps": None,
                "selected_slew_scale": None,
                "rejection_reasons": ["calibration_episode_failed"],
                "wrong_accept": False,
                "ranked_model_correct": False,
                "trusted_model_correct": False,
            }
        result["batch_selector_summary"] = selector
        result["trusted_model_available"] = bool(selector.get("trusted", False))
        return _json_safe(result)

    def _run_queue_tail_main(self, spec: dict[str, Any]) -> dict[str, Any]:
        started = time.time()
        internal = copy.deepcopy(spec)
        internal["_defer_cleanup"] = True
        internal["extended_horizon"] = False
        result: dict[str, Any]
        failed = True
        try:
            result = self.base_worker.evaluate(internal)
            original_spec = copy.deepcopy(spec)
            result["spec"] = original_spec
            if not result.get("success"):
                result["controller_revision"] = CONTROLLER_REVISION
                result["stage4_1r8_controller_revision"] = CONTROLLER_REVISION
                return _json_safe(result)
            horizon = int(spec["horizon_steps"])
            tail_steps = int(spec["tail_steps"])
            if horizon != self.horizon_steps or horizon != MAIN_CONTROL_STEPS + tail_steps:
                raise ValueError("queue-tail horizon/payload mismatch")
            actual_delay = int(spec.get("action_delay_steps", 0))
            plan = _tail_queue_plan(result.get("control_trace") or [], actual_delay, tail_steps)
            trajectory = list(result.get("trajectory") or [])
            tail_trace: list[dict[str, Any]] = []
            actual_gain = np.asarray(spec.get("actuator_gain_by_mode", [1.0, 1.0, 1.0]), dtype=float)
            actuator_bias = np.asarray(spec.get("actuator_bias_by_mode", [0.0, 0.0, 0.0]), dtype=float)
            failure_reason = ""
            for item in plan:
                currents_before = np.asarray(self.base_worker.env.last_state["currents_a_tsc"], dtype=float)
                command = np.asarray(item["command_mode_coefficients"], dtype=float)
                effective = actual_gain * command + actuator_bias
                action = self.base_worker._mode_action(effective, currents_before)
                _, _, terminated, truncated, info = self.base_worker.env.step(action)
                step_index = MAIN_CONTROL_STEPS + int(item["tail_index"]) + 1
                trajectory.append(r3.base._state_record(self.base_worker.env, step_index, action))
                currents_after = np.asarray(self.base_worker.env.last_state["currents_a_tsc"], dtype=float)
                tail_trace.append({
                    "tail_index": int(item["tail_index"]),
                    "environment_step": step_index - 1,
                    "source": item["source"],
                    "source_control_step": item["source_control_step"],
                    "pending_count_after_pop": int(item["pending_count_after_pop"]),
                    "command_mode_coefficients": command.tolist(),
                    "effective_mode_coefficients": effective.tolist(),
                    "currents_before_A": currents_before.tolist(),
                    "currents_after_A": currents_after.tolist(),
                    "actual_current_delta_A": (currents_after - currents_before).tolist(),
                    "action_norm_tsc": np.asarray(action, dtype=float).tolist(),
                    "zero_action_while_pending": bool(
                        item["source"] == "pending_issued_command"
                        and np.max(np.abs(np.asarray(action, dtype=float))) <= 1e-15
                        and np.linalg.norm(command) > 1e-12
                    ),
                })
                if terminated:
                    failure_reason = str(info.get("failure_reason", "queue-tail terminated"))
                    break
                if truncated and step_index < horizon:
                    failure_reason = "environment truncated before queue-tail horizon"
                    break
            result["trajectory"] = trajectory
            result["tail_queue_trace"] = tail_trace
            result["tail_queue_summary"] = {
                "tail_policy": spec.get("tail_policy"),
                "horizon_steps": horizon,
                "tail_steps": tail_steps,
                "actual_delay_steps": actual_delay,
                "pending_at_350ms_count": actual_delay,
                "pending_commands_applied": sum(row["source"] == "pending_issued_command" for row in tail_trace),
                "zero_increment_actions_after_queue_empty": sum(
                    row["source"] == "zero_current_increment_after_queue_empty" for row in tail_trace
                ),
                "pending_queue_fully_drained": bool(
                    len(tail_trace) == tail_steps
                    and int(tail_trace[-1]["pending_count_after_pop"] if tail_trace else 0) == 0
                ),
                "zero_action_while_pending_count": sum(bool(row["zero_action_while_pending"]) for row in tail_trace),
                "legacy_direct_zero_tail_bypassed": True,
            }
            success = bool(
                not failure_reason
                and len(trajectory) == horizon + 1
                and len(tail_trace) == tail_steps
                and not any(bool(row.get("abnormal", False)) for row in trajectory)
                and result["tail_queue_summary"]["pending_queue_fully_drained"]
                and result["tail_queue_summary"]["zero_action_while_pending_count"] == 0
            )
            result["success"] = success
            result["failure_reason"] = "" if success else (failure_reason or "incomplete/abnormal queue-tail trajectory")
            result["wall_time_s"] = float(time.time() - started)
            result["controller_revision"] = CONTROLLER_REVISION
            result["stage4_1r8_controller_revision"] = CONTROLLER_REVISION
            failed = not success
            return _json_safe(result)
        except Exception as exc:
            failed = True
            return _json_safe({
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
                "tail_queue_trace": [],
            })
        finally:
            self._cleanup_episode(failed=failed, reason="stage4_1r8_queue_tail")

    def evaluate(self, spec: dict[str, Any]) -> dict[str, Any]:
        phase = str(spec.get("phase", ""))
        if phase == "integrated_calibration":
            return self._run_integrated_calibration(spec)
        if phase in {"oracle_queue_tail", "calibrated_startup"}:
            return self._run_queue_tail_main(spec)
        raise ValueError(f"unsupported Stage4.1R8 worker phase {phase!r}")

    def close(self) -> None:
        self.r7_worker.close()


def _ray_actor_class():
    import ray

    @ray.remote(num_cpus=1, max_restarts=0)
    class Actor:
        def __init__(self, payload, library, bundle, worker_id, selector_cfg):
            self.worker = LocalStage41R8Worker(payload, library, bundle, worker_id, selector_cfg)

        def evaluate(self, spec):
            return self.worker.evaluate(spec)

        def close(self):
            self.worker.close()

    return Actor


def materialize_variant(ctx: Stage41R8Context, *, slew_scale: float, horizon_steps: int) -> tuple[str, dict[str, Any]]:
    variant_id, payload = r7.materialize_variant(
        ctx.r7_ctx,
        slew_scale=float(slew_scale),
        horizon_steps=int(horizon_steps),
    )
    return variant_id, payload


def evaluate_specs(
    ctx: Stage41R8Context,
    specs: Sequence[dict[str, Any]],
    *,
    output_dir: Path,
    backend: str,
    resume: bool,
) -> list[dict[str, Any]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    variants = ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.variants
    by_variant: dict[str, list[dict[str, Any]]] = {}
    for spec in specs:
        variant = str(spec["environment_variant"])
        if variant not in variants:
            raise KeyError(f"unmaterialized environment variant {variant}")
        by_variant.setdefault(variant, []).append(spec)
    pending_by_variant: dict[str, list[dict[str, Any]]] = {}
    for variant, rows in by_variant.items():
        pending = [
            row for row in rows
            if not (resume and _result_complete(output_dir / f"{row['experiment_id']}.json.gz"))
        ]
        if pending:
            pending_by_variant[variant] = pending
    library = ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.source_library
    bundle = ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.source_bundle
    if backend == "serial":
        for variant, pending in pending_by_variant.items():
            worker = LocalStage41R8Worker(
                variants[variant], library, bundle, f"stage41r8_{variant}_serial", ctx.cfg["batch_selector"]
            )
            try:
                for index, spec in enumerate(pending, 1):
                    atomic_write_json_gz(output_dir / f"{spec['experiment_id']}.json.gz", worker.evaluate(spec))
                    print(f"[Stage4.1R8 {variant}] {index}/{len(pending)}", flush=True)
            finally:
                worker.close()
    elif backend == "ray" and pending_by_variant:
        import ray

        requested = int(os.environ.get("STAGE4_1R8_WORKERS", ctx.cfg["parallel"]["n_workers"]))
        total_pending = sum(len(rows) for rows in pending_by_variant.values())
        plan = ensure_ray_worker_plan(
            ray,
            requested_workers=requested,
            pending_tasks=total_pending,
            ray_tmpdir=os.environ.get("RAY_TMPDIR", ctx.cfg["parallel"].get("ray_tmpdir", "")) or None,
            log_prefix="[Stage4.1R8 mixed-variant]",
        )
        allocation = r3.s40._allocate_variant_actor_counts(
            {variant: len(rows) for variant, rows in pending_by_variant.items()},
            plan.actor_count,
        )
        print(
            "[Stage4.1R8 mixed-variant] actor_allocation="
            + json.dumps(allocation, sort_keys=True, separators=(",", ":")),
            flush=True,
        )
        Actor = _ray_actor_class()
        actors_by_variant: dict[str, list[Any]] = {}
        all_actors: list[Any] = []
        for variant, count in allocation.items():
            actors = [
                Actor.remote(
                    variants[variant], library, bundle, f"stage41r8_{variant}_{index:03d}", ctx.cfg["batch_selector"]
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
                ready, _ = ray.wait(list(refs), num_returns=1, timeout=30.0)
                if not ready:
                    print(f"[Stage4.1R8 mixed-variant] waiting {done}/{total_pending}", flush=True)
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
                    atomic_write_json_gz(output_dir / f"{spec['experiment_id']}.json.gz", result)
                    done += 1
                    if done % 10 == 0 or not refs:
                        print(f"[Stage4.1R8 mixed-variant] {done}/{total_pending}", flush=True)
        finally:
            s2._close_ray_actors(
                all_actors,
                timeout_s=float(ctx.cfg["storage"].get("actor_close_timeout_s", 1800.0)),
            )
    elif backend not in {"serial", "ray"}:
        raise ValueError("backend must be 'ray' or 'serial'")
    return [read_json_gz(output_dir / f"{spec['experiment_id']}.json.gz") for spec in specs]


# ---------------------------------------------------------------------------
# Specs, tracking metrics, and rows
# ---------------------------------------------------------------------------


def _make_spec(
    *,
    phase: str,
    scenario: str,
    category: str,
    target: Mapping[str, Any] | None,
    controller_scale: float,
    environment_variant: str,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    target = copy.deepcopy(target or {"target_id": "calibration", "R_offset_m": 0.0, "Z_offset_m": 0.0, "Ip_offset_A": 0.0})
    extra = copy.deepcopy(dict(extra or {}))
    identity = {
        "revision": CONTROLLER_REVISION,
        "phase": phase,
        "scenario": scenario,
        "category": category,
        "target": target,
        "controller_scale": controller_scale,
        "environment_variant": environment_variant,
        "extra": extra,
    }
    return {
        "kind": "stage4_1r8_trusted_batch_calibration_queue_tail_closure",
        "controller_revision": CONTROLLER_REVISION,
        "experiment_id": _scenario_digest(identity),
        "phase": phase,
        "scenario": scenario,
        "category": category,
        "target_id": target.get("target_id", scenario),
        "target_R_offset_m": float(target.get("R_offset_m", 0.0)),
        "target_Z_offset_m": float(target.get("Z_offset_m", 0.0)),
        "target_Ip_offset_A": float(target.get("Ip_offset_A", 0.0)),
        "controller_scale": float(controller_scale),
        "environment_variant": environment_variant,
        **extra,
    }


def _target_task(spec: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "task_id": str(spec.get("scenario", spec.get("experiment_id", "scenario"))),
        "R_offset_m": float(spec.get("target_R_offset_m", 0.0)),
        "Z_offset_m": float(spec.get("target_Z_offset_m", 0.0)),
        "Ip_offset_A": float(spec.get("target_Ip_offset_A", 0.0)),
        "final": False,
        "mandatory": False,
        "parents": [],
        "category": str(spec.get("category", "r8")),
    }


def _velocity_components(y: np.ndarray, dt_s: float) -> np.ndarray:
    velocity = np.zeros((len(y), 2), dtype=float)
    if len(y) > 1:
        velocity[1:] = np.diff(y[:, :2], axis=0) / float(dt_s)
    return velocity


def tracking_metrics(ctx: Stage41R8Context, result: Mapping[str, Any], policy: Mapping[str, Any]) -> dict[str, Any]:
    if not result.get("success"):
        return {
            "stage3_4_target_tracking_pass": False,
            "stage3_4_tracking_minimum_signed_margin": -1e12,
            "failure_reason": result.get("failure_reason", "TSC failure"),
        }
    trajectory = list(result.get("trajectory") or [])
    horizon = len(trajectory) - 1
    expected_horizon = int(policy["horizon_steps"])
    if horizon != expected_horizon:
        raise ValueError(f"unexpected R8 queue-tail horizon {horizon}; expected {expected_horizon}")
    y = np.asarray([[row["R"], row["Z"], row["Ip"]] for row in trajectory], dtype=float)
    if not np.all(np.isfinite(y)):
        raise ValueError("successful R8 trajectory contains non-finite R/Z/Ip")
    metric_ctx = SimpleNamespace(
        cfg=copy.deepcopy(ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.base34.cfg),
        env_cfg=ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.base34.env_cfg,
    )
    metric_ctx.cfg["gate"].update(copy.deepcopy(ctx.cfg["gate"]))
    target = s34.target_absolute(metric_ctx, _target_task(result["spec"]))
    error = y - target[None, :]
    dt_s = float(metric_ctx.env_cfg["dt_ms"]) / 1000.0
    speed = np.linalg.norm(_velocity_components(y, dt_s), axis=1)
    gate = ctx.cfg["gate"]
    ip_cfg = gate["ip_tracking"]
    terminal_ip_abs = float(abs(error[-1, 2]))
    terminal_ip_margin = 1.0 - terminal_ip_abs / float(ip_cfg["terminal_abs_tolerance_A"])
    endpoint_rows: list[dict[str, Any]] = []
    for endpoint in map(int, policy["allowed_arrival_steps"]):
        if endpoint > horizon:
            continue
        hard = s32._endpoint_constraints_signed(
            error=error,
            speed=speed,
            endpoint=endpoint,
            horizon=horizon,
            tolerance=float(gate["precise_tolerance_m"]),
            endpoint_speed_limit=float(gate["terminal_velocity_max_m_per_s"]),
            rms_speed_limit=float(gate["late_velocity_rms_max_m_per_s"]),
            late_window_steps=int(gate["late_window_steps"]),
            ip_tolerance=float(gate["ip_safety_tolerance_A"]),
            streak_steps=int(gate["required_arrival_streak_steps"]),
            dt_ms=int(metric_ctx.env_cfg["dt_ms"]),
        )
        window_start = int(hard["window_start_step"])
        hold_ip = error[window_start:, 2]
        ip_hold_rms = float(np.sqrt(np.mean(hold_ip**2)))
        ip_max = float(np.max(np.abs(hold_ip)))
        ip_margins = np.asarray([
            terminal_ip_margin,
            1.0 - ip_hold_rms / float(ip_cfg["hold_rms_tolerance_A"]),
            1.0 - ip_max / float(ip_cfg["sustained_max_tolerance_A"]),
        ])
        combined = np.concatenate([[float(hard["minimum_signed_margin"])], ip_margins])
        endpoint_rows.append({
            **copy.deepcopy(hard),
            "stage3_4_ip_terminal_abs_error_A": terminal_ip_abs,
            "stage3_4_ip_hold_rms_error_A": ip_hold_rms,
            "stage3_4_ip_sustained_max_error_A": ip_max,
            "stage3_4_ip_terminal_signed_margin": float(ip_margins[0]),
            "stage3_4_ip_hold_rms_signed_margin": float(ip_margins[1]),
            "stage3_4_ip_sustained_signed_margin": float(ip_margins[2]),
            "stage3_4_ip_tracking_pass": bool(np.min(ip_margins) >= -1e-12),
            "stage3_4_target_tracking_pass": bool(hard.get("pass", False) and np.min(ip_margins) >= -1e-12),
            "stage3_4_tracking_minimum_signed_margin": float(np.min(combined)),
            "stage3_4_tracking_mean_signed_margin": float(np.mean(combined)),
        })
    if not endpoint_rows:
        raise RuntimeError("no allowed arrival endpoint is available")
    passing = [row for row in endpoint_rows if row["stage3_4_target_tracking_pass"]]
    pool = passing if passing else endpoint_rows
    chosen = max(
        pool,
        key=lambda row: (
            float(row["stage3_4_tracking_minimum_signed_margin"]),
            float(row["stage3_4_tracking_mean_signed_margin"]),
            -int(row["endpoint_step"]),
        ),
    )
    window_start = int(chosen["window_start_step"])
    hold_rz = error[window_start:, :2]
    action = np.asarray([row["action_norm_tsc"] for row in trajectory[1:]], dtype=float)
    action_rms = float(np.sqrt(np.mean(action**2))) if action.size else 0.0
    delta_action_rms = float(np.sqrt(np.mean(np.diff(action, axis=0) ** 2))) if len(action) > 1 else 0.0
    currents = np.asarray([row["currents_a_display"] for row in trajectory], dtype=float)
    env_cfg = metric_ctx.env_cfg
    min_i = np.asarray(env_cfg["min_current_a_display_order"], dtype=float)
    max_i = np.asarray(env_cfg["max_current_a_display_order"], dtype=float)
    center_i = 0.5 * (min_i + max_i)
    half_i = np.maximum(0.5 * (max_i - min_i), 1e-9)
    max_current_util = float(np.max(np.abs((currents - center_i[None, :]) / half_i[None, :])))
    trace = list(result.get("control_trace") or [])
    issued = np.asarray([row.get("issued_mode_coefficients", [0.0, 0.0, 0.0]) for row in trace], dtype=float)
    issued_rms = float(np.sqrt(np.mean(issued**2))) if issued.size else 0.0
    return {
        "n_trajectory_steps": len(trajectory),
        "terminal_R_error_m": float(error[-1, 0]),
        "terminal_Z_error_m": float(error[-1, 1]),
        "terminal_Ip_error_A": float(error[-1, 2]),
        "terminal_RZ_euclidean_error_m": float(np.linalg.norm(error[-1, :2])),
        "terminal_RZ_box_max_error_m": float(np.max(np.abs(error[-1, :2]))),
        "terminal_velocity_m_per_s": float(speed[-1]),
        "late_velocity_rms_m_per_s": float(np.sqrt(np.mean(speed[-int(gate["late_window_steps"]):] ** 2))),
        "max_velocity_m_per_s": float(np.max(speed)),
        "max_current_utilization": max_current_util,
        "stage3_4_horizon_steps": horizon,
        "stage3_4_best_endpoint_step": int(chosen["endpoint_step"]),
        "stage3_4_best_endpoint_ms": int(chosen["arrival_time_ms"]),
        "stage3_4_window_start_step": window_start,
        "stage3_4_sustained_box_max_error_m": float(chosen["sustained_box_max_error_m"]),
        "stage3_4_endpoint_velocity_m_per_s": float(chosen["endpoint_velocity_m_per_s"]),
        "stage3_4_endpoint_late_velocity_rms_m_per_s": float(chosen["endpoint_late_velocity_rms_m_per_s"]),
        "stage3_4_post_arrival_velocity_rms_m_per_s": float(chosen["post_arrival_velocity_rms_m_per_s"]),
        "stage3_4_final_velocity_m_per_s": float(chosen["final_velocity_m_per_s"]),
        "stage3_4_sustained_Ip_safety_max_error_A": float(chosen["sustained_Ip_max_error_A"]),
        "stage3_4_ip_terminal_abs_error_A": float(chosen["stage3_4_ip_terminal_abs_error_A"]),
        "stage3_4_ip_hold_rms_error_A": float(chosen["stage3_4_ip_hold_rms_error_A"]),
        "stage3_4_ip_sustained_max_error_A": float(chosen["stage3_4_ip_sustained_max_error_A"]),
        "stage3_4_ip_tracking_pass": bool(chosen["stage3_4_ip_tracking_pass"]),
        "stage3_4_target_tracking_pass": bool(chosen["stage3_4_target_tracking_pass"]),
        "stage3_4_tracking_minimum_signed_margin": float(chosen["stage3_4_tracking_minimum_signed_margin"]),
        "stage3_4_tracking_mean_signed_margin": float(chosen["stage3_4_tracking_mean_signed_margin"]),
        "stage3_4_hold_rz_rms_m": float(np.sqrt(np.mean(np.sum(hold_rz**2, axis=1)))),
        "stage3_4_endpoint_evaluations": endpoint_rows,
        "action_rms": action_rms,
        "delta_action_rms": delta_action_rms,
        "issued_mode_coefficient_rms": issued_rms,
        "repair_excess_rms": None,
        "gate_label": f"R8_{policy['policy_id']}_BY_{int(chosen['arrival_time_ms'])}MS_THROUGH_{horizon*10}MS",
    }


def calibration_result_row(result: Mapping[str, Any]) -> dict[str, Any]:
    spec = result["spec"]
    selector = result.get("batch_selector_summary") or {}
    trace = result.get("calibration_trace") or []
    deltas = np.asarray([row.get("actual_current_delta_A", np.zeros(N_COILS)) for row in trace], dtype=float)
    trajectory = result.get("trajectory") or []
    residual = np.zeros(N_COILS)
    if trajectory:
        residual = np.asarray(trajectory[-1]["currents_a_tsc"], dtype=float) - np.asarray(trajectory[0]["currents_a_tsc"], dtype=float)
    return {
        "experiment_id": result.get("experiment_id"),
        "actual_delay_steps": int(spec["action_delay_steps"]),
        "actual_slew_scale": float(spec["slew_scale"]),
        "noise_seed": int(spec.get("coil_current_measurement_seed", 0)),
        "success": bool(result.get("success", False)),
        "batch_trusted": bool(selector.get("trusted", False)),
        "batch_selected_delay_steps": selector.get("selected_delay_steps"),
        "batch_selected_slew_scale": selector.get("selected_slew_scale"),
        "batch_ranked_delay_steps": selector.get("ranked_best_delay_steps"),
        "batch_ranked_slew_scale": selector.get("ranked_best_slew_scale"),
        "batch_ranked_correct": bool(selector.get("ranked_model_correct", False)),
        "batch_trusted_correct": bool(selector.get("trusted_model_correct", False)),
        "batch_wrong_accept": bool(selector.get("wrong_accept", False)),
        "batch_rejection_reasons": selector.get("rejection_reasons"),
        "full_delta_log_likelihood": ((selector.get("splits") or {}).get("full") or {}).get("delta_log_likelihood"),
        "minimum_split_delta_log_likelihood": min(
            (
                _as_float(((selector.get("splits") or {}).get(name) or {}).get("delta_log_likelihood"), 0.0)
                for name in ("first_half", "second_half", "odd", "even")
            ),
            default=0.0,
        ),
        "maximum_abs_actual_current_delta_A": float(np.max(np.abs(deltas))) if deltas.size else 0.0,
        "final_max_abs_coil_current_residual_A": float(np.max(np.abs(residual))) if residual.size else 0.0,
        "wall_time_s": float(result.get("wall_time_s", 0.0)),
    }


def control_result_row(ctx: Stage41R8Context, result: Mapping[str, Any], policy: Mapping[str, Any]) -> dict[str, Any]:
    spec = result["spec"]
    metrics = tracking_metrics(ctx, result, policy)
    trajectory = list(result.get("trajectory") or [])
    physics_signature = ""
    if trajectory:
        array = np.asarray(
            [[row["R"], row["Z"], row["Ip"], *row["currents_a_tsc"], *row["action_norm_tsc"]] for row in trajectory],
            dtype=float,
        )
        physics_signature = _array_digest(array, "physics")
    trace = list(result.get("control_trace") or [])
    issued = np.asarray([row.get("issued_mode_coefficients", [0.0, 0.0, 0.0]) for row in trace], dtype=float)
    command_signature = _array_digest(issued, "cmd") if len(issued) else ""
    tail_summary = result.get("tail_queue_summary") or {}
    estimator = result.get("adaptive_estimator_summary") or {}
    return {
        "experiment_id": result.get("experiment_id"),
        "phase": spec.get("phase"),
        "scenario": spec.get("scenario"),
        "target_id": spec.get("target_id"),
        "policy_id": spec.get("queue_tail_policy_id"),
        "controller_variant": spec.get("controller_variant"),
        "actual_action_delay_steps": int(spec.get("action_delay_steps", 0)),
        "controller_action_delay_steps": int(spec.get("controller_action_delay_steps", 0)),
        "actual_slew_scale": float(spec.get("slew_scale", 1.0)),
        "controller_slew_scale_estimate": float(spec.get("controller_slew_scale_estimate", 1.0)),
        "calibration_token": spec.get("calibration_token"),
        "trusted_calibration_model": bool(spec.get("trusted_calibration_model", False)),
        "success": bool(result.get("success", False)),
        "failure_reason": result.get("failure_reason", ""),
        "pending_at_350ms_count": tail_summary.get("pending_at_350ms_count"),
        "pending_commands_applied": tail_summary.get("pending_commands_applied"),
        "pending_queue_fully_drained": tail_summary.get("pending_queue_fully_drained"),
        "zero_action_while_pending_count": tail_summary.get("zero_action_while_pending_count"),
        "monitor_estimated_delay_steps": estimator.get("selected_delay_steps"),
        "monitor_estimated_slew_scale": estimator.get("selected_slew_scale"),
        "monitor_transition_count": len(estimator.get("transitions") or []),
        "physics_signature": physics_signature,
        "issued_command_signature": command_signature,
        "wall_time_s": float(result.get("wall_time_s", 0.0)),
        **metrics,
    }


def _main_extra(
    ctx: Stage41R8Context,
    *,
    actual_delay: int,
    actual_slew: float,
    modeled_delay: int,
    modeled_slew: float,
    policy: Mapping[str, Any],
    variant: str,
    monitor_enabled: bool,
    calibration_token: str | None,
    trusted: bool,
) -> dict[str, Any]:
    extra = r7._main_extra(
        ctx.r7_ctx,
        variant="r7_precalibrated_clean_monitor" if monitor_enabled else "oracle",
        actual_delay=int(actual_delay),
        actual_slew=float(actual_slew),
        modeled_delay=int(modeled_delay),
        modeled_slew=float(modeled_slew),
        horizon_steps=35,
        calibration_row=(
            {"experiment_id": calibration_token, "calibration_profile": "r8_batch_trusted"}
            if calibration_token is not None else None
        ),
    )
    extra.update({
        "horizon_steps": int(policy["horizon_steps"]),
        "extended_horizon": True,
        "tail_steps": int(policy["tail_steps"]),
        "tail_policy": str(policy["tail_policy"]),
        "queue_tail_policy_id": str(policy["policy_id"]),
        "controller_variant": variant,
        "calibration_token": calibration_token,
        "trusted_calibration_model": bool(trusted),
        "queue_initialized_from_trusted_model_before_main_control": bool(trusted),
        "adaptive_handover": {"enabled": False},
    })
    if monitor_enabled:
        extra["adaptive_delay_slew_estimator"] = r7._confidence_estimator_cfg(
            ctx.r7_ctx, initial_delay=int(modeled_delay), initial_slew=float(modeled_slew)
        )
    else:
        extra.pop("adaptive_delay_slew_estimator", None)
    return extra


# ---------------------------------------------------------------------------
# Integrated calibration phase
# ---------------------------------------------------------------------------


def build_integrated_calibration_specs(ctx: Stage41R8Context) -> list[dict[str, Any]]:
    cfg = ctx.cfg["integrated_calibration"]
    plan = np.asarray(cfg["mode_command_plan"], dtype=float).tolist()
    estimator_cfg = r7._confidence_estimator_cfg(ctx.r7_ctx)
    specs: list[dict[str, Any]] = []
    for actual_slew in cfg["actual_slew_scales"]:
        variant_id, _ = materialize_variant(ctx, slew_scale=float(actual_slew), horizon_steps=int(cfg["environment_horizon_steps"]))
        for actual_delay in cfg["actual_delay_steps"]:
            seed = int(cfg["seed_base"]) + 1000 * int(actual_delay) + 100 * int(round(10 * float(actual_slew)))
            extra = {
                "horizon_steps": int(cfg["environment_horizon_steps"]),
                "slew_scale": float(actual_slew),
                "action_delay_steps": int(actual_delay),
                "calibration_mode_command_plan": plan,
                "calibration_estimator": estimator_cfg,
                "calibration_profile": "r8_integrated_noisy_20mA",
                "calibration_repeat": 0,
                "coil_current_measurement_noise_A": float(cfg["coil_current_measurement_noise_A"]),
                "coil_current_measurement_seed": seed,
                "controller_variant": "r8_integrated_batch_calibration_only",
            }
            specs.append(_make_spec(
                phase="integrated_calibration",
                scenario=f"cal_d{actual_delay}_s{float(actual_slew):.1f}",
                category="integrated_calibration",
                target=None,
                controller_scale=0.0,
                environment_variant=variant_id,
                extra=extra,
            ))
    return specs


def summarize_integrated_calibration(ctx: Stage41R8Context, rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    cfg = ctx.cfg["integrated_calibration"]
    expected = {
        (int(delay), float(slew))
        for delay in cfg["actual_delay_steps"]
        for slew in cfg["actual_slew_scales"]
    }
    observed = {(int(row["actual_delay_steps"]), float(row["actual_slew_scale"])) for row in rows}
    maximum_delta = max((_as_float(row.get("maximum_abs_actual_current_delta_A"), 0.0) for row in rows), default=0.0)
    nominal_delta = float(ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.source_env_cfg["current_slew_a_per_ms"]) * float(
        ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.source_env_cfg["dt_ms"]
    )
    coverage = bool(len(rows) == len(expected) and observed == expected)
    wrong = sum(bool(row.get("batch_wrong_accept")) for row in rows)
    passed = bool(
        coverage
        and all(bool(row.get("success")) for row in rows)
        and (not bool(cfg.get("require_all_trusted", True)) or all(bool(row.get("batch_trusted")) for row in rows))
        and (
            not bool(cfg.get("require_all_correct_in_finite_test", True))
            or all(bool(row.get("batch_trusted_correct")) for row in rows)
        )
        and wrong <= int(cfg["maximum_wrong_accept_count"])
        and maximum_delta <= float(cfg["maximum_physical_coil_delta_fraction_of_nominal_slew"]) * nominal_delta + 1e-12
        and max(
            (_as_float(row.get("final_max_abs_coil_current_residual_A"), math.inf) for row in rows),
            default=math.inf,
        ) <= float(cfg["maximum_final_max_abs_coil_residual_A"]) + 1e-12
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "phase": "integrated_calibration",
        "n_rollouts": len(rows),
        "expected_rollouts": len(expected),
        "coverage_complete": coverage,
        "n_successful": sum(bool(row.get("success")) for row in rows),
        "trusted_fraction": sum(bool(row.get("batch_trusted")) for row in rows) / max(len(rows), 1),
        "trusted_correct_fraction": sum(bool(row.get("batch_trusted_correct")) for row in rows) / max(len(rows), 1),
        "wrong_accept_count": wrong,
        "maximum_abs_actual_current_delta_A": maximum_delta,
        "maximum_delta_fraction_of_nominal": maximum_delta / max(nominal_delta, 1e-12),
        "maximum_final_coil_residual_A": max(
            (_as_float(row.get("final_max_abs_coil_current_residual_A"), 0.0) for row in rows), default=0.0
        ),
        "calibration_tokens_are_pair_level_not_target_duplicated": True,
        "passed": passed,
    }


def run_integrated_calibration(ctx: Stage41R8Context, *, backend: str, resume: bool) -> dict[str, Any]:
    specs = build_integrated_calibration_specs(ctx)
    results = evaluate_specs(
        ctx,
        specs,
        output_dir=ctx.paths.integrated_calibration / "raw",
        backend=backend,
        resume=resume,
    )
    rows = [calibration_result_row(result) for result in results]
    summary = summarize_integrated_calibration(ctx, rows)
    write_csv(ctx.paths.integrated_calibration / "results.csv", rows)
    atomic_write_json(ctx.paths.integrated_calibration / "results.json", rows)
    atomic_write_json(ctx.paths.integrated_calibration / "summary.json", summary)
    _update_state(ctx, integrated_calibration_complete=True, integrated_calibration_summary=summary)
    return summary


def _calibration_tokens(ctx: Stage41R8Context) -> dict[tuple[int, float], dict[str, Any]]:
    rows = read_json(ctx.paths.integrated_calibration / "results.json")
    output: dict[tuple[int, float], dict[str, Any]] = {}
    for row in rows:
        key = (int(row["actual_delay_steps"]), float(row["actual_slew_scale"]))
        if key in output:
            raise ValueError(f"duplicate integrated calibration token for {key}")
        output[key] = row
    return output


# ---------------------------------------------------------------------------
# Oracle queue-tail repair and selection
# ---------------------------------------------------------------------------


def build_oracle_queue_tail_specs(ctx: Stage41R8Context) -> list[dict[str, Any]]:
    cfg = ctx.cfg["oracle_queue_tail"]
    source_scale = float(ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.source_scale)
    specs: list[dict[str, Any]] = []
    for policy in cfg["policies"]:
        for actual_slew in cfg["actual_slew_scales"]:
            variant_id, _ = materialize_variant(
                ctx,
                slew_scale=float(actual_slew),
                horizon_steps=int(policy["horizon_steps"]),
            )
            for actual_delay in cfg["actual_delay_steps"]:
                for target in cfg["targets"]:
                    extra = _main_extra(
                        ctx,
                        actual_delay=int(actual_delay),
                        actual_slew=float(actual_slew),
                        modeled_delay=int(actual_delay),
                        modeled_slew=float(actual_slew),
                        policy=policy,
                        variant="r8_oracle_queue_tail",
                        monitor_enabled=False,
                        calibration_token=None,
                        trusted=True,
                    )
                    specs.append(_make_spec(
                        phase="oracle_queue_tail",
                        scenario=f"{policy['policy_id']}__{target['target_id']}__d{actual_delay}__s{float(actual_slew):.1f}",
                        category="oracle_queue_tail",
                        target=target,
                        controller_scale=source_scale,
                        environment_variant=variant_id,
                        extra=extra,
                    ))
    return specs


def _policy_lookup(ctx: Stage41R8Context) -> dict[str, dict[str, Any]]:
    return {str(policy["policy_id"]): copy.deepcopy(policy) for policy in ctx.cfg["oracle_queue_tail"]["policies"]}


def summarize_oracle_queue_tail(ctx: Stage41R8Context, rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    cfg = ctx.cfg["oracle_queue_tail"]
    policies = _policy_lookup(ctx)
    expected_cases = {
        (str(target["target_id"]), int(delay), float(slew))
        for target in cfg["targets"]
        for delay in cfg["actual_delay_steps"]
        for slew in cfg["actual_slew_scales"]
    }
    summaries: list[dict[str, Any]] = []
    for policy_id, policy in policies.items():
        subset = [row for row in rows if str(row.get("policy_id")) == policy_id]
        observed = {
            (str(row["target_id"]), int(row["actual_action_delay_steps"]), float(row["actual_slew_scale"]))
            for row in subset
        }
        coverage = bool(len(subset) == len(expected_cases) and observed == expected_cases)
        tracking_fraction = sum(bool(row.get("stage3_4_target_tracking_pass")) for row in subset) / max(len(subset), 1)
        minimum_margin = min(
            (_as_float(row.get("stage3_4_tracking_minimum_signed_margin"), -1e12) for row in subset),
            default=-1e12,
        )
        summary = {
            "policy_id": policy_id,
            "horizon_steps": int(policy["horizon_steps"]),
            "tail_steps": int(policy["tail_steps"]),
            "n_rollouts": len(subset),
            "coverage_complete": coverage,
            "all_environment_success": all(bool(row.get("success")) for row in subset),
            "tracking_fraction": tracking_fraction,
            "minimum_signed_margin": minimum_margin,
            "all_pending_queues_drained": all(bool(row.get("pending_queue_fully_drained")) for row in subset),
            "zero_action_while_pending_count": sum(_as_int(row.get("zero_action_while_pending_count"), 0) for row in subset),
            "passed_tracking_gate": bool(
                coverage
                and all(bool(row.get("success")) for row in subset)
                and tracking_fraction >= float(cfg["minimum_policy_tracking_fraction"])
                and minimum_margin >= float(cfg["minimum_selected_policy_signed_margin"])
                and all(bool(row.get("pending_queue_fully_drained")) for row in subset)
                and sum(_as_int(row.get("zero_action_while_pending_count"), 0) for row in subset) == 0
            ),
        }
        summaries.append(summary)
    global_coverage_complete = bool(
        len(rows) == len(expected_cases) * len(policies)
        and all(row["coverage_complete"] for row in summaries)
    )
    candidates = [row for row in summaries if row["passed_tracking_gate"]]
    selected: dict[str, Any] | None = None
    if global_coverage_complete and candidates:
        selected = min(
            candidates,
            key=lambda row: (
                int(row["horizon_steps"]),
                -float(row["minimum_signed_margin"]),
                str(row["policy_id"]),
            ),
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "phase": "oracle_queue_tail",
        "n_rollouts": len(rows),
        "expected_rollouts": len(expected_cases) * len(policies),
        "coverage_complete": global_coverage_complete,
        "policy_summaries": summaries,
        "selected_policy_id": None if selected is None else selected["policy_id"],
        "selected_policy_horizon_steps": None if selected is None else selected["horizon_steps"],
        "selected_policy_minimum_signed_margin": None if selected is None else selected["minimum_signed_margin"],
        "passed": selected is not None,
    }


def run_oracle_queue_tail(ctx: Stage41R8Context, *, backend: str, resume: bool) -> dict[str, Any]:
    specs = build_oracle_queue_tail_specs(ctx)
    results = evaluate_specs(
        ctx,
        specs,
        output_dir=ctx.paths.oracle_queue_tail / "raw",
        backend=backend,
        resume=resume,
    )
    policies = _policy_lookup(ctx)
    rows = [control_result_row(ctx, result, policies[str(result["spec"]["queue_tail_policy_id"])]) for result in results]
    summary = summarize_oracle_queue_tail(ctx, rows)
    write_csv(ctx.paths.oracle_queue_tail / "results.csv", rows)
    atomic_write_json(ctx.paths.oracle_queue_tail / "results.json", rows)
    write_csv(ctx.paths.oracle_queue_tail / "policy_summary.csv", summary["policy_summaries"])
    atomic_write_json(ctx.paths.oracle_queue_tail / "summary.json", summary)
    _update_state(ctx, oracle_queue_tail_complete=True, oracle_queue_tail_summary=summary)
    return summary


def _selected_policy(ctx: Stage41R8Context) -> dict[str, Any]:
    summary = read_json(ctx.paths.oracle_queue_tail / "summary.json")
    selected = summary.get("selected_policy_id")
    if not selected:
        raise RuntimeError("no R8 oracle queue-tail policy passed")
    policies = _policy_lookup(ctx)
    if selected not in policies:
        raise KeyError(f"selected queue-tail policy {selected!r} is not configured")
    return policies[selected]


# ---------------------------------------------------------------------------
# Trusted calibrated startup
# ---------------------------------------------------------------------------


def build_calibrated_startup_specs(ctx: Stage41R8Context) -> list[dict[str, Any]]:
    tokens = _calibration_tokens(ctx)
    policy = _selected_policy(ctx)
    cfg = ctx.cfg["calibrated_startup"]
    source_scale = float(ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.source_scale)
    specs: list[dict[str, Any]] = []
    for (actual_delay, actual_slew), token in sorted(tokens.items()):
        if not bool(token.get("batch_trusted")):
            continue
        modeled_delay = _as_int(token.get("batch_selected_delay_steps"), -999)
        modeled_slew = _as_float(token.get("batch_selected_slew_scale"), math.nan)
        if modeled_delay < 0 or not math.isfinite(modeled_slew):
            continue
        variant_id, _ = materialize_variant(
            ctx,
            slew_scale=float(actual_slew),
            horizon_steps=int(policy["horizon_steps"]),
        )
        for target in cfg["targets"]:
            extra = _main_extra(
                ctx,
                actual_delay=actual_delay,
                actual_slew=actual_slew,
                modeled_delay=modeled_delay,
                modeled_slew=modeled_slew,
                policy=policy,
                variant="r8_batch_trusted_precalibrated_monitor",
                monitor_enabled=bool(cfg["monitor_enabled"]),
                calibration_token=str(token["experiment_id"]),
                trusted=True,
            )
            specs.append(_make_spec(
                phase="calibrated_startup",
                scenario=f"{policy['policy_id']}__{target['target_id']}__d{actual_delay}__s{actual_slew:.1f}",
                category="calibrated_startup",
                target=target,
                controller_scale=source_scale,
                environment_variant=variant_id,
                extra=extra,
            ))
    return specs


def _oracle_rows_by_case(ctx: Stage41R8Context) -> dict[tuple[str, int, float], dict[str, Any]]:
    rows = read_json(ctx.paths.oracle_queue_tail / "results.json")
    selected = str(read_json(ctx.paths.oracle_queue_tail / "summary.json")["selected_policy_id"])
    output: dict[tuple[str, int, float], dict[str, Any]] = {}
    for row in rows:
        if str(row.get("policy_id")) != selected:
            continue
        key = (
            str(row["target_id"]),
            int(row["actual_action_delay_steps"]),
            float(row["actual_slew_scale"]),
        )
        output[key] = row
    return output


def _trace_arrays(result: Mapping[str, Any]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    trajectory = list(result.get("trajectory") or [])
    physics = np.asarray(
        [
            [row["R"], row["Z"], row["Ip"], *row["currents_a_tsc"], *row["action_norm_tsc"]]
            for row in trajectory
        ],
        dtype=float,
    )
    control_trace = list(result.get("control_trace") or [])
    issued = np.asarray(
        [row.get("issued_mode_coefficients", [0.0, 0.0, 0.0]) for row in control_trace],
        dtype=float,
    )
    tail_trace = list(result.get("tail_queue_trace") or [])
    tail_commands = np.asarray(
        [row.get("command_mode_coefficients", [0.0, 0.0, 0.0]) for row in tail_trace],
        dtype=float,
    )
    return physics, issued, tail_commands


def _trace_comparison(
    ctx: Stage41R8Context,
    calibrated_row: Mapping[str, Any],
    oracle_row: Mapping[str, Any],
    *,
    atol: float,
) -> dict[str, Any]:
    calibrated_path = ctx.paths.calibrated_startup / "raw" / f"{calibrated_row['experiment_id']}.json.gz"
    oracle_path = ctx.paths.oracle_queue_tail / "raw" / f"{oracle_row['experiment_id']}.json.gz"
    if not calibrated_path.is_file() or not oracle_path.is_file():
        return {
            "raw_files_available": False,
            "exact_equal": False,
            "numeric_equal": False,
            "physics_max_abs_difference": math.inf,
            "issued_command_max_abs_difference": math.inf,
            "tail_command_max_abs_difference": math.inf,
        }
    calibrated = read_json_gz(calibrated_path)
    oracle = read_json_gz(oracle_path)
    calibrated_arrays = _trace_arrays(calibrated)
    oracle_arrays = _trace_arrays(oracle)
    names = ("physics", "issued_command", "tail_command")
    maxima: dict[str, float] = {}
    exact = True
    numeric = True
    for name, left, right in zip(names, calibrated_arrays, oracle_arrays):
        if left.shape != right.shape:
            maxima[name] = math.inf
            exact = False
            numeric = False
            continue
        if left.size:
            maxima[name] = float(np.max(np.abs(left - right)))
        else:
            maxima[name] = 0.0
        exact = bool(exact and np.array_equal(left, right))
        numeric = bool(numeric and np.allclose(left, right, rtol=0.0, atol=float(atol), equal_nan=False))
    return {
        "raw_files_available": True,
        "exact_equal": exact,
        "numeric_equal": numeric,
        "physics_max_abs_difference": maxima["physics"],
        "issued_command_max_abs_difference": maxima["issued_command"],
        "tail_command_max_abs_difference": maxima["tail_command"],
    }


def summarize_calibrated_startup(ctx: Stage41R8Context, rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    cfg = ctx.cfg["calibrated_startup"]
    expected = {
        (str(target["target_id"]), delay, slew)
        for target in cfg["targets"]
        for delay in (0, 1, 2)
        for slew in (0.9, 1.0, 1.1)
    }
    observed = {
        (str(row["target_id"]), int(row["actual_action_delay_steps"]), float(row["actual_slew_scale"]))
        for row in rows
    }
    oracle = _oracle_rows_by_case(ctx)
    exact_trace_equal = 0
    numeric_trace_equal = 0
    signature_equal = 0
    comparisons: list[dict[str, Any]] = []
    trace_atol = float(cfg.get("numeric_trace_equivalence_atol", 0.0))
    for row in rows:
        key = (str(row["target_id"]), int(row["actual_action_delay_steps"]), float(row["actual_slew_scale"]))
        oracle_row = oracle.get(key)
        signatures_match = bool(
            oracle_row
            and str(row.get("physics_signature")) == str(oracle_row.get("physics_signature"))
            and str(row.get("issued_command_signature")) == str(oracle_row.get("issued_command_signature"))
        )
        comparison = (
            _trace_comparison(ctx, row, oracle_row, atol=trace_atol)
            if oracle_row is not None
            else {
                "raw_files_available": False,
                "exact_equal": False,
                "numeric_equal": False,
                "physics_max_abs_difference": math.inf,
                "issued_command_max_abs_difference": math.inf,
                "tail_command_max_abs_difference": math.inf,
            }
        )
        signature_equal += signatures_match
        exact_trace_equal += bool(comparison["exact_equal"])
        numeric_trace_equal += bool(comparison["numeric_equal"])
        comparisons.append({
            "target_id": key[0],
            "actual_delay_steps": key[1],
            "actual_slew_scale": key[2],
            "signature_equal_to_oracle": signatures_match,
            "exact_trace_equal_to_oracle": bool(comparison["exact_equal"]),
            "numeric_trace_equal_to_oracle": bool(comparison["numeric_equal"]),
            "physics_max_abs_difference": comparison["physics_max_abs_difference"],
            "issued_command_max_abs_difference": comparison["issued_command_max_abs_difference"],
            "tail_command_max_abs_difference": comparison["tail_command_max_abs_difference"],
            "calibrated_margin": row.get("stage3_4_tracking_minimum_signed_margin"),
            "oracle_margin": None if oracle_row is None else oracle_row.get("stage3_4_tracking_minimum_signed_margin"),
        })
    coverage = bool(len(rows) == len(expected) and observed == expected)
    exact_equivalence = exact_trace_equal / max(len(rows), 1)
    numeric_equivalence = numeric_trace_equal / max(len(rows), 1)
    signature_equivalence = signature_equal / max(len(rows), 1)
    untrusted_starts = sum(not bool(row.get("trusted_calibration_model")) for row in rows)
    calibration_tokens = {str(row.get("calibration_token")) for row in rows if row.get("calibration_token")}
    monitor_correct = sum(
        _as_int(row.get("monitor_estimated_delay_steps"), -999)
        == _as_int(row.get("actual_action_delay_steps"), -998)
        and math.isclose(
            _as_float(row.get("monitor_estimated_slew_scale"), 1e9),
            _as_float(row.get("actual_slew_scale"), -1e9),
            abs_tol=1e-12,
        )
        for row in rows
    )
    monitor_correct_fraction = monitor_correct / max(len(rows), 1)
    passed = bool(
        coverage
        and len(calibration_tokens) == 9
        and all(bool(row.get("success")) for row in rows)
        and all(bool(row.get("stage3_4_target_tracking_pass")) for row in rows)
        and exact_equivalence >= float(cfg["minimum_trace_equivalence_fraction"])
        and numeric_equivalence >= 1.0 - 1e-12
        and signature_equivalence >= float(cfg["minimum_trace_equivalence_fraction"])
        and monitor_correct_fraction >= 1.0 - 1e-12
        and all(bool(row.get("pending_queue_fully_drained")) for row in rows)
        and sum(_as_int(row.get("zero_action_while_pending_count"), 0) for row in rows) == 0
        and untrusted_starts == 0
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "phase": "calibrated_startup",
        "n_rollouts": len(rows),
        "expected_rollouts": len(expected),
        "coverage_complete": coverage,
        "n_successful": sum(bool(row.get("success")) for row in rows),
        "tracking_pass_fraction": sum(bool(row.get("stage3_4_target_tracking_pass")) for row in rows) / max(len(rows), 1),
        "exact_trace_equivalence_fraction": exact_equivalence,
        "numeric_trace_equivalence_fraction": numeric_equivalence,
        "signature_equivalence_fraction": signature_equivalence,
        "numeric_trace_equivalence_atol": trace_atol,
        "maximum_physics_trace_abs_difference": max(
            (_as_float(row.get("physics_max_abs_difference"), math.inf) for row in comparisons), default=math.inf
        ),
        "maximum_issued_command_abs_difference": max(
            (_as_float(row.get("issued_command_max_abs_difference"), math.inf) for row in comparisons), default=math.inf
        ),
        "maximum_tail_command_abs_difference": max(
            (_as_float(row.get("tail_command_max_abs_difference"), math.inf) for row in comparisons), default=math.inf
        ),
        "minimum_tracking_signed_margin": min(
            (_as_float(row.get("stage3_4_tracking_minimum_signed_margin"), -1e12) for row in rows), default=-1e12
        ),
        "untrusted_main_start_count": untrusted_starts,
        "calibration_tokens": len(calibration_tokens),
        "calibration_token_reused_for_both_targets": True,
        "monitor_final_model_correct_fraction": monitor_correct_fraction,
        "monitor_transition_count": sum(_as_int(row.get("monitor_transition_count"), 0) for row in rows),
        "comparisons": comparisons,
        "passed": passed,
    }


def run_calibrated_startup(ctx: Stage41R8Context, *, backend: str, resume: bool) -> dict[str, Any]:
    specs = build_calibrated_startup_specs(ctx)
    results = evaluate_specs(
        ctx,
        specs,
        output_dir=ctx.paths.calibrated_startup / "raw",
        backend=backend,
        resume=resume,
    ) if specs else []
    policy = _selected_policy(ctx)
    rows = [control_result_row(ctx, result, policy) for result in results]
    summary = summarize_calibrated_startup(ctx, rows)
    write_csv(ctx.paths.calibrated_startup / "results.csv", rows)
    atomic_write_json(ctx.paths.calibrated_startup / "results.json", rows)
    atomic_write_json(ctx.paths.calibrated_startup / "summary.json", summary)
    _update_state(ctx, calibrated_startup_complete=True, calibrated_startup_summary=summary)
    return summary


# ---------------------------------------------------------------------------
# Restart availability and final analysis
# ---------------------------------------------------------------------------


def run_restart_audit(ctx: Stage41R8Context) -> dict[str, Any]:
    root = Path(ctx.r7_ctx.r6_ctx.r5_ctx.r4_ctx.r3_ctx.source_env_cfg.get("simulation_root", "")).expanduser()
    available: list[str] = []
    for value in ctx.cfg["restart_audit"].get("candidate_folders", []):
        path = Path(value).expanduser()
        if not path.is_absolute():
            path = root / path
        if path.is_dir():
            available.append(str(path.resolve()))
    summary = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "phase": "restart_audit",
        "candidate_folders": list(ctx.cfg["restart_audit"].get("candidate_folders", [])),
        "available_folders": sorted(set(available)),
        "true_restart_validation_available": len(set(available)) >= int(ctx.cfg["restart_audit"].get("minimum_distinct_folders", 2)),
        "true_restart_validation_performed": False,
        "availability_requirement_for_stage4_1r8": False,
        "audit_completed": True,
        "passed": True,
    }
    atomic_write_json(ctx.paths.restart_audit / "summary.json", summary)
    _update_state(ctx, restart_audit_complete=True, restart_audit_summary=summary)
    return summary


def analyze(ctx: Stage41R8Context) -> dict[str, Any]:
    state = read_json(ctx.paths.state)
    source = state.get("source_audit_summary") or {}
    replay = state.get("source_replay_summary") or {}
    calibration = state.get("integrated_calibration_summary") or {}
    oracle = state.get("oracle_queue_tail_summary") or {}
    startup = state.get("calibrated_startup_summary") or {}
    restart = state.get("restart_audit_summary") or {}
    primary_pass = bool(
        source.get("passed")
        and replay.get("passed")
        and calibration.get("passed")
        and oracle.get("passed")
        and startup.get("passed")
    )
    verdict = (
        "STAGE4_1R8_FINITE_TRUSTED_CALIBRATION_QUEUE_TAIL_CLOSURE"
        if primary_pass
        else "STAGE4_1R8_TRUSTED_CALIBRATION_OR_QUEUE_TAIL_CLOSURE_INCOMPLETE"
    )
    summary = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "created_utc": utc_timestamp(),
        "verdict": verdict,
        "source_stage4_1r7_run": str(ctx.source_stage41r7_run),
        "source_audit_passed": bool(source.get("passed", False)),
        "batch_source_replay_passed": bool(replay.get("passed", False)),
        "integrated_calibration_passed": bool(calibration.get("passed", False)),
        "oracle_queue_tail_passed": bool(oracle.get("passed", False)),
        "calibrated_startup_passed": bool(startup.get("passed", False)),
        "selected_queue_tail_policy": oracle.get("selected_policy_id"),
        "finite_trusted_calibration_queue_tail_envelope_validated": primary_pass,
        "untrusted_default_main_start_allowed": False,
        "tail_pending_queue_bypass_allowed": False,
        "true_restart_validation_available": bool(restart.get("true_restart_validation_available", False)),
        "true_restart_validation_performed": False,
        "hardware_pre_shot_calibration_validated": False,
        "continuous_parameter_change_validated": False,
        "plant_parameter_robustness_validated": False,
        "unseen_hidden_state_robustness_validated": False,
        "deployment_robustness_validated": False,
        "finite_test_envelope_only": True,
        "warning": (
            "R8 can only close a finite static digital-twin envelope. It does not validate real restart state, "
            "hidden vessel/eddy history, continuously changing actuator parameters, plant-model error, or hardware calibration."
        ),
        "final_task": ctx.cfg["final_task"],
        "phases": {
            "source_audit": source,
            "batch_source_replay": replay,
            "integrated_calibration": calibration,
            "oracle_queue_tail": oracle,
            "calibrated_startup": startup,
            "restart_audit": restart,
        },
    }
    verdict_payload = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "verdict": verdict,
        "primary_pass": primary_pass,
        "selected_queue_tail_policy": oracle.get("selected_policy_id"),
        "next_if_pass": "Stage4.2 true restart and plant-parameter robustness; do not start BC/DAgger/RL yet.",
        "next_if_fail": (
            "If batch trust fails, redesign the calibration evidence gate. If no queue-tail policy passes, "
            "implement a queue-aware feedback tail rather than weakening the tracking gate."
        ),
        "final_task": ctx.cfg["final_task"],
    }
    atomic_write_json(ctx.paths.analysis / "stage4_1r8_analysis_summary.json", summary)
    atomic_write_json(ctx.paths.analysis / "stage4_1r8_verdict.json", verdict_payload)
    prior_stop_reason = str(state.get("stop_reason", "")).strip()
    if primary_pass:
        final_stop_reason = "pipeline_complete"
    elif prior_stop_reason and prior_stop_reason not in {"pipeline_complete", "closure_incomplete"}:
        final_stop_reason = prior_stop_reason
    else:
        final_stop_reason = "closure_incomplete"
    _update_state(ctx, finished=True, stop_reason=final_stop_reason, analysis_summary=summary)
    return summary


# ---------------------------------------------------------------------------
# Execution and self-test
# ---------------------------------------------------------------------------


def prepare(ctx: Stage41R8Context) -> dict[str, Any]:
    validate_config(ctx)
    preflight = runtime_preflight(ctx)
    initialize_run(ctx, preflight)
    return {"run_dir": str(ctx.paths.run_dir), "workers": preflight}


def execute(
    ctx: Stage41R8Context,
    *,
    command: str,
    backend: str,
    resume: bool,
) -> dict[str, Any]:
    prepare_payload = prepare(ctx)
    if command == "prepare":
        return prepare_payload
    source = run_source_audit(ctx)
    if command == "audit":
        return source
    if not source.get("passed"):
        _update_state(ctx, finished=True, stop_reason="source_audit_failed")
        run_restart_audit(ctx)
        return analyze(ctx)
    if command in {"all", "replay"}:
        replay = run_source_replay(ctx)
        if command == "replay":
            return replay
        if not replay.get("passed"):
            _update_state(ctx, finished=True, stop_reason="batch_source_replay_failed")
            run_restart_audit(ctx)
            return analyze(ctx)
    if command in {"all", "calibrate"}:
        calibration = run_integrated_calibration(ctx, backend=backend, resume=resume)
        if command == "calibrate":
            return calibration
        if not calibration.get("passed"):
            _update_state(ctx, finished=True, stop_reason="integrated_calibration_failed")
            run_restart_audit(ctx)
            return analyze(ctx)
    if command in {"all", "oracle"}:
        oracle = run_oracle_queue_tail(ctx, backend=backend, resume=resume)
        if command == "oracle":
            return oracle
        if not oracle.get("passed"):
            _update_state(ctx, finished=True, stop_reason="oracle_queue_tail_failed")
            run_restart_audit(ctx)
            return analyze(ctx)
    if command in {"all", "startup"}:
        startup = run_calibrated_startup(ctx, backend=backend, resume=resume)
        if command == "startup":
            return startup
        if not startup.get("passed"):
            _update_state(ctx, finished=True, stop_reason="calibrated_startup_failed")
    run_restart_audit(ctx)
    return analyze(ctx)


def self_test() -> dict[str, Any]:
    selector_cfg = {
        "delay_candidates": [0, 1, 2],
        "slew_candidates": [0.9, 1.0, 1.1],
        "nominal_coil_count": 14,
        "minimum_full_delta_log_likelihood": 50.0,
        "minimum_split_delta_log_likelihood": 20.0,
        "minimum_clean_score_ratio": 10.0,
        "minimum_clean_absolute_score_gap": 1e-12,
        "require_full_first_second_odd_even_consensus": True,
        "require_leave_one_out_consensus": True,
        "selector_revision": "self_test",
    }
    keys = [_candidate_key(delay, slew) for delay in (0, 1, 2) for slew in (0.9, 1.0, 1.1)]
    rows = []
    for step in range(10):
        row = {key: 0.08 + 0.001 * step for key in keys}
        row[_candidate_key(2, 1.1)] = 0.006 + 0.0001 * step
        row[_candidate_key(2, 1.0)] = 0.030 + 0.0001 * step
        rows.append(row)
    trusted = trusted_batch_select_from_residuals(
        rows,
        noise_sigma_a=0.02,
        nominal_max_delta_a=3.0,
        selector_cfg=selector_cfg,
    )
    ambiguous_rows = [{key: 0.01 for key in keys} for _ in range(10)]
    ambiguous = trusted_batch_select_from_residuals(
        ambiguous_rows,
        noise_sigma_a=0.02,
        nominal_max_delta_a=3.0,
        selector_cfg=selector_cfg,
    )
    fake_trace = [
        {"issued_mode_coefficients": [float(i), 0.0, 0.0]} for i in range(MAIN_CONTROL_STEPS)
    ]
    tail = _tail_queue_plan(fake_trace, actual_delay=2, tail_steps=4)
    passed = bool(
        trusted["trusted"]
        and trusted["selected_delay_steps"] == 2
        and math.isclose(trusted["selected_slew_scale"], 1.1)
        and not ambiguous["trusted"]
        and [row["source_control_step"] for row in tail[:2]] == [33, 34]
        and all(row["source"] == "zero_current_increment_after_queue_empty" for row in tail[2:])
    )
    return {
        "stage": STAGE,
        "controller_revision": CONTROLLER_REVISION,
        "package_revision": PACKAGE_REVISION,
        "trusted_selector_test": trusted,
        "ambiguous_selector_test": ambiguous,
        "tail_queue_plan_test": _json_safe(tail),
        "passed": passed,
    }


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Stage4.1R8 trusted batch calibration and queue-tail closure")
    parser.add_argument(
        "--config",
        default="configs/stage4_1r8_trusted_batch_calibration_queue_tail_closure_410ms.json",
    )
    parser.add_argument("--source-stage4-1r7-run")
    parser.add_argument("--run-dir")
    parser.add_argument("--backend", choices=["ray", "serial"], default="ray")
    parser.add_argument(
        "--command",
        choices=["all", "prepare", "audit", "replay", "calibrate", "oracle", "startup", "analyze"],
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
    if not args.source_stage4_1r7_run:
        parser.error("--source-stage4-1r7-run is required")
    if not args.run_dir:
        parser.error("--run-dir is required")
    ctx = load_stage41r8_config(
        Path(args.config),
        source_stage41r7_run=Path(args.source_stage4_1r7_run),
        run_dir_override=Path(args.run_dir),
    )
    if args.command == "analyze":
        prepare(ctx)
        payload = analyze(ctx)
    else:
        payload = execute(ctx, command=args.command, backend=args.backend, resume=bool(args.resume))
    print(json.dumps(_json_safe(payload), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
