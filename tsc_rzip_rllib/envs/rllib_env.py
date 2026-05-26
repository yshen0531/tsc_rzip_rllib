from __future__ import annotations

import os
from typing import Any

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from tsc_rzip_rllib.envs.factory import make_tsc_rzip_env
from tsc_rzip_rllib.envs.mock_rzip_env import MockRzipEnv


def _clamp_worker_threads() -> None:
    """Best-effort per-Ray-worker numerical thread clamp.

    The launcher exports OMP/MKL/OPENBLAS/TORCH limits before Ray starts,
    but Ray workers may import Torch/Numpy in fresh processes.  Calling this
    early inside each EnvRunner keeps rollout workers from multiplying CPU
    threads per TSC instance.
    """
    for key in [
        "OMP_NUM_THREADS",
        "MKL_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
        "TORCH_NUM_THREADS",
        "TORCH_NUM_INTEROP_THREADS",
        "VECLIB_MAXIMUM_THREADS",
        "BLIS_NUM_THREADS",
        "RAYON_NUM_THREADS",
    ]:
        os.environ.setdefault(key, "1")
    try:
        import torch

        torch.set_num_threads(1)
        torch.set_num_interop_threads(1)
    except Exception:
        pass


class RllibTscRzipEnv(gym.Env):
    """RLlib-facing env wrapper.

    Responsibilities:
      * select mock/native backend;
      * assign a unique worker_id for isolated TSC workspaces;
      * apply hold-success curriculum;
      * guard obs/reward/action against NaN/Inf before they enter RLlib.
    """

    metadata = {"render_modes": []}

    def __init__(self, env_config: dict[str, Any]):
        super().__init__()
        _clamp_worker_threads()
        self.env_config = dict(env_config)
        self.backend = str(self.env_config.get("backend", "native")).lower()
        self.worker_index = int(getattr(env_config, "worker_index", self.env_config.get("worker_index", 0)))
        self.vector_index = int(getattr(env_config, "vector_index", self.env_config.get("vector_index", 0)))
        self.seed_base = int(self.env_config.get("seed", 42))
        self.local_env_steps = 0
        self.episode_idx = 0
        self.curriculum_stage_index = -1
        self.curriculum_stage_name = ""
        self.curriculum_progress_steps = 0
        self.curriculum_unit = "local_env_steps"
        self.curriculum_num_workers = int(self.env_config.get("num_workers_for_curriculum", 1) or 1)

        guard_cfg = dict(self.env_config.get("finite_guard", {}))
        self.enable_finite_guard = bool(guard_cfg.get("enabled", True))
        self.nonfinite_penalty = float(guard_cfg.get("nonfinite_penalty", -1.0e4))
        self.terminate_on_nonfinite = bool(guard_cfg.get("terminate_on_nonfinite", True))

        worker_id = self.env_config.get("worker_id")
        if worker_id is None:
            worker_id = f"ray_w{self.worker_index:04d}_v{self.vector_index:03d}_pid{os.getpid()}"
        self.worker_id = str(worker_id)

        if self.backend == "mock":
            mock_cfg = dict(self.env_config.get("mock_config", {}))
            mock_cfg.setdefault("seed", self.seed_base + 1000 * self.worker_index + self.vector_index)
            self.env = MockRzipEnv(mock_cfg)
            self._base_hold = {}
        elif self.backend == "native":
            train_cfg = dict(self.env_config["train_config"])
            self.env = make_tsc_rzip_env(
                train_cfg,
                worker_id=self.worker_id,
                seed=self.seed_base + 1000 * self.worker_index + self.vector_index,
            )
            self._base_hold = {
                "hold_success_r_tol": float(self.env.hold_success_r_tol),
                "hold_success_z_tol": float(self.env.hold_success_z_tol),
                "hold_success_ip_tol": float(self.env.hold_success_ip_tol),
                "hold_eval_window_steps": int(self.env.hold_eval_window_steps),
                "hold_success_velocity_norm_max": float(self.env.hold_success_velocity_norm_max),
                "hold_success_action_mean_abs_max": float(self.env.hold_success_action_mean_abs_max),
                "hold_success_current_util_max": float(self.env.hold_success_current_util_max),
                "hold_success_vessel_total_a_max": float(self.env.hold_success_vessel_total_a_max),
                "hold_success_vessel_abs_sum_a_max": float(self.env.hold_success_vessel_abs_sum_a_max),
            }
        else:
            raise ValueError("env backend must be 'native' or 'mock', got %r" % self.backend)

        self.observation_space = self.env.observation_space
        self.action_space = self.env.action_space

    def _obs_dtype(self):
        return getattr(self.observation_space, "dtype", None) or np.float32

    def _action_dtype(self):
        return getattr(self.action_space, "dtype", None) or np.float32

    def _sanitize_obs(self, obs: Any, info: dict[str, Any], *, where: str):
        obs_arr = np.asarray(obs, dtype=self._obs_dtype())
        if not self.enable_finite_guard:
            return obs_arr, False
        bad = not np.all(np.isfinite(obs_arr))
        if bad:
            info[f"rllib_env/nonfinite_obs_{where}"] = True
            info["rllib_env/nonfinite_failure"] = True
            obs_arr = np.nan_to_num(obs_arr, nan=0.0, posinf=1.0e6, neginf=-1.0e6).astype(self._obs_dtype(), copy=False)
        return obs_arr, bool(bad)

    def _sanitize_action(self, action: Any, info: dict[str, Any]):
        action_arr = np.asarray(action, dtype=self._action_dtype())
        if self.enable_finite_guard and not np.all(np.isfinite(action_arr)):
            info["rllib_env/nonfinite_action"] = True
            info["rllib_env/nonfinite_failure"] = True
            action_arr = np.nan_to_num(action_arr, nan=0.0, posinf=1.0, neginf=-1.0).astype(self._action_dtype(), copy=False)
            bad = True
        else:
            bad = False
        if isinstance(self.action_space, spaces.Box):
            action_arr = np.clip(action_arr, self.action_space.low, self.action_space.high)
        return action_arr, bool(bad)

    def _sanitize_reward(self, reward: Any, info: dict[str, Any]):
        try:
            reward_f = float(reward)
        except Exception:
            reward_f = float("nan")
        bad = not np.isfinite(reward_f)
        if self.enable_finite_guard and bad:
            info["rllib_env/nonfinite_reward"] = True
            info["rllib_env/nonfinite_failure"] = True
            reward_f = float(self.nonfinite_penalty)
        return float(reward_f), bool(bad)

    def _add_common_info(self, info: dict[str, Any]) -> dict[str, Any]:
        info = dict(info or {})
        info["rllib_worker_index"] = self.worker_index
        info["rllib_vector_index"] = self.vector_index
        info["rllib_worker_id"] = self.worker_id
        info["rllib_local_env_steps"] = self.local_env_steps
        if self.backend == "native":
            for name in [
                "reach_deadline_step",
                "hold_ramp_start_step",
                "hold_ramp_end_step",
                "hold_start_step",
                "w_reach_progress",
                "w_action",
                "w_delta_action",
                "w_vessel_total",
                "w_vessel_abs_sum",
                "w_hold_action",
                "w_hold_vessel_multiplier",
                "hold_success_r_tol",
                "hold_success_z_tol",
                "hold_success_ip_tol",
                "hold_success_velocity_norm_max",
                "hold_success_action_mean_abs_max",
                "hold_success_current_util_max",
                "hold_success_vessel_total_a_max",
                "hold_success_vessel_abs_sum_a_max",
            ]:
                info[f"curriculum_{name}"] = float(getattr(self.env, name, 0.0))
            info["curriculum_stage_index"] = int(self.curriculum_stage_index)
            info["curriculum_stage_name"] = str(self.curriculum_stage_name)
            info["curriculum_progress_steps"] = int(self.curriculum_progress_steps)
            info["curriculum_unit"] = str(self.curriculum_unit)
            info["curriculum_num_workers"] = int(self.curriculum_num_workers)
        return info

    def _curriculum_effective_steps(self, cur: dict[str, Any]) -> int:
        """Return stage-selection step count.

        B8.2 used per-worker local steps, which made curricula depend on the
        number of EnvRunners.  B8.3 supports global env-step thresholds by
        multiplying the local steps seen by this EnvRunner by the resolved
        number of sampling workers.  This makes stage timing stable when we
        move from 96 to 192 TSC workers.
        """
        unit = str(cur.get("unit", cur.get("curriculum_unit", "local_env_steps"))).lower()
        self.curriculum_unit = unit
        if unit in {"global_env_steps", "env_steps", "aggregate_env_steps"}:
            return int(self.local_env_steps * max(1, self.curriculum_num_workers))
        return int(self.local_env_steps)

    def _select_curriculum_stage(self, stages: list[dict[str, Any]], cur: dict[str, Any]):
        if not stages:
            return None, -1, 0
        effective_steps = self._curriculum_effective_steps(cur)

        force_name = cur.get("force_stage_name")
        force_index = cur.get("force_stage_index")
        if force_name is not None:
            for i, stage in enumerate(stages):
                if str(stage.get("name", f"stage_{i}")) == str(force_name):
                    return stage, i, effective_steps
        if force_index is not None:
            idx = max(0, min(int(force_index), len(stages) - 1))
            return stages[idx], idx, effective_steps

        selected = stages[-1]
        selected_idx = len(stages) - 1
        for i, stage in enumerate(stages):
            if "until_global_env_steps" in stage:
                until = int(stage["until_global_env_steps"])
            elif "until_env_steps" in stage:
                until = int(stage["until_env_steps"])
            elif "until_local_steps" in stage:
                # Legacy local-step stages still work.
                local_until = int(stage["until_local_steps"])
                until = local_until if self.curriculum_unit == "local_env_steps" else local_until * max(1, self.curriculum_num_workers)
            else:
                until = 10**18
            if effective_steps < until:
                selected = stage
                selected_idx = i
                break
        return selected, selected_idx, effective_steps

    def _apply_attribute_curriculum(self) -> None:
        """Apply task/reward curriculum to env attributes.

        B8.3 supports global env-step thresholds so the same curriculum schedule
        remains meaningful when changing the number of EnvRunners.  No action
        priors or demonstrations are injected; stages only change task/reward
        difficulty.
        """
        if self.backend != "native":
            return
        train_cfg = self.env_config.get("train_config", {})
        cur = train_cfg.get("curriculum", {}).get("env_attributes", {})
        if not cur.get("enabled", False):
            return
        stages = list(cur.get("stages", []))
        if not stages:
            return

        selected, selected_idx, effective_steps = self._select_curriculum_stage(stages, cur)
        if selected is None:
            return

        self.curriculum_stage_index = int(selected_idx)
        self.curriculum_stage_name = str(selected.get("name", f"stage_{selected_idx}"))
        self.curriculum_progress_steps = int(effective_steps)

        params = dict(selected.get("env_params", {}))
        for k, v in selected.items():
            if k not in {
                "name",
                "until_local_steps",
                "until_env_steps",
                "until_global_env_steps",
                "env_params",
            }:
                params.setdefault(k, v)

        for name, value in params.items():
            if hasattr(self.env, name):
                current = getattr(self.env, name)
                try:
                    if isinstance(current, bool):
                        casted = bool(value)
                    elif isinstance(current, int) and not isinstance(current, bool):
                        casted = int(value)
                    else:
                        casted = float(value)
                    setattr(self.env, name, casted)
                except Exception:
                    setattr(self.env, name, value)

    def _apply_hold_curriculum(self) -> None:
        if self.backend != "native":
            return
        train_cfg = self.env_config.get("train_config", {})
        cur = train_cfg.get("curriculum", {}).get("hold_success", {})
        if not cur.get("enabled", False):
            return
        stages = list(cur.get("stages", []))
        if not stages:
            return
        selected, _, _ = self._select_curriculum_stage(stages, cur)
        if selected is None:
            return
        for name, base in self._base_hold.items():
            setattr(self.env, name, float(selected.get(name, base)))

    def reset(self, *, seed=None, options=None):
        self.episode_idx += 1
        self._apply_attribute_curriculum()
        self._apply_hold_curriculum()
        if seed is None:
            seed = self.seed_base + 100000 * self.worker_index + 1000 * self.vector_index + self.episode_idx
        obs, info = self.env.reset(seed=seed, options=options)
        info = self._add_common_info(dict(info or {}))
        info["rllib_episode_idx"] = self.episode_idx
        obs, bad_obs = self._sanitize_obs(obs, info, where="reset")
        if bad_obs:
            info["rllib_env/reset_obs_was_sanitized"] = True
        return obs, info

    def step(self, action):
        self._apply_attribute_curriculum()
        self._apply_hold_curriculum()
        pre_info: dict[str, Any] = {}
        safe_action, bad_action = self._sanitize_action(action, pre_info)
        obs, reward, terminated, truncated, info = self.env.step(safe_action)
        self.local_env_steps += 1
        info = self._add_common_info(dict(info or {}))
        info.update(pre_info)
        obs, bad_obs = self._sanitize_obs(obs, info, where="step")
        reward, bad_reward = self._sanitize_reward(reward, info)
        if bad_action:
            info["rllib_env/action_was_sanitized"] = True
        if bad_obs:
            info["rllib_env/step_obs_was_sanitized"] = True
        if bad_reward:
            info["rllib_env/reward_was_sanitized"] = True
        if self.enable_finite_guard and self.terminate_on_nonfinite and (bad_action or bad_obs or bad_reward):
            terminated = True
            truncated = False
            info["rllib_env/terminated_by_finite_guard"] = True
        return obs, reward, bool(terminated), bool(truncated), info

    def close(self):
        if hasattr(self, "env") and self.env is not None:
            self.env.close()
        super().close()
