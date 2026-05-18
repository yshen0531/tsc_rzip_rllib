#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

# CPU-cluster safety defaults. Set before importing Ray/Torch-heavy modules.
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")
os.environ.setdefault("TORCH_NUM_THREADS", "1")
os.environ.setdefault("VECLIB_MAXIMUM_THREADS", "1")
os.environ.setdefault("BLIS_NUM_THREADS", "1")
os.environ.setdefault("RAYON_NUM_THREADS", "1")
os.environ.setdefault("RAY_ACCEL_ENV_VAR_OVERRIDE_ON_ZERO", "0")

import ray
from ray.tune.registry import register_env
from ray.rllib.algorithms.sac import SACConfig

try:
    from ray.rllib.core.rl_module.default_model_config import DefaultModelConfig
except Exception:  # pragma: no cover - for older Ray installs
    DefaultModelConfig = None

from tsc_rzip_rllib.envs.rllib_env import RllibTscRzipEnv
from tsc_rzip_rllib.utils.config import deep_update, load_json


def available_cpu_count() -> int:
    """Return CPUs available to this process.

    On cluster nodes with cpuset/cgroup/taskset constraints, sched_getaffinity(0)
    is usually more useful than os.cpu_count(), because it reports the cores that
    this job is actually allowed to use.
    """
    try:
        return max(1, len(os.sched_getaffinity(0)))
    except Exception:
        return max(1, os.cpu_count() or 1)


def resolve_count(spec: Any, *, total: int, reserve: int, default_frac: float = 0.75) -> int:
    """Resolve a user-facing parallelism spec into an integer worker count.

    Accepted forms:
      - null or "auto": use default_frac * (available CPUs - reserve)
      - "auto:0.70": use 70% of (available CPUs - reserve)
      - 0 < float < 1: use that fraction of (available CPUs - reserve)
      - integer >= 1: use exactly that many workers, capped only by Ray resources
    """
    usable = max(1, int(total) - int(reserve))

    if spec is None or str(spec).strip().lower() == "auto":
        return max(1, int(usable * default_frac))

    if isinstance(spec, str):
        text = spec.strip().lower()
        if text.startswith("auto:"):
            return max(1, int(usable * float(text.split(":", 1)[1])))
        val = float(text)
    else:
        val = float(spec)

    if 0.0 < val < 1.0:
        return max(1, int(usable * val))

    return max(1, int(val))


def recursive_find(obj: Any, key: str) -> Any:
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for v in obj.values():
            out = recursive_find(v, key)
            if out is not None:
                return out
    elif isinstance(obj, list):
        for v in obj:
            out = recursive_find(v, key)
            if out is not None:
                return out
    return None


def json_safe(obj: Any) -> Any:
    try:
        json.dumps(obj)
        return obj
    except Exception:
        if isinstance(obj, dict):
            return {str(k): json_safe(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [json_safe(v) for v in obj]
        return str(obj)


def expand_macros(obj: Any, macros: dict[str, str]) -> Any:
    if isinstance(obj, str):
        out = os.path.expandvars(obj)
        for k, v in macros.items():
            out = out.replace("{" + k + "}", str(v))
        return out
    if isinstance(obj, list):
        return [expand_macros(x, macros) for x in obj]
    if isinstance(obj, dict):
        return {k: expand_macros(v, macros) for k, v in obj.items()}
    return obj


def load_merged_json(path: Path, override_path: Path | None = None) -> dict[str, Any]:
    cfg = load_json(path)
    if override_path is not None:
        cfg = deep_update(cfg, load_json(override_path))
    return cfg


def parallel_cfg_from(rllib_cfg: dict[str, Any]) -> dict[str, Any]:
    """Return the new parallel config, with legacy ray-key fallback.

    New configs should use the top-level "parallel" section. The fallback keeps
    old override files from failing immediately, but new cluster_*.json files are
    no longer needed.
    """
    if "parallel" in rllib_cfg:
        return dict(rllib_cfg.get("parallel", {}))

    # Backward compatibility for older configs that still have "ray".
    old = dict(rllib_cfg.get("ray", {}))
    return {
        "ray_address": old.get("address"),
        "ray_num_cpus": old.get("num_cpus"),
        "local_mode": old.get("local_mode", False),
        "include_dashboard": old.get("include_dashboard", False),
        "num_tsc_workers": old.get("num_env_runners", "auto:0.75"),
        "reserve_cpus": old.get("reserve_cpus", 4),
        "num_cpus_per_tsc_worker": old.get("num_cpus_per_env_runner", 1),
        "num_envs_per_tsc_worker": old.get("num_envs_per_env_runner", 1),
        "num_cpus_for_main_process": old.get("num_cpus_for_main_process", 1),
        "sample_timeout_s": old.get("sample_timeout_s", 300.0),
        "max_requests_in_flight_per_tsc_worker": old.get("max_requests_in_flight_per_env_runner", 1),
        "rollout_fragment_length": old.get("rollout_fragment_length", "auto"),
        "batch_mode": old.get("batch_mode", "truncate_episodes"),
    }


def prepare_train_config(
    *,
    project_dir: Path,
    run_dir: Path,
    rllib_cfg: dict[str, Any],
    train_override: Path | None,
) -> dict[str, Any]:
    train_cfg_path = Path(rllib_cfg["train_config"])
    if not train_cfg_path.is_absolute():
        train_cfg_path = project_dir / train_cfg_path
    train_cfg = load_merged_json(train_cfg_path, train_override)

    tsc_all_root = os.environ.get("TSC_ALL_ROOT", str(project_dir.parent))
    macros = {
        "PROJECT_DIR": str(project_dir),
        "TSC_ALL_ROOT": str(tsc_all_root),
    }

    train_cfg = expand_macros(train_cfg, macros)

    env_config_path = Path(train_cfg["env_config"])
    if not env_config_path.is_absolute():
        env_config_path = project_dir / env_config_path

    tsc_cfg = load_json(env_config_path)
    tsc_cfg = expand_macros(tsc_cfg, macros)

    runtime_cfg_dir = run_dir / "resolved_configs"
    runtime_cfg_dir.mkdir(parents=True, exist_ok=True)
    runtime_tsc_cfg_path = runtime_cfg_dir / "tsc_low_field_side_118.resolved.json"
    runtime_tsc_cfg_path.write_text(
        json.dumps(tsc_cfg, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    train_cfg["env_config"] = str(runtime_tsc_cfg_path)
    runtime_train_cfg_path = runtime_cfg_dir / "train_config.resolved.json"
    runtime_train_cfg_path.write_text(
        json.dumps(train_cfg, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return train_cfg


def build_config(rllib_cfg: dict[str, Any], train_cfg: dict[str, Any], run_id: str):
    pcfg = parallel_cfg_from(rllib_cfg)
    sac_cfg = rllib_cfg.get("sac", {})
    model_cfg = rllib_cfg.get("model", {})
    env_cfg = rllib_cfg.get("env", {})
    report_cfg = rllib_cfg.get("reporting", {})

    total_cpus = available_cpu_count()
    reserve_cpus = int(pcfg.get("reserve_cpus", 4))
    num_tsc_workers = resolve_count(
        pcfg.get("num_tsc_workers", "auto:0.75"),
        total=total_cpus,
        reserve=reserve_cpus,
        default_frac=0.75,
    )

    num_envs_per_tsc_worker = int(pcfg.get("num_envs_per_tsc_worker", 1))
    if num_envs_per_tsc_worker != 1:
        print(
            "WARNING: num_envs_per_tsc_worker != 1. "
            "For TSC, this can reintroduce vector-env waiting inside a worker. "
            "Recommended value is 1."
        )

    env_config = {
        "backend": env_cfg.get("backend", "native"),
        "seed": int(rllib_cfg.get("seed", 42)),
        "train_config": train_cfg,
        "mock_config": env_cfg.get("mock_config", {}),
        "run_id": run_id,
    }

    config = (
        SACConfig()
        .api_stack(
            enable_rl_module_and_learner=True,
            enable_env_runner_and_connector_v2=True,
        )
        .framework("torch")
        .environment(
            env="RllibTscRzipEnv-v0",
            env_config=env_config,
            disable_env_checking=bool(env_cfg.get("disable_env_checking", False)),
        )
        .env_runners(
            num_env_runners=int(num_tsc_workers),
            num_envs_per_env_runner=int(num_envs_per_tsc_worker),
            num_cpus_per_env_runner=float(pcfg.get("num_cpus_per_tsc_worker", 1)),
            rollout_fragment_length=pcfg.get("rollout_fragment_length", "auto"),
            batch_mode=str(pcfg.get("batch_mode", "truncate_episodes")),
            sample_timeout_s=float(pcfg.get("sample_timeout_s", 300.0)),
            max_requests_in_flight_per_env_runner=int(
                pcfg.get("max_requests_in_flight_per_tsc_worker", 1)
            ),
            explore=True,
        )
        .learners(
            num_learners=int(rllib_cfg.get("learner", {}).get("num_learners", 1)),
            num_cpus_per_learner=float(
                rllib_cfg.get("learner", {}).get("num_cpus_per_learner", 2)
            ),
            num_gpus_per_learner=float(
                rllib_cfg.get("learner", {}).get("num_gpus_per_learner", 0)
            ),
        )
        .resources(
            num_cpus_for_main_process=float(pcfg.get("num_cpus_for_main_process", 1)),
        )
        .training(
            gamma=float(sac_cfg.get("gamma", 0.995)),
            tau=float(sac_cfg.get("tau", 0.005)),
            n_step=sac_cfg.get("n_step", 1),
            twin_q=bool(sac_cfg.get("twin_q", True)),
            actor_lr=float(sac_cfg.get("actor_lr", 3.0e-5)),
            critic_lr=float(sac_cfg.get("critic_lr", 3.0e-4)),
            alpha_lr=float(sac_cfg.get("alpha_lr", 3.0e-4)),
            initial_alpha=float(sac_cfg.get("initial_alpha", 1.0)),
            target_entropy=sac_cfg.get("target_entropy", "auto"),
            grad_clip=sac_cfg.get("grad_clip", 10.0),
            clip_actions=bool(sac_cfg.get("clip_actions", True)),
            num_steps_sampled_before_learning_starts=int(
                sac_cfg.get("num_steps_sampled_before_learning_starts", 10000)
            ),
            train_batch_size_per_learner=int(
                sac_cfg.get("train_batch_size_per_learner", 1024)
            ),
            training_intensity=sac_cfg.get("training_intensity", 1.0),
            replay_buffer_config=copy.deepcopy(
                sac_cfg.get(
                    "replay_buffer_config",
                    {
                        "type": "PrioritizedEpisodeReplayBuffer",
                        "capacity": 200000,
                        "alpha": 0.6,
                        "beta": 0.4,
                    },
                )
            ),
            store_buffer_in_checkpoints=bool(
                sac_cfg.get("store_buffer_in_checkpoints", False)
            ),
        )
        .reporting(
            min_time_s_per_iteration=float(report_cfg.get("min_time_s_per_iteration", 1.0)),
            min_sample_timesteps_per_iteration=int(
                report_cfg.get("min_sample_timesteps_per_iteration", 100)
            ),
        )
        .debugging(log_level=str(rllib_cfg.get("log_level", "INFO")))
    )

    if DefaultModelConfig is not None:
        default_model_config = DefaultModelConfig(
            fcnet_hiddens=list(model_cfg.get("fcnet_hiddens", [512, 512, 256])),
            fcnet_activation=str(model_cfg.get("fcnet_activation", "swish")),
            fcnet_use_layernorm=bool(model_cfg.get("fcnet_use_layernorm", True)),
            head_fcnet_hiddens=list(model_cfg.get("head_fcnet_hiddens", [256])),
            head_fcnet_activation=str(model_cfg.get("head_fcnet_activation", "swish")),
        )
        config = config.rl_module(model_config=default_model_config)
    else:
        print(
            "WARNING: DefaultModelConfig not available in this Ray version; "
            "using RLlib default SAC model."
        )

    resolved = {
        "available_cpus": total_cpus,
        "reserve_cpus": reserve_cpus,
        "num_tsc_workers_requested": pcfg.get("num_tsc_workers", "auto:0.75"),
        "num_tsc_workers_resolved": int(num_tsc_workers),
        "num_env_runners": int(num_tsc_workers),
        "num_envs_per_env_runner": int(num_envs_per_tsc_worker),
        "num_cpus_per_env_runner": float(pcfg.get("num_cpus_per_tsc_worker", 1)),
        "num_learners": int(rllib_cfg.get("learner", {}).get("num_learners", 1)),
        "num_cpus_per_learner": float(
            rllib_cfg.get("learner", {}).get("num_cpus_per_learner", 2)
        ),
        "train_batch_size_per_learner": int(sac_cfg.get("train_batch_size_per_learner", 1024)),
        "backend": env_config["backend"],
    }
    return config, resolved


def save_algo(algo, path: Path):
    path.mkdir(parents=True, exist_ok=True)
    if hasattr(algo, "save_to_path"):
        return algo.save_to_path(str(path))
    return algo.save(str(path))


def restore_algo(algo, path: str):
    if hasattr(algo, "restore_from_path"):
        return algo.restore_from_path(path)
    return algo.restore(path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/rllib_sac.json")
    parser.add_argument("--override", default=None, help="Optional JSON override for RLlib config.")
    parser.add_argument("--train-override", default=None, help="Optional JSON override for old-style train config.")
    parser.add_argument("--run-name", default=None)
    parser.add_argument("--stop-env-steps", type=int, default=None)
    parser.add_argument("--resume-checkpoint", default=None)
    parser.add_argument("--local-mode", action="store_true")
    args = parser.parse_args()

    project_dir = Path(__file__).resolve().parents[1]
    cfg_path = Path(args.config)
    if not cfg_path.is_absolute():
        cfg_path = project_dir / cfg_path
    override_path = Path(args.override) if args.override else None
    if override_path is not None and not override_path.is_absolute():
        override_path = project_dir / override_path
    train_override = Path(args.train_override) if args.train_override else None
    if train_override is not None and not train_override.is_absolute():
        train_override = project_dir / train_override

    rllib_cfg = load_merged_json(cfg_path, override_path)
    pcfg = parallel_cfg_from(rllib_cfg)

    run_name = args.run_name or rllib_cfg.get("run_name", "rllib_sac_tsc_rzip")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_id = f"{run_name}_{stamp}"

    log_root = Path(rllib_cfg.get("log_root", "ray_results"))
    ckpt_root = Path(rllib_cfg.get("checkpoint_root", "ray_checkpoints"))
    if not log_root.is_absolute():
        log_root = project_dir / log_root
    if not ckpt_root.is_absolute():
        ckpt_root = project_dir / ckpt_root
    run_dir = log_root / run_id
    ckpt_dir = ckpt_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    ckpt_dir.mkdir(parents=True, exist_ok=True)

    train_cfg = prepare_train_config(
        project_dir=project_dir,
        run_dir=run_dir,
        rllib_cfg=rllib_cfg,
        train_override=train_override,
    )
    (run_dir / "rllib_config.used.json").write_text(
        json.dumps(rllib_cfg, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # Ray runtime temp directory. Keep it short because Ray creates UNIX sockets under it.
    ray_tmpdir = os.environ.get("RAY_TMPDIR")
    if not ray_tmpdir:
        ray_tmpdir = f"/tmp/ry_{os.environ.get('USER', 'user')}"
    tmpdir = os.environ.get("TMPDIR")
    if not tmpdir:
        tmpdir = os.path.join(ray_tmpdir, "tmp")
        os.environ["TMPDIR"] = tmpdir
    Path(ray_tmpdir).mkdir(parents=True, exist_ok=True)
    Path(tmpdir).mkdir(parents=True, exist_ok=True)

    ray_init_kwargs = {
        "local_mode": bool(args.local_mode or pcfg.get("local_mode", False)),
        "include_dashboard": bool(pcfg.get("include_dashboard", False)),
        "ignore_reinit_error": True,
        "_temp_dir": str(Path(ray_tmpdir).resolve()),
    }
    if pcfg.get("object_store_memory", None) is not None:
        ray_init_kwargs["object_store_memory"] = int(pcfg["object_store_memory"])
    if pcfg.get("ray_address"):
        ray_init_kwargs["address"] = pcfg["ray_address"]
    if pcfg.get("ray_num_cpus") is not None:
        ray_init_kwargs["num_cpus"] = int(pcfg["ray_num_cpus"])

    print("========== Ray init ==========")
    print(f"RAY_TMPDIR          = {ray_tmpdir}")
    print(f"TMPDIR              = {tmpdir}")
    print(f"ray_init_kwargs     = {ray_init_kwargs}")
    print("==============================")

    register_env("RllibTscRzipEnv-v0", lambda env_config: RllibTscRzipEnv(env_config))
    ray.init(**ray_init_kwargs)

    config, resolved = build_config(rllib_cfg, train_cfg, run_id)
    (run_dir / "resolved_parallelism.json").write_text(
        json.dumps(resolved, indent=2),
        encoding="utf-8",
    )

    print("========== RLlib TSC-RZIP SAC ==========")
    print(f"project_dir                  = {project_dir}")
    print(f"run_dir                      = {run_dir}")
    print(f"checkpoint_dir               = {ckpt_dir}")
    print(f"backend                      = {resolved['backend']}")
    print(f"available_cpus               = {resolved['available_cpus']}")
    print(f"reserve_cpus                 = {resolved['reserve_cpus']}")
    print(f"num_tsc_workers requested    = {resolved['num_tsc_workers_requested']}")
    print(f"num_tsc_workers resolved     = {resolved['num_tsc_workers_resolved']}")
    print(f"num_env_runners              = {resolved['num_env_runners']}")
    print(f"num_envs_per_env_runner      = {resolved['num_envs_per_env_runner']}")
    print(f"num_cpus_per_env_runner      = {resolved['num_cpus_per_env_runner']}")
    print(f"num_learners                 = {resolved['num_learners']}")
    print(f"num_cpus_per_learner         = {resolved['num_cpus_per_learner']}")
    print(f"train_batch_size_per_learner = {resolved['train_batch_size_per_learner']}")
    print("num_tsc_workers maps to RLlib num_env_runners.")
    print("When num_envs_per_tsc_worker=1, each EnvRunner owns one independent TSC environment.")
    print("========================================")

    algo = config.build()
    if args.resume_checkpoint:
        print(f"Restoring checkpoint: {args.resume_checkpoint}")
        restore_algo(algo, args.resume_checkpoint)

    stop_env_steps = int(args.stop_env_steps or rllib_cfg.get("stop_env_steps", 2_000_000))
    checkpoint_every_iters = int(rllib_cfg.get("checkpoint_every_iters", 20))
    result_jsonl = run_dir / "train_results.jsonl"
    t0 = time.time()
    last_checkpoint = None

    try:
        iteration = 0
        while True:
            iteration += 1
            result = algo.train()
            env_steps = (
                recursive_find(result, "num_env_steps_sampled_lifetime")
                or recursive_find(result, "num_env_steps_sampled")
                or recursive_find(result, "env_steps_sampled")
                or recursive_find(result, "num_agent_steps_sampled_lifetime")
                or 0
            )
            ret_mean = recursive_find(result, "episode_return_mean") or recursive_find(result, "episode_reward_mean")
            len_mean = recursive_find(result, "episode_len_mean") or recursive_find(result, "episode_length_mean")
            elapsed = time.time() - t0
            fps = float(env_steps) / max(elapsed, 1e-9)
            print(
                f"[iter {iteration:05d}] env_steps={int(env_steps):>10d} "
                f"return_mean={ret_mean} len_mean={len_mean} fps={fps:.3f}"
            )
            with result_jsonl.open("a", encoding="utf-8") as f:
                f.write(json.dumps(json_safe(result), ensure_ascii=False) + "\n")

            if iteration % checkpoint_every_iters == 0:
                last_checkpoint = save_algo(algo, ckpt_dir / f"iter_{iteration:06d}")
                print(f"[checkpoint] {last_checkpoint}")

            if int(env_steps) >= stop_env_steps:
                break
    except KeyboardInterrupt:
        print("KeyboardInterrupt received. Saving current checkpoint...")
    finally:
        last_checkpoint = save_algo(algo, ckpt_dir / "final")
        print(f"[final checkpoint] {last_checkpoint}")
        algo.stop()
        ray.shutdown()

    print(f"Done. Logs: {run_dir}")
    print(f"Done. Checkpoints: {ckpt_dir}")


if __name__ == "__main__":
    main()
