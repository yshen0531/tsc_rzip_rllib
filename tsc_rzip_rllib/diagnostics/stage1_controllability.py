from __future__ import annotations

import copy
import csv
import gzip
import hashlib
import json
import math
import os
import shutil
import sys
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np

from tsc_rzip_rllib.core.coil_order import (
    DISPLAY_COIL_NAMES,
    TSC_COIL_NAMES,
    display_to_tsc,
    tsc_matrix_to_display,
    tsc_to_display,
)


# -----------------------------------------------------------------------------
# Generic utilities
# -----------------------------------------------------------------------------


def atomic_write_text(path: Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".tmp.{os.getpid()}")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def atomic_write_json(path: Path, payload: Any, *, indent: int = 2) -> None:
    atomic_write_text(path, json.dumps(payload, indent=indent, ensure_ascii=False, allow_nan=False))


def atomic_write_json_gz(path: Path, payload: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".tmp.{os.getpid()}")
    with gzip.open(tmp, "wt", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    os.replace(tmp, path)


def read_json(path: Path | str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def read_json_gz(path: Path | str) -> Any:
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return json.load(f)


def sha256_file(path: Path | str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            block = f.read(1024 * 1024)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def deep_replace_strings(value: Any, replacements: dict[str, str]) -> Any:
    if isinstance(value, dict):
        return {k: deep_replace_strings(v, replacements) for k, v in value.items()}
    if isinstance(value, list):
        return [deep_replace_strings(v, replacements) for v in value]
    if isinstance(value, str):
        out = value
        for key, repl in replacements.items():
            out = out.replace("{" + key + "}", repl)
        return out
    return value


def resolve_path(path: str | Path, *, base_dir: Path) -> Path:
    p = Path(path).expanduser()
    if not p.is_absolute():
        p = base_dir / p
    return p.resolve()


def ensure_finite_array(name: str, arr: np.ndarray) -> np.ndarray:
    arr = np.asarray(arr, dtype=float)
    if not np.all(np.isfinite(arr)):
        raise ValueError(f"{name} contains non-finite values")
    return arr


def safe_float(value: Any, default: float = float("nan")) -> float:
    try:
        out = float(value)
    except Exception:
        return default
    return out if math.isfinite(out) else default


def utc_timestamp() -> str:
    return time.strftime("%Y%m%d_%H%M%S", time.gmtime())


def write_csv(path: Path, rows: Iterable[dict[str, Any]], fieldnames: Sequence[str] | None = None) -> None:
    rows = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        keys: list[str] = []
        seen: set[str] = set()
        for row in rows:
            for key in row:
                if key not in seen:
                    keys.append(key)
                    seen.add(key)
        fieldnames = keys
    tmp = path.with_name(path.name + f".tmp.{os.getpid()}")
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(fieldnames), extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------


@dataclass(frozen=True)
class Stage1Paths:
    project_dir: Path
    stage_config_path: Path
    train_config_path: Path
    env_config_path: Path
    run_dir: Path
    raw_dir: Path
    analysis_dir: Path
    candidate_dir: Path
    validation_dir: Path


@dataclass(frozen=True)
class ResolvedStage1Config:
    cfg: dict[str, Any]
    train_cfg: dict[str, Any]
    env_cfg: dict[str, Any]
    paths: Stage1Paths


def load_and_resolve_stage1_config(
    stage_config_path: str | Path,
    *,
    run_dir_override: str | Path | None = None,
) -> ResolvedStage1Config:
    stage_path = Path(stage_config_path).expanduser().resolve()
    project_dir = Path(os.environ.get("PROJECT_DIR", Path.cwd())).expanduser().resolve()
    tsc_all_root = Path(os.environ.get("TSC_ALL_ROOT", project_dir.parent)).expanduser().resolve()
    replacements = {
        "PROJECT_DIR": str(project_dir),
        "TSC_ALL_ROOT": str(tsc_all_root),
    }

    raw_stage = deep_replace_strings(read_json(stage_path), replacements)
    train_path = resolve_path(raw_stage["train_config"], base_dir=project_dir)
    raw_train = deep_replace_strings(read_json(train_path), replacements)
    env_path = resolve_path(raw_train["env_config"], base_dir=project_dir)
    raw_env = deep_replace_strings(read_json(env_path), replacements)

    if run_dir_override is None:
        root = resolve_path(raw_stage.get("output_root", "stage1_runs"), base_dir=project_dir)
        run_name = raw_stage.get("run_name", "stage1_controllability_100ms")
        run_dir = root / f"{run_name}_{utc_timestamp()}"
    else:
        run_dir = resolve_path(run_dir_override, base_dir=project_dir)

    # Materialize a private resolved train config for the diagnostic run.  Reward
    # values are irrelevant, but the environment constructor requires them.
    horizon = int(raw_stage["scan"]["horizon_steps"])
    if horizon < 2:
        raise ValueError("scan.horizon_steps must be >= 2")
    raw_train = copy.deepcopy(raw_train)
    # Point workers at the fully macro-resolved private copy that initialize_run
    # materializes before any Ray actor is created.
    raw_train["env_config"] = str(run_dir / "env_config.resolved.json")
    raw_train.setdefault("episode", {})["max_episode_steps"] = horizon
    raw_train.setdefault("target", {}).update(raw_stage["target"])

    paths = Stage1Paths(
        project_dir=project_dir,
        stage_config_path=stage_path,
        train_config_path=train_path,
        env_config_path=env_path,
        run_dir=run_dir,
        raw_dir=run_dir / "raw_experiments",
        analysis_dir=run_dir / "analysis",
        candidate_dir=run_dir / "candidate_sequences",
        validation_dir=run_dir / "validation",
    )
    return ResolvedStage1Config(raw_stage, raw_train, raw_env, paths)


def initialize_run(resolved: ResolvedStage1Config) -> None:
    p = resolved.paths
    for d in [p.run_dir, p.raw_dir, p.analysis_dir, p.candidate_dir, p.validation_dir]:
        d.mkdir(parents=True, exist_ok=True)
    atomic_write_json(p.run_dir / "stage1_config.resolved.json", resolved.cfg)
    atomic_write_json(p.run_dir / "train_config.resolved.json", resolved.train_cfg)
    atomic_write_json(p.run_dir / "env_config.resolved.json", resolved.env_cfg)
    atomic_write_json(
        p.run_dir / "run_manifest.json",
        {
            "created_utc": utc_timestamp(),
            "stage_config_source": str(p.stage_config_path),
            "train_config_source": str(p.train_config_path),
            "env_config_source": str(p.env_config_path),
            "project_dir": str(p.project_dir),
            "python": sys.version,
            "coil_order_tsc": TSC_COIL_NAMES,
            "coil_order_display": DISPLAY_COIL_NAMES,
        },
    )


# -----------------------------------------------------------------------------
# Experiment specification and TSC rollout
# -----------------------------------------------------------------------------


def experiment_id(spec: dict[str, Any]) -> str:
    kind = str(spec["kind"])
    if kind == "baseline":
        return f"baseline_r{int(spec['repeat']):02d}"
    return (
        f"scan_k{int(spec['injection_step']):02d}_"
        f"c{int(spec['coil_index_tsc']):02d}_{TSC_COIL_NAMES[int(spec['coil_index_tsc'])]}_"
        f"a{float(spec['amplitude_fraction']):.6f}_s{int(spec['sign']):+d}"
    ).replace("+", "p").replace("-", "m").replace(".", "d")


def build_scan_specs(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    scan = cfg["scan"]
    horizon = int(scan["horizon_steps"])
    injection_steps = [int(x) for x in scan.get("injection_steps", list(range(horizon)))]
    amplitudes = [float(x) for x in scan.get("amplitude_fractions", [0.5, 1.0])]
    baseline_repeats = int(scan.get("baseline_repeats", 3))
    for k in injection_steps:
        if not 0 <= k < horizon:
            raise ValueError(f"invalid injection step {k} for horizon {horizon}")
    for a in amplitudes:
        if not 0 < a <= 1.0:
            raise ValueError(f"amplitude fraction must be in (0,1], got {a}")

    specs: list[dict[str, Any]] = []
    for repeat in range(baseline_repeats):
        specs.append({"kind": "baseline", "repeat": repeat, "horizon_steps": horizon})
    for k in injection_steps:
        for coil in range(14):
            for amplitude in amplitudes:
                for sign in (-1, 1):
                    specs.append(
                        {
                            "kind": "scan",
                            "injection_step": k,
                            "coil_index_tsc": coil,
                            "coil_name_tsc": TSC_COIL_NAMES[coil],
                            "amplitude_fraction": amplitude,
                            "sign": sign,
                            "horizon_steps": horizon,
                        }
                    )
    for spec in specs:
        spec["experiment_id"] = experiment_id(spec)
    return specs


def _state_record(env: Any, step_index: int, action_tsc: np.ndarray) -> dict[str, Any]:
    state = env.last_state
    if state is None:
        raise RuntimeError("environment has no last_state")
    timing = state.get("runner_timing", {}) or {}
    return {
        "step_index": int(step_index),
        "time_ms": int(state.get("time_ms", -1)),
        "R": float(state["R"]),
        "Z": float(state["Z"]),
        "Ip": float(state["Ip"]),
        "vessel_current_total_a": float(state.get("vessel_current_total_a", 0.0)),
        "vessel_current_abs_sum_a": float(state.get("vessel_current_abs_sum_a", 0.0)),
        "vessel_current_rms_a": float(state.get("vessel_current_rms_a", 0.0)),
        "vessel_current_max_abs_a": float(state.get("vessel_current_max_abs_a", 0.0)),
        "currents_a_tsc": np.asarray(state["currents_a_tsc"], dtype=float).tolist(),
        "currents_a_display": np.asarray(state["currents_a_display"], dtype=float).tolist(),
        "action_norm_tsc": np.asarray(action_tsc, dtype=float).tolist(),
        "action_norm_display": tsc_to_display(np.asarray(action_tsc, dtype=float)).tolist(),
        "abnormal": bool(state.get("abnormal", False)),
        "gotsc_subprocess_s": safe_float(timing.get("gotsc_subprocess_s"), 0.0),
        "step_total_s": safe_float(timing.get("step_total_s"), 0.0),
    }


def run_one_experiment(env: Any, spec: dict[str, Any]) -> dict[str, Any]:
    started = time.time()
    horizon = int(spec["horizon_steps"])
    trajectory: list[dict[str, Any]] = []
    failure_reason = ""
    try:
        env.reset()
        zero = np.zeros(14, dtype=np.float32)
        trajectory.append(_state_record(env, 0, zero))
        for k in range(horizon):
            action = np.zeros(14, dtype=np.float32)
            if spec["kind"] == "scan" and k == int(spec["injection_step"]):
                action[int(spec["coil_index_tsc"])] = float(spec["sign"]) * float(spec["amplitude_fraction"])
            _, _, terminated, truncated, info = env.step(action)
            trajectory.append(_state_record(env, k + 1, action))
            if terminated:
                failure_reason = str(info.get("failure_reason", "terminated"))
                break
            if truncated and k + 1 < horizon:
                failure_reason = "environment truncated before requested horizon"
                break
        success = len(trajectory) == horizon + 1 and not any(bool(x["abnormal"]) for x in trajectory)
        if not success and not failure_reason:
            failure_reason = "incomplete or abnormal trajectory"
        result: dict[str, Any] = {
            "schema_version": 1,
            "experiment_id": spec["experiment_id"],
            "spec": spec,
            "success": bool(success),
            "failure_reason": failure_reason,
            "wall_time_s": float(time.time() - started),
            "trajectory": trajectory,
        }
        if spec["kind"] == "scan" and len(trajectory) > int(spec["injection_step"]) + 1:
            k = int(spec["injection_step"])
            coil = int(spec["coil_index_tsc"])
            before = np.asarray(trajectory[k]["currents_a_tsc"], dtype=float)
            after = np.asarray(trajectory[k + 1]["currents_a_tsc"], dtype=float)
            result["effective_injection_delta_a"] = float(after[coil] - before[coil])
            result["requested_action_norm"] = float(spec["sign"]) * float(spec["amplitude_fraction"])
        return result
    except Exception as exc:
        return {
            "schema_version": 1,
            "experiment_id": spec.get("experiment_id", "unknown"),
            "spec": spec,
            "success": False,
            "failure_reason": repr(exc),
            "traceback": traceback.format_exc(),
            "wall_time_s": float(time.time() - started),
            "trajectory": trajectory,
        }


class LocalWorker:
    def __init__(self, train_cfg: dict[str, Any], worker_id: str):
        from tsc_rzip_rllib.envs.factory import make_tsc_rzip_env
        self.env = make_tsc_rzip_env(copy.deepcopy(train_cfg), worker_id=worker_id, seed=None)

    def run_experiment(self, spec: dict[str, Any]) -> dict[str, Any]:
        return run_one_experiment(self.env, spec)

    def close(self) -> None:
        self.env.close()


def _ray_actor_class():
    try:
        import ray
    except Exception as exc:  # pragma: no cover - server dependency
        raise RuntimeError("Ray is required for backend='ray'") from exc

    @ray.remote(num_cpus=1, max_restarts=0)
    class RayTscExperimentWorker:
        def __init__(self, train_cfg: dict[str, Any], worker_id: str):
            self.worker = LocalWorker(train_cfg, worker_id)

        def run_experiment(self, spec: dict[str, Any]) -> dict[str, Any]:
            return self.worker.run_experiment(spec)

        def close(self) -> None:
            self.worker.close()

    return RayTscExperimentWorker


def _result_path(raw_dir: Path, exp_id: str) -> Path:
    return raw_dir / f"{exp_id}.json.gz"


def _is_complete_result(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        payload = read_json_gz(path)
        return bool(payload.get("success", False))
    except Exception:
        return False


def run_scan(resolved: ResolvedStage1Config, *, backend: str = "ray", resume: bool = True) -> dict[str, Any]:
    initialize_run(resolved)
    cfg = resolved.cfg
    specs = build_scan_specs(cfg)
    pending = []
    for spec in specs:
        path = _result_path(resolved.paths.raw_dir, spec["experiment_id"])
        if resume and _is_complete_result(path):
            continue
        pending.append(spec)

    summary = {
        "total_specs": len(specs),
        "already_complete": len(specs) - len(pending),
        "pending": len(pending),
        "backend": backend,
        "started_utc": utc_timestamp(),
    }
    atomic_write_json(resolved.paths.run_dir / "scan_status.json", summary)
    if not pending:
        summary.update({"completed": len(specs), "failed": 0, "finished_utc": utc_timestamp()})
        atomic_write_json(resolved.paths.run_dir / "scan_status.json", summary)
        return summary

    failed = 0
    completed = len(specs) - len(pending)
    if backend == "serial":
        worker = LocalWorker(resolved.train_cfg, "stage1_serial")
        try:
            for idx, spec in enumerate(pending, start=1):
                result = worker.run_experiment(spec)
                atomic_write_json_gz(_result_path(resolved.paths.raw_dir, spec["experiment_id"]), result)
                completed += int(bool(result.get("success")))
                failed += int(not bool(result.get("success")))
                if idx % 5 == 0 or idx == len(pending):
                    print(f"[stage1 scan] {idx}/{len(pending)} new experiments, failed={failed}", flush=True)
        finally:
            worker.close()
    elif backend == "ray":
        import ray

        parallel = cfg.get("parallel", {})
        n_workers = int(os.environ.get("STAGE1_WORKERS", parallel.get("n_workers", 192)))
        n_workers = max(1, min(n_workers, len(pending)))
        ray_tmpdir = os.environ.get("RAY_TMPDIR", parallel.get("ray_tmpdir", "")) or None
        if not ray.is_initialized():
            ray.init(
                num_cpus=n_workers,
                include_dashboard=False,
                ignore_reinit_error=True,
                _temp_dir=ray_tmpdir,
                log_to_driver=False,
            )
        Actor = _ray_actor_class()
        actors = [Actor.remote(resolved.train_cfg, f"stage1_scan_{i:03d}") for i in range(n_workers)]
        refs: dict[Any, dict[str, Any]] = {}
        for idx, spec in enumerate(pending):
            ref = actors[idx % n_workers].run_experiment.remote(spec)
            refs[ref] = spec
        new_done = 0
        try:
            while refs:
                ready, _ = ray.wait(list(refs), num_returns=1, timeout=30.0)
                if not ready:
                    print(f"[stage1 scan] waiting; completed new={new_done}/{len(pending)}", flush=True)
                    continue
                for ref in ready:
                    spec = refs.pop(ref)
                    try:
                        result = ray.get(ref)
                    except Exception as exc:
                        result = {
                            "schema_version": 1,
                            "experiment_id": spec["experiment_id"],
                            "spec": spec,
                            "success": False,
                            "failure_reason": repr(exc),
                            "traceback": traceback.format_exc(),
                            "trajectory": [],
                        }
                    atomic_write_json_gz(_result_path(resolved.paths.raw_dir, spec["experiment_id"]), result)
                    new_done += 1
                    completed += int(bool(result.get("success")))
                    failed += int(not bool(result.get("success")))
                    if new_done % 10 == 0 or not refs:
                        print(
                            f"[stage1 scan] {new_done}/{len(pending)} new experiments; "
                            f"success={completed}, failed={failed}",
                            flush=True,
                        )
        finally:
            for actor in actors:
                try:
                    ray.kill(actor, no_restart=True)
                except Exception:
                    pass
    else:
        raise ValueError("backend must be 'ray' or 'serial'")

    summary.update(
        {
            "completed_success": completed,
            "failed": failed,
            "finished_utc": utc_timestamp(),
        }
    )
    atomic_write_json(resolved.paths.run_dir / "scan_status.json", summary)
    return summary


# -----------------------------------------------------------------------------
# System identification
# -----------------------------------------------------------------------------


def load_scan_results(raw_dir: Path) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for path in sorted(Path(raw_dir).glob("*.json.gz")):
        try:
            payload = read_json_gz(path)
            payload["_path"] = str(path)
            results.append(payload)
        except Exception as exc:
            results.append(
                {
                    "experiment_id": path.stem,
                    "success": False,
                    "failure_reason": f"failed to read result: {exc!r}",
                    "_path": str(path),
                }
            )
    return results


def trajectory_array(result: dict[str, Any], key: str) -> np.ndarray:
    return np.asarray([row[key] for row in result["trajectory"]], dtype=float)


def baseline_summary(results: list[dict[str, Any]], horizon: int) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    base = [r for r in results if r.get("success") and r.get("spec", {}).get("kind") == "baseline"]
    if not base:
        raise RuntimeError("no successful baseline experiment found")
    keys = ["R", "Z", "Ip", "vessel_current_total_a", "vessel_current_abs_sum_a"]
    arrays: dict[str, np.ndarray] = {}
    spread: dict[str, float] = {}
    for key in keys:
        stack = np.stack([trajectory_array(r, key) for r in base], axis=0)
        if stack.shape[1] != horizon + 1:
            raise RuntimeError(f"baseline {key} has wrong horizon: {stack.shape}")
        arrays[key] = np.median(stack, axis=0)
        spread[key] = float(np.max(np.ptp(stack, axis=0))) if stack.shape[0] > 1 else 0.0
    current_stack = np.stack(
        [np.asarray([x["currents_a_tsc"] for x in r["trajectory"]], dtype=float) for r in base],
        axis=0,
    )
    arrays["currents_a_tsc"] = np.median(current_stack, axis=0)
    meta = {
        "baseline_repeats_successful": len(base),
        "max_repeat_spread": spread,
        "initial_state": {k: float(arrays[k][0]) for k in ["R", "Z", "Ip"]},
        "terminal_state": {k: float(arrays[k][-1]) for k in ["R", "Z", "Ip"]},
    }
    return arrays, meta


def fit_response_tensor(
    results: list[dict[str, Any]],
    baseline: dict[str, np.ndarray],
    *,
    horizon: int,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Fit dy/d(current increment A) for each output time, injection time, coil.

    Returns tensor with shape (horizon+1, 3, horizon, 14).  Columns before an
    injection are retained and should be close to zero; this is useful for
    diagnosing nondeterminism or indexing errors.
    """
    tensor = np.zeros((horizon + 1, 3, horizon, 14), dtype=float)
    fit_rows: list[dict[str, Any]] = []
    by_group: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for result in results:
        spec = result.get("spec", {})
        if not result.get("success") or spec.get("kind") != "scan":
            continue
        k = int(spec["injection_step"])
        c = int(spec["coil_index_tsc"])
        by_group.setdefault((k, c), []).append(result)

    missing: list[dict[str, Any]] = []
    baseline_y = np.column_stack([baseline["R"], baseline["Z"], baseline["Ip"]])
    for k in range(horizon):
        for c in range(14):
            group = by_group.get((k, c), [])
            usable = []
            for r in group:
                x = safe_float(r.get("effective_injection_delta_a"))
                y = np.column_stack(
                    [trajectory_array(r, "R"), trajectory_array(r, "Z"), trajectory_array(r, "Ip")]
                )
                if y.shape != (horizon + 1, 3) or not math.isfinite(x) or abs(x) < 1e-9:
                    continue
                usable.append((x, y - baseline_y, r))
            if len(usable) < 2:
                missing.append({"injection_step": k, "coil_index_tsc": c, "n_usable": len(usable)})
                continue
            x = np.asarray([u[0] for u in usable], dtype=float)
            dy = np.stack([u[1] for u in usable], axis=0)
            denom = float(np.dot(x, x))
            slope = np.tensordot(x, dy, axes=(0, 0)) / max(denom, 1e-12)
            tensor[:, :, k, c] = slope
            prediction = x[:, None, None] * slope[None, :, :]
            residual = dy - prediction
            signal_norm = float(np.linalg.norm(dy))
            residual_norm = float(np.linalg.norm(residual))
            signal_by_output = np.linalg.norm(dy, axis=(0, 1))
            residual_by_output = np.linalg.norm(residual, axis=(0, 1))
            pre_norm = float(np.linalg.norm(slope[: k + 1]))
            post_norm = float(np.linalg.norm(slope[k + 1 :]))
            fit_rows.append(
                {
                    "injection_step": k,
                    "coil_index_tsc": c,
                    "coil_name_tsc": TSC_COIL_NAMES[c],
                    "n_points": len(usable),
                    "n_positive": int(np.sum(x > 0)),
                    "n_negative": int(np.sum(x < 0)),
                    "bidirectional": bool(np.any(x > 0) and np.any(x < 0)),
                    "min_effective_delta_a": float(np.min(x)),
                    "max_effective_delta_a": float(np.max(x)),
                    "relative_nonlinearity_residual": residual_norm / max(signal_norm, 1e-12),
                    "relative_nonlinearity_R": float(residual_by_output[0] / max(signal_by_output[0], 1e-12)),
                    "relative_nonlinearity_Z": float(residual_by_output[1] / max(signal_by_output[1], 1e-12)),
                    "relative_nonlinearity_Ip": float(residual_by_output[2] / max(signal_by_output[2], 1e-12)),
                    "pre_injection_leakage_norm": pre_norm,
                    "post_injection_response_norm": post_norm,
                    "relative_pre_injection_leakage": pre_norm / max(post_norm, 1e-12),
                }
            )
    if missing:
        raise RuntimeError(f"insufficient successful scan points for {len(missing)} channel/time groups; first={missing[:5]}")
    return tensor, {"fit_rows": fit_rows, "missing": missing}


def output_weights(cfg: dict[str, Any]) -> np.ndarray:
    a = cfg["analysis"]
    return np.asarray(
        [
            1.0 / float(a.get("r_scale_m", 0.08)),
            1.0 / float(a.get("z_scale_m", 0.08)),
            float(a.get("ip_weight", 0.15)) / float(a.get("ip_scale_a", 8000.0)),
        ],
        dtype=float,
    )


def build_lifted_matrix(response: np.ndarray, output_steps: Sequence[int]) -> np.ndarray:
    horizon = response.shape[2]
    rows: list[np.ndarray] = []
    for t in output_steps:
        rows.append(response[int(t), :, :, :].reshape(3, horizon * 14))
    return np.vstack(rows)


def build_spatial_sensitivity(response: np.ndarray, weights: np.ndarray) -> np.ndarray:
    horizon = response.shape[2]
    rows: list[np.ndarray] = []
    for k in range(horizon):
        for t in range(k + 1, horizon + 1):
            block = response[t, :, k, :] * weights[:, None]
            rows.append(block)
    return np.vstack(rows)


def orient_modes(vt: np.ndarray) -> np.ndarray:
    modes = vt.T.copy()
    for j in range(modes.shape[1]):
        idx = int(np.argmax(np.abs(modes[:, j])))
        if modes[idx, j] < 0:
            modes[:, j] *= -1.0
    return modes


def pair_mode_library_tsc() -> dict[str, np.ndarray]:
    pairs = ["CS1", "CS2", "CS3", "CS4", "PF2", "PF3", "PF4"]
    modes: dict[str, np.ndarray] = {}
    for prefix in pairs:
        for mode_name, signs in [("common", (1.0, 1.0)), ("differential", (1.0, -1.0))]:
            display = np.zeros(14, dtype=float)
            display[DISPLAY_COIL_NAMES.index(prefix + "U")] = signs[0]
            display[DISPLAY_COIL_NAMES.index(prefix + "L")] = signs[1]
            display /= np.linalg.norm(display)
            modes[f"{prefix}_{mode_name}"] = display_to_tsc(display)
    return modes


def svd_diagnostics(response: np.ndarray, cfg: dict[str, Any]) -> dict[str, Any]:
    weights = output_weights(cfg)
    spatial = build_spatial_sensitivity(response, weights)
    u, s, vt = np.linalg.svd(spatial, full_matrices=False)
    modes_tsc = orient_modes(vt)
    energy = s**2
    cumulative = np.cumsum(energy) / max(float(np.sum(energy)), 1e-30)
    analysis = cfg["analysis"]
    energy_target = float(analysis.get("mode_energy_target", 0.99))
    singular_ratio_floor = float(analysis.get("singular_ratio_floor", 1e-3))
    k_energy = int(np.searchsorted(cumulative, energy_target) + 1)
    k_ratio = int(np.sum(s / max(float(s[0]), 1e-30) >= singular_ratio_floor))
    recommended_k = max(1, min(int(analysis.get("max_recommended_modes", 8)), max(k_energy, k_ratio)))

    pair_rows = []
    for name, vector in pair_mode_library_tsc().items():
        gain = float(np.linalg.norm(spatial @ vector))
        pair_rows.append({"mode": name, "weighted_response_gain": gain})
    pair_rows.sort(key=lambda x: x["weighted_response_gain"], reverse=True)

    return {
        "spatial_matrix": spatial,
        "singular_values": s,
        "cumulative_energy": cumulative,
        "modes_tsc": modes_tsc,
        "modes_display": tsc_matrix_to_display(modes_tsc.T).T,
        "recommended_k": recommended_k,
        "condition_number_nonzero": float(s[0] / max(s[-1], 1e-30)),
        "pair_mode_rows": pair_rows,
    }


def horizon_controllability_rows(response: np.ndarray, cfg: dict[str, Any]) -> list[dict[str, Any]]:
    weights = output_weights(cfg)
    horizon = response.shape[2]
    rows: list[dict[str, Any]] = []
    for t in range(1, horizon + 1):
        h = response[t, :, :t, :].reshape(3, t * 14)
        hw = weights[:, None] * h
        s = np.linalg.svd(hw, compute_uv=False)
        rank = int(np.linalg.matrix_rank(hw, tol=max(hw.shape) * np.finfo(float).eps * max(float(s[0]), 1.0)))
        rows.append(
            {
                "output_step": t,
                "time_ms_from_start": int(t * cfg["scan"]["dt_ms"]),
                "rank_weighted_RZI": rank,
                "sigma_1": float(s[0]) if len(s) > 0 else 0.0,
                "sigma_2": float(s[1]) if len(s) > 1 else 0.0,
                "sigma_3": float(s[2]) if len(s) > 2 else 0.0,
                "condition_nonzero": float(s[0] / max(s[rank - 1], 1e-30)) if rank else float("inf"),
            }
        )
    return rows


def compute_terminal_reachable_set(
    response: np.ndarray,
    baseline: dict[str, np.ndarray],
    cfg: dict[str, Any],
) -> dict[str, Any]:
    """Compute the local linear 100 ms R/Z reachable-set boundary.

    The projection is obtained by maximizing support functions in evenly spaced
    directions under the exact per-step slew and cumulative coil-current limits.
    A weak terminal Ip band can be enforced so that the R/Z polygon is not
    purchased with an unacceptable plasma-current excursion.
    """
    try:
        from scipy.optimize import linprog
        from scipy.spatial import ConvexHull
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("scipy is required for reachable-set analysis") from exc

    horizon = response.shape[2]
    env_cfg = cfg["_env_config"]
    analysis = cfg["analysis"]
    directions = int(analysis.get("reachable_set_directions", 72))
    ip_tolerance = float(analysis.get("reachable_set_ip_tolerance_a", 8000.0))
    max_delta_a = float(env_cfg["current_slew_a_per_ms"]) * float(env_cfg["dt_ms"])

    h_terminal = response[horizon, :, :, :].reshape(3, horizon * 14)
    h_rz = h_terminal[:2]
    h_ip = h_terminal[2]
    baseline_terminal = np.asarray(
        [baseline["R"][-1], baseline["Z"][-1], baseline["Ip"][-1]], dtype=float
    )
    target = np.asarray([cfg["target"]["R"], cfg["target"]["Z"], cfg["target"]["Ip"]], dtype=float)

    cum = cumulative_current_matrix(horizon)
    initial = np.asarray(baseline["currents_a_tsc"][0], dtype=float)
    min_current = display_to_tsc(np.asarray(env_cfg["min_current_a_display_order"], dtype=float))
    max_current = display_to_tsc(np.asarray(env_cfg["max_current_a_display_order"], dtype=float))
    lower_current = np.tile(min_current - initial, horizon)
    upper_current = np.tile(max_current - initial, horizon)

    a_ub = [cum, -cum]
    b_ub = [upper_current, -lower_current]
    if ip_tolerance > 0:
        ip_center_delta = target[2] - baseline_terminal[2]
        a_ub.extend([h_ip[None, :], -h_ip[None, :]])
        b_ub.extend(
            [
                np.asarray([ip_center_delta + ip_tolerance]),
                np.asarray([-ip_center_delta + ip_tolerance]),
            ]
        )
    a_ub_arr = np.vstack(a_ub)
    b_ub_arr = np.concatenate(b_ub)
    bounds = [(-max_delta_a, max_delta_a)] * (horizon * 14)

    points = []
    failed = 0
    for i in range(directions):
        theta = 2.0 * math.pi * i / directions
        direction = np.asarray([math.cos(theta), math.sin(theta)], dtype=float)
        c = -(direction @ h_rz)
        result = linprog(c, A_ub=a_ub_arr, b_ub=b_ub_arr, bounds=bounds, method="highs")
        if not result.success:
            failed += 1
            continue
        delta = h_rz @ np.asarray(result.x, dtype=float)
        point = baseline_terminal[:2] + delta
        predicted_ip = baseline_terminal[2] + float(h_ip @ result.x)
        points.append(
            {
                "direction_index": i,
                "theta_rad": theta,
                "R": float(point[0]),
                "Z": float(point[1]),
                "Ip": float(predicted_ip),
                "support": float(direction @ point),
            }
        )

    target_inside = False
    hull_vertices: list[int] = []
    if len(points) >= 3:
        pts = np.asarray([[x["R"], x["Z"]] for x in points], dtype=float)
        try:
            hull = ConvexHull(pts)
            hull_vertices = [int(x) for x in hull.vertices]
            # scipy hull equations are n.x + b <= 0 inside.
            target_inside = bool(np.all(hull.equations[:, :2] @ target[:2] + hull.equations[:, 2] <= 1e-9))
        except Exception:
            # A rank-one actuator projection legitimately produces a line rather
            # than a 2-D polygon.  Report it without aborting the full analysis.
            hull_vertices = []
            target_inside = False

    return {
        "points": points,
        "failed_directions": failed,
        "target_inside_local_linear_RZ_projection": target_inside,
        "hull_vertex_indices": hull_vertices,
        "baseline_terminal": {"R": float(baseline_terminal[0]), "Z": float(baseline_terminal[1]), "Ip": float(baseline_terminal[2])},
        "target": {"R": float(target[0]), "Z": float(target[1]), "Ip": float(target[2])},
        "terminal_ip_tolerance_a": ip_tolerance,
        "max_delta_current_a_per_step": max_delta_a,
    }


# -----------------------------------------------------------------------------
# Constrained reachability optimization
# -----------------------------------------------------------------------------


def block_diag_mode_transform(horizon: int, modes_tsc: np.ndarray) -> np.ndarray:
    modes_tsc = np.asarray(modes_tsc, dtype=float)
    k = modes_tsc.shape[1]
    out = np.zeros((horizon * 14, horizon * k), dtype=float)
    for t in range(horizon):
        out[t * 14 : (t + 1) * 14, t * k : (t + 1) * k] = modes_tsc
    return out


def cumulative_current_matrix(horizon: int) -> np.ndarray:
    # Maps flattened time-major coil increments u[t,coil] to cumulative changes.
    mat = np.zeros((horizon * 14, horizon * 14), dtype=float)
    for t in range(horizon):
        for tau in range(t + 1):
            mat[t * 14 : (t + 1) * 14, tau * 14 : (tau + 1) * 14] = np.eye(14)
    return mat


def build_quadratic_tracking_system(
    response: np.ndarray,
    baseline: dict[str, np.ndarray],
    cfg: dict[str, Any],
    *,
    mode_transform: np.ndarray,
    target_fraction: float,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    horizon = response.shape[2]
    opt = cfg["optimization"]
    target = np.asarray([cfg["target"]["R"], cfg["target"]["Z"], cfg["target"]["Ip"]], dtype=float)
    base_y = np.column_stack([baseline["R"], baseline["Z"], baseline["Ip"]])
    target_y = base_y[0] + float(target_fraction) * (target - base_y[0])
    selected = [int(x) for x in opt.get("tracking_steps", list(range(max(1, horizon - 3), horizon + 1)))]
    step_weights = np.asarray(opt.get("tracking_step_weights", [1.0] * len(selected)), dtype=float)
    if len(step_weights) != len(selected):
        raise ValueError("optimization.tracking_step_weights length must match tracking_steps")
    out_w = output_weights(cfg)

    blocks: list[np.ndarray] = []
    targets: list[np.ndarray] = []
    for idx, t in enumerate(selected):
        h = response[t, :, :, :].reshape(3, horizon * 14) @ mode_transform
        w = out_w * math.sqrt(float(step_weights[idx]))
        blocks.append(w[:, None] * h)
        targets.append(w * (target_y - base_y[t]))

    # Penalize R/Z velocity in the late window.  The target velocity is zero.
    velocity_weight = float(opt.get("velocity_weight", 0.15))
    dt_s = float(cfg["scan"]["dt_ms"]) / 1000.0
    velocity_steps = [int(x) for x in opt.get("velocity_steps", selected[1:]) if int(x) >= 1]
    for t in velocity_steps:
        h_now = response[t, :2, :, :].reshape(2, horizon * 14)
        h_prev = response[t - 1, :2, :, :].reshape(2, horizon * 14)
        h_vel = ((h_now - h_prev) / dt_s) @ mode_transform
        base_vel = (base_y[t, :2] - base_y[t - 1, :2]) / dt_s
        scale = np.asarray(
            [1.0 / float(opt.get("r_velocity_scale_m_per_s", 1.0)), 1.0 / float(opt.get("z_velocity_scale_m_per_s", 1.0))]
        )
        w = scale * math.sqrt(velocity_weight)
        blocks.append(w[:, None] * h_vel)
        targets.append(-w * base_vel)

    a = np.vstack(blocks)
    b = np.concatenate(targets)
    return a, b, {
        "tracking_steps": selected,
        "target_fraction": float(target_fraction),
        "target_state": target_y.tolist(),
        "base_initial_state": base_y[0].tolist(),
    }


def solve_reachability_candidate(
    response: np.ndarray,
    baseline: dict[str, np.ndarray],
    modes_tsc: np.ndarray,
    cfg: dict[str, Any],
    *,
    target_fraction: float,
    label: str,
) -> dict[str, Any]:
    try:
        from scipy.optimize import Bounds, LinearConstraint, minimize
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("scipy is required for constrained reachability optimization") from exc

    horizon = response.shape[2]
    modes_tsc = ensure_finite_array("modes_tsc", modes_tsc)
    if modes_tsc.shape[0] != 14:
        raise ValueError(f"modes_tsc must have shape (14,k), got {modes_tsc.shape}")
    k_modes = modes_tsc.shape[1]
    transform = block_diag_mode_transform(horizon, modes_tsc)
    a_track, b_track, meta = build_quadratic_tracking_system(
        response, baseline, cfg, mode_transform=transform, target_fraction=target_fraction
    )
    opt = cfg["optimization"]
    action_l2 = float(opt.get("action_increment_l2", 1e-3))
    current_l2 = float(opt.get("current_deviation_l2", 1e-5))
    cum = cumulative_current_matrix(horizon)
    cum_mode = cum @ transform

    n = horizon * k_modes
    q = a_track.T @ a_track
    c = -(a_track.T @ b_track)
    if action_l2 > 0:
        q += action_l2 * (transform.T @ transform)
    if current_l2 > 0:
        q += current_l2 * (cum_mode.T @ cum_mode)
    q = 0.5 * (q + q.T)

    def objective(x: np.ndarray) -> float:
        return float(0.5 * x @ q @ x + c @ x + 0.5 * b_track @ b_track)

    def jacobian(x: np.ndarray) -> np.ndarray:
        return q @ x + c

    env_cfg = cfg["_env_config"]
    max_delta_a = float(env_cfg["current_slew_a_per_ms"]) * float(env_cfg["dt_ms"])
    initial_currents = np.asarray(baseline["currents_a_tsc"][0], dtype=float)
    min_current = display_to_tsc(np.asarray(env_cfg["min_current_a_display_order"], dtype=float))
    max_current = display_to_tsc(np.asarray(env_cfg["max_current_a_display_order"], dtype=float))
    lower_current = np.tile(min_current - initial_currents, horizon)
    upper_current = np.tile(max_current - initial_currents, horizon)
    current_constraint = LinearConstraint(cum_mode, lower_current, upper_current)

    # Coefficients themselves do not have a direct physical bound.  Bound them
    # generously; exact per-coil slew is enforced as a linear constraint below.
    coeff_bound = float(opt.get("mode_coefficient_bound_a", max_delta_a * math.sqrt(14.0)))
    bounds = Bounds(-coeff_bound * np.ones(n), coeff_bound * np.ones(n))
    slew_constraint = LinearConstraint(transform, -max_delta_a, max_delta_a)

    x0 = np.zeros(n, dtype=float)
    result = minimize(
        objective,
        x0,
        jac=jacobian,
        method="SLSQP",
        bounds=bounds,
        constraints=[slew_constraint, current_constraint],
        options={
            "maxiter": int(opt.get("max_iterations", 1200)),
            "ftol": float(opt.get("ftol", 1e-10)),
            "disp": False,
        },
    )
    x = np.asarray(result.x, dtype=float)
    increments = (transform @ x).reshape(horizon, 14)
    cumulative = np.cumsum(increments, axis=0)
    currents = initial_currents[None, :] + cumulative

    base_y = np.column_stack([baseline["R"], baseline["Z"], baseline["Ip"]])
    h_all = np.vstack([response[t, :, :, :].reshape(3, horizon * 14) for t in range(horizon + 1)])
    predicted = base_y + (h_all @ increments.reshape(-1)).reshape(horizon + 1, 3)
    target = np.asarray([cfg["target"]["R"], cfg["target"]["Z"], cfg["target"]["Ip"]], dtype=float)
    r_tol = float(cfg["analysis"].get("r_scale_m", 0.08))
    z_tol = float(cfg["analysis"].get("z_scale_m", 0.08))
    distance = np.sqrt(((predicted[:, 0] - target[0]) / r_tol) ** 2 + ((predicted[:, 1] - target[1]) / z_tol) ** 2)
    terminal_error = predicted[-1] - target

    return {
        "label": label,
        "success": bool(result.success),
        "optimizer_status": int(result.status),
        "optimizer_message": str(result.message),
        "objective": float(result.fun),
        "n_modes": int(k_modes),
        "target_fraction": float(target_fraction),
        "metadata": meta,
        "action_increment_a_tsc": increments.tolist(),
        "action_increment_a_display": tsc_matrix_to_display(increments).tolist(),
        "action_norm_tsc": (increments / max_delta_a).tolist(),
        "current_a_tsc": currents.tolist(),
        "current_a_display": tsc_matrix_to_display(currents).tolist(),
        "predicted_trajectory": [
            {
                "step_index": t,
                "R": float(predicted[t, 0]),
                "Z": float(predicted[t, 1]),
                "Ip": float(predicted[t, 2]),
                "normalized_RZ_distance": float(distance[t]),
            }
            for t in range(horizon + 1)
        ],
        "predicted_terminal_error": {
            "R": float(terminal_error[0]),
            "Z": float(terminal_error[1]),
            "Ip": float(terminal_error[2]),
        },
        "predicted_min_normalized_RZ_distance": float(np.min(distance)),
        "predicted_terminal_normalized_RZ_distance": float(distance[-1]),
        "max_abs_increment_a": float(np.max(np.abs(increments))),
        "max_current_utilization": float(
            np.max(
                np.maximum(
                    np.abs(currents - initial_currents[None, :])
                    / np.maximum(max_current - min_current, 1e-9)[None, :],
                    0.0,
                )
            )
        ),
    }


def generate_analysis_plots(
    resolved: ResolvedStage1Config,
    baseline: dict[str, np.ndarray],
    svd: dict[str, Any],
    reachable: dict[str, Any],
    candidate_summary: list[dict[str, Any]],
) -> None:
    try:
        import matplotlib.pyplot as plt
    except Exception:
        return

    out = resolved.paths.analysis_dir
    singular = np.asarray(svd["singular_values"], dtype=float)
    plt.figure(figsize=(8, 5))
    plt.semilogy(np.arange(1, len(singular) + 1), singular, marker="o")
    plt.xlabel("Spatial coil mode index")
    plt.ylabel("Weighted singular value")
    plt.title("Stage-1 spatial actuator singular values")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(out / "spatial_singular_values.png", dpi=180)
    plt.close()

    modes_display = np.asarray(svd["modes_display"], dtype=float)
    k = min(int(svd["recommended_k"]), 8)
    plt.figure(figsize=(10, 6))
    image = plt.imshow(modes_display[:, :k], aspect="auto", origin="lower")
    plt.colorbar(image, label="Mode coefficient")
    plt.xticks(np.arange(k), [f"Mode {i+1}" for i in range(k)], rotation=45, ha="right")
    plt.yticks(np.arange(14), DISPLAY_COIL_NAMES)
    plt.title("Recommended spatial coil modes (display order)")
    plt.tight_layout()
    plt.savefig(out / "recommended_coil_modes.png", dpi=180)
    plt.close()

    points = reachable.get("points", [])
    if points:
        pts = np.asarray([[p["R"], p["Z"]] for p in points], dtype=float)
        target = reachable["target"]
        base = reachable["baseline_terminal"]
        hull_idx = reachable.get("hull_vertex_indices", [])
        plt.figure(figsize=(7, 7))
        plt.scatter(pts[:, 0], pts[:, 1], s=15, label="Support points")
        if hull_idx:
            ordered = pts[np.asarray(hull_idx, dtype=int)]
            ordered = np.vstack([ordered, ordered[0]])
            plt.plot(ordered[:, 0], ordered[:, 1], label="Local reachable boundary")
        plt.scatter([base["R"]], [base["Z"]], marker="x", s=80, label="Zero-action terminal")
        plt.scatter([target["R"]], [target["Z"]], marker="*", s=120, label="Target")
        plt.xlabel("R (m)")
        plt.ylabel("Z (m)")
        plt.title("Local linear 100 ms reachable set with current/slew limits")
        plt.grid(True)
        plt.axis("equal")
        plt.legend()
        plt.tight_layout()
        plt.savefig(out / "reachable_set_100ms.png", dpi=180)
        plt.close()

    if candidate_summary:
        rows = sorted(candidate_summary, key=lambda x: (x["n_modes"], x["target_fraction"]))
        plt.figure(figsize=(9, 5))
        for fraction in sorted(set(float(x["target_fraction"]) for x in rows)):
            sub = [x for x in rows if float(x["target_fraction"]) == fraction]
            plt.plot(
                [x["n_modes"] for x in sub],
                [x["predicted_terminal_normalized_RZ_distance"] for x in sub],
                marker="o",
                label=f"target fraction {fraction:g}",
            )
        plt.xlabel("Number of spatial modes")
        plt.ylabel("Predicted terminal normalized R/Z distance")
        plt.title("Constrained linear reachability by action-space dimension")
        plt.grid(True)
        plt.legend()
        plt.tight_layout()
        plt.savefig(out / "linear_candidate_mode_count.png", dpi=180)
        plt.close()


def generate_validation_plots(
    resolved: ResolvedStage1Config,
    validation_rows: list[dict[str, Any]],
) -> None:
    try:
        import matplotlib.pyplot as plt
    except Exception:
        return
    successful = [r for r in validation_rows if r.get("success")]
    if not successful:
        return
    successful = sorted(successful, key=lambda x: x["min_normalized_RZ_distance"])
    labels = [f"{x['candidate_label']}\nscale={x['sequence_scale']}" for x in successful]
    values = [x["min_normalized_RZ_distance"] for x in successful]
    plt.figure(figsize=(max(9, len(labels) * 0.8), 5))
    plt.bar(np.arange(len(labels)), values)
    plt.axhline(1.0, linestyle="--", label="1x tube")
    plt.axhline(2.0, linestyle=":", label="2x tube")
    plt.xticks(np.arange(len(labels)), labels, rotation=60, ha="right")
    plt.ylabel("Minimum normalized R/Z distance")
    plt.title("Real-TSC validation of optimized 100 ms sequences")
    plt.grid(True, axis="y")
    plt.legend()
    plt.tight_layout()
    plt.savefig(resolved.paths.validation_dir / "validation_min_distance.png", dpi=180)
    plt.close()

def candidate_rows(candidate: dict[str, Any]) -> list[dict[str, Any]]:
    increments_tsc = np.asarray(candidate["action_increment_a_tsc"], dtype=float)
    increments_display = tsc_matrix_to_display(increments_tsc)
    action_norm_tsc = np.asarray(candidate["action_norm_tsc"], dtype=float)
    action_norm_display = tsc_matrix_to_display(action_norm_tsc)
    rows: list[dict[str, Any]] = []
    for t in range(increments_tsc.shape[0]):
        row: dict[str, Any] = {"step_index": t}
        for i, name in enumerate(TSC_COIL_NAMES):
            row[f"delta_a_tsc_{name}"] = float(increments_tsc[t, i])
            row[f"action_norm_tsc_{name}"] = float(action_norm_tsc[t, i])
        for i, name in enumerate(DISPLAY_COIL_NAMES):
            row[f"delta_a_display_{name}"] = float(increments_display[t, i])
            row[f"action_norm_display_{name}"] = float(action_norm_display[t, i])
        rows.append(row)
    return rows


def run_analysis(resolved: ResolvedStage1Config) -> dict[str, Any]:
    initialize_run(resolved)
    cfg = copy.deepcopy(resolved.cfg)
    cfg["_env_config"] = resolved.env_cfg
    cfg["scan"]["dt_ms"] = int(resolved.env_cfg["dt_ms"])
    horizon = int(cfg["scan"]["horizon_steps"])
    results = load_scan_results(resolved.paths.raw_dir)
    successful = [r for r in results if r.get("success")]
    expected = len(build_scan_specs(cfg))
    failed = [r for r in results if not r.get("success")]
    if len(results) < expected:
        raise RuntimeError(
            f"scan incomplete: expected {expected} result files, found {len(results)}. "
            "Resume the scan before analysis."
        )

    # Individual large perturbations may legitimately fail TSC.  The response
    # fitter only requires at least two finite perturbations for each
    # (injection time, coil) group and will raise a precise error if a local
    # derivative cannot be identified.
    baseline, baseline_meta = baseline_summary(successful, horizon)
    response, fit_meta = fit_response_tensor(successful, baseline, horizon=horizon)
    svd = svd_diagnostics(response, cfg)
    horizon_rows = horizon_controllability_rows(response, cfg)
    reachable = compute_terminal_reachable_set(response, baseline, cfg)

    np.save(resolved.paths.analysis_dir / "response_tensor_dy_per_a.npy", response)
    np.save(resolved.paths.analysis_dir / "spatial_sensitivity_weighted.npy", svd["spatial_matrix"])
    np.save(resolved.paths.analysis_dir / "coil_modes_tsc.npy", svd["modes_tsc"])

    mode_rows = []
    for mode_index in range(14):
        row: dict[str, Any] = {
            "mode_index": mode_index + 1,
            "singular_value": float(svd["singular_values"][mode_index]),
            "singular_value_ratio": float(svd["singular_values"][mode_index] / max(svd["singular_values"][0], 1e-30)),
            "cumulative_energy": float(svd["cumulative_energy"][mode_index]),
        }
        for i, name in enumerate(TSC_COIL_NAMES):
            row[f"tsc_{name}"] = float(svd["modes_tsc"][i, mode_index])
        for i, name in enumerate(DISPLAY_COIL_NAMES):
            row[f"display_{name}"] = float(svd["modes_display"][i, mode_index])
        mode_rows.append(row)
    write_csv(resolved.paths.analysis_dir / "coil_modes.csv", mode_rows)
    write_csv(resolved.paths.analysis_dir / "horizon_controllability.csv", horizon_rows)
    write_csv(resolved.paths.analysis_dir / "pair_mode_ranking.csv", svd["pair_mode_rows"])
    write_csv(resolved.paths.analysis_dir / "response_fit_quality.csv", fit_meta["fit_rows"])
    write_csv(resolved.paths.analysis_dir / "reachable_set_100ms.csv", reachable["points"])
    atomic_write_json(resolved.paths.analysis_dir / "reachable_set_100ms.json", reachable)

    baseline_rows = []
    for t in range(horizon + 1):
        baseline_rows.append(
            {
                "step_index": t,
                "time_ms_from_start": t * int(resolved.env_cfg["dt_ms"]),
                "R": float(baseline["R"][t]),
                "Z": float(baseline["Z"][t]),
                "Ip": float(baseline["Ip"][t]),
                "vessel_current_total_a": float(baseline["vessel_current_total_a"][t]),
                "vessel_current_abs_sum_a": float(baseline["vessel_current_abs_sum_a"][t]),
            }
        )
    write_csv(resolved.paths.analysis_dir / "baseline_trajectory.csv", baseline_rows)

    opt = cfg["optimization"]
    mode_counts = sorted(set(int(x) for x in opt.get("mode_counts", [2, 3, 4, 5, 6, 8, 14])))
    mode_counts = [x for x in mode_counts if 1 <= x <= 14]
    fractions = [float(x) for x in opt.get("target_fractions", [0.5, 0.75, 1.0])]
    candidates: list[dict[str, Any]] = []
    for k in mode_counts:
        if k == 14 and bool(opt.get("full_14d_identity", True)):
            modes = np.eye(14)
            label_prefix = "full14"
        else:
            modes = svd["modes_tsc"][:, :k]
            label_prefix = f"svd{k:02d}"
        for fraction in fractions:
            label = f"{label_prefix}_target{fraction:.2f}".replace(".", "p")
            candidate = solve_reachability_candidate(
                response,
                baseline,
                modes,
                cfg,
                target_fraction=fraction,
                label=label,
            )
            candidates.append(candidate)
            atomic_write_json(resolved.paths.candidate_dir / f"{label}.json", candidate)
            write_csv(resolved.paths.candidate_dir / f"{label}.csv", candidate_rows(candidate))

    candidate_summary = []
    for c in candidates:
        candidate_summary.append(
            {
                "label": c["label"],
                "optimizer_success": c["success"],
                "n_modes": c["n_modes"],
                "target_fraction": c["target_fraction"],
                "objective": c["objective"],
                "predicted_terminal_R_error_m": c["predicted_terminal_error"]["R"],
                "predicted_terminal_Z_error_m": c["predicted_terminal_error"]["Z"],
                "predicted_terminal_Ip_error_A": c["predicted_terminal_error"]["Ip"],
                "predicted_min_normalized_RZ_distance": c["predicted_min_normalized_RZ_distance"],
                "predicted_terminal_normalized_RZ_distance": c["predicted_terminal_normalized_RZ_distance"],
                "max_abs_increment_a": c["max_abs_increment_a"],
                "max_current_utilization": c["max_current_utilization"],
            }
        )
    candidate_summary.sort(key=lambda x: (not x["optimizer_success"], x["predicted_terminal_normalized_RZ_distance"], x["objective"]))
    write_csv(resolved.paths.analysis_dir / "candidate_summary_linear.csv", candidate_summary)
    generate_analysis_plots(resolved, baseline, svd, reachable, candidate_summary)

    fit_rows = fit_meta["fit_rows"]
    reliability_cfg = cfg["analysis"].get("reliability", {})
    failed_fraction = len(failed) / max(expected, 1)
    median_nonlinearity = float(np.median([x["relative_nonlinearity_residual"] for x in fit_rows]))
    p90_nonlinearity = float(np.quantile([x["relative_nonlinearity_residual"] for x in fit_rows], 0.90))
    max_relative_leakage = float(np.max([x["relative_pre_injection_leakage"] for x in fit_rows]))
    non_bidirectional_groups = int(sum(not bool(x["bidirectional"]) for x in fit_rows))
    spread = baseline_meta["max_repeat_spread"]
    reliability_checks = {
        "baseline_R_spread_ok": float(spread.get("R", 0.0)) <= float(reliability_cfg.get("max_baseline_R_spread_m", 1e-4)),
        "baseline_Z_spread_ok": float(spread.get("Z", 0.0)) <= float(reliability_cfg.get("max_baseline_Z_spread_m", 1e-4)),
        "baseline_Ip_spread_ok": float(spread.get("Ip", 0.0)) <= float(reliability_cfg.get("max_baseline_Ip_spread_a", 50.0)),
        "failed_fraction_ok": failed_fraction <= float(reliability_cfg.get("max_failed_scan_fraction", 0.02)),
        "median_nonlinearity_ok": median_nonlinearity <= float(reliability_cfg.get("max_median_nonlinearity", 0.20)),
        "p90_nonlinearity_ok": p90_nonlinearity <= float(reliability_cfg.get("max_p90_nonlinearity", 0.40)),
        "pre_injection_leakage_ok": max_relative_leakage <= float(reliability_cfg.get("max_relative_pre_injection_leakage", 0.05)),
        "bidirectional_groups_ok": non_bidirectional_groups == 0,
    }

    analysis_summary = {
        "baseline": baseline_meta,
        "scan_experiments_expected": expected,
        "scan_experiments_successful": len(successful),
        "scan_experiments_failed": len(failed),
        "response_fit": {
            "median_relative_nonlinearity_residual": median_nonlinearity,
            "p90_relative_nonlinearity_residual": p90_nonlinearity,
            "max_relative_nonlinearity_residual": float(np.max([x["relative_nonlinearity_residual"] for x in fit_rows])),
            "max_relative_pre_injection_leakage": max_relative_leakage,
            "non_bidirectional_groups": non_bidirectional_groups,
        },
        "identification_reliability": {
            "reliable": bool(all(reliability_checks.values())),
            "checks": reliability_checks,
            "failed_scan_fraction": failed_fraction,
        },
        "svd": {
            "singular_values": svd["singular_values"].tolist(),
            "cumulative_energy": svd["cumulative_energy"].tolist(),
            "recommended_mode_count": int(svd["recommended_k"]),
            "condition_number_nonzero": svd["condition_number_nonzero"],
        },
        "reachable_set_100ms": {
            "target_inside_local_linear_RZ_projection": reachable["target_inside_local_linear_RZ_projection"],
            "failed_directions": reachable["failed_directions"],
            "terminal_ip_tolerance_a": reachable["terminal_ip_tolerance_a"],
        },
        "best_linear_candidate": candidate_summary[0] if candidate_summary else None,
    }
    atomic_write_json(resolved.paths.analysis_dir / "analysis_summary.json", analysis_summary)
    return analysis_summary


# -----------------------------------------------------------------------------
# Nonlinear TSC validation of optimized sequences
# -----------------------------------------------------------------------------


def select_validation_candidates(resolved: ResolvedStage1Config) -> list[dict[str, Any]]:
    cfg = resolved.cfg
    validation = cfg["validation"]
    all_candidates = []
    for path in sorted(resolved.paths.candidate_dir.glob("*.json")):
        payload = read_json(path)
        payload["_path"] = str(path)
        if payload.get("success"):
            all_candidates.append(payload)
    if not all_candidates:
        raise RuntimeError("no successful optimized candidates found")
    all_candidates.sort(
        key=lambda c: (
            c["predicted_terminal_normalized_RZ_distance"],
            c["objective"],
            c["n_modes"],
        )
    )

    selected: list[dict[str, Any]] = []
    labels = set(validation.get("explicit_candidate_labels", []))
    for c in all_candidates:
        if c["label"] in labels:
            selected.append(c)
    best_per_mode = int(validation.get("best_per_mode_count", 1))
    if best_per_mode > 0:
        counts: dict[int, int] = {}
        for c in all_candidates:
            n = int(c["n_modes"])
            if counts.get(n, 0) < best_per_mode:
                selected.append(c)
                counts[n] = counts.get(n, 0) + 1
    max_base = int(validation.get("max_base_candidates", 4))
    dedup: dict[str, dict[str, Any]] = {c["label"]: c for c in selected}
    if len(dedup) < max_base:
        for c in all_candidates:
            dedup.setdefault(c["label"], c)
            if len(dedup) >= max_base:
                break
    selected = list(dedup.values())[:max_base]

    scales = [float(x) for x in validation.get("sequence_scales", [0.5, 0.75, 1.0])]
    specs: list[dict[str, Any]] = []
    horizon = int(cfg["scan"]["horizon_steps"])
    for candidate in selected:
        action = np.asarray(candidate["action_norm_tsc"], dtype=float)
        if action.shape != (horizon, 14):
            raise ValueError(f"candidate {candidate['label']} has wrong action shape {action.shape}")
        for scale in scales:
            validation_id = f"{candidate['label']}_scale{scale:.3f}".replace(".", "p")
            specs.append(
                {
                    "kind": "validation",
                    "validation_id": validation_id,
                    "experiment_id": validation_id,
                    "candidate_label": candidate["label"],
                    "sequence_scale": scale,
                    "horizon_steps": horizon,
                    "action_sequence_norm_tsc": np.clip(scale * action, -1.0, 1.0).tolist(),
                }
            )
    return specs


def run_validation_experiment(env: Any, spec: dict[str, Any]) -> dict[str, Any]:
    started = time.time()
    horizon = int(spec["horizon_steps"])
    action_sequence = np.asarray(spec["action_sequence_norm_tsc"], dtype=float)
    trajectory: list[dict[str, Any]] = []
    failure_reason = ""
    try:
        env.reset()
        zero = np.zeros(14, dtype=float)
        trajectory.append(_state_record(env, 0, zero))
        for k in range(horizon):
            action = np.clip(action_sequence[k], -1.0, 1.0).astype(np.float32)
            _, _, terminated, truncated, info = env.step(action)
            trajectory.append(_state_record(env, k + 1, action))
            if terminated:
                failure_reason = str(info.get("failure_reason", "terminated"))
                break
            if truncated and k + 1 < horizon:
                failure_reason = "environment truncated before requested horizon"
                break
        success = len(trajectory) == horizon + 1 and not any(bool(x["abnormal"]) for x in trajectory)
        return {
            "schema_version": 1,
            "experiment_id": spec["experiment_id"],
            "spec": spec,
            "success": bool(success),
            "failure_reason": failure_reason if not success else "",
            "wall_time_s": float(time.time() - started),
            "trajectory": trajectory,
        }
    except Exception as exc:
        return {
            "schema_version": 1,
            "experiment_id": spec.get("experiment_id", "unknown"),
            "spec": spec,
            "success": False,
            "failure_reason": repr(exc),
            "traceback": traceback.format_exc(),
            "wall_time_s": float(time.time() - started),
            "trajectory": trajectory,
        }


class LocalValidationWorker:
    def __init__(self, train_cfg: dict[str, Any], worker_id: str):
        from tsc_rzip_rllib.envs.factory import make_tsc_rzip_env
        self.env = make_tsc_rzip_env(copy.deepcopy(train_cfg), worker_id=worker_id, seed=None)

    def run_validation(self, spec: dict[str, Any]) -> dict[str, Any]:
        return run_validation_experiment(self.env, spec)

    def close(self) -> None:
        self.env.close()


def _ray_validation_actor_class():
    import ray

    @ray.remote(num_cpus=1, max_restarts=0)
    class RayValidationWorker:
        def __init__(self, train_cfg: dict[str, Any], worker_id: str):
            self.worker = LocalValidationWorker(train_cfg, worker_id)

        def run_validation(self, spec: dict[str, Any]) -> dict[str, Any]:
            return self.worker.run_validation(spec)

        def close(self) -> None:
            self.worker.close()

    return RayValidationWorker


def validation_metrics(result: dict[str, Any], cfg: dict[str, Any], env_cfg: dict[str, Any]) -> dict[str, Any]:
    target = np.asarray([cfg["target"]["R"], cfg["target"]["Z"], cfg["target"]["Ip"]], dtype=float)
    trajectory = result.get("trajectory", [])
    if not trajectory:
        return {
            "validation_id": result.get("experiment_id"),
            "success": False,
            "failure_reason": result.get("failure_reason", "empty trajectory"),
        }
    y = np.asarray([[x["R"], x["Z"], x["Ip"]] for x in trajectory], dtype=float)
    errors = y - target[None, :]
    r_tol = float(cfg["analysis"].get("r_scale_m", 0.08))
    z_tol = float(cfg["analysis"].get("z_scale_m", 0.08))
    dist = np.sqrt((errors[:, 0] / r_tol) ** 2 + (errors[:, 1] / z_tol) ** 2)
    dt_s = float(env_cfg["dt_ms"]) / 1000.0
    velocity = np.zeros((len(y), 2), dtype=float)
    if len(y) > 1:
        velocity[1:] = np.diff(y[:, :2], axis=0) / dt_s
    velocity_norm = np.linalg.norm(velocity, axis=1)
    late_n = min(int(cfg["validation"].get("late_window_steps", 4)), len(y))
    late = slice(len(y) - late_n, len(y))
    currents = np.asarray([x["currents_a_display"] for x in trajectory], dtype=float)
    min_i = np.asarray(env_cfg["min_current_a_display_order"], dtype=float)
    max_i = np.asarray(env_cfg["max_current_a_display_order"], dtype=float)
    center = 0.5 * (min_i + max_i)
    half = 0.5 * (max_i - min_i)
    current_util = np.max(np.abs((currents - center[None, :]) / np.maximum(half[None, :], 1e-9)))
    tube_1x_rz = (np.abs(errors[:, 0]) <= r_tol) & (np.abs(errors[:, 1]) <= z_tol)
    tube_2x_rz = (np.abs(errors[:, 0]) <= 2 * r_tol) & (np.abs(errors[:, 1]) <= 2 * z_tol)
    gate_ip_tolerance = float(cfg["validation"].get("gate_ip_tolerance_a", 10000.0))
    ip_safe = np.abs(errors[:, 2]) <= gate_ip_tolerance
    tube_1x = tube_1x_rz & ip_safe
    tube_2x = tube_2x_rz & ip_safe
    initial_dist = float(dist[0])
    return {
        "validation_id": result.get("experiment_id"),
        "candidate_label": result.get("spec", {}).get("candidate_label"),
        "sequence_scale": result.get("spec", {}).get("sequence_scale"),
        "success": bool(result.get("success", False)),
        "failure_reason": result.get("failure_reason", ""),
        "terminal_R_error_m": float(errors[-1, 0]),
        "terminal_Z_error_m": float(errors[-1, 1]),
        "terminal_Ip_error_A": float(errors[-1, 2]),
        "terminal_normalized_RZ_distance": float(dist[-1]),
        "min_normalized_RZ_distance": float(np.min(dist)),
        "relative_distance_reduction": float((initial_dist - np.min(dist)) / max(initial_dist, 1e-12)),
        "first_step_within_2x_RZ_only": int(np.where(tube_2x_rz)[0][0]) if np.any(tube_2x_rz) else -1,
        "first_step_within_1x_RZ_only": int(np.where(tube_1x_rz)[0][0]) if np.any(tube_1x_rz) else -1,
        "first_step_within_2x": int(np.where(tube_2x)[0][0]) if np.any(tube_2x) else -1,
        "first_step_within_1x": int(np.where(tube_1x)[0][0]) if np.any(tube_1x) else -1,
        "terminal_within_2x_RZ_only": bool(tube_2x_rz[-1]),
        "terminal_within_1x_RZ_only": bool(tube_1x_rz[-1]),
        "terminal_within_2x": bool(tube_2x[-1]),
        "terminal_within_1x": bool(tube_1x[-1]),
        "gate_ip_tolerance_A": gate_ip_tolerance,
        "late_fraction_within_2x": float(np.mean(tube_2x[late])),
        "late_fraction_within_1x": float(np.mean(tube_1x[late])),
        "late_R_rms_m": float(np.sqrt(np.mean(errors[late, 0] ** 2))),
        "late_Z_rms_m": float(np.sqrt(np.mean(errors[late, 1] ** 2))),
        "terminal_velocity_m_per_s": float(velocity_norm[-1]),
        "max_velocity_m_per_s": float(np.max(velocity_norm)),
        "late_velocity_rms_m_per_s": float(np.sqrt(np.mean(velocity_norm[late] ** 2))),
        "max_current_utilization": float(current_util),
        "wall_time_s": float(result.get("wall_time_s", 0.0)),
    }


def run_validation(resolved: ResolvedStage1Config, *, backend: str = "ray", resume: bool = True) -> dict[str, Any]:
    initialize_run(resolved)
    specs = select_validation_candidates(resolved)
    pending = []
    for spec in specs:
        path = resolved.paths.validation_dir / f"{spec['validation_id']}.json.gz"
        if resume and _is_complete_result(path):
            continue
        pending.append(spec)

    if backend == "serial":
        worker = LocalValidationWorker(resolved.train_cfg, "stage1_validation_serial")
        try:
            for idx, spec in enumerate(pending, start=1):
                result = worker.run_validation(spec)
                atomic_write_json_gz(resolved.paths.validation_dir / f"{spec['validation_id']}.json.gz", result)
                print(f"[stage1 validation] {idx}/{len(pending)}", flush=True)
        finally:
            worker.close()
    elif backend == "ray" and pending:
        import ray

        parallel = resolved.cfg.get("parallel", {})
        n_workers = int(os.environ.get("STAGE1_WORKERS", parallel.get("n_workers", 192)))
        n_workers = max(1, min(n_workers, len(pending)))
        ray_tmpdir = os.environ.get("RAY_TMPDIR", parallel.get("ray_tmpdir", "")) or None
        if not ray.is_initialized():
            ray.init(
                num_cpus=n_workers,
                include_dashboard=False,
                ignore_reinit_error=True,
                _temp_dir=ray_tmpdir,
                log_to_driver=False,
            )
        Actor = _ray_validation_actor_class()
        actors = [Actor.remote(resolved.train_cfg, f"stage1_val_{i:03d}") for i in range(n_workers)]
        refs = {
            actors[idx % n_workers].run_validation.remote(spec): spec for idx, spec in enumerate(pending)
        }
        done_count = 0
        try:
            while refs:
                ready, _ = ray.wait(list(refs), num_returns=1, timeout=30.0)
                if not ready:
                    print(f"[stage1 validation] waiting {done_count}/{len(pending)}", flush=True)
                    continue
                for ref in ready:
                    spec = refs.pop(ref)
                    try:
                        result = ray.get(ref)
                    except Exception as exc:
                        result = {
                            "experiment_id": spec["validation_id"],
                            "spec": spec,
                            "success": False,
                            "failure_reason": repr(exc),
                            "traceback": traceback.format_exc(),
                            "trajectory": [],
                        }
                    atomic_write_json_gz(resolved.paths.validation_dir / f"{spec['validation_id']}.json.gz", result)
                    done_count += 1
                    print(f"[stage1 validation] {done_count}/{len(pending)}", flush=True)
        finally:
            for actor in actors:
                try:
                    ray.kill(actor, no_restart=True)
                except Exception:
                    pass
    elif backend != "ray":
        raise ValueError("backend must be 'ray' or 'serial'")

    results = []
    for path in sorted(resolved.paths.validation_dir.glob("*.json.gz")):
        payload = read_json_gz(path)
        results.append(validation_metrics(payload, resolved.cfg, resolved.env_cfg))
    results.sort(
        key=lambda x: (
            not bool(x.get("success")),
            safe_float(x.get("min_normalized_RZ_distance"), float("inf")),
            safe_float(x.get("terminal_normalized_RZ_distance"), float("inf")),
        )
    )
    write_csv(resolved.paths.validation_dir / "validation_summary.csv", results)
    generate_validation_plots(resolved, results)
    verdict = build_gate_a_verdict(resolved, results)
    atomic_write_json(resolved.paths.validation_dir / "gate_a_verdict.json", verdict)
    atomic_write_text(resolved.paths.run_dir / "STAGE1_REPORT.md", render_stage1_report(resolved, results, verdict))
    return verdict


def build_gate_a_verdict(resolved: ResolvedStage1Config, rows: list[dict[str, Any]]) -> dict[str, Any]:
    successful = [r for r in rows if r.get("success")]
    reached_1x = [r for r in successful if r.get("first_step_within_1x", -1) >= 0]
    terminal_1x = [r for r in successful if r.get("terminal_within_1x")]
    reached_2x = [r for r in successful if r.get("first_step_within_2x", -1) >= 0]
    reduction_threshold = float(resolved.cfg["validation"].get("promising_distance_reduction", 0.5))
    promising = [r for r in successful if safe_float(r.get("relative_distance_reduction"), 0.0) >= reduction_threshold]
    if terminal_1x:
        status = "PASS_TERMINAL_1X"
        interpretation = "At least one real-TSC sequence is inside the 1x R/Z target tube at 100 ms."
    elif reached_1x:
        status = "PASS_REACHED_1X_TRANSIENT"
        interpretation = "At least one real-TSC sequence reaches the 1x tube, but does not remain there at 100 ms."
    elif reached_2x:
        status = "PROMISING_REACHED_2X"
        interpretation = "No 1x reach yet, but at least one real-TSC sequence reaches the relaxed 2x tube."
    elif promising:
        status = "PROMISING_LARGE_REDUCTION"
        interpretation = "No target-tube reach, but a real-TSC candidate reduces normalized R/Z distance substantially."
    else:
        status = "FAIL_OR_INCONCLUSIVE"
        interpretation = "No validated real-TSC sequence reaches the relaxed tube or produces the required distance reduction."
    best = successful[0] if successful else None
    return {
        "status": status,
        "interpretation": interpretation,
        "n_validations": len(rows),
        "n_successful_tsc": len(successful),
        "n_reached_1x": len(reached_1x),
        "n_terminal_1x": len(terminal_1x),
        "n_reached_2x": len(reached_2x),
        "best_validation": best,
        "gate_definition": {
            "r_1x_m": float(resolved.cfg["analysis"].get("r_scale_m", 0.08)),
            "z_1x_m": float(resolved.cfg["analysis"].get("z_scale_m", 0.08)),
            "horizon_steps": int(resolved.cfg["scan"]["horizon_steps"]),
            "dt_ms": int(resolved.env_cfg["dt_ms"]),
        },
    }


def render_stage1_report(
    resolved: ResolvedStage1Config,
    validation_rows: list[dict[str, Any]],
    verdict: dict[str, Any],
) -> str:
    analysis_path = resolved.paths.analysis_dir / "analysis_summary.json"
    analysis = read_json(analysis_path) if analysis_path.exists() else {}
    best = verdict.get("best_validation") or {}
    lines = [
        "# Stage 1 — TSC/RZIP controllability and 100 ms reachability report",
        "",
        f"- Verdict: **{verdict['status']}**",
        f"- Interpretation: {verdict['interpretation']}",
        f"- Real-TSC validations: {verdict['n_successful_tsc']} successful / {verdict['n_validations']} total",
        "",
        "## Baseline",
        "",
        f"- Initial state: `{analysis.get('baseline', {}).get('initial_state')}`",
        f"- Zero-action terminal state: `{analysis.get('baseline', {}).get('terminal_state')}`",
        f"- Baseline repeat spread: `{analysis.get('baseline', {}).get('max_repeat_spread')}`",
        "",
        "## Local system identification",
        "",
        f"- Recommended spatial coil-mode count: `{analysis.get('svd', {}).get('recommended_mode_count')}`",
        f"- Singular values: `{analysis.get('svd', {}).get('singular_values')}`",
        f"- Median response-fit nonlinearity residual: `{analysis.get('response_fit', {}).get('median_relative_nonlinearity_residual')}`",
        "",
        "## Best nonlinear TSC validation",
        "",
        f"- Candidate: `{best.get('candidate_label')}`",
        f"- Sequence scale: `{best.get('sequence_scale')}`",
        f"- Terminal R error: `{best.get('terminal_R_error_m')}` m",
        f"- Terminal Z error: `{best.get('terminal_Z_error_m')}` m",
        f"- Minimum normalized R/Z distance: `{best.get('min_normalized_RZ_distance')}`",
        f"- Terminal normalized R/Z distance: `{best.get('terminal_normalized_RZ_distance')}`",
        f"- First step within 2x tube: `{best.get('first_step_within_2x')}`",
        f"- First step within 1x tube: `{best.get('first_step_within_1x')}`",
        f"- Terminal velocity: `{best.get('terminal_velocity_m_per_s')}` m/s",
        "",
        "## Interpretation rules",
        "",
        "- PASS_TERMINAL_1X: a real-TSC candidate is inside the 1x tube at 100 ms.",
        "- PASS_REACHED_1X_TRANSIENT: a candidate reaches the 1x tube but does not remain there.",
        "- PROMISING_REACHED_2X: a candidate reaches the 2x tube.",
        "- PROMISING_LARGE_REDUCTION: substantial real-TSC distance reduction without tube entry.",
        "- FAIL_OR_INCONCLUSIVE: current local model/action limits/horizon do not produce enough progress.",
        "",
        "The real-TSC validation is the source of truth; the local linear prediction is diagnostic only.",
    ]
    return "\n".join(lines) + "\n"


# -----------------------------------------------------------------------------
# Synthetic self-test (no TSC)
# -----------------------------------------------------------------------------


def synthetic_self_test() -> dict[str, Any]:
    horizon = 4
    rng = np.random.default_rng(1234)
    response = np.zeros((horizon + 1, 3, horizon, 14), dtype=float)
    for t in range(horizon + 1):
        for k in range(horizon):
            if t > k:
                decay = 1.0 - 0.1 * (t - k - 1)
                response[t, :, k, :] = decay * rng.normal(scale=[0.005, 0.004, 30.0], size=(14, 3)).T
    baseline = {
        "R": np.linspace(0.55, 0.56, horizon + 1),
        "Z": np.linspace(-0.15, -0.14, horizon + 1),
        "Ip": np.linspace(30000, 29800, horizon + 1),
        "currents_a_tsc": np.zeros((horizon + 1, 14)),
    }
    cfg = {
        "target": {"R": 0.75, "Z": 0.0, "Ip": 29779.724},
        "scan": {"horizon_steps": horizon, "dt_ms": 10},
        "analysis": {
            "r_scale_m": 0.08,
            "z_scale_m": 0.08,
            "ip_scale_a": 8000.0,
            "ip_weight": 0.15,
            "mode_energy_target": 0.99,
            "singular_ratio_floor": 1e-3,
            "max_recommended_modes": 8,
        },
        "optimization": {
            "tracking_steps": [2, 3, 4],
            "tracking_step_weights": [0.5, 0.8, 1.0],
            "velocity_steps": [3, 4],
            "velocity_weight": 0.1,
            "r_velocity_scale_m_per_s": 1.0,
            "z_velocity_scale_m_per_s": 1.0,
            "action_increment_l2": 1e-3,
            "current_deviation_l2": 1e-5,
            "max_iterations": 100,
            "ftol": 1e-9,
        },
        "_env_config": {
            "current_slew_a_per_ms": 0.3,
            "dt_ms": 10,
            "min_current_a_display_order": [-400.0] * 14,
            "max_current_a_display_order": [400.0] * 14,
        },
    }
    svd = svd_diagnostics(response, cfg)
    candidate = solve_reachability_candidate(
        response, baseline, svd["modes_tsc"][:, :4], cfg, target_fraction=0.5, label="synthetic"
    )
    assert np.asarray(candidate["action_increment_a_tsc"]).shape == (horizon, 14)
    assert candidate["max_abs_increment_a"] <= 3.0 + 1e-6
    return {
        "status": "ok",
        "recommended_modes": svd["recommended_k"],
        "optimizer_success": candidate["success"],
        "max_abs_increment_a": candidate["max_abs_increment_a"],
    }
