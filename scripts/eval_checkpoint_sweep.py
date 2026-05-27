#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shlex
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

PROJECT_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

THREAD_ENV = {
    "OMP_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1",
    "OPENBLAS_NUM_THREADS": "1",
    "NUMEXPR_NUM_THREADS": "1",
    "TORCH_NUM_THREADS": "1",
    "TORCH_NUM_INTEROP_THREADS": "1",
    "VECLIB_MAXIMUM_THREADS": "1",
    "BLIS_NUM_THREADS": "1",
    "RAYON_NUM_THREADS": "1",
    "RAY_ACCEL_ENV_VAR_OVERRIDE_ON_ZERO": "0",
}

RESOURCE_ERROR_PATTERNS = (
    "Resource temporarily unavailable",
    "BlockingIOError",
    "_fork_exec",
    "start_gcs_server",
    "validate_socket_filename failed",
    "AF_UNIX path length",
)


@dataclass(frozen=True)
class EvalJob:
    job_index: int
    checkpoint: str
    checkpoint_label: str
    checkpoint_iter: int
    stage: str
    action_mode: str
    episodes: int
    out_csv: str
    log_file: str
    ray_tmpdir: str
    ray_cpus: int
    object_store_memory: int
    seed: int


def parse_csv_list(text: str | None) -> list[str]:
    if text is None:
        return []
    return [x.strip() for x in str(text).split(",") if x.strip()]


def slugify(text: str, max_len: int = 140) -> str:
    s = re.sub(r"[^A-Za-z0-9_.=-]+", "_", str(text)).strip("_")
    return s[:max_len] if len(s) > max_len else s


def short_ray_tmpdir(ray_tmp_root: Path, sweep_id: str, job_index: int) -> str:
    # Ray creates sockets under <_temp_dir>/session_.../sockets/plasma_store.
    # Linux AF_UNIX socket paths are short, so keep <_temp_dir> extremely short.
    return str(ray_tmp_root / sweep_id / f"j{job_index:04d}")


def checkpoint_iter_from_name(path: Path) -> int:
    name = path.name
    if name == "final":
        return 10**12
    m = re.search(r"iter[_-]?(\d+)", name)
    if m:
        return int(m.group(1))
    return -1


def is_checkpoint_dir(path: Path) -> bool:
    if not path.is_dir():
        return False
    return any((path / name).exists() for name in ("rllib_checkpoint.json", "algorithm_state.pkl", "metadata.json"))


def find_latest_checkpoint_root(project_dir: Path, prefix: str) -> Path:
    roots = sorted((project_dir / "ray_checkpoints").glob(prefix), key=lambda p: p.stat().st_mtime)
    if not roots:
        raise FileNotFoundError(f"No checkpoint roots matched: {project_dir / 'ray_checkpoints' / prefix}")
    return roots[-1]


def find_checkpoints(root: Path, *, stride: int, include_final: bool, max_checkpoints: int | None, explicit: list[str]) -> list[Path]:
    if explicit:
        out = []
        for item in explicit:
            p = Path(item)
            if not p.is_absolute():
                p = root / item
            if not is_checkpoint_dir(p):
                raise FileNotFoundError(f"Not a checkpoint dir: {p}")
            out.append(p)
        return out

    candidates = [p for p in root.iterdir() if is_checkpoint_dir(p)]
    iter_ckpts: list[Path] = []
    final_ckpt: Path | None = None
    for p in candidates:
        if p.name == "final":
            final_ckpt = p
        elif checkpoint_iter_from_name(p) >= 0:
            it = checkpoint_iter_from_name(p)
            if stride <= 1 or it % stride == 0:
                iter_ckpts.append(p)

    iter_ckpts.sort(key=checkpoint_iter_from_name)
    if max_checkpoints is not None and max_checkpoints > 0 and len(iter_ckpts) > max_checkpoints:
        if max_checkpoints == 1:
            iter_ckpts = [iter_ckpts[-1]]
        else:
            idxs = [round(i * (len(iter_ckpts) - 1) / (max_checkpoints - 1)) for i in range(max_checkpoints)]
            iter_ckpts = [iter_ckpts[i] for i in sorted(set(idxs))]

    if include_final and final_ckpt is not None:
        iter_ckpts.append(final_ckpt)
    return iter_ckpts


def load_summary(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def mean_episode_value(summary: dict[str, Any], key: str) -> Any:
    episodes = summary.get("episodes") or []
    vals = []
    for ep in episodes:
        v = ep.get(key)
        if isinstance(v, (int, float)) and v == v:
            vals.append(float(v))
    if not vals:
        return None
    return sum(vals) / len(vals)


def log_has_resource_error(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        txt = path.read_text(encoding="utf-8", errors="ignore")[-20000:]
    except Exception:
        return False
    return any(pat in txt for pat in RESOURCE_ERROR_PATTERNS)


def flatten_summary(job: EvalJob, *, returncode: int, elapsed_s: float, summary_path: Path | None, error: str = "", attempts: int = 1) -> dict[str, Any]:
    row: dict[str, Any] = {
        "checkpoint_label": job.checkpoint_label,
        "checkpoint_iter": job.checkpoint_iter,
        "checkpoint": job.checkpoint,
        "stage": job.stage,
        "action_mode": job.action_mode,
        "episodes_requested": job.episodes,
        "returncode": returncode,
        "attempts": attempts,
        "elapsed_s": round(float(elapsed_s), 3),
        "out_csv": job.out_csv,
        "summary_json": str(summary_path) if summary_path else "",
        "log_file": job.log_file,
        "error": error,
    }
    if summary_path and summary_path.exists():
        try:
            s = load_summary(summary_path)
            row.update({
                "mean_return": s.get("mean_return"),
                "mean_len": s.get("mean_len"),
                "hold_success_rate": s.get("hold_success_rate"),
                "quality_success_rate": s.get("quality_success_rate"),
                "mean_time_to_first_reach_step": s.get("mean_time_to_first_reach_step"),
                "mean_time_to_stable_hold_step": s.get("mean_time_to_stable_hold_step"),
                "mean_terminal_R_error": mean_episode_value(s, "terminal_R_error"),
                "mean_terminal_Z_error": mean_episode_value(s, "terminal_Z_error"),
                "mean_terminal_Ip_error": mean_episode_value(s, "terminal_Ip_error"),
                "mean_terminal_velocity_norm": mean_episode_value(s, "terminal_velocity_norm"),
                "mean_mean_abs_action": mean_episode_value(s, "mean_abs_action"),
                "mean_max_abs_action": mean_episode_value(s, "max_abs_action"),
                "mean_hold_window_mean_abs_action": mean_episode_value(s, "hold_window_mean_abs_action"),
                "mean_terminal_vessel_abs_sum_a": mean_episode_value(s, "terminal_vessel_current_abs_sum_a"),
                "mean_max_vessel_abs_sum_a": mean_episode_value(s, "max_vessel_current_abs_sum_a"),
            })
        except Exception as e:
            row["error"] = (row.get("error") or "") + f" summary_parse_error={e}"
    return row


def run_job(
    job: EvalJob,
    *,
    python_bin: str,
    config: str,
    override: str | None,
    backend: str | None,
    max_steps: int | None,
    max_retries: int,
    retry_sleep_sec: float,
    retry_backoff: float,
) -> dict[str, Any]:
    out_csv = Path(job.out_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    log_file = Path(job.log_file)
    log_file.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        python_bin,
        str(PROJECT_DIR / "scripts" / "eval_rllib_checkpoint.py"),
        "--config", config,
        "--checkpoint", job.checkpoint,
        "--episodes", str(job.episodes),
        "--out", job.out_csv,
        "--eval-stage", job.stage,
        "--action-mode", job.action_mode,
        "--seed", str(job.seed),
        "--ray-cpus", str(job.ray_cpus),
        "--object-store-memory", str(job.object_store_memory),
    ]
    if override:
        cmd.extend(["--override", override])
    if backend:
        cmd.extend(["--backend", backend])
    if max_steps is not None:
        cmd.extend(["--max-steps", str(max_steps)])

    env = os.environ.copy()
    env.update(THREAD_ENV)
    env["PYTHONPATH"] = f"{PROJECT_DIR}:{env.get('PYTHONPATH', '')}"
    env["RAY_TMPDIR"] = job.ray_tmpdir
    env["TMPDIR"] = str(Path(job.ray_tmpdir) / "tmp")
    Path(env["TMPDIR"]).mkdir(parents=True, exist_ok=True)

    start_all = time.time()
    last_returncode = 999
    last_error = ""
    attempts_done = 0

    # Append attempts to the same log.  A resource error is often transient during Ray/GCS startup storms.
    for attempt in range(1, max(1, int(max_retries)) + 2):
        attempts_done = attempt
        with log_file.open("a", encoding="utf-8") as lf:
            lf.write("\n" + "=" * 80 + "\n")
            lf.write(f"ATTEMPT {attempt}\n")
            lf.write("COMMAND: " + " ".join(shlex.quote(x) for x in cmd) + "\n")
            lf.write("RAY_TMPDIR=" + env["RAY_TMPDIR"] + "\n")
            lf.flush()
            proc = subprocess.run(cmd, stdout=lf, stderr=subprocess.STDOUT, env=env, cwd=str(PROJECT_DIR))
        last_returncode = proc.returncode
        summary_path = out_csv.with_suffix(".summary.json")
        if proc.returncode == 0 and summary_path.exists():
            elapsed = time.time() - start_all
            return flatten_summary(job, returncode=0, elapsed_s=elapsed, summary_path=summary_path, attempts=attempt)

        resource_like = log_has_resource_error(log_file)
        last_error = f"eval_subprocess_returncode={proc.returncode}"
        if resource_like:
            last_error += " resource_startup_error_detected"
        if attempt <= int(max_retries) and resource_like:
            sleep_s = float(retry_sleep_sec) * (float(retry_backoff) ** (attempt - 1))
            with log_file.open("a", encoding="utf-8") as lf:
                lf.write(f"\nRetrying after resource startup error; sleep {sleep_s:.1f} s\n")
            time.sleep(sleep_s)
            continue
        break

    elapsed = time.time() - start_all
    return flatten_summary(job, returncode=last_returncode, elapsed_s=elapsed, summary_path=out_csv.with_suffix(".summary.json"), error=last_error, attempts=attempts_done)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keys: list[str] = []
    for row in rows:
        for k in row.keys():
            if k not in keys:
                keys.append(k)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    p = argparse.ArgumentParser(description="Parallel checkpoint sweep for deterministic/stochastic RLlib checkpoint eval.")
    p.add_argument("--config", default="configs/rllib_sac.json")
    p.add_argument("--override", default=None)
    p.add_argument("--checkpoint-root", default=None, help="Root like ray_checkpoints/train_b83_...; default latest train_b83_*")
    p.add_argument("--checkpoint-root-prefix", default="train_b83_*", help="Used only when --checkpoint-root is omitted")
    p.add_argument("--checkpoints", default="", help="Comma-separated checkpoint dirs/names. If relative, resolved under checkpoint-root.")
    p.add_argument("--checkpoint-stride", type=int, default=25, help="Select iter_N checkpoints where N %% stride == 0")
    p.add_argument("--include-final", action="store_true", default=True)
    p.add_argument("--no-final", dest="include_final", action="store_false")
    p.add_argument("--max-checkpoints", type=int, default=0, help="Evenly subsample iter checkpoints; 0 means no limit")
    p.add_argument("--stages", default="final", help="Comma list: final,stage2,stage1,...")
    p.add_argument("--modes", default="deterministic,stochastic", help="Comma list: deterministic,stochastic")
    p.add_argument("--episodes", type=int, default=1, help="Default episodes per job")
    p.add_argument("--episodes-deterministic", type=int, default=None)
    p.add_argument("--episodes-stochastic", type=int, default=3)
    p.add_argument("--num-workers", type=int, default=8, help="Number of eval subprocesses in parallel")
    p.add_argument("--ray-cpus-per-job", type=int, default=2)
    p.add_argument("--object-store-memory", type=int, default=536870912)
    p.add_argument("--seed", type=int, default=12345)
    p.add_argument("--backend", default=None, choices=["native", "mock"])
    p.add_argument("--max-steps", type=int, default=None)
    p.add_argument("--out-dir", default=None)
    p.add_argument("--ray-tmp-root", default=None, help="Short root for per-job Ray temp dirs. Default: /tmp/rs<uid>")
    p.add_argument("--python", default=sys.executable)
    p.add_argument("--startup-stagger-sec", type=float, default=0.75, help="Delay between launching eval jobs to avoid Ray/GCS fork storms")
    p.add_argument("--max-retries", type=int, default=2, help="Retry eval jobs that fail during Ray/resource startup")
    p.add_argument("--retry-sleep-sec", type=float, default=20.0)
    p.add_argument("--retry-backoff", type=float, default=1.7)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    checkpoint_root = Path(args.checkpoint_root) if args.checkpoint_root else find_latest_checkpoint_root(PROJECT_DIR, args.checkpoint_root_prefix)
    if not checkpoint_root.is_absolute():
        checkpoint_root = PROJECT_DIR / checkpoint_root
    if not checkpoint_root.exists():
        raise FileNotFoundError(f"checkpoint-root does not exist: {checkpoint_root}")

    explicit = parse_csv_list(args.checkpoints)
    ckpts = find_checkpoints(
        checkpoint_root,
        stride=args.checkpoint_stride,
        include_final=args.include_final,
        max_checkpoints=(args.max_checkpoints or None),
        explicit=explicit,
    )
    if not ckpts:
        raise RuntimeError(f"No checkpoints selected under {checkpoint_root}")

    stages = parse_csv_list(args.stages)
    modes = parse_csv_list(args.modes)
    bad_modes = [m for m in modes if m not in {"deterministic", "stochastic"}]
    if bad_modes:
        raise ValueError(f"bad modes: {bad_modes}")

    stamp = time.strftime("%Y%m%d_%H%M%S")
    root_name = checkpoint_root.name
    out_dir = Path(args.out_dir) if args.out_dir else PROJECT_DIR / "eval_sweeps" / f"{root_name}_sweep_{stamp}"
    if not out_dir.is_absolute():
        out_dir = PROJECT_DIR / out_dir
    (out_dir / "logs").mkdir(parents=True, exist_ok=True)
    (out_dir / "csv").mkdir(parents=True, exist_ok=True)

    jobs: list[EvalJob] = []
    uid = os.getuid() if hasattr(os, "getuid") else 0
    ray_tmp_root = Path(args.ray_tmp_root) if args.ray_tmp_root else Path(f"/tmp/rs{uid}")
    sweep_id = "s" + stamp[-10:].replace("_", "")
    job_counter = 0
    for ckpt in ckpts:
        label = ckpt.name
        it = checkpoint_iter_from_name(ckpt)
        for stage in stages:
            for mode in modes:
                eps = args.episodes_stochastic if mode == "stochastic" else (args.episodes_deterministic or args.episodes)
                job_name = slugify(f"{label}_{stage}_{mode}")
                job_counter += 1
                jobs.append(EvalJob(
                    job_index=job_counter,
                    checkpoint=str(ckpt),
                    checkpoint_label=label,
                    checkpoint_iter=int(it),
                    stage=stage,
                    action_mode=mode,
                    episodes=int(eps),
                    out_csv=str(out_dir / "csv" / f"{job_name}.csv"),
                    log_file=str(out_dir / "logs" / f"{job_name}.log"),
                    ray_tmpdir=short_ray_tmpdir(ray_tmp_root, sweep_id, job_counter),
                    ray_cpus=int(args.ray_cpus_per_job),
                    object_store_memory=int(args.object_store_memory),
                    seed=int(args.seed),
                ))

    metadata = {
        "checkpoint_root": str(checkpoint_root),
        "num_checkpoints": len(ckpts),
        "checkpoints": [str(p) for p in ckpts],
        "stages": stages,
        "modes": modes,
        "num_jobs": len(jobs),
        "num_workers": int(args.num_workers),
        "out_dir": str(out_dir),
        "config": args.config,
        "override": args.override,
        "ray_tmp_root": str(ray_tmp_root),
        "sweep_id": sweep_id,
        "startup_stagger_sec": args.startup_stagger_sec,
        "max_retries": args.max_retries,
        "retry_sleep_sec": args.retry_sleep_sec,
        "retry_backoff": args.retry_backoff,
    }
    (out_dir / "sweep_metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    (out_dir / "jobs.json").write_text(json.dumps([asdict(j) for j in jobs], indent=2, ensure_ascii=False), encoding="utf-8")

    print("========== checkpoint sweep ==========")
    print(f"checkpoint_root = {checkpoint_root}")
    print(f"out_dir         = {out_dir}")
    print(f"checkpoints     = {len(ckpts)}")
    print(f"stages          = {stages}")
    print(f"modes           = {modes}")
    print(f"jobs            = {len(jobs)}")
    print(f"parallel jobs   = {args.num_workers}")
    print(f"ray_tmp_root    = {ray_tmp_root}")
    print(f"sweep_id        = {sweep_id}")
    print(f"stagger_sec     = {args.startup_stagger_sec}")
    print(f"max_retries     = {args.max_retries}")
    print("======================================")

    if args.dry_run:
        for j in jobs:
            print(json.dumps(asdict(j), ensure_ascii=False))
        return

    rows: list[dict[str, Any]] = []
    max_workers = max(1, int(args.num_workers))
    next_idx = 0
    done_count = 0
    active = {}

    def submit_one(ex: ThreadPoolExecutor) -> None:
        nonlocal next_idx
        job = jobs[next_idx]
        fut = ex.submit(
            run_job,
            job,
            python_bin=args.python,
            config=args.config,
            override=args.override,
            backend=args.backend,
            max_steps=args.max_steps,
            max_retries=args.max_retries,
            retry_sleep_sec=args.retry_sleep_sec,
            retry_backoff=args.retry_backoff,
        )
        active[fut] = job
        next_idx += 1

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        # Initial ramp-up: submit jobs gradually to avoid simultaneous ray.init/GCS fork storms.
        while next_idx < len(jobs) and len(active) < max_workers:
            submit_one(ex)
            if args.startup_stagger_sec > 0 and len(active) < max_workers and next_idx < len(jobs):
                time.sleep(float(args.startup_stagger_sec))

        while active:
            done, _pending = wait(active.keys(), return_when=FIRST_COMPLETED)
            for fut in done:
                job = active.pop(fut)
                done_count += 1
                try:
                    row = fut.result()
                except Exception as e:
                    row = flatten_summary(job, returncode=999, elapsed_s=0.0, summary_path=None, error=f"launcher_exception={e}")
                rows.append(row)
                status = "OK" if row.get("returncode") == 0 else "FAIL"
                print(
                    f"[{done_count:04d}/{len(jobs):04d}] {status} "
                    f"{job.checkpoint_label} stage={job.stage} mode={job.action_mode} "
                    f"return={row.get('mean_return')} mean_abs_action={row.get('mean_mean_abs_action')} "
                    f"hold={row.get('hold_success_rate')} attempts={row.get('attempts')} log={job.log_file}",
                    flush=True,
                )
                write_csv(out_dir / "sweep_results.partial.csv", rows)

                if next_idx < len(jobs):
                    submit_one(ex)
                    if args.startup_stagger_sec > 0:
                        time.sleep(float(args.startup_stagger_sec))

    rows.sort(key=lambda r: (int(r.get("checkpoint_iter", -1)), str(r.get("stage")), str(r.get("action_mode"))))
    write_csv(out_dir / "sweep_results.csv", rows)
    (out_dir / "sweep_results.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False, allow_nan=True), encoding="utf-8")

    print("\nSaved:")
    print(f"  {out_dir / 'sweep_results.csv'}")
    print(f"  {out_dir / 'sweep_results.json'}")
    print(f"  {out_dir / 'sweep_metadata.json'}")
    failed = [r for r in rows if r.get("returncode") != 0]
    if failed:
        print(f"WARNING: {len(failed)} jobs failed. Inspect logs under {out_dir / 'logs'}")
        sys.exit(2)


if __name__ == "__main__":
    main()
