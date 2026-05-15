from __future__ import annotations

import os
from typing import Any

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from tsc_rzip_rllib.envs.factory import make_tsc_rzip_env
from tsc_rzip_rllib.envs.mock_rzip_env import MockRzipEnv


class RllibTscRzipEnv(gym.Env):
    """RLlib-facing env wrapper.

    The wrapped native environment and all TSC runner code live in this new
    project package. Nothing is imported from the old sibling tsc_rzip_rl tree.

    Main responsibilities:
      1. select mock/native backend;
      2. assign a unique worker_id for isolated TSC workspaces;
      3. apply hold-success curriculum;
      4. guard obs/reward/action against NaN/Inf before they enter RLlib.
    """

    metadata = {"render_modes": []}

    def __init__(self, env_config: dict[str, Any]):
        super().__init__()

        self.env_config = dict(env_config)
        self.backend = str(self.env_config.get("backend", "native")).lower()

        self.worker_index = int(
            getattr(env_config, "worker_index", self.env_config.get("worker_index", 0))
        )
        self.vector_index = int(
            getattr(env_config, "vector_index", self.env_config.get("vector_index", 0))
        )

        self.seed_base = int(self.env_config.get("seed", 42))
        self.local_env_steps = 0
        self.episode_idx = 0

        # Finite-guard settings. These defaults are deliberately conservative.
        guard_cfg = dict(self.env_config.get("finite_guard", {}))
        self.enable_finite_guard = bool(guard_cfg.get("enabled", True))
        self.nonfinite_penalty = float(guard_cfg.get("nonfinite_penalty", -1.0e4))
        self.obs_nan_value = float(guard_cfg.get("obs_nan_value", 0.0))
        self.obs_posinf_value = float(guard_cfg.get("obs_posinf_value", 1.0e6))
        self.obs_neginf_value = float(guard_cfg.get("obs_neginf_value", -1.0e6))
        self.action_nan_value = float(guard_cfg.get("action_nan_value", 0.0))
        self.action_posinf_value = float(guard_cfg.get("action_posinf_value", 1.0))
        self.action_neginf_value = float(guard_cfg.get("action_neginf_value", -1.0))
        self.terminate_on_nonfinite = bool(guard_cfg.get("terminate_on_nonfinite", True))

        worker_id = self.env_config.get("worker_id")
        if worker_id is None:
            worker_id = (
                f"ray_w{self.worker_index:04d}_"
                f"v{self.vector_index:03d}_"
                f"pid{os.getpid()}"
            )
        self.worker_id = str(worker_id)

        if self.backend == "mock":
            mock_cfg = dict(self.env_config.get("mock_config", {}))
            mock_cfg.setdefault(
                "seed",
                self.seed_base + 1000 * self.worker_index + self.vector_index,
            )
            self.env = MockRzipEnv(mock_cfg)

        elif self.backend == "native":
            train_cfg = dict(self.env_config["train_config"])
            self.env = make_tsc_rzip_env(
                train_cfg,
                worker_id=self.worker_id,
                seed=self.seed_base + 1000 * self.worker_index + self.vector_index,
            )

            # Save the initial hold-success settings for curriculum fallback.
            self._base_hold = {
                "hold_success_r_tol": float(self.env.hold_success_r_tol),
                "hold_success_z_tol": float(self.env.hold_success_z_tol),
                "hold_success_ip_tol": float(self.env.hold_success_ip_tol),
                "hold_eval_window_steps": int(self.env.hold_eval_window_steps),
                "hold_success_action_mean_abs_max": float(
                    self.env.hold_success_action_mean_abs_max
                ),
                "hold_success_current_util_max": float(
                    self.env.hold_success_current_util_max
                ),
            }

        else:
            raise ValueError(
                "env backend must be 'native' or 'mock', got %r" % self.backend
            )

        self.observation_space = self.env.observation_space
        self.action_space = self.env.action_space

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _obs_dtype(self):
        dtype = getattr(self.observation_space, "dtype", None)
        return dtype if dtype is not None else np.float32

    def _action_dtype(self):
        dtype = getattr(self.action_space, "dtype", None)
        return dtype if dtype is not None else np.float32

    def _sanitize_obs(self, obs: Any, info: dict[str, Any], *, where: str):
        """Convert obs to ndarray and replace NaN/Inf if needed."""
        obs_arr = np.asarray(obs, dtype=self._obs_dtype())

        if not self.enable_finite_guard:
            return obs_arr, False

        bad_obs = not np.all(np.isfinite(obs_arr))
        if bad_obs:
            info[f"rllib_env/nonfinite_obs_{where}"] = True
            info["rllib_env/nonfinite_failure"] = True
            obs_arr = np.nan_to_num(
                obs_arr,
                nan=self.obs_nan_value,
                posinf=self.obs_posinf_value,
                neginf=self.obs_neginf_value,
            ).astype(self._obs_dtype(), copy=False)

        return obs_arr, bool(bad_obs)

    def _sanitize_action(self, action: Any, info: dict[str, Any]):
        """Replace non-finite action entries before passing them to the base env."""
        action_arr = np.asarray(action, dtype=self._action_dtype())

        if not self.enable_finite_guard:
            return action_arr, False

        bad_action = not np.all(np.isfinite(action_arr))
        if bad_action:
            info["rllib_env/nonfinite_action"] = True
            info["rllib_env/nonfinite_failure"] = True
            action_arr = np.nan_to_num(
                action_arr,
                nan=self.action_nan_value,
                posinf=self.action_posinf_value,
                neginf=self.action_neginf_value,
            ).astype(self._action_dtype(), copy=False)

        # If the action space is a Box, clip after replacing NaN/Inf.
        if isinstance(self.action_space, spaces.Box):
            action_arr = np.clip(action_arr, self.action_space.low, self.action_space.high)

        return action_arr, bool(bad_action)

    def _sanitize_reward(self, reward: Any, info: dict[str, Any]):
        """Convert reward to finite float."""
        try:
            reward_f = float(reward)
        except Exception:
            reward_f = float("nan")

        if not self.enable_finite_guard:
            return reward_f, False

        bad_reward = not np.isfinite(reward_f)
        if bad_reward:
            info["rllib_env/nonfinite_reward"] = True
            info["rllib_env/nonfinite_failure"] = True
            reward_f = float(self.nonfinite_penalty)

        return float(reward_f), bool(bad_reward)

    def _add_common_info(self, info: dict[str, Any]) -> dict[str, Any]:
        info = dict(info or {})
        info["rllib_worker_index"] = self.worker_index
        info["rllib_vector_index"] = self.vector_index
        info["rllib_worker_id"] = self.worker_id
        info["rllib_local_env_steps"] = self.local_env_steps

        if self.backend == "native":
            info["curriculum_hold_success_r_tol"] = float(
                getattr(self.env, "hold_success_r_tol", 0.0)
            )
            info["curriculum_hold_success_z_tol"] = float(
                getattr(self.env, "hold_success_z_tol", 0.0)
            )
            info["curriculum_hold_success_ip_tol"] = float(
                getattr(self.env, "hold_success_ip_tol", 0.0)
            )

        return info

    # ------------------------------------------------------------------
    # Curriculum
    # ------------------------------------------------------------------
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

        selected = stages[-1]
        for stage in stages:
            until = int(
                stage.get(
                    "until_env_steps",
                    stage.get("until_local_steps", 10**18),
                )
            )
            if self.local_env_steps < until:
                selected = stage
                break

        self.env.hold_success_r_tol = float(
            selected.get(
                "hold_success_r_tol",
                self._base_hold["hold_success_r_tol"],
            )
        )
        self.env.hold_success_z_tol = float(
            selected.get(
                "hold_success_z_tol",
                self._base_hold["hold_success_z_tol"],
            )
        )
        self.env.hold_success_ip_tol = float(
            selected.get(
                "hold_success_ip_tol",
                self._base_hold["hold_success_ip_tol"],
            )
        )
        self.env.hold_success_action_mean_abs_max = float(
            selected.get(
                "hold_success_action_mean_abs_max",
                self._base_hold["hold_success_action_mean_abs_max"],
            )
        )
        self.env.hold_success_current_util_max = float(
            selected.get(
                "hold_success_current_util_max",
                self._base_hold["hold_success_current_util_max"],
            )
        )

    # ------------------------------------------------------------------
    # Gymnasium API
    # ------------------------------------------------------------------
    def reset(self, *, seed=None, options=None):
        self.episode_idx += 1
        self._apply_hold_curriculum()

        if seed is None:
            seed = (
                self.seed_base
                + 100000 * self.worker_index
                + 1000 * self.vector_index
                + self.episode_idx
            )

        obs, info = self.env.reset(seed=seed, options=options)
        info = self._add_common_info(dict(info or {}))
        info["rllib_episode_idx"] = self.episode_idx

        obs, bad_obs = self._sanitize_obs(obs, info, where="reset")
        if bad_obs:
            info["rllib_env/reset_obs_was_sanitized"] = True

        return obs, info

    def step(self, action):
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

        if self.enable_finite_guard and self.terminate_on_nonfinite:
            if bad_action or bad_obs or bad_reward:
                terminated = True
                truncated = False
                info["rllib_env/terminated_by_finite_guard"] = True

        return obs, reward, bool(terminated), bool(truncated), info

    def close(self):
        if hasattr(self, "env") and self.env is not None:
            self.env.close()
        super().close()