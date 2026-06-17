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
    if isinstance(train_cfg.get("target_randomization", None), dict):
        train_cfg["target_randomization"]["enabled"] = False
        train_cfg["target_randomization"]["eval_disabled"] = True
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


def sanitize_metric_name(name: str) -> str:
    out = []
    for ch in str(name):
        if ch.isalnum() or ch in {"_", "-"}:
            out.append(ch)
        else:
            out.append("_")
    return "".join(out).strip("_") or "unnamed"


def action_names_from_cfg(cfg: dict[str, Any], action_dim: int) -> list[str]:
    train_cfg = cfg.get("train_config_resolved", {}) if isinstance(cfg, dict) else {}
    env_path = train_cfg.get("env_config") if isinstance(train_cfg, dict) else None
    names: list[str] = []
    if env_path:
        try:
            env_cfg = load_json(resolve_path_maybe_relative(str(env_path), base_dir=PROJECT_DIR))
            names = [str(x) for x in env_cfg.get("coil_names_display_order", [])]
        except Exception:
            names = []
    if len(names) != int(action_dim):
        names = [f"a{i:02d}" for i in range(int(action_dim))]
    return [sanitize_metric_name(x) for x in names]


def info_float(info: dict[str, Any] | None, key: str, default: float = 0.0) -> float:
    try:
        if info is None:
            return float(default)
        return float(info.get(key, default))
    except Exception:
        return float(default)


def mode_coeff_lookup(mode_names: list[str] | None, mode_coeff: Any | None) -> dict[str, float]:
    if mode_names is None or mode_coeff is None:
        return {}
    try:
        arr = np.asarray(mode_coeff, dtype=np.float64).reshape(-1)
    except Exception:
        return {}
    out: dict[str, float] = {}
    for i, raw_name in enumerate(list(mode_names)):
        if i >= arr.size:
            break
        out[sanitize_metric_name(str(raw_name))] = float(arr[i])
    return out


def apply_extra_reward_shaping(
    reward: float,
    info: dict[str, Any] | None,
    reward_params: dict[str, Any] | None,
    *,
    prev_info: dict[str, Any] | None = None,
    mode_names: list[str] | None = None,
    mode_coeff: Any | None = None,
) -> tuple[float, dict[str, float]]:
    rp = reward_params or {}
    extra_cfg = rp.get("extra_reward_shaping", {}) if isinstance(rp.get("extra_reward_shaping", {}), dict) else {}
    if extra_cfg and not bool(extra_cfg.get("enabled", True)):
        return float(reward), {}
    shaped = float(reward)
    out: dict[str, float] = {}
    r_err = info_float(info, "R_error", info_float(info, "terminal_R_error", 0.0))
    z_err = info_float(info, "Z_error", info_float(info, "terminal_Z_error", 0.0))
    prev_r_err = info_float(prev_info, "R_error", info_float(prev_info, "terminal_R_error", r_err))

    w_r_neg = float(rp.get("w_r_negative_bias_strong", 0.0) or 0.0)
    if w_r_neg > 0.0:
        deadband = float(rp.get("r_neg_deadband_m", 0.10) or 0.0)
        ref = max(float(rp.get("r_neg_ref_m", 0.05) or 0.05), 1.0e-12)
        power = float(rp.get("r_neg_power", 2.0) or 2.0)
        r_neg = max(0.0, -r_err - deadband)
        penalty = w_r_neg * (r_neg / ref) ** power
        shaped -= penalty
        out["extra_r_negative_bias_penalty"] = float(penalty)
        out["extra_r_negative_bias_active"] = float(r_neg > 0.0)
        out["extra_r_negative_bias_margin_m"] = float(r_neg)

    w_r_prog = float(rp.get("w_r_negative_progress", 0.0) or 0.0)
    if w_r_prog > 0.0:
        enable_m = float(rp.get("r_negative_progress_enable_m", -0.08) or -0.08)
        ref = max(float(rp.get("r_negative_progress_ref_m", 0.03) or 0.03), 1.0e-12)
        clip = float(rp.get("r_negative_progress_clip", 2.5) or 2.5)
        active = (r_err < enable_m) or (prev_r_err < enable_m)
        progress_m = r_err - prev_r_err
        progress_norm = float(np.clip(progress_m / ref, -clip, clip)) if active else 0.0
        bonus = w_r_prog * progress_norm
        shaped += bonus
        out["extra_r_negative_progress_bonus"] = float(bonus)
        out["extra_r_negative_progress_m"] = float(progress_m)
        out["extra_r_negative_progress_active"] = float(bool(active))

    w_pos_base = float(rp.get("w_z_positive_bias", 0.0) or 0.0)
    w_pos_eff = w_pos_base
    gate_threshold = rp.get("z_pos_gate_r_threshold_m", None)
    if gate_threshold is not None and r_err < float(gate_threshold):
        w_pos_eff *= float(rp.get("z_pos_gate_multiplier", 1.0) or 1.0)
    out["extra_z_positive_bias_weight_effective"] = float(w_pos_eff)
    if w_pos_eff > 0.0:
        deadband = float(rp.get("z_pos_deadband_m", 0.03) or 0.0)
        ref = max(float(rp.get("z_pos_ref_m", 0.05) or 0.05), 1.0e-12)
        power = float(rp.get("z_pos_power", 2.0) or 2.0)
        z_pos = max(0.0, z_err - deadband)
        penalty = w_pos_eff * (z_pos / ref) ** power
        shaped -= penalty
        out["extra_z_positive_bias_penalty"] = float(penalty)
        out["extra_z_positive_bias_active"] = float(z_pos > 0.0)

    coeffs = mode_coeff_lookup(mode_names, mode_coeff)
    common_names_raw = rp.get("common_mode_coeff_names", ["outer_pf_common_shape", "cs_common_flux"])
    if isinstance(common_names_raw, str):
        common_names = [common_names_raw]
    else:
        common_names = list(common_names_raw or [])
    common_names = [sanitize_metric_name(str(x)) for x in common_names]
    selected = [coeffs[name] for name in common_names if name in coeffs]
    if selected:
        vals = np.asarray(selected, dtype=np.float64)
        l2 = float(np.mean(vals ** 2))
        w_l2 = float(rp.get("w_common_mode_coeff_l2", 0.0) or 0.0)
        if w_l2 > 0.0:
            penalty = w_l2 * l2
            shaped -= penalty
            out["extra_common_mode_coeff_l2_penalty"] = float(penalty)
        soft_limit = float(rp.get("common_mode_coeff_soft_limit", 1.0) or 1.0)
        w_sat = float(rp.get("w_common_mode_coeff_saturation", 0.0) or 0.0)
        sat_excess = np.maximum(0.0, np.abs(vals) - soft_limit)
        sat = float(np.mean(sat_excess ** 2))
        if w_sat > 0.0:
            penalty = w_sat * sat
            shaped -= penalty
            out["extra_common_mode_coeff_saturation_penalty"] = float(penalty)
        out["extra_common_mode_coeff_abs_mean"] = float(np.mean(np.abs(vals)))
        out["extra_common_mode_coeff_abs_max"] = float(np.max(np.abs(vals)))
    return float(shaped), out

def actor_pre_tanh_step(actor: RecurrentGaussianActor, obs: torch.Tensor, hidden: torch.Tensor | None, *, deterministic: bool):
    if obs.ndim == 1:
        obs_seq = obs.view(1, 1, -1)
    elif obs.ndim == 2:
        obs_seq = obs.unsqueeze(1)
    else:
        obs_seq = obs
    dist, mean, _log_std, h = actor.distribution(obs_seq, hidden)
    pre_tanh = mean if deterministic else dist.rsample()
    comps = actor.action_components_from_pre_tanh(pre_tanh)
    return pre_tanh, comps, h


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
    eval_train_cfg = force_stage(cfg["train_config_resolved"], args.eval_stage)
    env_cfg = {
        "backend": cfg.get("env", {}).get("backend", "native"),
        "train_config": eval_train_cfg,
        "seed": int(args.seed),
        "worker_index": 0,
        "vector_index": 0,
        "num_workers_for_curriculum": 1,
        "finite_guard": cfg.get("env", {}).get("finite_guard", {"enabled": True}),
    }
    env = RllibTscRzipEnv(env_cfg)
    reward_params = dict(eval_train_cfg.get("reward", {}))
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
    # When evaluating a B91 run resumed from a B90 checkpoint, saved checkpoints
    # normally contain the B91 config.  This optional refresh is also useful for
    # direct diagnostic evaluation of an older checkpoint under a newer config.
    if bool(cfg.get("model", {}).get("physics_blend", {}).get("force_config_after_resume", False)):
        if hasattr(actor, "reset_physics_modes_from_config"):
            actor.reset_physics_modes_from_config(cfg.get("model", {}).get("physics_blend", None))
    actor.eval()
    action_scale = checkpoint_action_scale(saved_cfg, payload)
    physics_blend_alpha = checkpoint_physics_blend_alpha(saved_cfg, payload)
    if hasattr(actor, "set_physics_blend_alpha"):
        actor.set_physics_blend_alpha(physics_blend_alpha)
    print(f"Eval action_scale={action_scale} physics_blend_alpha={physics_blend_alpha}")
    coil_names = action_names_from_cfg(cfg, action_dim)
    mode_names = [sanitize_metric_name(x) for x in getattr(actor, "physics_mode_names", [])]

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
        last_terminated = False
        last_truncated = False
        while not done:
            prev_info = dict(last_info or {})
            with torch.no_grad():
                _pre_tanh, comps, hidden = actor_pre_tanh_step(
                    actor,
                    torch.as_tensor(obs, dtype=torch.float32),
                    hidden,
                    deterministic=(args.action_mode == "deterministic"),
                )
                action_t = comps["blended_action"] * float(action_scale)
                raw_t = comps["raw_action"] * float(action_scale)
                physics_t = comps["physics_action"] * float(action_scale)
                mode_t = comps["mode_coeff"]
                mode_raw_t = comps.get("mode_coeff_raw", mode_t)
            action = action_t[:, -1, :].cpu().numpy().reshape(-1).astype(np.float32)
            raw_action = raw_t[:, -1, :].cpu().numpy().reshape(-1)
            physics_action = physics_t[:, -1, :].cpu().numpy().reshape(-1)
            mode_coeff = mode_t[:, -1, :].cpu().numpy().reshape(-1) if len(mode_names) > 0 else np.zeros(0)
            mode_coeff_raw = mode_raw_t[:, -1, :].cpu().numpy().reshape(-1) if len(mode_names) > 0 else np.zeros(0)
            next_obs, reward_env, terminated, truncated, info = env.step(action)
            info = dict(info or {})
            reward, extra_reward_info = apply_extra_reward_shaping(
                float(reward_env), info, reward_params,
                prev_info=prev_info, mode_names=mode_names, mode_coeff=mode_coeff,
            )
            info.update(extra_reward_info)
            done = bool(terminated or truncated)
            last_terminated = bool(terminated)
            last_truncated = bool(truncated)
            row = {
                "episode": ep,
                "step": step,
                "reward": float(reward),
                "reward_env": float(reward_env),
                "terminated": bool(terminated),
                "truncated": bool(truncated),
                "action_mode": args.action_mode,
                "eval_stage": args.eval_stage,
                "action_scale": float(action_scale),
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
                "extra_z_positive_bias_penalty": float(info.get("extra_z_positive_bias_penalty", 0.0)),
                "extra_z_positive_bias_weight_effective": float(info.get("extra_z_positive_bias_weight_effective", 0.0)),
                "extra_r_negative_bias_penalty": float(info.get("extra_r_negative_bias_penalty", 0.0)),
                "extra_r_negative_progress_bonus": float(info.get("extra_r_negative_progress_bonus", 0.0)),
                "extra_r_negative_progress_m": float(info.get("extra_r_negative_progress_m", 0.0)),
                "extra_common_mode_coeff_l2_penalty": float(info.get("extra_common_mode_coeff_l2_penalty", 0.0)),
                "extra_common_mode_coeff_saturation_penalty": float(info.get("extra_common_mode_coeff_saturation_penalty", 0.0)),
                "extra_common_mode_coeff_abs_mean": float(info.get("extra_common_mode_coeff_abs_mean", 0.0)),
            }
            for i, cname in enumerate(coil_names):
                row[f"action/{cname}"] = float(action[i])
                row[f"raw_action/{cname}"] = float(raw_action[i])
                row[f"physics_action/{cname}"] = float(physics_action[i])
            for i, mname in enumerate(mode_names):
                row[f"mode_coeff/{mname}"] = float(mode_coeff[i])
                row[f"mode_coeff_raw/{mname}"] = float(mode_coeff_raw[i])
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
            "terminated": bool(last_terminated),
            "truncated": bool(last_truncated),
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
            "terminal_extra_z_positive_bias_penalty": float(last_info.get("extra_z_positive_bias_penalty", 0.0)),
            "terminal_extra_z_positive_bias_weight_effective": float(last_info.get("extra_z_positive_bias_weight_effective", 0.0)),
            "terminal_extra_r_negative_bias_penalty": float(last_info.get("extra_r_negative_bias_penalty", 0.0)),
            "terminal_extra_r_negative_progress_bonus": float(last_info.get("extra_r_negative_progress_bonus", 0.0)),
            "terminal_extra_r_negative_progress_m": float(last_info.get("extra_r_negative_progress_m", 0.0)),
            "terminal_extra_common_mode_coeff_l2_penalty": float(last_info.get("extra_common_mode_coeff_l2_penalty", 0.0)),
            "terminal_extra_common_mode_coeff_saturation_penalty": float(last_info.get("extra_common_mode_coeff_saturation_penalty", 0.0)),
            "terminal_extra_common_mode_coeff_abs_mean": float(last_info.get("extra_common_mode_coeff_abs_mean", 0.0)),
        }
        summaries.append(summ)
        print(f"[eval episode {ep}] return={summ['episode_return']:.3f} len={step} hold={summ['hold_success']} first_reach={summ['time_to_first_reach_step']} stable={summ['time_to_stable_hold_step']}")
    env.close()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    if rows:
        with open(out, "w", newline="", encoding="utf-8") as f:
            fieldnames = []
            for row in rows:
                for key in row.keys():
                    if key not in fieldnames:
                        fieldnames.append(key)
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
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
