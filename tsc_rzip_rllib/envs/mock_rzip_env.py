from __future__ import annotations

from collections import deque
from typing import Any

import gymnasium as gym
import numpy as np
from gymnasium import spaces


class MockRzipEnv(gym.Env):
    """Small deterministic stand-in for cluster/Ray smoke tests.

    It has the same action shape and observation layout as the TSC RZIP env,
    but it does not run TSC. Use only to test Ray/RLlib installation and CPU
    fan-out before launching the expensive native TSC backend.
    """

    metadata = {"render_modes": []}

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__()
        config = dict(config or {})
        self.max_episode_steps = int(config.get("max_episode_steps", 80))
        self.target = np.asarray(config.get("target", [0.75, 0.0, 29779.724]), dtype=float)
        self.r_scale = float(config.get("r_scale", 0.05))
        self.z_scale = float(config.get("z_scale", 0.05))
        self.ip_scale = float(config.get("ip_scale", 30000.0))
        self.current_scale_a = float(config.get("current_scale_a", 1000.0))
        self.max_delta_current = float(config.get("max_delta_current", 1.5))
        self.noise = float(config.get("noise", 0.0))
        self.rng = np.random.default_rng(int(config.get("seed", 42)))

        self.action_space = spaces.Box(-1.0, 1.0, shape=(14,), dtype=np.float32)
        self.observation_space = spaces.Box(-np.inf, np.inf, shape=(39,), dtype=np.float32)

        self.step_count = 0
        self.x = np.zeros(3, dtype=float)
        self.prev_x = np.zeros(3, dtype=float)
        self.currents = np.zeros(14, dtype=float)
        self.prev_action = np.zeros(14, dtype=float)
        self.prev_err = np.zeros(3, dtype=float)
        self.hold_abs_r_window = deque(maxlen=30)
        self.hold_abs_z_window = deque(maxlen=30)
        self.hold_abs_ip_window = deque(maxlen=30)

    def reset(self, *, seed=None, options=None):
        if seed is not None:
            self.rng = np.random.default_rng(int(seed))
        self.step_count = 0
        self.x = np.asarray([0.70, 0.025, 25000.0], dtype=float)
        self.prev_x = self.x.copy()
        self.currents[:] = 0.0
        self.prev_action[:] = 0.0
        self.prev_err = self._err()
        self.hold_abs_r_window.clear()
        self.hold_abs_z_window.clear()
        self.hold_abs_ip_window.clear()
        return self._obs(), self._info(False, False)

    def step(self, action):
        action = np.clip(np.asarray(action, dtype=float), -1.0, 1.0)
        self.step_count += 1
        self.prev_x = self.x.copy()
        self.currents = np.clip(self.currents + action * self.max_delta_current, -800.0, 800.0)

        # Toy dynamics with coil groups coupled to R/Z/Ip.
        u_r = 0.012 * np.tanh(np.mean(action[8:14]))
        u_z = 0.010 * np.tanh(np.mean(action[0::2]) - np.mean(action[1::2]))
        u_ip = 700.0 * np.tanh(np.mean(action[:8]))
        drift = np.asarray([u_r, u_z, u_ip])
        relax = 0.06 * (self.target - self.x)
        relax[2] *= 0.25
        noise = self.noise * self.rng.standard_normal(3)
        self.x = self.x + drift + relax + noise

        err_raw = self.x - self.target
        self.hold_abs_r_window.append(abs(float(err_raw[0])))
        self.hold_abs_z_window.append(abs(float(err_raw[1])))
        self.hold_abs_ip_window.append(abs(float(err_raw[2])))

        err = self._err()
        reward = -float(err[0] ** 2 + err[1] ** 2 + 0.2 * err[2] ** 2)
        reward -= 0.01 * float(np.mean(action**2))
        reached = abs(err_raw[0]) < 0.04 and abs(err_raw[1]) < 0.04 and abs(err_raw[2]) < 1200
        if reached:
            reward += 2.0
        truncated = self.step_count >= self.max_episode_steps
        terminated = False
        self.prev_action = action.copy()
        self.prev_err = err.copy()
        return self._obs(), reward, terminated, truncated, self._info(reached, truncated)

    def _err(self):
        return np.asarray([
            (self.x[0] - self.target[0]) / self.r_scale,
            (self.x[1] - self.target[1]) / self.z_scale,
            (self.x[2] - self.target[2]) / self.ip_scale,
        ], dtype=float)

    def _obs(self):
        dt = 0.005
        deriv = (self.x - self.prev_x) / dt
        obs = np.concatenate([
            self._err(),
            self.currents / self.current_scale_a,
            np.asarray([deriv[0], deriv[1], deriv[2] / 1e5], dtype=float),
            self.prev_err,
            self.prev_action,
            np.asarray([min(1.0, self.step_count / max(1, self.max_episode_steps))], dtype=float),
            np.asarray([0.0], dtype=float),
        ])
        return np.nan_to_num(obs).astype(np.float32)

    def _info(self, reached: bool, truncated: bool):
        err_raw = self.x - self.target
        return {
            "time_ms": 1100 + 5 * self.step_count,
            "R": float(self.x[0]),
            "Z": float(self.x[1]),
            "Ip": float(self.x[2]),
            "R_error": float(err_raw[0]),
            "Z_error": float(err_raw[1]),
            "Ip_error": float(err_raw[2]),
            "hold_success": bool(reached and truncated),
            "quality_success": bool(reached),
            "tsc_failed": False,
            "is_success": bool(reached),
        }
