#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import csv
import json
import math
import os
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

# Safety defaults before importing Ray/Torch.
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")
os.environ.setdefault("TORCH_NUM_THREADS", "1")
os.environ.setdefault("TORCH_NUM_INTEROP_THREADS", "1")
os.environ.setdefault("VECLIB_MAXIMUM_THREADS", "1")
os.environ.setdefault("BLIS_NUM_THREADS", "1")
os.environ.setdefault("RAYON_NUM_THREADS", "1")
os.environ.setdefault("RAY_ACCEL_ENV_VAR_OVERRIDE_ON_ZERO", "0")

import numpy as np
import ray
import torch
import torch.nn.functional as F

from tsc_rzip_rllib.envs.rllib_env import RllibTscRzipEnv
from tsc_rzip_rllib.mpo.models import (
    RecurrentGaussianActor,
    RecurrentQCritic,
    gaussian_kl,
    hard_update,
    soft_update,
    tanh_gaussian_log_prob,
)
from tsc_rzip_rllib.mpo.privileged import build_privileged_vector, privileged_dim
from tsc_rzip_rllib.mpo.replay import SequenceReplayBuffer
from tsc_rzip_rllib.utils.config import deep_update, load_json


def json_safe(obj: Any) -> Any:
    try:
        json.dumps(obj)
        return obj
    except Exception:
        if isinstance(obj, dict):
            return {str(k): json_safe(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [json_safe(x) for x in obj]
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return str(obj)


def now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


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
        # Project layout: /.../tsc_all/tsc_rzip_rllib/scripts/train_mpo.py
        tsc_all_root = str(PROJECT_DIR.parent)
    return {
        "USER": os.environ.get("USER", "user"),
        "RUN_ID": str(run_id),
        "TSC_ALL_ROOT": str(Path(tsc_all_root).expanduser()),
        "PROJECT_DIR": str(PROJECT_DIR),
    }


def resolve_path_maybe_relative(path_text: str, *, base_dir: Path = PROJECT_DIR) -> Path:
    p = Path(str(path_text)).expanduser()
    if not p.is_absolute():
        p = base_dir / p
    return p


def resolve_tsc_config_file(train_cfg: dict[str, Any], *, out_dir: Path, macros: dict[str, str]) -> dict[str, Any]:
    """Resolve nested env_config JSON macros and point train_cfg to a concrete file.

    The outer train config is already expanded, but env_config points to another
    JSON file (usually configs/tsc_low_field_side_118.json).  That nested file
    can contain placeholders such as {TSC_ALL_ROOT}, ${TSC_ALL_ROOT}, {USER},
    and {RUN_ID}.  TSCConfig.from_json() validates paths directly and does not
    expand those placeholders, so we must materialize a resolved copy before
    constructing any environment.
    """
    cfg = json.loads(json.dumps(train_cfg))
    if "env_config" not in cfg:
        raise KeyError("train_cfg must contain 'env_config'.")

    env_config_path = resolve_path_maybe_relative(expand_macros(str(cfg["env_config"]), macros))
    if not env_config_path.exists():
        raise FileNotFoundError(
            f"env_config JSON not found after macro expansion: {env_config_path}\n"
            f"TSC_ALL_ROOT={macros.get('TSC_ALL_ROOT')}"
        )

    nested = load_json(env_config_path)
    nested = expand_macros(nested, macros)

    out_dir.mkdir(parents=True, exist_ok=True)
    resolved_path = out_dir / f"{env_config_path.stem}.resolved.json"
    with open(resolved_path, "w", encoding="utf-8") as f:
        json.dump(json_safe(nested), f, indent=2, ensure_ascii=False)

    cfg["env_config"] = str(resolved_path)
    cfg.setdefault("_resolved_external_configs", {})["env_config_original"] = str(env_config_path)
    cfg["_resolved_external_configs"]["env_config_resolved"] = str(resolved_path)
    cfg["_resolved_macros"] = dict(macros)
    return cfg

def load_merged_json(path: Path, override_path: Path | None = None) -> dict[str, Any]:
    cfg = load_json(path)
    if override_path is not None:
        cfg = deep_update(cfg, load_json(override_path))
    return cfg


def ray_worker_env_vars() -> dict[str, str]:
    keys = [
        "OMP_NUM_THREADS",
        "MKL_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
        "TORCH_NUM_THREADS",
        "TORCH_NUM_INTEROP_THREADS",
        "VECLIB_MAXIMUM_THREADS",
        "BLIS_NUM_THREADS",
        "RAYON_NUM_THREADS",
        "RAY_ACCEL_ENV_VAR_OVERRIDE_ON_ZERO",
    ]
    return {k: os.environ.get(k, "1") for k in keys}


def available_cpu_count() -> int:
    try:
        return max(1, len(os.sched_getaffinity(0)))
    except Exception:
        return max(1, os.cpu_count() or 1)


def disk_health_report(paths: list[Path]) -> list[dict[str, Any]]:
    out = []
    seen = set()
    for p in paths:
        try:
            p = Path(p).expanduser()
            p.mkdir(parents=True, exist_ok=True)
            key = str(p.resolve())
            if key in seen:
                continue
            seen.add(key)
            usage = shutil.disk_usage(p)
            st = os.statvfs(str(p))
            inode_pct = 100.0 * float(st.f_favail / st.f_files) if st.f_files > 0 else 100.0
            out.append(
                {
                    "path": key,
                    "free_gb": float(usage.free / (1024**3)),
                    "used_percent": float(100.0 * usage.used / max(usage.total, 1)),
                    "free_inodes": int(st.f_favail),
                    "total_inodes": int(st.f_files),
                    "inode_free_percent": inode_pct,
                }
            )
        except Exception as exc:
            out.append({"path": str(p), "error": repr(exc)})
    return out


def piecewise_constant_schedule(schedule: Any, step: int, default: float) -> float:
    """Return the last value whose threshold step has been reached.

    Accepts [[step, value], ...] or [{"step": ..., "value": ...}, ...].
    This is intentionally piecewise-constant so it is easy to reason about
    safety limits in control experiments.
    """
    if not schedule:
        return float(default)
    pairs: list[tuple[int, float]] = []
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
        if int(step) >= int(threshold):
            out = float(value)
        else:
            break
    return float(out)


def bounded_policy_loss(
    loss: torch.Tensor,
    clip_range: Any | None = None,
    lower: float | None = None,
    upper: float | None = None,
) -> torch.Tensor:
    """Asymmetric scalar policy-loss bound for MPO actor updates.

    B85c used a symmetric torch.clamp(policy_loss_raw, -5, 5).  That is
    dangerous for this experiment: when policy_loss_raw stays above +5 the
    clamp has zero gradient and the actor mean is driven toward zero only by
    regularization.  B86 keeps the positive-loss gradient alive by default
    and clips only the aggressive negative direction.

    Backward compatibility: if clip_range is supplied, it is still accepted,
    but B86 configs should use policy_loss_lower_clip / policy_loss_upper_clip.
    Set policy_loss_upper_clip to null to avoid the B85c no-op failure mode.
    """
    if clip_range is not None:
        # Legacy configs.  Preserve old behavior unless explicit lower/upper
        # keys are also supplied.
        if lower is None:
            lower = float(clip_range[0])
        if upper is None and len(clip_range) > 1 and clip_range[1] is not None:
            upper = float(clip_range[1])
    out = loss
    if lower is not None:
        lo = torch.as_tensor(float(lower), dtype=loss.dtype, device=loss.device)
        out = torch.maximum(out, lo)
    if upper is not None:
        hi = torch.as_tensor(float(upper), dtype=loss.dtype, device=loss.device)
        out = torch.minimum(out, hi)
    return out



@ray.remote
class MpoRolloutWorker:
    def __init__(self, worker_index: int, cfg: dict[str, Any], actor_state: dict[str, Any] | None = None):
        self.worker_index = int(worker_index)
        self.cfg = cfg
        seed = int(cfg.get("seed", 42)) + 1000 * self.worker_index
        np.random.seed(seed)
        torch.manual_seed(seed)
        torch.set_num_threads(1)
        torch.set_num_interop_threads(1)

        train_cfg = dict(cfg["train_config_resolved"])
        par = cfg.get("parallel", {})
        env_cfg = {
            "backend": cfg.get("env", {}).get("backend", "native"),
            "train_config": train_cfg,
            "seed": seed,
            "worker_index": self.worker_index,
            "vector_index": 0,
            "num_workers_for_curriculum": int(par.get("num_tsc_workers", 1)),
            "finite_guard": cfg.get("env", {}).get("finite_guard", {"enabled": True}),
        }
        self.env = RllibTscRzipEnv(env_cfg)
        self.obs_dim = int(np.prod(self.env.observation_space.shape))
        self.action_dim = int(np.prod(self.env.action_space.shape))
        p_cfg = cfg.get("privileged", {})
        self.priv_keys = p_cfg.get("keys")
        self.priv_include_currents = bool(p_cfg.get("include_currents", True))
        self.priv_current_scale_a = float(p_cfg.get("current_scale_a", 1000.0))
        self.priv_clip = float(p_cfg.get("clip", 50.0))
        self.priv_scales = dict(p_cfg.get("scales", {}))
        self.priv_dim = privileged_dim(self.priv_keys, include_currents=self.priv_include_currents)
        m_cfg = cfg.get("model", {})
        self.actor = RecurrentGaussianActor(
            self.obs_dim,
            self.action_dim,
            hidden_size=int(m_cfg.get("actor_gru_hidden", 128)),
            mlp_hiddens=list(m_cfg.get("actor_mlp_hiddens", [256, 256])),
            activation=str(m_cfg.get("activation", "silu")),
            log_std_min=float(m_cfg.get("log_std_min", -5.0)),
            log_std_max=float(m_cfg.get("log_std_max", 1.0)),
            physics_blend=m_cfg.get("physics_blend", None),
        )
        if actor_state is not None:
            self.actor.load_state_dict(actor_state)
        self.actor.eval()
        self.action_scale = float(cfg.get("mpo", {}).get("actor_output_scale_init", 1.0))
        phys_cfg = cfg.get("model", {}).get("physics_blend", {})
        self.physics_blend_alpha = float(phys_cfg.get("alpha_init", phys_cfg.get("alpha", 0.0)))
        if hasattr(self.actor, "set_physics_blend_alpha"):
            self.actor.set_physics_blend_alpha(self.physics_blend_alpha)
        self.hidden = self.actor.init_hidden(1)
        self.obs, self.info = self.env.reset(seed=seed)
        self.obs = np.asarray(self.obs, dtype=np.float32).reshape(-1)
        self.priv = self._priv(self.info)
        self.episode_return = 0.0
        self.episode_len = 0
        self.completed_episodes: list[dict[str, Any]] = []

    def _priv(self, info: dict[str, Any] | None) -> np.ndarray:
        return build_privileged_vector(
            info,
            keys=self.priv_keys,
            scales=self.priv_scales,
            include_currents=self.priv_include_currents,
            current_scale_a=self.priv_current_scale_a,
            clip=self.priv_clip,
        )

    def set_actor_weights(self, state: dict[str, Any], action_scale: float | None = None, physics_blend_alpha: float | None = None) -> None:
        self.actor.load_state_dict(state)
        self.actor.eval()
        if action_scale is not None:
            self.action_scale = float(action_scale)
        if physics_blend_alpha is not None:
            self.physics_blend_alpha = float(physics_blend_alpha)
            if hasattr(self.actor, "set_physics_blend_alpha"):
                self.actor.set_physics_blend_alpha(self.physics_blend_alpha)

    def set_action_scale(self, action_scale: float, physics_blend_alpha: float | None = None) -> None:
        self.action_scale = float(action_scale)
        if physics_blend_alpha is not None:
            self.physics_blend_alpha = float(physics_blend_alpha)
            if hasattr(self.actor, "set_physics_blend_alpha"):
                self.actor.set_physics_blend_alpha(self.physics_blend_alpha)

    def rollout(self, fragment_steps: int, deterministic: bool = False) -> dict[str, Any]:
        obs_l, priv_l, act_l, rew_l, done_l, nobs_l, npriv_l, mask_l, info_l = [], [], [], [], [], [], [], [], []
        env_steps = 0
        action_abs = []
        for _ in range(int(fragment_steps)):
            obs_t = torch.as_tensor(self.obs, dtype=torch.float32)
            with torch.no_grad():
                action_t, self.hidden = self.actor.act_step(
                    obs_t, self.hidden, deterministic=deterministic, action_scale=self.action_scale
                )
            action = action_t.cpu().numpy().reshape(-1).astype(np.float32)
            next_obs, reward, terminated, truncated, info = self.env.step(action)
            done = bool(terminated or truncated)
            next_obs_arr = np.asarray(next_obs, dtype=np.float32).reshape(-1)
            next_priv = self._priv(info)

            obs_l.append(self.obs.copy())
            priv_l.append(self.priv.copy())
            act_l.append(action.copy())
            rew_l.append(float(reward))
            done_l.append(float(done))
            nobs_l.append(next_obs_arr.copy())
            npriv_l.append(next_priv.copy())
            mask_l.append(1.0)
            info_l.append({k: v for k, v in dict(info or {}).items() if isinstance(v, (int, float, bool, str))})
            action_abs.append(float(np.mean(np.abs(action))))

            self.episode_return += float(reward)
            self.episode_len += 1
            env_steps += 1
            self.obs = next_obs_arr
            self.priv = next_priv

            if done:
                ep = {
                    "episode_return": float(self.episode_return),
                    "episode_len": int(self.episode_len),
                    "hold_success": bool(info.get("hold_success", False)),
                    "quality_success": bool(info.get("quality_success", False)),
                    "time_to_first_reach_step": int(info.get("time_to_first_reach_step", info.get("first_reach_step", -1))),
                    "time_to_stable_hold_step": int(info.get("time_to_stable_hold_step", info.get("first_stable_hold_step", -1))),
                    "terminal_R_error": float(info.get("terminal_R_error", info.get("R_error", 0.0))),
                    "terminal_Z_error": float(info.get("terminal_Z_error", info.get("Z_error", 0.0))),
                    "terminal_Ip_error": float(info.get("terminal_Ip_error", info.get("Ip_error", 0.0))),
                    "mean_abs_action_fragment": float(np.mean(action_abs)) if action_abs else 0.0,
                }
                self.completed_episodes.append(ep)
                self.obs, self.info = self.env.reset()
                self.obs = np.asarray(self.obs, dtype=np.float32).reshape(-1)
                self.priv = self._priv(self.info)
                self.hidden = self.actor.init_hidden(1)
                self.episode_return = 0.0
                self.episode_len = 0

        episodes = self.completed_episodes
        self.completed_episodes = []
        return {
            "obs": np.asarray(obs_l, dtype=np.float32),
            "priv": np.asarray(priv_l, dtype=np.float32),
            "action": np.asarray(act_l, dtype=np.float32),
            "reward": np.asarray(rew_l, dtype=np.float32),
            "done": np.asarray(done_l, dtype=np.float32),
            "next_obs": np.asarray(nobs_l, dtype=np.float32),
            "next_priv": np.asarray(npriv_l, dtype=np.float32),
            "mask": np.asarray(mask_l, dtype=np.float32),
            "info": info_l,
            "worker_index": self.worker_index,
            "env_steps": int(env_steps),
            "fragment_mean_reward": float(np.mean(rew_l)) if rew_l else 0.0,
            "fragment_mean_abs_action": float(np.mean(action_abs)) if action_abs else 0.0,
            "episodes": episodes,
        }

    def close(self):
        try:
            self.env.close()
        except Exception:
            pass


class MpoLearner:
    def __init__(self, cfg: dict[str, Any], obs_dim: int, priv_dim: int, action_dim: int, device: str):
        self.cfg = cfg
        self.device = torch.device(device)
        m_cfg = cfg.get("model", {})
        mpo_cfg = cfg.get("mpo", {})
        self.actor = RecurrentGaussianActor(
            obs_dim,
            action_dim,
            hidden_size=int(m_cfg.get("actor_gru_hidden", 128)),
            mlp_hiddens=list(m_cfg.get("actor_mlp_hiddens", [256, 256])),
            activation=str(m_cfg.get("activation", "silu")),
            log_std_min=float(m_cfg.get("log_std_min", -5.0)),
            log_std_max=float(m_cfg.get("log_std_max", 1.0)),
            physics_blend=m_cfg.get("physics_blend", None),
        ).to(self.device)
        self.q1 = RecurrentQCritic(
            obs_dim,
            priv_dim,
            action_dim,
            hidden_size=int(m_cfg.get("critic_gru_hidden", 256)),
            mlp_hiddens=list(m_cfg.get("critic_mlp_hiddens", [512, 512])),
            activation=str(m_cfg.get("activation", "silu")),
        ).to(self.device)
        self.q2 = RecurrentQCritic(
            obs_dim,
            priv_dim,
            action_dim,
            hidden_size=int(m_cfg.get("critic_gru_hidden", 256)),
            mlp_hiddens=list(m_cfg.get("critic_mlp_hiddens", [512, 512])),
            activation=str(m_cfg.get("activation", "silu")),
        ).to(self.device)
        self.tq1 = copy.deepcopy(self.q1).to(self.device)
        self.tq2 = copy.deepcopy(self.q2).to(self.device)
        hard_update(self.tq1, self.q1)
        hard_update(self.tq2, self.q2)
        self.actor_opt = torch.optim.Adam(self.actor.parameters(), lr=float(mpo_cfg.get("actor_lr", 1e-4)))
        self.critic_opt = torch.optim.Adam(list(self.q1.parameters()) + list(self.q2.parameters()), lr=float(mpo_cfg.get("critic_lr", 3e-4)))
        self.log_eta = torch.nn.Parameter(torch.tensor(float(np.log(np.exp(float(mpo_cfg.get("eta_init", 1.0))) - 1.0)), device=self.device))
        self.eta_opt = torch.optim.Adam([self.log_eta], lr=float(mpo_cfg.get("eta_lr", 1e-3)))
        self.action_dim = int(action_dim)
        self.gamma = float(mpo_cfg.get("gamma", 0.997))
        self.tau = float(mpo_cfg.get("tau", 0.005))
        self.grad_clip = float(mpo_cfg.get("grad_clip", 10.0))
        self.num_action_samples = int(mpo_cfg.get("num_action_samples", 32))
        self.eta_epsilon = float(mpo_cfg.get("eta_epsilon", 0.1))
        self.eta_min = float(mpo_cfg.get("eta_min", 1.0e-3))
        self.kl_coeff = float(mpo_cfg.get("kl_coeff", 1.0))
        self.kl_target = float(mpo_cfg.get("kl_target", 0.02))
        self.entropy_coeff = float(mpo_cfg.get("entropy_coeff", 0.0))
        self.target_noise = float(mpo_cfg.get("target_policy_noise", 0.0))
        self.target_noise_clip = float(mpo_cfg.get("target_noise_clip", 0.3))

        # B85-stable: damp the two failure modes seen in B85-current:
        #   (1) critic/Q scale growth; (2) deterministic action saturation.
        self.critic_loss_type = str(mpo_cfg.get("critic_loss", "mse")).lower()
        self.huber_delta = float(mpo_cfg.get("huber_delta", 10.0))
        self.reward_scale = float(mpo_cfg.get("reward_scale", 1.0))
        self.reward_clip = mpo_cfg.get("reward_clip", None)
        self.target_q_clip = mpo_cfg.get("target_q_clip", None)
        self.eta_max = mpo_cfg.get("eta_max", None)
        self.actor_action_l2_coeff = float(mpo_cfg.get("actor_action_l2_coeff", 0.0))
        self.actor_action_saturation_coeff = float(mpo_cfg.get("actor_action_saturation_coeff", 0.0))
        self.actor_action_soft_limit = float(mpo_cfg.get("actor_action_soft_limit", 0.75))
        self.e_step_center_q = bool(mpo_cfg.get("e_step_center_q", True))
        self.e_step_normalize_q = bool(mpo_cfg.get("e_step_normalize_q", True))
        self.e_step_q_clip = float(mpo_cfg.get("e_step_q_clip", 8.0))

        # B86 balanced actor controls.  These are intentionally actor-side,
        # not only reward-side: B85-stable pushed actions too high, while B85c
        # clipped positive policy-loss gradients and collapsed deterministic mean
        # actions back to no-op.
        self.actor_update_every = max(1, int(mpo_cfg.get("actor_update_every", 1)))
        self.policy_loss_clip = mpo_cfg.get("policy_loss_clip", None)
        self.policy_loss_lower_clip = mpo_cfg.get("policy_loss_lower_clip", None)
        self.policy_loss_upper_clip = mpo_cfg.get("policy_loss_upper_clip", None)
        self.action_scale_default = float(mpo_cfg.get("actor_output_scale", mpo_cfg.get("actor_output_scale_init", 1.0)))
        self.action_scale_schedule = mpo_cfg.get("actor_output_scale_schedule", None)
        self.action_scale = float(self.action_scale_default)

        phys_cfg = m_cfg.get("physics_blend", {})
        self.physics_blend_alpha_default = float(phys_cfg.get("alpha", phys_cfg.get("alpha_init", 0.0)))
        self.physics_blend_alpha_schedule = phys_cfg.get("alpha_schedule", None)
        self.physics_blend_alpha = float(self.physics_blend_alpha_default)
        if hasattr(self.actor, "set_physics_blend_alpha"):
            self.actor.set_physics_blend_alpha(self.physics_blend_alpha)

        self.update_count = 0

    def set_env_steps(self, env_steps: int) -> None:
        self.action_scale = piecewise_constant_schedule(
            self.action_scale_schedule, int(env_steps), self.action_scale_default
        )
        self.physics_blend_alpha = piecewise_constant_schedule(
            self.physics_blend_alpha_schedule, int(env_steps), self.physics_blend_alpha_default
        )
        if hasattr(self.actor, "set_physics_blend_alpha"):
            self.actor.set_physics_blend_alpha(self.physics_blend_alpha)

    def _clamp_eta_(self) -> None:
        if self.eta_max is None:
            return
        eta_max = max(float(self.eta_max), self.eta_min + 1.0e-6)
        # eta = softplus(log_eta) + eta_min; inverse softplus for clamp.
        max_raw = eta_max - self.eta_min
        inv = math.log(math.expm1(max_raw)) if max_raw < 50.0 else max_raw
        with torch.no_grad():
            self.log_eta.clamp_(max=inv)

    def _apply_reward_and_target_scaling(self, reward: torch.Tensor, target_q: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        r = reward * self.reward_scale
        if self.reward_clip is not None:
            lo, hi = float(self.reward_clip[0]), float(self.reward_clip[1])
            r = torch.clamp(r, lo, hi)
        tq = target_q
        if self.target_q_clip is not None:
            lo, hi = float(self.target_q_clip[0]), float(self.target_q_clip[1])
            tq = torch.clamp(tq, lo, hi)
        return r, tq

    def _td_loss(self, pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        if self.critic_loss_type in {"huber", "smooth_l1", "smoothl1"}:
            try:
                return F.huber_loss(pred, target, reduction="none", delta=self.huber_delta)
            except TypeError:
                return F.smooth_l1_loss(pred, target, reduction="none", beta=self.huber_delta)
        return (pred - target).pow(2)

    def _prepare_e_step_q(self, q_cand: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        q = q_cand.detach()
        if self.e_step_center_q:
            q = q - q.mean(dim=-1, keepdim=True)
        if self.e_step_normalize_q:
            q = q / torch.clamp(q.std(dim=-1, keepdim=True), min=1.0e-3)
        if self.e_step_q_clip > 0.0:
            q = torch.clamp(q, -self.e_step_q_clip, self.e_step_q_clip)
        return q * mask.unsqueeze(-1)

    def actor_state_cpu(self) -> dict[str, Any]:
        return {k: v.detach().cpu() for k, v in self.actor.state_dict().items()}

    def _to_torch(self, batch: dict[str, np.ndarray]) -> dict[str, torch.Tensor]:
        return {k: torch.as_tensor(v, dtype=torch.float32, device=self.device) for k, v in batch.items()}

    def update(self, batch_np: dict[str, np.ndarray]) -> dict[str, float]:
        b = self._to_torch(batch_np)
        obs = b["obs"]
        priv = b["priv"]
        action = b["action"]
        reward = b["reward"]
        done = b["done"]
        next_obs = b["next_obs"]
        next_priv = b["next_priv"]
        mask = b["mask"]
        mask_sum = torch.clamp(mask.sum(), min=1.0)

        # Critic update.
        with torch.no_grad():
            next_action, _, _, _, _ = self.actor.sample(next_obs, deterministic=False, action_scale=self.action_scale)
            if self.target_noise > 0.0:
                noise = torch.randn_like(next_action) * self.target_noise
                noise = noise.clamp(-self.target_noise_clip, self.target_noise_clip)
                next_action = (next_action + noise).clamp(-1.0, 1.0)
            target_q = torch.min(self.tq1(next_obs, next_priv, next_action), self.tq2(next_obs, next_priv, next_action))
            scaled_reward, target_q = self._apply_reward_and_target_scaling(reward, target_q)
            y = scaled_reward + self.gamma * (1.0 - done) * target_q
            if self.target_q_clip is not None:
                lo, hi = float(self.target_q_clip[0]), float(self.target_q_clip[1])
                y = torch.clamp(y, lo, hi)
        q1 = self.q1(obs, priv, action)
        q2 = self.q2(obs, priv, action)
        critic_loss = ((self._td_loss(q1, y) + self._td_loss(q2, y)) * mask).sum() / mask_sum
        self.critic_opt.zero_grad(set_to_none=True)
        critic_loss.backward()
        torch.nn.utils.clip_grad_norm_(list(self.q1.parameters()) + list(self.q2.parameters()), self.grad_clip)
        self.critic_opt.step()

        # MPO E-step temperature update and M-step actor update.
        with torch.no_grad():
            old_dist, old_mean, old_log_std, _ = self.actor.distribution(obs)
            # Candidate pre-tanh samples: [B,T,K,A]
            B, T, latent_dim = old_mean.shape
            eps = torch.randn(B, T, self.num_action_samples, latent_dim, device=self.device)
            old_std = old_log_std.exp().unsqueeze(2)
            pre_tanh = old_mean.unsqueeze(2) + old_std * eps
            cand_action = self.actor.action_from_pre_tanh(pre_tanh, action_scale=self.action_scale)
            obs_rep = obs.unsqueeze(2).expand(B, T, self.num_action_samples, obs.shape[-1]).permute(0, 2, 1, 3).reshape(B * self.num_action_samples, T, obs.shape[-1])
            priv_rep = priv.unsqueeze(2).expand(B, T, self.num_action_samples, priv.shape[-1]).permute(0, 2, 1, 3).reshape(B * self.num_action_samples, T, priv.shape[-1])
            action_dim = cand_action.shape[-1]
            act_rep = cand_action.permute(0, 2, 1, 3).reshape(B * self.num_action_samples, T, action_dim)
            q_cand = torch.min(self.q1(obs_rep, priv_rep, act_rep), self.q2(obs_rep, priv_rep, act_rep))
            q_cand = q_cand.reshape(B, self.num_action_samples, T).permute(0, 2, 1)  # [B,T,K]
            q_cand = q_cand * mask.unsqueeze(-1)

        eta = F.softplus(self.log_eta) + self.eta_min
        q_e = self._prepare_e_step_q(q_cand, mask)
        # Dual objective for eta: eta*eps + eta*E[logmeanexp(A/eta)].
        # B85-stable uses centered/normalized candidate advantages A to prevent
        # absolute Q-scale growth from driving eta and actor updates into a saturated policy.
        lse = torch.logsumexp(q_e / eta, dim=-1) - np.log(self.num_action_samples)
        eta_loss = (eta * self.eta_epsilon + eta * ((lse * mask).sum() / mask_sum))
        self.eta_opt.zero_grad(set_to_none=True)
        eta_loss.backward()
        torch.nn.utils.clip_grad_norm_([self.log_eta], self.grad_clip)
        self.eta_opt.step()
        self._clamp_eta_()
        eta_used = (F.softplus(self.log_eta) + self.eta_min).detach()

        with torch.no_grad():
            weights = torch.softmax(q_e / eta_used, dim=-1)  # [B,T,K]
            pre_tanh_detached = pre_tanh.detach()
            old_mean_detached = old_mean.detach()
            old_log_std_detached = old_log_std.detach()

        _, new_mean, new_log_std, _ = self.actor.distribution(obs)
        new_mean_k = new_mean.unsqueeze(2).expand_as(pre_tanh_detached)
        new_log_std_k = new_log_std.unsqueeze(2).expand_as(pre_tanh_detached)
        logp_new = tanh_gaussian_log_prob(pre_tanh_detached, new_mean_k, new_log_std_k)  # [B,T,K]
        policy_loss_raw = -((weights * logp_new).sum(dim=-1) * mask).sum() / mask_sum
        policy_loss_used = bounded_policy_loss(policy_loss_raw, self.policy_loss_clip, self.policy_loss_lower_clip, self.policy_loss_upper_clip)
        kl = gaussian_kl(old_mean_detached, old_log_std_detached, new_mean, new_log_std)
        kl_mean = (kl * mask).sum() / mask_sum
        # Penalize only KL above target, leaving small useful updates alone.
        kl_penalty = self.kl_coeff * torch.relu(kl_mean - self.kl_target).pow(2)
        entropy = (0.5 + 0.5 * np.log(2.0 * np.pi) + new_log_std).sum(dim=-1)
        entropy_mean = (entropy * mask).sum() / mask_sum
        mean_components = self.actor.action_components_from_pre_tanh(new_mean)
        mean_action_unscaled = mean_components["blended_action"]
        mean_action = mean_action_unscaled * self.action_scale
        raw_mean_action = mean_components["raw_action"] * self.action_scale
        phys_mean_action = mean_components["physics_action"] * self.action_scale
        mode_coeff = mean_components["mode_coeff"]
        actor_action_l2 = self.actor_action_l2_coeff * ((mean_action.pow(2).mean(dim=-1) * mask).sum() / mask_sum)
        sat_excess = torch.relu(mean_action.abs() - self.actor_action_soft_limit)
        actor_action_saturation = self.actor_action_saturation_coeff * ((sat_excess.pow(2).mean(dim=-1) * mask).sum() / mask_sum)
        actor_loss = policy_loss_used + kl_penalty - self.entropy_coeff * entropy_mean + actor_action_l2 + actor_action_saturation
        self.update_count += 1
        actor_update_applied = (self.update_count % self.actor_update_every == 0)
        if actor_update_applied:
            self.actor_opt.zero_grad(set_to_none=True)
            actor_loss.backward()
            torch.nn.utils.clip_grad_norm_(self.actor.parameters(), self.grad_clip)
            self.actor_opt.step()

        soft_update(self.tq1, self.q1, self.tau)
        soft_update(self.tq2, self.q2, self.tau)
        with torch.no_grad():
            q_mean = ((q1 + q2) * 0.5 * mask).sum() / mask_sum
            target_mean = (y * mask).sum() / mask_sum
        return {
            "critic_loss": float(critic_loss.detach().cpu()),
            "actor_loss": float(actor_loss.detach().cpu()),
            "policy_loss_raw": float(policy_loss_raw.detach().cpu()),
            "policy_loss_used": float(policy_loss_used.detach().cpu()),
            "policy_loss_lower_clip": float(self.policy_loss_lower_clip) if self.policy_loss_lower_clip is not None else float("nan"),
            "policy_loss_upper_clip": float(self.policy_loss_upper_clip) if self.policy_loss_upper_clip is not None else float("nan"),
            "kl_mean": float(kl_mean.detach().cpu()),
            "entropy_mean": float(entropy_mean.detach().cpu()),
            "eta": float((F.softplus(self.log_eta) + self.eta_min).detach().cpu()),
            "eta_loss": float(eta_loss.detach().cpu()),
            "q_mean": float(q_mean.detach().cpu()),
            "target_q_mean": float(target_mean.detach().cpu()),
            "candidate_q_mean": float(((q_cand.detach() * mask.unsqueeze(-1)).sum() / (mask_sum * self.num_action_samples)).cpu()),
            "candidate_adv_mean": float(((q_e.detach() * mask.unsqueeze(-1)).sum() / (mask_sum * self.num_action_samples)).cpu()),
            "candidate_adv_std": float(torch.std(q_e.detach()[mask.unsqueeze(-1).expand_as(q_e) > 0.5]).cpu()) if torch.any(mask > 0.5) else 0.0,
            "actor_action_l2_penalty": float(actor_action_l2.detach().cpu()),
            "actor_action_saturation_penalty": float(actor_action_saturation.detach().cpu()),
            "actor_mean_abs_action": float(((mean_action.abs().mean(dim=-1) * mask).sum() / mask_sum).detach().cpu()),
            "actor_raw_mean_abs_action": float(((raw_mean_action.abs().mean(dim=-1) * mask).sum() / mask_sum).detach().cpu()),
            "actor_physics_mean_abs_action": float(((phys_mean_action.abs().mean(dim=-1) * mask).sum() / mask_sum).detach().cpu()),
            "actor_mode_coeff_mean_abs": float(((mode_coeff.abs().mean(dim=-1) * mask).sum() / mask_sum).detach().cpu()) if mode_coeff.numel() > 0 else 0.0,
            "actor_action_scale": float(self.action_scale),
            "actor_physics_blend_alpha": float(self.physics_blend_alpha),
            "actor_update_applied": float(actor_update_applied),
            "critic_loss_type": 1.0 if self.critic_loss_type in {"huber", "smooth_l1", "smoothl1"} else 0.0,
        }

    def save_checkpoint(self, path: Path, stats: dict[str, Any]) -> None:
        path.mkdir(parents=True, exist_ok=True)
        payload = {
            "actor": self.actor.state_dict(),
            "q1": self.q1.state_dict(),
            "q2": self.q2.state_dict(),
            "tq1": self.tq1.state_dict(),
            "tq2": self.tq2.state_dict(),
            "actor_opt": self.actor_opt.state_dict(),
            "critic_opt": self.critic_opt.state_dict(),
            "eta_opt": self.eta_opt.state_dict(),
            "log_eta": self.log_eta.detach().cpu(),
            "action_scale": float(self.action_scale),
            "physics_blend_alpha": float(self.physics_blend_alpha),
            "update_count": int(self.update_count),
            "stats": json_safe(stats),
            "config": json_safe(self.cfg),
        }
        torch.save(payload, path / "mpo_checkpoint.pt")
        with open(path / "checkpoint_info.json", "w", encoding="utf-8") as f:
            json.dump(json_safe(stats), f, indent=2, ensure_ascii=False)


def infer_spaces(cfg: dict[str, Any]) -> tuple[int, int, int]:
    env_cfg = {
        "backend": cfg.get("env", {}).get("backend", "native"),
        "train_config": cfg["train_config_resolved"],
        "seed": int(cfg.get("seed", 42)),
        "worker_index": 0,
        "vector_index": 0,
        "num_workers_for_curriculum": int(cfg.get("parallel", {}).get("num_tsc_workers", 1)),
        "finite_guard": cfg.get("env", {}).get("finite_guard", {"enabled": True}),
    }
    env = RllibTscRzipEnv(env_cfg)
    obs, info = env.reset(seed=int(cfg.get("seed", 42)))
    obs_dim = int(np.prod(env.observation_space.shape))
    action_dim = int(np.prod(env.action_space.shape))
    p_cfg = cfg.get("privileged", {})
    priv_dim = privileged_dim(p_cfg.get("keys"), include_currents=bool(p_cfg.get("include_currents", True)))
    env.close()
    return obs_dim, priv_dim, action_dim


def build_run_dirs(cfg: dict[str, Any], config_path: Path) -> tuple[Path, Path, str]:
    stamp = now_stamp()
    run_name = str(cfg.get("run_name", config_path.stem)) + "_" + stamp
    log_root = Path(str(cfg.get("log_root", "ray_results"))).expanduser()
    ckpt_root = Path(str(cfg.get("checkpoint_root", "mpo_checkpoints"))).expanduser()
    run_dir = log_root / run_name
    ckpt_dir = ckpt_root / run_name
    run_dir.mkdir(parents=True, exist_ok=True)
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    return run_dir, ckpt_dir, run_name


def summarize_episodes(episodes: list[dict[str, Any]]) -> dict[str, Any]:
    if not episodes:
        return {}
    out = {"episodes_completed": len(episodes)}
    for key in [
        "episode_return",
        "episode_len",
        "hold_success",
        "quality_success",
        "time_to_first_reach_step",
        "time_to_stable_hold_step",
        "terminal_R_error",
        "terminal_Z_error",
        "terminal_Ip_error",
        "mean_abs_action_fragment",
    ]:
        vals = []
        for ep in episodes:
            v = ep.get(key)
            if isinstance(v, bool):
                vals.append(float(v))
            elif isinstance(v, (int, float)) and np.isfinite(v):
                vals.append(float(v))
        if vals:
            out[f"episode_{key}_mean"] = float(np.mean(vals))
    return out


def force_stage_for_eval(train_cfg: dict[str, Any], stage_name: str | None) -> dict[str, Any]:
    if not stage_name or stage_name == "default":
        return json.loads(json.dumps(train_cfg))
    cfg = json.loads(json.dumps(train_cfg))
    cur = cfg.get("curriculum", {}).get("env_attributes", {})
    stages = list(cur.get("stages", []))
    aliases = {"final": "stage3", "strict": "stage3"}
    target = aliases.get(str(stage_name), str(stage_name))
    match = None
    for st in stages:
        name = str(st.get("name", ""))
        if target == name or name.startswith(target) or target in name:
            match = st
    if match is None:
        raise ValueError(f"Cannot find eval stage {stage_name!r} in train_config curriculum")
    cfg.setdefault("curriculum", {}).setdefault("env_attributes", {})["enabled"] = False
    cfg.setdefault("reward", {}).update(dict(match.get("env_params", {})))
    return cfg


def run_online_policy_probe(
    cfg: dict[str, Any],
    learner: MpoLearner,
    *,
    iteration: int,
    env_steps: int,
    seed: int,
    stage: str,
    deterministic: bool,
    prefix: str,
) -> dict[str, Any]:
    """Run one final-stage episode in-process for online diagnosis.

    Deterministic probe is the deployable policy check.  Optional stochastic
    probe helps distinguish "the distribution can sometimes find useful
    actions" from "the deterministic mean is stuck/no-op".
    """
    train_cfg = force_stage_for_eval(cfg["train_config_resolved"], stage)
    env_cfg = {
        "backend": cfg.get("env", {}).get("backend", "native"),
        "train_config": train_cfg,
        "seed": int(seed),
        "worker_index": int(cfg.get("parallel", {}).get("num_tsc_workers", 192)) + 10000 + int(iteration) + (0 if deterministic else 5000),
        "vector_index": 0,
        "num_workers_for_curriculum": 1,
        "finite_guard": cfg.get("env", {}).get("finite_guard", {"enabled": True}),
    }
    env = RllibTscRzipEnv(env_cfg)
    obs, info = env.reset(seed=int(seed))
    obs = np.asarray(obs, dtype=np.float32).reshape(-1)
    hidden = learner.actor.init_hidden(1, device=learner.device)
    total = 0.0
    steps = 0
    action_abs: list[float] = []
    max_abs = 0.0
    last_info = dict(info or {})
    learner.actor.eval()
    try:
        done = False
        while not done:
            with torch.no_grad():
                a, hidden = learner.actor.act_step(
                    torch.as_tensor(obs, dtype=torch.float32, device=learner.device),
                    hidden,
                    deterministic=bool(deterministic),
                    action_scale=float(learner.action_scale),
                )
            action = a.detach().cpu().numpy().reshape(-1).astype(np.float32)
            next_obs, reward, terminated, truncated, info = env.step(action)
            done = bool(terminated or truncated)
            total += float(reward)
            steps += 1
            action_abs.append(float(np.mean(np.abs(action))))
            max_abs = max(max_abs, float(np.max(np.abs(action))))
            obs = np.asarray(next_obs, dtype=np.float32).reshape(-1)
            last_info = dict(info or {})
    finally:
        try:
            env.close()
        except Exception:
            pass

    def f(key: str, fallback: str | None = None, default: float = 0.0) -> float:
        try:
            if key in last_info:
                return float(last_info.get(key))
            if fallback is not None:
                return float(last_info.get(fallback, default))
            return float(default)
        except Exception:
            return float(default)

    r_err = f("terminal_R_error", "R_error")
    z_err = f("terminal_Z_error", "Z_error")
    ip_err = f("terminal_Ip_error", "Ip_error")
    mean_action = float(np.mean(action_abs)) if action_abs else 0.0
    esc = cfg.get("early_stop", {})
    score_r_ref = max(float(esc.get("score_r_ref", 0.05)), 1.0e-12)
    score_z_ref = max(float(esc.get("score_z_ref", 0.05)), 1.0e-12)
    score_ip_ref = max(float(esc.get("score_ip_ref", 3000.0)), 1.0e-12)
    score_ip_weight = float(esc.get("score_ip_weight", 0.2))
    score_action_weight = float(esc.get("score_action_weight", 0.2))
    shape_score = abs(r_err) / score_r_ref + abs(z_err) / score_z_ref
    ip_score = abs(ip_err) / score_ip_ref
    relaxed_score = shape_score + score_ip_weight * ip_score + score_action_weight * mean_action

    return {
        f"{prefix}_iteration": int(iteration),
        f"{prefix}_env_steps": int(env_steps),
        f"{prefix}_return": float(total),
        f"{prefix}_len": int(steps),
        f"{prefix}_hold_success": float(bool(last_info.get("hold_success", False))),
        f"{prefix}_quality_success": float(bool(last_info.get("quality_success", False))),
        f"{prefix}_first_reach": int(last_info.get("time_to_first_reach_step", last_info.get("first_reach_step", -1))),
        f"{prefix}_stable_hold": int(last_info.get("time_to_stable_hold_step", last_info.get("first_stable_hold_step", -1))),
        f"{prefix}_terminal_R_error": float(r_err),
        f"{prefix}_terminal_Z_error": float(z_err),
        f"{prefix}_terminal_Ip_error": float(ip_err),
        f"{prefix}_terminal_velocity_norm": f("terminal_velocity_norm", "velocity_norm"),
        f"{prefix}_mean_abs_action": float(mean_action),
        f"{prefix}_max_abs_action": float(max_abs),
        f"{prefix}_shape_score": float(shape_score),
        f"{prefix}_ip_score": float(ip_score),
        f"{prefix}_relaxed_score": float(relaxed_score),
        f"{prefix}_action_scale": float(learner.action_scale),
        f"{prefix}_physics_blend_alpha": float(getattr(learner, "physics_blend_alpha", 0.0)),
    }


def run_online_deterministic_probe(
    cfg: dict[str, Any], learner: MpoLearner, *, iteration: int, env_steps: int, seed: int, stage: str
) -> dict[str, Any]:
    return run_online_policy_probe(
        cfg, learner, iteration=iteration, env_steps=env_steps, seed=seed,
        stage=stage, deterministic=True, prefix="eval_final_det"
    )


def run_online_stochastic_probe(
    cfg: dict[str, Any], learner: MpoLearner, *, iteration: int, env_steps: int, seed: int, stage: str
) -> dict[str, Any]:
    return run_online_policy_probe(
        cfg, learner, iteration=iteration, env_steps=env_steps, seed=seed,
        stage=stage, deterministic=False, prefix="eval_final_stoch"
    )


def should_early_stop_from_probe(cfg: dict[str, Any], iteration: int, probe: dict[str, Any], bad_probe_count: int) -> tuple[bool, int, str]:
    esc = cfg.get("early_stop", {})
    if not bool(esc.get("enabled", False)):
        return False, bad_probe_count, "disabled"
    if int(iteration) < int(esc.get("min_iteration", 0)):
        return False, bad_probe_count, "below_min_iteration"

    first_reach = int(probe.get("eval_final_det_first_reach", -1))
    hold_success = float(probe.get("eval_final_det_hold_success", 0.0)) > 0.0
    ma = float(probe.get("eval_final_det_mean_abs_action", 0.0))
    r = float(probe.get("eval_final_det_terminal_R_error", 0.0))
    z = float(probe.get("eval_final_det_terminal_Z_error", 0.0))
    ip = float(probe.get("eval_final_det_terminal_Ip_error", 0.0))
    shape_score = float(probe.get("eval_final_det_shape_score", abs(r) / max(float(esc.get("score_r_ref", 0.05)), 1e-12) + abs(z) / max(float(esc.get("score_z_ref", 0.05)), 1e-12)))
    relaxed_score = float(probe.get("eval_final_det_relaxed_score", shape_score + float(esc.get("score_ip_weight", 0.2)) * abs(ip) / max(float(esc.get("score_ip_ref", 3000.0)), 1e-12)))

    bad = False
    reasons: list[str] = []
    if not hold_success:
        if first_reach < 0:
            if bool(esc.get("bad_if_no_first_reach_after_min_iter", False)):
                bad = True
                reasons.append("no_first_reach")
            thr_hi = esc.get("bad_if_no_first_reach_and_mean_action_gt", None)
            if thr_hi is not None and ma > float(thr_hi):
                bad = True
                reasons.append(f"no_first_reach_and_mean_action>{float(thr_hi)}")
            thr_lo = esc.get("bad_if_no_first_reach_and_mean_action_lt", None)
            if thr_lo is not None and ma < float(thr_lo):
                bad = True
                reasons.append(f"no_first_reach_and_mean_action<{float(thr_lo)}")
        z_thr = esc.get("bad_if_z_abs_gt", None)
        if z_thr is not None and abs(z) > float(z_thr):
            bad = True
            reasons.append(f"z_abs>{float(z_thr)}")
        r_neg_thr = esc.get("bad_if_r_error_lt", None)
        if r_neg_thr is not None and r < float(r_neg_thr):
            bad = True
            reasons.append(f"r_error<{float(r_neg_thr)}")
        shape_thr = esc.get("bad_if_shape_score_gt", None)
        if shape_thr is not None and shape_score > float(shape_thr):
            bad = True
            reasons.append(f"shape_score>{float(shape_thr)}")
        relaxed_thr = esc.get("bad_if_relaxed_score_gt", None)
        if relaxed_thr is not None and relaxed_score > float(relaxed_thr):
            bad = True
            reasons.append(f"relaxed_score>{float(relaxed_thr)}")

    if bad:
        bad_probe_count += 1
    else:
        bad_probe_count = 0
    req = int(esc.get("require_consecutive_bad_probes", 2))
    if bad_probe_count >= req:
        return True, bad_probe_count, ";".join(reasons) or "bad_probe"
    return False, bad_probe_count, ";".join(reasons) if bad else "ok"


def main():
    ap = argparse.ArgumentParser(description="Train recurrent MPO for TSC R/Z/Ip control (B88 z-recovery relaxed-Ip-lite compatible).")
    ap.add_argument("--config", required=True, help="MPO training config JSON.")
    ap.add_argument("--override", default=None, help="Optional JSON override.")
    ap.add_argument("--resume", default=None, help="Optional checkpoint directory containing mpo_checkpoint.pt.")
    args = ap.parse_args()

    cfg_path = Path(args.config)
    cfg = load_merged_json(cfg_path, Path(args.override) if args.override else None)

    run_dir, ckpt_dir, run_name = build_run_dirs(cfg, cfg_path)
    cfg["resolved_run_name"] = run_name

    # Resolve placeholders in both the MPO train config and the nested TSC env config.
    # This fixes paths like {TSC_ALL_ROOT}/tsc_simulation/TSC-PCS/gotsc.
    macros = default_macros(run_name)
    os.environ.setdefault("TSC_ALL_ROOT", macros["TSC_ALL_ROOT"])
    train_cfg_path = resolve_path_maybe_relative(expand_macros(str(cfg.get("train_config", "configs/train_b83_fixed_target_1ms.json")), macros))
    train_cfg = expand_macros(load_json(train_cfg_path), macros)
    resolved_cfg_dir = run_dir / "resolved_configs"
    train_cfg = resolve_tsc_config_file(train_cfg, out_dir=resolved_cfg_dir, macros=macros)
    cfg["train_config_resolved"] = train_cfg

    with open(resolved_cfg_dir / "train_config.resolved.json", "w", encoding="utf-8") as f:
        json.dump(json_safe(train_cfg), f, indent=2, ensure_ascii=False)
    with open(run_dir / "mpo_config.resolved.json", "w", encoding="utf-8") as f:
        json.dump(json_safe(cfg), f, indent=2, ensure_ascii=False)

    # Short Ray temp dir to avoid AF_UNIX socket path length issues.
    uid = os.getuid() if hasattr(os, "getuid") else 0
    ray_tmp = Path(os.environ.get("RAY_TMPDIR", f"/tmp/rm{uid}"))
    ray_tmp.mkdir(parents=True, exist_ok=True)
    os.environ["RAY_TMPDIR"] = str(ray_tmp)
    os.environ["TMPDIR"] = str(ray_tmp / "tmp")
    Path(os.environ["TMPDIR"]).mkdir(parents=True, exist_ok=True)

    par = cfg.get("parallel", {})
    ray_num_cpus = int(par.get("ray_num_cpus", min(available_cpu_count(), 200)))
    object_store_memory = int(par.get("object_store_memory", 8 * 1024**3))
    print("========== B85 MPO Ray init ==========")
    print(f"run_name         = {run_name}")
    print(f"ray_num_cpus     = {ray_num_cpus}")
    print(f"RAY_TMPDIR       = {os.environ['RAY_TMPDIR']}")
    print(f"num_tsc_workers  = {par.get('num_tsc_workers')}")
    print("======================================")
    ray.init(
        address=par.get("ray_address", None),
        num_cpus=ray_num_cpus if par.get("ray_address", None) is None else None,
        include_dashboard=bool(par.get("include_dashboard", False)),
        ignore_reinit_error=True,
        _temp_dir=str(ray_tmp),
        object_store_memory=object_store_memory,
        runtime_env={"env_vars": ray_worker_env_vars()},
    )

    obs_dim, priv_dim, action_dim = infer_spaces(cfg)
    device = "cuda" if (torch.cuda.is_available() and int(cfg.get("learner", {}).get("num_gpus", 0)) > 0) else "cpu"
    learner = MpoLearner(cfg, obs_dim, priv_dim, action_dim, device=device)
    learner.set_env_steps(0)
    if args.resume:
        payload = torch.load(Path(args.resume) / "mpo_checkpoint.pt", map_location=device)
        learner.actor.load_state_dict(payload["actor"])
        learner.q1.load_state_dict(payload["q1"])
        learner.q2.load_state_dict(payload["q2"])
        learner.tq1.load_state_dict(payload.get("tq1", payload["q1"]))
        learner.tq2.load_state_dict(payload.get("tq2", payload["q2"]))
        if "actor_opt" in payload:
            try:
                learner.actor_opt.load_state_dict(payload["actor_opt"])
                learner.critic_opt.load_state_dict(payload["critic_opt"])
                learner.eta_opt.load_state_dict(payload["eta_opt"])
            except Exception as exc:
                print(f"Warning: optimizer state not restored cleanly: {exc}")
        if "log_eta" in payload:
            with torch.no_grad():
                learner.log_eta.copy_(payload["log_eta"].to(device))
        learner.update_count = int(payload.get("update_count", 0))
        print(f"Resumed MPO checkpoint: {args.resume}")

    replay_cfg = cfg.get("replay", {})
    replay = SequenceReplayBuffer(capacity_fragments=int(replay_cfg.get("capacity_fragments", 100000)), seed=int(cfg.get("seed", 42)))
    num_workers = int(par.get("num_tsc_workers", 192))
    fragment_steps = int(par.get("fragment_steps", 32))
    rollout_deterministic = bool(par.get("rollout_deterministic", False))
    workers = [MpoRolloutWorker.options(num_cpus=float(par.get("num_cpus_per_tsc_worker", 1))).remote(i, cfg, learner.actor_state_cpu()) for i in range(num_workers)]
    ray.get([w.set_action_scale.remote(float(learner.action_scale)) for w in workers])

    stop_env_steps = int(cfg.get("stop_env_steps", 5_000_000))
    warmup_steps = int(cfg.get("mpo", {}).get("warmup_steps", 100_000))
    batch_size = int(cfg.get("mpo", {}).get("batch_size", 256))
    seq_len = int(cfg.get("mpo", {}).get("sequence_len", 32))
    updates_per_iter = int(cfg.get("mpo", {}).get("updates_per_iter", 64))
    checkpoint_every_iters = int(cfg.get("checkpoint_every_iters", 25))
    probe_cfg = cfg.get("deterministic_probe", {})
    probe_enabled = bool(probe_cfg.get("enabled", False))
    probe_every_iters = int(probe_cfg.get("every_iters", checkpoint_every_iters if checkpoint_every_iters > 0 else 25))
    probe_stage = str(probe_cfg.get("eval_stage", "final"))
    probe_seed = int(probe_cfg.get("seed", 12345))
    stoch_probe_cfg = cfg.get("stochastic_probe", {})
    stoch_probe_enabled = bool(stoch_probe_cfg.get("enabled", False))
    stoch_probe_every_iters = int(stoch_probe_cfg.get("every_iters", probe_every_iters))
    stoch_probe_stage = str(stoch_probe_cfg.get("eval_stage", probe_stage))
    stoch_probe_seed = int(stoch_probe_cfg.get("seed", probe_seed + 1000))
    sync_every_iters = int(cfg.get("parallel", {}).get("actor_sync_interval_iters", 1))
    results_path = run_dir / "train_results.jsonl"
    csv_path = run_dir / "train_results.csv"
    csv_fields = None
    total_steps = 0
    iteration = 0
    start_time = time.time()
    pending = {w.rollout.remote(fragment_steps, rollout_deterministic): w for w in workers}
    last_actor_state = learner.actor_state_cpu()
    bad_probe_count = 0

    try:
        while total_steps < stop_env_steps:
            iteration += 1
            iter_t0 = time.time()
            # Collect one fragment from every worker per iteration.
            episodes: list[dict[str, Any]] = []
            frag_rewards = []
            frag_actions = []
            for _ in range(num_workers):
                ready, _ = ray.wait(list(pending.keys()), num_returns=1, timeout=float(par.get("sample_timeout_s", 3600.0)))
                if not ready:
                    raise TimeoutError("Timed out waiting for rollout fragment")
                ref = ready[0]
                w = pending.pop(ref)
                data = ray.get(ref)
                replay.add_from_dict(data)
                total_steps += int(data.get("env_steps", 0))
                frag_rewards.append(float(data.get("fragment_mean_reward", 0.0)))
                frag_actions.append(float(data.get("fragment_mean_abs_action", 0.0)))
                episodes.extend(list(data.get("episodes", [])))
                pending[w.rollout.remote(fragment_steps, rollout_deterministic)] = w

            losses = []
            learner.set_env_steps(total_steps)
            if total_steps >= warmup_steps and replay.can_sample(batch_size, seq_len):
                for _ in range(updates_per_iter):
                    batch = replay.sample(batch_size=batch_size, seq_len=seq_len)
                    losses.append(learner.update(batch))
                if iteration % sync_every_iters == 0:
                    last_actor_state = learner.actor_state_cpu()
                    ray.get([w.set_actor_weights.remote(last_actor_state, float(learner.action_scale), float(learner.physics_blend_alpha)) for w in workers])
            elif iteration % sync_every_iters == 0:
                # Keep rollout workers' hard action scale schedule synchronized even during warmup.
                ray.get([w.set_action_scale.remote(float(learner.action_scale), float(learner.physics_blend_alpha)) for w in workers])

            loss_mean = {}
            if losses:
                for k in losses[0].keys():
                    loss_mean[k] = float(np.mean([x[k] for x in losses if k in x]))

            ep_summary = summarize_episodes(episodes)
            elapsed = time.time() - start_time
            result = {
                "training_iteration": iteration,
                "env_steps": int(total_steps),
                "time_total_s": float(elapsed),
                "time_this_iter_s": float(time.time() - iter_t0),
                "env_steps_per_s_total": float(total_steps / max(elapsed, 1.0e-9)),
                "fragment_mean_reward": float(np.mean(frag_rewards)) if frag_rewards else 0.0,
                "fragment_mean_abs_action": float(np.mean(frag_actions)) if frag_actions else 0.0,
                "updates_this_iter": int(len(losses)),
                "actor_action_scale": float(learner.action_scale),
                "actor_physics_blend_alpha": float(learner.physics_blend_alpha),
                **{f"learner/{k}": v for k, v in loss_mean.items()},
                **{f"replay/{k}": v for k, v in replay.stats().items()},
                **ep_summary,
            }
            stop_now = False
            probe_for_early_stop = None
            if probe_enabled and probe_every_iters > 0 and iteration % probe_every_iters == 0:
                try:
                    probe = run_online_deterministic_probe(
                        cfg, learner, iteration=iteration, env_steps=total_steps,
                        seed=probe_seed, stage=probe_stage
                    )
                    probe_for_early_stop = probe
                    result.update(probe)
                except Exception as exc:
                    result["eval_final_det_error"] = repr(exc)
            if stoch_probe_enabled and stoch_probe_every_iters > 0 and iteration % stoch_probe_every_iters == 0:
                try:
                    stoch_probe = run_online_stochastic_probe(
                        cfg, learner, iteration=iteration, env_steps=total_steps,
                        seed=stoch_probe_seed + iteration, stage=stoch_probe_stage
                    )
                    result.update(stoch_probe)
                except Exception as exc:
                    result["eval_final_stoch_error"] = repr(exc)
            if probe_for_early_stop is not None:
                stop_now, bad_probe_count, reason = should_early_stop_from_probe(cfg, iteration, probe_for_early_stop, bad_probe_count)
                result["early_stop_bad_probe_count"] = int(bad_probe_count)
                result["early_stop_reason"] = str(reason)
                result["early_stop_triggered"] = bool(stop_now)
            with open(results_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(json_safe(result), ensure_ascii=False) + "\n")
            if csv_fields is None:
                csv_fields = list(result.keys())
                with open(csv_path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=csv_fields, extrasaction="ignore")
                    writer.writeheader()
                    writer.writerow(result)
            else:
                with open(csv_path, "a", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=csv_fields, extrasaction="ignore")
                    writer.writerow(result)

            print(json.dumps(json_safe(result), ensure_ascii=False), flush=True)
            if checkpoint_every_iters > 0 and iteration % checkpoint_every_iters == 0:
                learner.save_checkpoint(ckpt_dir / f"iter_{iteration:06d}", result)
            if bool(result.get("early_stop_triggered", False)):
                print(f"MPO early stop triggered at iter={iteration}: {result.get('early_stop_reason')}", flush=True)
                break
            if total_steps >= stop_env_steps:
                break
    finally:
        try:
            ray.get([w.close.remote() for w in workers], timeout=60)
        except Exception:
            pass
        learner.save_checkpoint(ckpt_dir / "final", {"training_iteration": iteration, "env_steps": total_steps, "time_total_s": time.time() - start_time})
        with open(run_dir / "disk_health_latest.json", "w", encoding="utf-8") as f:
            json.dump(disk_health_report([run_dir, ckpt_dir, Path(os.environ["RAY_TMPDIR"])]), f, indent=2)
        ray.shutdown()

    print(f"MPO training finished. run_dir={run_dir} checkpoint_dir={ckpt_dir}")


if __name__ == "__main__":
    main()
