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
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")
os.environ.setdefault("TORCH_NUM_THREADS", "1")
os.environ.setdefault("TORCH_NUM_INTEROP_THREADS", "1")

import numpy as np
import torch

from tsc_rzip_rllib.envs.rllib_env import RllibTscRzipEnv
from tsc_rzip_rllib.mpo.models import RecurrentGaussianActor
from tsc_rzip_rllib.utils.config import deep_update, load_json


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




def default_macros(run_id: str) -> dict[str, str]:
    tsc_all_root = os.environ.get("TSC_ALL_ROOT")
    if not tsc_all_root:
        tsc_all_root = str(PROJECT_DIR.parent)
    return {
        "USER": os.environ.get("USER", "user"),
        "RUN_ID": str(run_id),
        "TSC_ALL_ROOT": str(Path(tsc_all_root).expanduser()),
        "PROJECT_DIR": str(PROJECT_DIR),
    }


def piecewise_constant_schedule(schedule, step: int, default: float) -> float:
    if not schedule:
        return float(default)
    pairs = []
    for item in schedule:
        try:
            if isinstance(item, dict):
                pairs.append((int(item.get("step", item.get("env_steps", 0))), float(item.get("value", item.get("scale")))))
            else:
                pairs.append((int(item[0]), float(item[1])))
        except Exception:
            continue
    if not pairs:
        return float(default)
    pairs.sort(key=lambda x: x[0])
    out = float(default)
    for threshold, value in pairs:
        if int(step) >= threshold:
            out = float(value)
        else:
            break
    return float(out)


def checkpoint_action_scale(saved_cfg: dict[str, Any], payload: dict[str, Any]) -> float:
    mpo_cfg = saved_cfg.get("mpo", {})
    default = float(mpo_cfg.get("actor_output_scale", mpo_cfg.get("actor_output_scale_init", payload.get("action_scale", 1.0))))
    stats = payload.get("stats", {}) if isinstance(payload.get("stats", {}), dict) else {}
    step = int(stats.get("env_steps", 0))
    return piecewise_constant_schedule(mpo_cfg.get("actor_output_scale_schedule", None), step, default)


def checkpoint_physics_blend_alpha(saved_cfg: dict[str, Any], payload: dict[str, Any]) -> float:
    model_cfg = saved_cfg.get("model", {})
    phys_cfg = model_cfg.get("physics_blend", {}) if isinstance(model_cfg, dict) else {}
    default = float(phys_cfg.get("alpha", phys_cfg.get("alpha_init", payload.get("physics_blend_alpha", 0.0))))
    stats = payload.get("stats", {}) if isinstance(payload.get("stats", {}), dict) else {}
    step = int(stats.get("env_steps", 0))
    return piecewise_constant_schedule(phys_cfg.get("alpha_schedule", None), step, default)



def resolve_path_maybe_relative(path_text: str, *, base_dir: Path = PROJECT_DIR) -> Path:
    p = Path(str(path_text)).expanduser()
    if not p.is_absolute():
        p = base_dir / p
    return p


def resolve_tsc_config_file(train_cfg: dict[str, Any], *, out_dir: Path, macros: dict[str, str]) -> dict[str, Any]:
    cfg = json.loads(json.dumps(train_cfg))
    env_config_path = resolve_path_maybe_relative(expand_macros(str(cfg["env_config"]), macros))
    if not env_config_path.exists():
        raise FileNotFoundError(
            f"env_config JSON not found after macro expansion: {env_config_path}; "
            f"TSC_ALL_ROOT={macros.get('TSC_ALL_ROOT')}"
        )
    nested = expand_macros(load_json(env_config_path), macros)
    out_dir.mkdir(parents=True, exist_ok=True)
    resolved_path = out_dir / f"{env_config_path.stem}.eval.{os.getpid()}.resolved.json"
    with open(resolved_path, "w", encoding="utf-8") as f:
        json.dump(nested, f, indent=2, ensure_ascii=False)
    cfg["env_config"] = str(resolved_path)
    cfg.setdefault("_resolved_external_configs", {})["env_config_original"] = str(env_config_path)
    cfg["_resolved_external_configs"]["env_config_resolved"] = str(resolved_path)
    return cfg

def load_cfg(config: Path, override: Path | None = None) -> dict[str, Any]:
    cfg = load_json(config)
    if override is not None:
        cfg = deep_update(cfg, load_json(override))
    run_id = str(cfg.get("run_name", config.stem))
    macros = default_macros(run_id)
    os.environ.setdefault("TSC_ALL_ROOT", macros["TSC_ALL_ROOT"])
    train_cfg_path = resolve_path_maybe_relative(expand_macros(str(cfg.get("train_config", "configs/train_b83_fixed_target_1ms.json")), macros))
    train_cfg = expand_macros(load_json(train_cfg_path), macros)
    tmp_root = Path(os.environ.get("TMPDIR", "/tmp")) / f"mpo_eval_resolved_{os.getpid()}"
    cfg["train_config_resolved"] = resolve_tsc_config_file(train_cfg, out_dir=tmp_root, macros=macros)
    return cfg


def force_stage(train_cfg: dict[str, Any], stage_name: str | None) -> dict[str, Any]:
    if not stage_name or stage_name == "default":
        return train_cfg
    cfg = json.loads(json.dumps(train_cfg))
    cur = cfg.get("curriculum", {}).get("env_attributes", {})
    stages = list(cur.get("stages", []))
    aliases = {"final": "stage3", "strict": "stage3"}
    target = aliases.get(stage_name, stage_name)
    match = None
    for st in stages:
        name = str(st.get("name", ""))
        if target == name or name.startswith(target) or target in name:
            match = st
    if match is None:
        raise ValueError(f"Cannot find eval stage {stage_name!r} in train_config curriculum")
    cfg.setdefault("curriculum", {}).setdefault("env_attributes", {})["enabled"] = False
    cfg.setdefault("reward", {}).update(dict(match.get("env_params", {})))
    print(f"Eval stage fixed to: {match.get('name')}")
    return cfg


def make_env(cfg: dict[str, Any], seed: int, stage: str | None):
    train_cfg = force_stage(cfg["train_config_resolved"], stage)
    env_cfg = {
        "backend": cfg.get("env", {}).get("backend", "native"),
        "train_config": train_cfg,
        "seed": int(seed),
        "worker_index": 0,
        "vector_index": 0,
        "num_workers_for_curriculum": 1,
        "finite_guard": cfg.get("env", {}).get("finite_guard", {"enabled": True}),
    }
    return RllibTscRzipEnv(env_cfg)


def scalar_info(info: dict[str, Any], key: str, default: float = 0.0) -> float:
    try:
        return float(info.get(key, default))
    except Exception:
        return float(default)


def main():
    ap = argparse.ArgumentParser(description="Evaluate B85 MPO recurrent actor checkpoint.")
    ap.add_argument("--config", required=True)
    ap.add_argument("--checkpoint", required=True, help="Checkpoint dir containing mpo_checkpoint.pt")
    ap.add_argument("--episodes", type=int, default=5)
    ap.add_argument("--out", required=True)
    ap.add_argument("--eval-stage", default="final", help="default, stage0, stage1, stage2, final")
    ap.add_argument("--action-mode", default="deterministic", choices=["deterministic", "stochastic"])
    ap.add_argument("--seed", type=int, default=12345)
    ap.add_argument("--override", default=None)
    args = ap.parse_args()

    cfg = load_cfg(Path(args.config), Path(args.override) if args.override else None)
    payload = torch.load(Path(args.checkpoint) / "mpo_checkpoint.pt", map_location="cpu")
    saved_cfg = payload.get("config", cfg)
    # Use current cfg env paths but saved model dimensions.
    env = make_env(cfg, args.seed, args.eval_stage)
    obs_dim = int(np.prod(env.observation_space.shape))
    action_dim = int(np.prod(env.action_space.shape))
    m_cfg = saved_cfg.get("model", cfg.get("model", {}))
    actor = RecurrentGaussianActor(
        obs_dim,
        action_dim,
        hidden_size=int(m_cfg.get("actor_gru_hidden", 128)),
        mlp_hiddens=list(m_cfg.get("actor_mlp_hiddens", [256, 256])),
        activation=str(m_cfg.get("activation", "silu")),
        log_std_min=float(m_cfg.get("log_std_min", -5.0)),
        log_std_max=float(m_cfg.get("log_std_max", 1.0)),
        physics_blend=m_cfg.get("physics_blend", None),
    )
    actor.load_state_dict(payload["actor"])
    actor.eval()
    action_scale = checkpoint_action_scale(saved_cfg, payload)
    physics_blend_alpha = checkpoint_physics_blend_alpha(saved_cfg, payload)
    if hasattr(actor, "set_physics_blend_alpha"):
        actor.set_physics_blend_alpha(physics_blend_alpha)
    print(f"Eval action_scale={action_scale} physics_blend_alpha={physics_blend_alpha}")

    rows = []
    summaries = []
    for ep in range(int(args.episodes)):
        obs, info = env.reset(seed=args.seed + ep)
        obs = np.asarray(obs, dtype=np.float32).reshape(-1)
        hidden = actor.init_hidden(1)
        done = False
        total = 0.0
        step = 0
        action_abs = []
        last_info = dict(info or {})
        while not done:
            with torch.no_grad():
                a, hidden = actor.act_step(
                    torch.as_tensor(obs, dtype=torch.float32),
                    hidden,
                    deterministic=(args.action_mode == "deterministic"),
                    action_scale=action_scale,
                )
            action = a.cpu().numpy().reshape(-1).astype(np.float32)
            next_obs, reward, terminated, truncated, info = env.step(action)
            done = bool(terminated or truncated)
            row = {
                "episode": ep,
                "step": step,
                "reward": float(reward),
                "terminated": bool(terminated),
                "truncated": bool(truncated),
                "action_mode": args.action_mode,
                "eval_stage": args.eval_stage,
                "physics_blend_alpha": float(physics_blend_alpha),
                "R_error": scalar_info(info, "R_error"),
                "Z_error": scalar_info(info, "Z_error"),
                "Ip_error": scalar_info(info, "Ip_error"),
                "velocity_norm": scalar_info(info, "velocity_norm"),
                "mean_abs_action": float(np.mean(np.abs(action))),
                "max_abs_action": float(np.max(np.abs(action))),
                "vessel_current_total_a": scalar_info(info, "vessel_current_total_a"),
                "vessel_current_abs_sum_a": scalar_info(info, "vessel_current_abs_sum_a"),
                "current_util_max": scalar_info(info, "current_util_max"),
            }
            rows.append(row)
            total += float(reward)
            action_abs.append(float(np.mean(np.abs(action))))
            obs = np.asarray(next_obs, dtype=np.float32).reshape(-1)
            last_info = dict(info or {})
            step += 1
        summ = {
            "episode": ep,
            "episode_return": float(total),
            "episode_len": int(step),
            "terminated": bool(last_info.get("terminated", False)),
            "truncated": True,
            "hold_success": bool(last_info.get("hold_success", False)),
            "quality_success": bool(last_info.get("quality_success", False)),
            "is_success": bool(last_info.get("is_success", False)),
            "time_to_first_reach_step": int(last_info.get("time_to_first_reach_step", last_info.get("first_reach_step", -1))),
            "time_to_stable_hold_step": int(last_info.get("time_to_stable_hold_step", last_info.get("first_stable_hold_step", -1))),
            "terminal_R_error": scalar_info(last_info, "terminal_R_error", scalar_info(last_info, "R_error")),
            "terminal_Z_error": scalar_info(last_info, "terminal_Z_error", scalar_info(last_info, "Z_error")),
            "terminal_Ip_error": scalar_info(last_info, "terminal_Ip_error", scalar_info(last_info, "Ip_error")),
            "terminal_velocity_norm": scalar_info(last_info, "terminal_velocity_norm", scalar_info(last_info, "velocity_norm")),
            "mean_abs_action": float(np.mean(action_abs)) if action_abs else 0.0,
            "max_abs_action": float(max([r["max_abs_action"] for r in rows if r["episode"] == ep], default=0.0)),
            "terminal_vessel_current_total_a": scalar_info(last_info, "terminal_vessel_current_total_a", scalar_info(last_info, "vessel_current_total_a")),
            "terminal_vessel_current_abs_sum_a": scalar_info(last_info, "terminal_vessel_current_abs_sum_a", scalar_info(last_info, "vessel_current_abs_sum_a")),
        }
        summaries.append(summ)
        print(f"[eval episode {ep}] return={summ['episode_return']:.3f} len={step} hold={summ['hold_success']} first_reach={summ['time_to_first_reach_step']} stable={summ['time_to_stable_hold_step']}")
    env.close()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    if rows:
        with open(out, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
    summary = {
        "checkpoint": str(args.checkpoint),
        "episodes": summaries,
        "mean_return": float(np.mean([x["episode_return"] for x in summaries])) if summaries else None,
        "mean_len": float(np.mean([x["episode_len"] for x in summaries])) if summaries else None,
        "hold_success_rate": float(np.mean([x["hold_success"] for x in summaries])) if summaries else 0.0,
        "quality_success_rate": float(np.mean([x["quality_success"] for x in summaries])) if summaries else 0.0,
        "action_mode": args.action_mode,
        "eval_stage": args.eval_stage,
        "action_scale": float(action_scale),
        "physics_blend_alpha": float(physics_blend_alpha),
        "out_csv": str(out),
    }
    with open(out.with_suffix(out.suffix + ".summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"Saved eval CSV: {out}")
    print(f"Saved summary: {out.with_suffix(out.suffix + '.summary.json')}")


if __name__ == "__main__":
    main()
