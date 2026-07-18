from __future__ import annotations

import copy
import csv
import gzip
import json
import math
import os
import shutil
import time
from pathlib import Path
from typing import Any

import numpy as np

from tsc_rzip_rllib.diagnostics import stage1_controllability as base


def _read_csv(path: Path) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _shutdown_ray() -> None:
    try:
        import ray

        if ray.is_initialized():
            ray.shutdown()
    except Exception:
        pass


def _source_from_manifest(run_dir: Path) -> Path | None:
    manifest = run_dir / "stage1_1_manifest.json"
    if not manifest.exists():
        return None
    payload = base.read_json(manifest)
    source = payload.get("source_stage1_run")
    return Path(source).expanduser().resolve() if source else None


def resolve_source_run(source_run: str | Path | None, run_dir: Path) -> Path:
    if source_run is not None:
        source = Path(source_run).expanduser().resolve()
    else:
        source = _source_from_manifest(run_dir)
        if source is None:
            raise ValueError("--source-run is required when creating a new Stage1.1 run")
    required = [
        source / "raw_experiments",
        source / "train_config.resolved.json",
        source / "env_config.resolved.json",
        source / "stage1_config.resolved.json",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError("source Stage1 run is incomplete: " + ", ".join(missing))
    return source


def _adopt_source_runtime_config(
    resolved: base.ResolvedStage1Config,
    source_run: Path,
) -> None:
    source_train = base.read_json(source_run / "train_config.resolved.json")
    source_env = base.read_json(source_run / "env_config.resolved.json")
    source_stage = base.read_json(source_run / "stage1_config.resolved.json")

    source_target = source_stage.get("target", {})
    requested_target = resolved.cfg.get("target", {})
    for key in ("R", "Z", "Ip"):
        if not math.isclose(float(source_target[key]), float(requested_target[key]), rel_tol=0.0, abs_tol=1e-9):
            raise ValueError(f"Stage1.1 target {key} differs from source Stage1 run")
    source_horizon = int(source_stage["scan"]["horizon_steps"])
    requested_horizon = int(resolved.cfg["scan"]["horizon_steps"])
    if source_horizon != requested_horizon:
        raise ValueError("Stage1.1 horizon differs from source Stage1 run")

    # Use the exact runtime configuration that generated the source data.  Only
    # redirect env_config to the private Stage1.1 resolved copy.
    resolved.env_cfg.clear()
    resolved.env_cfg.update(copy.deepcopy(source_env))
    # The 21 source failures were 120 s TSC timeouts rather than a coherent
    # physical channel/sign failure.  Stage1.1 retries with lower concurrency
    # and a slightly larger operational timeout.  This does not change the
    # physics, action sequence, or state definition.
    retry_timeout = float(resolved.cfg.get("supplement", {}).get("retry_tsc_timeout_s", source_env.get("tsc_timeout_s", 120.0)))
    resolved.env_cfg["tsc_timeout_s"] = retry_timeout
    resolved.train_cfg.clear()
    resolved.train_cfg.update(copy.deepcopy(source_train))
    resolved.train_cfg["env_config"] = str(resolved.paths.run_dir / "env_config.resolved.json")
    resolved.train_cfg.setdefault("episode", {})["max_episode_steps"] = requested_horizon
    resolved.train_cfg.setdefault("target", {}).update(copy.deepcopy(requested_target))


def prepare_stage1_1_run(
    resolved: base.ResolvedStage1Config,
    *,
    source_run: str | Path | None,
) -> Path:
    run_dir = resolved.paths.run_dir
    source = resolve_source_run(source_run, run_dir)
    _adopt_source_runtime_config(resolved, source)
    base.initialize_run(resolved)

    copied = 0
    for source_path in sorted((source / "raw_experiments").glob("*.json.gz")):
        destination = resolved.paths.raw_dir / source_path.name
        if destination.exists():
            continue
        shutil.copy2(source_path, destination)
        copied += 1

    reference = run_dir / "source_reference"
    reference.mkdir(parents=True, exist_ok=True)
    for relative in [
        "STAGE1_REPORT.md",
        "analysis/analysis_summary.json",
        "analysis/coil_modes.csv",
        "analysis/candidate_summary_linear.csv",
        "validation/validation_summary.csv",
        "validation/gate_a_verdict.json",
    ]:
        source_path = source / relative
        if source_path.exists():
            destination = reference / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            if not destination.exists():
                shutil.copy2(source_path, destination)
    source_validation = reference / "validation_raw"
    source_validation.mkdir(exist_ok=True)
    for source_path in sorted((source / "validation").glob("*.json.gz")):
        destination = source_validation / source_path.name
        if not destination.exists():
            shutil.copy2(source_path, destination)

    manifest = {
        "stage": "Stage1.1",
        "created_utc": base.utc_timestamp(),
        "source_stage1_run": str(source),
        "source_raw_experiments": len(list((source / "raw_experiments").glob("*.json.gz"))),
        "new_raw_files_copied": copied,
        "source_start_folder": resolved.env_cfg.get("start_folder"),
        "stage1_1_tsc_timeout_s": resolved.env_cfg.get("tsc_timeout_s"),
        "horizon_steps": int(resolved.cfg["scan"]["horizon_steps"]),
        "dt_ms": int(resolved.env_cfg["dt_ms"]),
        "target": copy.deepcopy(resolved.cfg["target"]),
    }
    base.atomic_write_json(run_dir / "stage1_1_manifest.json", manifest)
    return source


def pending_scan_specs(resolved: base.ResolvedStage1Config) -> list[dict[str, Any]]:
    pending: list[dict[str, Any]] = []
    for spec in base.build_scan_specs(resolved.cfg):
        path = resolved.paths.raw_dir / f"{spec['experiment_id']}.json.gz"
        if not base._is_complete_result(path):
            pending.append(spec)
    return pending


def write_failed_experiment_report(resolved: base.ResolvedStage1Config) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(resolved.paths.raw_dir.glob("*.json.gz")):
        try:
            payload = base.read_json_gz(path)
        except Exception as exc:
            rows.append({
                "experiment_id": path.stem,
                "success": False,
                "failure_reason": f"unreadable result: {exc!r}",
            })
            continue
        if payload.get("success"):
            continue
        spec = payload.get("spec", {})
        rows.append({
            "experiment_id": payload.get("experiment_id"),
            "kind": spec.get("kind"),
            "injection_step": spec.get("injection_step"),
            "coil_index_tsc": spec.get("coil_index_tsc"),
            "coil_name_tsc": spec.get("coil_name_tsc"),
            "amplitude_fraction": spec.get("amplitude_fraction"),
            "sign": spec.get("sign"),
            "trajectory_length": len(payload.get("trajectory", [])),
            "wall_time_s": payload.get("wall_time_s"),
            "failure_reason": payload.get("failure_reason"),
        })
    base.write_csv(resolved.paths.run_dir / "failed_experiments_current.csv", rows)
    return rows


def retry_failed_scan(
    resolved: base.ResolvedStage1Config,
    *,
    allow_incomplete: bool = False,
) -> dict[str, Any]:
    plan = resolved.cfg.get("supplement", {}).get(
        "retry_plan",
        [
            {"backend": "ray", "workers": 12},
            {"backend": "ray", "workers": 4},
            {"backend": "serial", "workers": 1},
        ],
    )
    rounds: list[dict[str, Any]] = []
    original_workers = os.environ.get("STAGE1_WORKERS")
    try:
        for round_index, entry in enumerate(plan, start=1):
            pending_before = pending_scan_specs(resolved)
            if not pending_before:
                break
            backend = str(entry.get("backend", "ray"))
            workers = int(entry.get("workers", 1))
            os.environ["STAGE1_WORKERS"] = str(max(1, workers))
            _shutdown_ray()
            started = time.time()
            result = base.run_scan(resolved, backend=backend, resume=True)
            _shutdown_ray()
            pending_after = pending_scan_specs(resolved)
            row = {
                "round": round_index,
                "backend": backend,
                "workers": workers,
                "pending_before": len(pending_before),
                "pending_after": len(pending_after),
                "newly_recovered": len(pending_before) - len(pending_after),
                "wall_time_s": time.time() - started,
                "run_scan_summary": result,
            }
            rounds.append(row)
            print(
                f"[Stage1.1 retry] round={round_index} backend={backend} workers={workers} "
                f"pending {len(pending_before)} -> {len(pending_after)}",
                flush=True,
            )
    finally:
        _shutdown_ray()
        if original_workers is None:
            os.environ.pop("STAGE1_WORKERS", None)
        else:
            os.environ["STAGE1_WORKERS"] = original_workers

    remaining = write_failed_experiment_report(resolved)
    summary = {
        "rounds": rounds,
        "remaining_failed": len(remaining),
        "scan_complete": len(remaining) == 0,
        "finished_utc": base.utc_timestamp(),
    }
    base.atomic_write_json(resolved.paths.run_dir / "stage1_1_retry_summary.json", summary)
    if remaining and not allow_incomplete:
        raise RuntimeError(
            f"Stage1.1 still has {len(remaining)} failed scan experiments after all retry rounds. "
            "Inspect failed_experiments_current.csv or rerun with --allow-incomplete-scan."
        )
    return summary


def _response_groups(
    resolved: base.ResolvedStage1Config,
) -> tuple[dict[str, np.ndarray], dict[tuple[int, int], list[tuple[float, np.ndarray]]]]:
    horizon = int(resolved.cfg["scan"]["horizon_steps"])
    results = base.load_scan_results(resolved.paths.raw_dir)
    successful = [result for result in results if result.get("success")]
    baseline, _ = base.baseline_summary(successful, horizon)
    base_y = np.column_stack([baseline["R"], baseline["Z"], baseline["Ip"]])
    groups: dict[tuple[int, int], list[tuple[float, np.ndarray]]] = {}
    for result in successful:
        spec = result.get("spec", {})
        if spec.get("kind") != "scan":
            continue
        x = base.safe_float(result.get("effective_injection_delta_a"))
        if not math.isfinite(x) or abs(x) < 1e-12:
            continue
        y = np.column_stack([
            base.trajectory_array(result, "R"),
            base.trajectory_array(result, "Z"),
            base.trajectory_array(result, "Ip"),
        ])
        groups.setdefault((int(spec["injection_step"]), int(spec["coil_index_tsc"])), []).append((x, y - base_y))
    return baseline, groups


def bootstrap_mode_robustness(
    resolved: base.ResolvedStage1Config,
) -> dict[str, Any]:
    try:
        from scipy.linalg import subspace_angles
    except Exception as exc:
        raise RuntimeError("scipy is required for Stage1.1 mode-robustness analysis") from exc

    horizon = int(resolved.cfg["scan"]["horizon_steps"])
    _, groups = _response_groups(resolved)
    missing = [
        (k, coil) for k in range(horizon) for coil in range(14)
        if (k, coil) not in groups
    ]
    if missing:
        raise RuntimeError(f"response groups missing after retry: {missing[:10]}")

    weights = base.output_weights(resolved.cfg)

    def fit_tensor(selected: dict[tuple[int, int], list[tuple[float, np.ndarray]]]) -> np.ndarray:
        response = np.zeros((horizon + 1, 3, horizon, 14), dtype=float)
        for (k, coil), items in selected.items():
            x = np.asarray([item[0] for item in items], dtype=float)
            dy = np.stack([item[1] for item in items])
            response[:, :, k, coil] = np.tensordot(x, dy, axes=(0, 0)) / max(float(x @ x), 1e-30)
        return response

    reference_response = fit_tensor(groups)
    _, reference_s, reference_vt = np.linalg.svd(
        base.build_spatial_sensitivity(reference_response, weights),
        full_matrices=False,
    )
    reference_modes = reference_vt.T
    n_samples = int(resolved.cfg.get("supplement", {}).get("bootstrap_samples", 300))
    seed = int(resolved.cfg.get("supplement", {}).get("bootstrap_seed", 20260718))
    rng = np.random.default_rng(seed)
    sample_rows: list[dict[str, Any]] = []
    for sample_index in range(n_samples):
        selected: dict[tuple[int, int], list[tuple[float, np.ndarray]]] = {}
        for key, items in groups.items():
            positive = [item for item in items if item[0] > 0]
            negative = [item for item in items if item[0] < 0]
            if not positive or not negative:
                raise RuntimeError(f"non-bidirectional group encountered in bootstrap: {key}")
            selected[key] = [
                positive[int(rng.integers(len(positive)))],
                negative[int(rng.integers(len(negative)))],
            ]
        response = fit_tensor(selected)
        _, singular, vt = np.linalg.svd(
            base.build_spatial_sensitivity(response, weights),
            full_matrices=False,
        )
        modes = vt.T
        row: dict[str, Any] = {
            "sample_index": sample_index,
            "sigma_1": float(singular[0]),
            "sigma_2": float(singular[1]),
            "sigma_3": float(singular[2]),
            "sigma_4": float(singular[3]),
        }
        for mode_count in (1, 2, 3, 4, 5, 8):
            angles = np.rad2deg(subspace_angles(reference_modes[:, :mode_count], modes[:, :mode_count]))
            row[f"mode_{mode_count}_max_principal_angle_deg"] = float(np.max(angles))
            row[f"mode_{mode_count}_mean_principal_angle_deg"] = float(np.mean(angles))
        sample_rows.append(row)
    base.write_csv(resolved.paths.analysis_dir / "mode_bootstrap_samples.csv", sample_rows)

    summary_rows: list[dict[str, Any]] = []
    for mode_count in (1, 2, 3, 4, 5, 8):
        values = np.asarray([row[f"mode_{mode_count}_max_principal_angle_deg"] for row in sample_rows])
        summary_rows.append({
            "mode_count": mode_count,
            "max_principal_angle_p50_deg": float(np.quantile(values, 0.50)),
            "max_principal_angle_p90_deg": float(np.quantile(values, 0.90)),
            "max_principal_angle_p95_deg": float(np.quantile(values, 0.95)),
            "max_principal_angle_p99_deg": float(np.quantile(values, 0.99)),
            "max_principal_angle_max_deg": float(np.max(values)),
        })
    base.write_csv(resolved.paths.analysis_dir / "mode_bootstrap_robustness_summary.csv", summary_rows)
    summary = {
        "n_samples": n_samples,
        "seed": seed,
        "reference_singular_values": reference_s.tolist(),
        "rows": summary_rows,
    }
    base.atomic_write_json(resolved.paths.analysis_dir / "mode_bootstrap_robustness_summary.json", summary)
    return summary


def rescore_source_reference(
    resolved: base.ResolvedStage1Config,
) -> list[dict[str, Any]]:
    reference = resolved.paths.run_dir / "source_reference"
    raw_dir = reference / "validation_raw"
    rows: list[dict[str, Any]] = []
    for path in sorted(raw_dir.glob("*.json.gz")):
        payload = base.read_json_gz(path)
        spec = payload.setdefault("spec", {})
        label = str(spec.get("candidate_label") or "")
        if label.startswith("svd") and len(label) >= 5:
            try:
                spec["candidate_n_modes"] = int(label[3:5])
            except ValueError:
                pass
        elif label.startswith("full14"):
            spec["candidate_n_modes"] = 14
        rows.append(base.validation_metrics(payload, resolved.cfg, resolved.env_cfg))

    baseline_path = resolved.paths.raw_dir / "baseline_r00.json.gz"
    if baseline_path.exists():
        payload = copy.deepcopy(base.read_json_gz(baseline_path))
        payload["experiment_id"] = "zero_action_baseline"
        payload["spec"] = {
            "candidate_label": "zero_action_baseline",
            "sequence_scale": 0.0,
            "kind": "reference_baseline",
        }
        rows.append(base.validation_metrics(payload, resolved.cfg, resolved.env_cfg))
    base._attach_zero_action_comparisons(rows)
    base.write_csv(reference / "validation_summary_strict.csv", rows)
    verdict = base.build_gate_a_verdict(resolved, rows)
    base.atomic_write_json(reference / "gate_verdict_strict.json", verdict)
    return rows


def generate_stage1_1_plots(resolved: base.ResolvedStage1Config) -> None:
    try:
        import matplotlib.pyplot as plt
    except Exception:
        return
    summary_path = resolved.paths.validation_dir / "validation_summary.csv"
    if not summary_path.exists():
        return
    rows = _read_csv(summary_path)
    candidates = [row for row in rows if row.get("candidate_label") != "zero_action_baseline" and row.get("success") == "True"]
    if not candidates:
        return

    plt.figure(figsize=(8, 5))
    for row in candidates:
        x = float(row["terminal_RZ_euclidean_error_m"]) * 1000.0
        y = float(row["terminal_velocity_m_per_s"])
        label = f"m{row.get('candidate_n_modes')} s={float(row['sequence_scale']):.2f}"
        plt.scatter([x], [y])
        plt.annotate(label, (x, y))
    plt.axhline(float(resolved.cfg["validation"]["terminal_velocity_max_m_per_s"]), linestyle="--")
    plt.xlabel("Terminal Euclidean R/Z error (mm)")
    plt.ylabel("Terminal velocity (m/s)")
    plt.title("Stage1.1 low-dimensional accuracy–damping trade-off")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(resolved.paths.validation_dir / "stage1_1_accuracy_damping_tradeoff.png", dpi=180)
    plt.close()

    mode_counts = sorted({int(float(row["candidate_n_modes"])) for row in candidates})
    scales = sorted({float(row["sequence_scale"]) for row in candidates})
    for metric, ylabel, filename in [
        ("terminal_RZ_euclidean_error_m", "Terminal error (mm)", "stage1_1_error_by_mode.png"),
        ("terminal_velocity_m_per_s", "Terminal velocity (m/s)", "stage1_1_velocity_by_mode.png"),
    ]:
        plt.figure(figsize=(8, 5))
        for scale in scales:
            sub = [row for row in candidates if math.isclose(float(row["sequence_scale"]), scale)]
            sub.sort(key=lambda row: int(float(row["candidate_n_modes"])))
            y = [float(row[metric]) * (1000.0 if metric.endswith("error_m") else 1.0) for row in sub]
            plt.plot([int(float(row["candidate_n_modes"])) for row in sub], y, marker="o", label=f"scale={scale:.2f}")
        plt.xticks(mode_counts)
        plt.xlabel("SVD mode count")
        plt.ylabel(ylabel)
        plt.title(f"Stage1.1 {ylabel.lower()} by action-space dimension")
        plt.grid(True)
        plt.legend()
        plt.tight_layout()
        plt.savefig(resolved.paths.validation_dir / filename, dpi=180)
        plt.close()


def run_stage1_1_analysis(resolved: base.ResolvedStage1Config) -> dict[str, Any]:
    analysis = base.run_analysis(resolved)
    robustness = bootstrap_mode_robustness(resolved)
    analysis["mode_bootstrap_robustness"] = robustness
    base.atomic_write_json(resolved.paths.analysis_dir / "analysis_summary.json", analysis)
    return analysis


def run_stage1_1_validation(
    resolved: base.ResolvedStage1Config,
    *,
    backend: str,
    resume: bool,
) -> dict[str, Any]:
    rescore_source_reference(resolved)
    verdict = base.run_validation(resolved, backend=backend, resume=resume)
    generate_stage1_1_plots(resolved)
    report = resolved.paths.run_dir / "STAGE1_REPORT.md"
    if report.exists():
        shutil.copy2(report, resolved.paths.run_dir / "STAGE1_1_REPORT.md")
    return verdict


def synthetic_stage1_1_test() -> dict[str, Any]:
    cfg = {
        "target": {"R": 0.75, "Z": 0.0, "Ip": 30000.0},
        "analysis": {"r_scale_m": 0.08, "z_scale_m": 0.08},
        "validation": {
            "late_window_steps": 4,
            "gate_ip_tolerance_a": 10000.0,
            "tolerance_boxes_m": [0.02, 0.03, 0.04, 0.08],
        },
    }
    env_cfg = {
        "dt_ms": 10,
        "min_current_a_display_order": [-100.0] * 14,
        "max_current_a_display_order": [100.0] * 14,
    }
    trajectory = []
    for step in range(11):
        # Step 0 is inside 20 mm, then leaves, then returns to a damped 30 mm hold.
        if step == 0:
            r_error, z_error = -0.005, 0.010
        elif step < 8:
            r_error, z_error = -0.040, 0.040
        else:
            r_error, z_error = -0.025, 0.025
        trajectory.append({
            "R": 0.75 + r_error,
            "Z": z_error,
            "Ip": 30000.0,
            "currents_a_display": [0.0] * 14,
        })
    result = {
        "experiment_id": "synthetic",
        "spec": {"candidate_label": "svd03_target1p00", "candidate_n_modes": 3, "sequence_scale": 0.85},
        "success": True,
        "trajectory": trajectory,
    }
    metrics = base.validation_metrics(result, cfg, env_cfg)
    assert metrics["first_step_after_step0_within_20mm"] == -1
    assert metrics["trailing_streak_within_30mm_steps"] == 3
    assert metrics["terminal_within_30mm"]
    return {
        "step0_exclusion_ok": True,
        "trailing_streak_ok": True,
        "terminal_error_mm": metrics["terminal_RZ_euclidean_error_m"] * 1000.0,
    }
