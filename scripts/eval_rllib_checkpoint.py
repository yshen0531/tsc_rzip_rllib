#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any
import torch
from ray.rllib.core import Columns

# ---------------------------------------------------------------------------
# Make project importable when running:
#   python scripts/eval_rllib_checkpoint.py ...
# ---------------------------------------------------------------------------
PROJECT_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = Path(__file__).resolve().parent

if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

# ---------------------------------------------------------------------------
# CPU-cluster safety defaults.
# Must be set before importing Ray/Torch-heavy code.
# ---------------------------------------------------------------------------
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
import pandas as pd
import ray
from ray.tune.registry import register_env

from tsc_rzip_rllib.envs.rllib_env import RllibTscRzipEnv
from tsc_rzip_rllib.utils.config import deep_update, load_json

# Reuse the exact training config construction path so model/env spaces match.
from train_rllib_sac import (
    build_config,
    prepare_train_config,
    restore_algo,
)


def scalar_or_string(v: Any) -> bool:
    return isinstance(v, (int, float, str, bool, np.integer, np.floating, np.bool_))


def to_jsonable(v: Any) -> Any:
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        return float(v)
    if isinstance(v, (np.bool_,)):
        return bool(v)
    if isinstance(v, np.ndarray):
        return v.tolist()
    try:
        json.dumps(v)
        return v
    except Exception:
        return str(v)


def load_merged_json(path: Path, override_path: Path | None = None) -> dict[str, Any]:
    cfg = load_json(path)
    if override_path is not None:
        cfg = deep_update(cfg, load_json(override_path))
    return cfg


def build_algo_compat(config):
    """Ray 2.55 warns that build() is deprecated in favor of build_algo()."""
    if hasattr(config, "build_algo"):
        return config.build_algo()
    return config.build()


def _get_default_module(algo):
    """Return the default single-agent RLModule from a restored Algorithm."""
    module = None

    # Ray 2.55 new API stack: Algorithm.get_module(default_policy) is the
    # supported replacement path for old Policy access.
    if hasattr(algo, "get_module"):
        try:
            module = algo.get_module("default_policy")
        except Exception:
            module = None

    # Fallbacks for slightly different Ray builds.
    if module is None and hasattr(algo, "module"):
        module = algo.module

    if module is None:
        raise RuntimeError(
            "Could not get RLModule from Algorithm. "
            "This eval script expects RLlib new API stack with algo.get_module('default_policy')."
        )

    if hasattr(module, "eval"):
        module.eval()

    return module


def _tensor_to_numpy(x):
    if isinstance(x, torch.Tensor):
        return x.detach().cpu().numpy()
    return np.asarray(x)


def _extract_action_from_rlmodule_output(module, out):
    """Extract deterministic continuous action from RLModule forward_inference output.

    Different RLlib versions/modules may return either:
      - Columns.ACTIONS directly; or
      - Columns.ACTION_DIST_INPUTS, from which we construct the inference distribution.
    """
    actions_key = getattr(Columns, "ACTIONS", "actions")
    dist_inputs_key = getattr(Columns, "ACTION_DIST_INPUTS", "action_dist_inputs")

    # Most direct case: module already returns actions.
    if isinstance(out, dict) and actions_key in out:
        action = out[actions_key]
        action = _tensor_to_numpy(action)[0]
        return action

    # Some RLModules return action distribution parameters.
    if isinstance(out, dict) and dist_inputs_key in out:
        logits = out[dist_inputs_key]

        dist_cls = None
        if hasattr(module, "get_inference_action_dist_cls"):
            dist_cls = module.get_inference_action_dist_cls()
        elif hasattr(module, "action_dist_cls"):
            dist_cls = module.action_dist_cls

        if dist_cls is None:
            raise RuntimeError(
                "RLModule returned action distribution inputs, but no inference "
                "action distribution class was found."
            )

        # RLlib distribution classes commonly provide from_logits().
        if hasattr(dist_cls, "from_logits"):
            dist = dist_cls.from_logits(logits)
        else:
            dist = dist_cls(logits)

        # For deterministic evaluation, use deterministic version if available.
        if hasattr(dist, "to_deterministic"):
            dist = dist.to_deterministic()

        action = dist.sample()
        action = _tensor_to_numpy(action)[0]
        return action

    raise RuntimeError(
        "Could not extract action from RLModule.forward_inference output. "
        f"Output type={type(out)}, keys={list(out.keys()) if isinstance(out, dict) else None}"
    )


def compute_action_compat(algo, obs: np.ndarray):
    """Return a clipped deterministic action from a restored RLlib new-stack Algorithm."""
    module = _get_default_module(algo)

    obs = np.asarray(obs, dtype=np.float32)
    if obs.ndim != 1:
        obs = obs.reshape(-1)

    obs_t = torch.as_tensor(obs[None, :], dtype=torch.float32)

    with torch.no_grad():
        out = module.forward_inference({"obs": obs_t})

    action = _extract_action_from_rlmodule_output(module, out)

    action = np.asarray(action, dtype=np.float32).reshape(-1)
    action = np.nan_to_num(action, nan=0.0, posinf=1.0, neginf=-1.0)
    action = np.clip(action, -1.0, 1.0)
    return action


def make_eval_rllib_config(
    rllib_cfg: dict[str, Any],
    *,
    ray_cpus: int,
    object_store_memory: int,
) -> dict[str, Any]:
    """Shrink training config to a safe single-env evaluation config.

    We restore the same checkpointed model, but we do NOT need 96 EnvRunners
    during eval. One EnvRunner is enough to infer spaces and build the Algorithm.
    """
    cfg = json.loads(json.dumps(rllib_cfg))

    cfg.setdefault("env", {})
    cfg["env"]["backend"] = "native"
    cfg["env"]["disable_env_checking"] = False

    cfg.setdefault("parallel", {})
    cfg["parallel"].update(
        {
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
        }
    )

    cfg.setdefault("learner", {})
    cfg["learner"].update(
        {
            "num_learners": 1,
            "num_cpus_per_learner": 1,
            "num_gpus_per_learner": 0,
        }
    )

    return cfg


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/rllib_sac.json")
    parser.add_argument("--override", default=None)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--episodes", type=int, default=3)
    parser.add_argument("--out", default="eval_rollout.csv")
    parser.add_argument("--seed", type=int, default=12345)
    parser.add_argument("--ray-cpus", type=int, default=4)
    parser.add_argument("--object-store-memory", type=int, default=536870912)
    parser.add_argument("--max-steps", type=int, default=None)
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = PROJECT_DIR / config_path

    override_path = Path(args.override) if args.override else None
    if override_path is not None and not override_path.is_absolute():
        override_path = PROJECT_DIR / override_path

    checkpoint_path = Path(args.checkpoint)
    if not checkpoint_path.is_absolute():
        checkpoint_path = PROJECT_DIR / checkpoint_path

    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = PROJECT_DIR / out_path

    eval_root = PROJECT_DIR / "eval_results"
    eval_root.mkdir(parents=True, exist_ok=True)
    run_dir = eval_root / (out_path.stem + "_resolved")
    run_dir.mkdir(parents=True, exist_ok=True)

    rllib_cfg_raw = load_merged_json(config_path, override_path)
    rllib_cfg = make_eval_rllib_config(
        rllib_cfg_raw,
        ray_cpus=args.ray_cpus,
        object_store_memory=args.object_store_memory,
    )

    train_cfg = prepare_train_config(
        project_dir=PROJECT_DIR,
        run_dir=run_dir,
        rllib_cfg=rllib_cfg,
        train_override=None,
    )

    ray_tmpdir = os.environ.get("RAY_TMPDIR")
    if not ray_tmpdir:
        user = os.environ.get("USER", "user")
        ray_tmpdir = f"/tmp/ry_eval_{user}"

    tmpdir = os.environ.get("TMPDIR")
    if not tmpdir:
        tmpdir = os.path.join(ray_tmpdir, "tmp")
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

    # Ray local_mode is no longer supported in recent Ray, so use a tiny real
    # local Ray runtime instead. ray.init() starts/attaches to a local Ray instance
    # when no address is supplied.
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
        config, resolved = build_config(rllib_cfg, train_cfg, run_id="eval")
        print("========== Eval RLlib config ==========")
        print(json.dumps(resolved, indent=2))
        print("=======================================")

        algo = build_algo_compat(config)
        print(f"Restoring checkpoint: {checkpoint_path}")
        restore_algo(algo, str(checkpoint_path))

        env_config = {
            "backend": "native",
            "seed": int(args.seed),
            "train_config": train_cfg,
            "run_id": "eval_rollout",
            "worker_id": "eval_worker_pid%d" % os.getpid(),
        }
        env = RllibTscRzipEnv(env_config)

        rows: list[dict[str, Any]] = []
        episode_summaries: list[dict[str, Any]] = []

        for ep in range(int(args.episodes)):
            obs, info = env.reset(seed=args.seed + ep)
            obs = np.asarray(obs, dtype=np.float32)

            ep_return = 0.0
            ep_len = 0
            terminated = False
            truncated = False

            max_steps = args.max_steps
            if max_steps is None:
                max_steps = int(getattr(env.env, "max_episode_steps", 100000))

            while not (terminated or truncated) and ep_len < max_steps:
                action = compute_action_compat(algo, obs)
                next_obs, reward, terminated, truncated, step_info = env.step(action)
                next_obs = np.asarray(next_obs, dtype=np.float32)

                ep_return += float(reward)

                row: dict[str, Any] = {
                    "episode": ep,
                    "step": ep_len,
                    "reward": float(reward),
                    "episode_return_so_far": float(ep_return),
                    "terminated": bool(terminated),
                    "truncated": bool(truncated),
                }

                for i, x in enumerate(obs):
                    row[f"obs_{i:03d}"] = float(x)

                for i, a in enumerate(action):
                    row[f"action_{i:02d}"] = float(a)

                for k, v in dict(step_info or {}).items():
                    if scalar_or_string(v):
                        row[f"info/{k}"] = to_jsonable(v)

                rows.append(row)
                obs = next_obs
                ep_len += 1

            episode_summaries.append(
                {
                    "episode": ep,
                    "episode_return": float(ep_return),
                    "episode_len": int(ep_len),
                    "terminated": bool(terminated),
                    "truncated": bool(truncated),
                }
            )

            print(
                f"[eval episode {ep}] "
                f"return={ep_return:.6g} len={ep_len} "
                f"terminated={terminated} truncated={truncated}"
            )

        df = pd.DataFrame(rows)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(out_path, index=False)

        summary = {
            "checkpoint": str(checkpoint_path),
            "episodes": episode_summaries,
            "mean_return": float(np.mean([x["episode_return"] for x in episode_summaries]))
            if episode_summaries
            else None,
            "mean_len": float(np.mean([x["episode_len"] for x in episode_summaries]))
            if episode_summaries
            else None,
            "out_csv": str(out_path),
        }

        summary_path = out_path.with_suffix(".summary.json")
        summary_path.write_text(
            json.dumps(summary, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        print(f"Saved rollout CSV: {out_path}")
        print(f"Saved summary:     {summary_path}")

    finally:
        if env is not None:
            env.close()
        if algo is not None:
            algo.stop()
        ray.shutdown()


if __name__ == "__main__":
    main()