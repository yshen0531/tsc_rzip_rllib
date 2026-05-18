#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path
from typing import Any

PROJECT_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = Path(__file__).resolve().parent
for p in (PROJECT_DIR, SCRIPTS_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

# CPU-cluster safety defaults.  Set before importing Ray/Torch-heavy code.
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")
os.environ.setdefault("TORCH_NUM_THREADS", "1")
os.environ.setdefault("VECLIB_MAXIMUM_THREADS", "1")
os.environ.setdefault("BLIS_NUM_THREADS", "1")
os.environ.setdefault("RAYON_NUM_THREADS", "1")
os.environ.setdefault("RAY_ACCEL_ENV_VAR_OVERRIDE_ON_ZERO", "0")

import numpy as np
import ray
import torch
from ray.rllib.core import Columns
from ray.tune.registry import register_env

from tsc_rzip_rllib.envs.rllib_env import RllibTscRzipEnv
from tsc_rzip_rllib.utils.config import deep_update, load_json
from train_rllib_sac import build_config, prepare_train_config, restore_algo


EVAL_KEYS = [
    "time_ms", "R", "Z", "Ip", "R_error", "Z_error", "Ip_error",
    "R_error_norm", "Z_error_norm", "Ip_error_norm", "velocity_norm",
    "vessel_current_total_a", "vessel_current_signed_sum_a", "vessel_current_abs_sum_a",
    "vessel_current_rms_a", "vessel_current_max_abs_a", "current_util_max",
    "episode_overshoot_count", "first_reach_step", "first_stable_hold_step",
    "hold_window_len", "hold_window_mean_abs_action", "hold_window_max_abs_R_error",
    "hold_window_max_abs_Z_error", "hold_window_max_abs_Ip_error",
    "hold_window_max_velocity_norm", "hold_window_max_current_util",
    "hold_window_max_vessel_total_abs_a", "hold_window_max_vessel_abs_sum_a",
    "tsc_failed", "hold_success", "quality_success", "is_success",
    "tracking_penalty", "pre_hold_tracking_boost_penalty", "deriv_penalty_base",
    "deriv_penalty_near", "overshoot_penalty", "error_growth_penalty",
    "vessel_penalty_raw", "hold_vessel_penalty", "action_penalty",
    "delta_action_penalty", "hold_weight", "fast_reach_bonus_now",
    "strict_reached_now", "reach_progress_bonus",
]


def load_merged_json(path: Path, override_path: Path | None = None) -> dict[str, Any]:
    cfg = load_json(path)
    if override_path is not None:
        cfg = deep_update(cfg, load_json(override_path))
    return cfg


def make_eval_rllib_config(rllib_cfg: dict[str, Any], *, ray_cpus: int, object_store_memory: int) -> dict[str, Any]:
    cfg = json.loads(json.dumps(rllib_cfg))
    cfg.setdefault("env", {})["backend"] = cfg.get("env", {}).get("backend", "native")
    cfg.setdefault("parallel", {}).update({
        "ray_num_cpus": ray_cpus,
        "object_store_memory": object_store_memory,
        "reserve_cpus": 1,
        "num_tsc_workers": 1,
        "num_envs_per_tsc_worker": 1,
        "num_cpus_per_tsc_worker": 1,
        "num_cpus_for_main_process": 1,
        "sample_timeout_s": 3600.0,
        "max_requests_in_flight_per_tsc_worker": 1,
        "rollout_fragment_length": "auto",
        "batch_mode": "truncate_episodes",
    })
    cfg.setdefault("learner", {}).update({
        "num_learners": 1,
        "num_cpus_per_learner": 1,
        "num_gpus_per_learner": 0,
    })
    return cfg


def build_algo_compat(config):
    if hasattr(config, "build_algo"):
        return config.build_algo()
    return config.build()


def _get_default_module(algo):
    module = None
    if hasattr(algo, "get_module"):
        for module_id in ("default_policy", "default_module", None):
            try:
                module = algo.get_module(module_id) if module_id is not None else algo.get_module()
                if module is not None:
                    break
            except Exception:
                pass
    if module is None and hasattr(algo, "module"):
        module = algo.module
    if module is None:
        raise RuntimeError("Could not get RLModule from Algorithm.")
    if hasattr(module, "eval"):
        module.eval()
    return module


def _tensor_to_numpy(x):
    if isinstance(x, torch.Tensor):
        return x.detach().cpu().numpy()
    return np.asarray(x)


def _extract_action_from_rlmodule_output(module, out):
    actions_key = getattr(Columns, "ACTIONS", "actions")
    dist_inputs_key = getattr(Columns, "ACTION_DIST_INPUTS", "action_dist_inputs")

    if isinstance(out, dict) and actions_key in out:
        return _tensor_to_numpy(out[actions_key])[0]

    if isinstance(out, dict) and dist_inputs_key in out:
        logits = out[dist_inputs_key]
        dist_cls = None
        if hasattr(module, "get_inference_action_dist_cls"):
            dist_cls = module.get_inference_action_dist_cls()
        elif hasattr(module, "action_dist_cls"):
            dist_cls = module.action_dist_cls
        if dist_cls is None:
            raise RuntimeError("RLModule returned distribution inputs, but no distribution class was found.")
        dist = dist_cls.from_logits(logits) if hasattr(dist_cls, "from_logits") else dist_cls(logits)
        if hasattr(dist, "to_deterministic"):
            dist = dist.to_deterministic()
        if hasattr(dist, "deterministic_sample"):
            action = dist.deterministic_sample()
        else:
            action = dist.sample()
        return _tensor_to_numpy(action)[0]

    raise RuntimeError(
        "Could not extract action from RLModule.forward_inference output. "
        f"type={type(out)}, keys={list(out.keys()) if isinstance(out, dict) else None}"
    )


def compute_action_compat(algo, obs: np.ndarray) -> np.ndarray:
    module = _get_default_module(algo)
    obs = np.asarray(obs, dtype=np.float32).reshape(-1)
    obs_t = torch.as_tensor(obs[None, :], dtype=torch.float32)
    with torch.no_grad():
        out = module.forward_inference({"obs": obs_t})
    action = _extract_action_from_rlmodule_output(module, out)
    action = np.asarray(action, dtype=np.float32).reshape(-1)
    action = np.nan_to_num(action, nan=0.0, posinf=1.0, neginf=-1.0)
    return np.clip(action, -1.0, 1.0)


def as_scalar(v: Any) -> Any:
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        return float(v)
    if isinstance(v, (np.bool_,)):
        return bool(v)
    if isinstance(v, (int, float, str, bool)) or v is None:
        return v
    return ""


def safe_float(v: Any, default: float = float("nan")) -> float:
    try:
        return float(v)
    except Exception:
        return default


def summarize_episode(ep: int, ep_ret: float, ep_len: int, rows: list[dict[str, Any]], last_info: dict[str, Any]) -> dict[str, Any]:
    def vals(key: str) -> list[float]:
        out = []
        for r in rows:
            x = safe_float(r.get(key), float("nan"))
            if np.isfinite(x):
                out.append(x)
        return out

    def max_abs(key: str) -> float | None:
        xs = vals(key)
        return float(max(abs(x) for x in xs)) if xs else None

    def max_val(key: str) -> float | None:
        xs = vals(key)
        return float(max(xs)) if xs else None

    def mean_abs(key: str) -> float | None:
        xs = vals(key)
        return float(np.mean(np.abs(xs))) if xs else None

    return {
        "episode": int(ep),
        "episode_return": float(ep_ret),
        "episode_len": int(ep_len),
        "terminated": bool(last_info.get("terminated", False)),
        "truncated": bool(last_info.get("truncated", False)),
        "hold_success": bool(last_info.get("hold_success", False)),
        "quality_success": bool(last_info.get("quality_success", False)),
        "is_success": bool(last_info.get("is_success", False)),
        "time_to_first_reach_step": int(last_info.get("time_to_first_reach_step", last_info.get("first_reach_step", -1)) or -1),
        "time_to_stable_hold_step": int(last_info.get("time_to_stable_hold_step", last_info.get("first_stable_hold_step", -1)) or -1),
        "terminal_R_error": safe_float(last_info.get("terminal_R_error", last_info.get("R_error", 0.0))),
        "terminal_Z_error": safe_float(last_info.get("terminal_Z_error", last_info.get("Z_error", 0.0))),
        "terminal_Ip_error": safe_float(last_info.get("terminal_Ip_error", last_info.get("Ip_error", 0.0))),
        "terminal_R_abs_error": safe_float(last_info.get("terminal_R_abs_error", abs(safe_float(last_info.get("R_error", 0.0))))),
        "terminal_Z_abs_error": safe_float(last_info.get("terminal_Z_abs_error", abs(safe_float(last_info.get("Z_error", 0.0))))),
        "terminal_Ip_abs_error": safe_float(last_info.get("terminal_Ip_abs_error", abs(safe_float(last_info.get("Ip_error", 0.0))))),
        "terminal_velocity_norm": safe_float(last_info.get("terminal_velocity_norm", last_info.get("velocity_norm", 0.0))),
        "max_abs_R_error": max_abs("R_error"),
        "max_abs_Z_error": max_abs("Z_error"),
        "max_abs_Ip_error": max_abs("Ip_error"),
        "max_velocity_norm": max_val("velocity_norm"),
        "mean_abs_action": mean_abs("action_mean_abs"),
        "max_abs_action": max_val("action_max_abs"),
        "max_current_util": max_val("current_util_max"),
        "terminal_vessel_current_total_a": safe_float(last_info.get("terminal_vessel_current_total_a", last_info.get("vessel_current_total_a", 0.0))),
        "terminal_vessel_current_abs_sum_a": safe_float(last_info.get("terminal_vessel_current_abs_sum_a", last_info.get("vessel_current_abs_sum_a", 0.0))),
        "max_vessel_current_abs_sum_a": max_val("vessel_current_abs_sum_a"),
        "max_vessel_current_total_abs_a": max(abs(x) for x in vals("vessel_current_total_a")) if vals("vessel_current_total_a") else None,
        "hold_window_max_abs_R_error": safe_float(last_info.get("hold_window_max_abs_R_error")),
        "hold_window_max_abs_Z_error": safe_float(last_info.get("hold_window_max_abs_Z_error")),
        "hold_window_max_abs_Ip_error": safe_float(last_info.get("hold_window_max_abs_Ip_error")),
        "hold_window_max_velocity_norm": safe_float(last_info.get("hold_window_max_velocity_norm")),
        "hold_window_mean_abs_action": safe_float(last_info.get("hold_window_mean_abs_action")),
        "hold_window_max_vessel_abs_sum_a": safe_float(last_info.get("hold_window_max_vessel_abs_sum_a")),
        "episode_overshoot_count": int(safe_float(last_info.get("episode_overshoot_count", 0), 0)),
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--config", default="configs/rllib_sac.json")
    p.add_argument("--override", default=None)
    p.add_argument("--checkpoint", required=True)
    p.add_argument("--episodes", type=int, default=3)
    p.add_argument("--out", default="eval_rollout.csv")
    p.add_argument("--backend", default=None, choices=["native", "mock"])
    p.add_argument("--seed", type=int, default=12345)
    p.add_argument("--ray-cpus", type=int, default=4)
    p.add_argument("--object-store-memory", type=int, default=536870912)
    p.add_argument("--max-steps", type=int, default=None)
    args = p.parse_args()

    cfg_path = Path(args.config)
    if not cfg_path.is_absolute():
        cfg_path = PROJECT_DIR / cfg_path
    override_path = Path(args.override) if args.override else None
    if override_path and not override_path.is_absolute():
        override_path = PROJECT_DIR / override_path

    rllib_cfg_raw = load_merged_json(cfg_path, override_path)
    if args.backend:
        rllib_cfg_raw.setdefault("env", {})["backend"] = args.backend
    rllib_cfg = make_eval_rllib_config(rllib_cfg_raw, ray_cpus=args.ray_cpus, object_store_memory=args.object_store_memory)

    eval_dir = PROJECT_DIR / "eval_runs" / (Path(args.out).stem + "_resolved")
    eval_dir.mkdir(parents=True, exist_ok=True)
    train_cfg = prepare_train_config(project_dir=PROJECT_DIR, run_dir=eval_dir, rllib_cfg=rllib_cfg, train_override=None)

    ray_tmpdir = os.environ.get("RAY_TMPDIR", f"/tmp/ry_eval_{os.environ.get('USER','user')}")
    tmpdir = os.environ.get("TMPDIR", str(Path(ray_tmpdir) / "tmp"))
    os.environ["TMPDIR"] = tmpdir
    Path(ray_tmpdir).mkdir(parents=True, exist_ok=True)
    Path(tmpdir).mkdir(parents=True, exist_ok=True)

    print("========== Eval Ray init ==========")
    print(f"RAY_TMPDIR             = {ray_tmpdir}")
    print(f"TMPDIR                 = {tmpdir}")
    print(f"ray_cpus               = {args.ray_cpus}")
    print(f"object_store_memory    = {args.object_store_memory}")
    print("local_mode             = disabled; Ray no longer supports ray.init(local_mode=True)")
    print("===================================")

    register_env("RllibTscRzipEnv-v0", lambda env_config: RllibTscRzipEnv(env_config))
    ray.init(
        include_dashboard=False,
        ignore_reinit_error=True,
        _temp_dir=str(Path(ray_tmpdir).resolve()),
        num_cpus=args.ray_cpus,
        object_store_memory=args.object_store_memory,
    )

    algo = None
    env = None
    try:
        config, resolved = build_config(rllib_cfg, train_cfg, "eval")
        print("========== Eval RLlib config ==========")
        print(json.dumps(resolved, indent=2))
        print("=======================================")
        algo = build_algo_compat(config)
        checkpoint = Path(args.checkpoint)
        if not checkpoint.is_absolute():
            checkpoint = PROJECT_DIR / checkpoint
        print(f"Restoring checkpoint: {checkpoint}")
        restore_algo(algo, str(checkpoint))

        env = RllibTscRzipEnv({
            "backend": rllib_cfg.get("env", {}).get("backend", "native"),
            "train_config": train_cfg,
            "seed": args.seed,
            "run_id": "eval_rollout",
            "worker_id": f"eval_worker_pid{os.getpid()}",
        })

        all_rows: list[dict[str, Any]] = []
        summaries: list[dict[str, Any]] = []
        max_steps = args.max_steps or int(getattr(env.env, "max_episode_steps", 100000))

        for ep in range(args.episodes):
            obs, info = env.reset(seed=args.seed + ep)
            ep_ret = 0.0
            ep_rows: list[dict[str, Any]] = []
            last_info = dict(info or {})
            terminated = truncated = False
            step = 0
            while not (terminated or truncated) and step < max_steps:
                action = compute_action_compat(algo, obs)
                obs, reward, terminated, truncated, info = env.step(action)
                ep_ret += float(reward)
                info = dict(info or {})
                row = {
                    "episode": ep,
                    "step": step,
                    "reward": float(reward),
                    "episode_return_so_far": float(ep_ret),
                    "terminated": bool(terminated),
                    "truncated": bool(truncated),
                    "action_mean_abs": float(np.mean(np.abs(action))),
                    "action_max_abs": float(np.max(np.abs(action))),
                }
                for i, a in enumerate(action):
                    row[f"action_{i:02d}"] = float(a)
                for k in EVAL_KEYS:
                    row[k] = as_scalar(info.get(k, ""))
                ep_rows.append(row)
                all_rows.append(row)
                last_info = info
                step += 1
            last_info["terminated"] = bool(terminated)
            last_info["truncated"] = bool(truncated or step >= max_steps)
            summary = summarize_episode(ep, ep_ret, step, ep_rows, last_info)
            summaries.append(summary)
            print(
                f"[eval episode {ep}] return={ep_ret:.6g} len={step} "
                f"hold_success={summary['hold_success']} "
                f"first_reach={summary['time_to_first_reach_step']} "
                f"stable_hold={summary['time_to_stable_hold_step']}"
            )

        out = Path(args.out)
        if not out.is_absolute():
            out = PROJECT_DIR / out
        out.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = list(all_rows[0].keys()) if all_rows else ["episode", "step"]
        with out.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_rows)

        aggregate = {
            "checkpoint": str(Path(args.checkpoint)),
            "episodes": summaries,
            "mean_return": float(np.mean([s["episode_return"] for s in summaries])) if summaries else None,
            "mean_len": float(np.mean([s["episode_len"] for s in summaries])) if summaries else None,
            "hold_success_rate": float(np.mean([s["hold_success"] for s in summaries])) if summaries else None,
            "quality_success_rate": float(np.mean([s["quality_success"] for s in summaries])) if summaries else None,
            "mean_time_to_first_reach_step": float(np.mean([s["time_to_first_reach_step"] for s in summaries if s["time_to_first_reach_step"] >= 0])) if any(s["time_to_first_reach_step"] >= 0 for s in summaries) else None,
            "mean_time_to_stable_hold_step": float(np.mean([s["time_to_stable_hold_step"] for s in summaries if s["time_to_stable_hold_step"] >= 0])) if any(s["time_to_stable_hold_step"] >= 0 for s in summaries) else None,
            "out_csv": str(out),
        }
        summary_out = out.with_suffix(".summary.json")
        summary_out.write_text(json.dumps(aggregate, indent=2, ensure_ascii=False, allow_nan=True), encoding="utf-8")
        print(f"Saved rollout CSV: {out}")
        print(f"Saved summary:     {summary_out}")
    finally:
        if env is not None:
            env.close()
        if algo is not None:
            algo.stop()
        ray.shutdown()


if __name__ == "__main__":
    main()
