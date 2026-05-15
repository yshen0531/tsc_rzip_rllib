#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

import numpy as np
import ray
from ray.tune.registry import register_env
from ray.rllib.algorithms.sac import SACConfig

from tsc_rzip_rllib.envs.rllib_env import RllibTscRzipEnv
from tsc_rzip_rllib.utils.config import load_json
from scripts.train_rllib_sac import prepare_train_config, build_config, restore_algo


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--config", default="configs/rllib_sac.json")
    p.add_argument("--checkpoint", required=True)
    p.add_argument("--episodes", type=int, default=3)
    p.add_argument("--out", default="eval_rollout.csv")
    p.add_argument("--backend", default=None, choices=[None, "native", "mock"])
    args = p.parse_args()

    project_dir = PROJECT_DIR
    cfg_path = Path(args.config)
    if not cfg_path.is_absolute():
        cfg_path = project_dir / cfg_path
    rllib_cfg = load_json(cfg_path)
    if args.backend:
        rllib_cfg.setdefault("env", {})["backend"] = args.backend

    eval_dir = project_dir / "eval_runs"
    eval_dir.mkdir(parents=True, exist_ok=True)
    train_cfg = prepare_train_config(project_dir=project_dir, run_dir=eval_dir, rllib_cfg=rllib_cfg, train_override=None)

    register_env("RllibTscRzipEnv-v0", lambda env_config: RllibTscRzipEnv(env_config))
    ray.init(local_mode=True, include_dashboard=False, ignore_reinit_error=True)
    config, _ = build_config(rllib_cfg, train_cfg, "eval")
    algo = config.build()
    restore_algo(algo, args.checkpoint)

    env = RllibTscRzipEnv({"backend": rllib_cfg.get("env", {}).get("backend", "native"), "train_config": train_cfg, "seed": 12345})
    rows = []
    for ep in range(args.episodes):
        obs, info = env.reset(seed=12345 + ep)
        done = False
        step = 0
        ep_ret = 0.0
        while not done:
            try:
                action = algo.compute_single_action(obs, explore=False)
            except TypeError:
                action = algo.compute_single_action(obs)
            if isinstance(action, tuple):
                action = action[0]
            obs, reward, terminated, truncated, info = env.step(np.asarray(action, dtype=np.float32))
            done = bool(terminated or truncated)
            ep_ret += float(reward)
            row = {"episode": ep, "step": step, "reward": float(reward), "episode_return_so_far": ep_ret}
            for k in ["time_ms", "R", "Z", "Ip", "R_error", "Z_error", "Ip_error", "tsc_failed", "hold_success", "quality_success", "is_success"]:
                row[k] = info.get(k, "")
            rows.append(row)
            step += 1

    out = Path(args.out)
    if not out.is_absolute():
        out = project_dir / out
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["episode", "step"])
        writer.writeheader()
        writer.writerows(rows)
    env.close()
    algo.stop()
    ray.shutdown()
    print(f"Wrote: {out}")


if __name__ == "__main__":
    main()
