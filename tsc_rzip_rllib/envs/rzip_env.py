from __future__ import annotations

import uuid
from collections import deque
from typing import Any, Dict, Optional, Tuple

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from tsc_rzip_rllib.core.coil_order import TSC_COIL_NAMES
from tsc_rzip_rllib.core.runner import TSCConfig, TSCStepRunner


class TscRzipEnv(gym.Env):
    """Gymnasium environment for TSC-based R/Z/Ip control.

    Unit convention:
        action:
            normalized [-1, 1]^14

        action mapped to:
            single-turn coil current increment [A], TSC order

        observation coil-current part:
            single-turn coil current [A], TSC order

        runner -> TSC:
            kA-turn = A * turns / 1000
    """

    metadata = {"render_modes": []}

    def __init__(
        self,
        config_path: str,
        target: Tuple[float, float, float],
        max_episode_steps: int = 50,
        r_scale: float = 0.05,
        z_scale: float = 0.05,
        ip_scale: float = 3.0e4,
        current_scale_a: float = 1000.0,
        r_velocity_scale: float = 1.0,
        z_velocity_scale: float = 1.0,
        ip_derivative_scale: float = 1.0e5,
        vessel_current_scale_a: float = 1.0e5,
        include_derivatives: bool = True,
        include_error_history: bool = True,
        include_previous_action: bool = True,
        include_time_fraction: bool = True,
        include_vessel_current: bool = True,
        time_fraction_denominator_steps: int | None = None,
        clip_time_fraction: bool = True,
        w_r: float = 1.0,
        w_z: float = 1.0,
        w_ip: float = 0.2,
        w_action: float = 1.0e-2,
        w_current: float = 1.0e-4,
        w_action_saturation: float = 8.0e-2,
        action_soft_limit: float = 0.75,
        w_current_limit: float = 15.0,
        current_soft_limit: float = 0.75,
        w_r_guard: float = 2.0,
        r_guard_m: float = 0.08,
        w_z_guard: float = 2.0,
        z_guard_m: float = 0.08,
        w_ip_guard: float = 0.5,
        ip_guard_a: float = 2500.0,
        reach_deadline_step: int = 60,
        reach_success_r_tol: float = 0.045,
        reach_success_z_tol: float = 0.045,
        reach_success_ip_tol: float = 1800.0,
        fast_reach_bonus: float = 120.0,
        w_reach_progress: float = 0.35,
        w_pre_hold_tracking_boost: float = 0.7,
        hold_start_step: int = 120,
        w_hold_r: float = 4.0,
        w_hold_z: float = 4.0,
        w_hold_ip: float = 0.4,
        w_hold_action: float = 0.05,
        w_delta_action: float = 0.03,
        w_hold_current_drift: float = 0.12,
        hold_success_bonus: float = 700.0,
        hold_eval_window_steps: int = 100,
        hold_success_r_tol: float = 0.04,
        hold_success_z_tol: float = 0.04,
        hold_success_ip_tol: float = 1200.0,
        hold_success_action_mean_abs_max: float = 0.40,
        hold_success_current_util_max: float = 0.8,
        failure_penalty: float = -1000.0,
        failure_penalty_per_remaining_step: float = -5.0,
        survival_bonus: float = 100.0,
        quality_success_bonus: float = 500.0,
        quality_success_r_tol: float = 0.05,
        quality_success_z_tol: float = 0.05,
        quality_success_ip_tol: float = 1500.0,
        quality_success_max_r_error: float = 0.08,
        quality_success_max_z_error: float = 0.08,
        quality_success_max_ip_error: float = 2500.0,
        terminate_on_tsc_failure: bool = True,
        worker_id: str | None = None,
        keep_tsc_workspace: bool | None = None,
    ):
        super().__init__()

        self.cfg = TSCConfig.from_json(config_path)
        self.target = np.asarray(target, dtype=float)
        self.max_episode_steps = int(max_episode_steps)

        self.r_scale = float(r_scale)
        self.z_scale = float(z_scale)
        self.ip_scale = float(ip_scale)
        self.current_scale_a = float(current_scale_a)

        self.r_velocity_scale = float(r_velocity_scale)
        self.z_velocity_scale = float(z_velocity_scale)
        self.ip_derivative_scale = float(ip_derivative_scale)
        self.vessel_current_scale_a = float(vessel_current_scale_a)

        self.include_derivatives = bool(include_derivatives)
        self.include_error_history = bool(include_error_history)
        self.include_previous_action = bool(include_previous_action)
        self.include_time_fraction = bool(include_time_fraction)
        self.include_vessel_current = bool(include_vessel_current)
        self.time_fraction_denominator_steps = (
            None if time_fraction_denominator_steps is None else int(time_fraction_denominator_steps)
        )
        self.clip_time_fraction = bool(clip_time_fraction)

        self.w_r = float(w_r)
        self.w_z = float(w_z)
        self.w_ip = float(w_ip)
        self.w_action = float(w_action)
        self.w_current = float(w_current)
        self.w_action_saturation = float(w_action_saturation)
        self.action_soft_limit = float(action_soft_limit)

        self.w_current_limit = float(w_current_limit)
        self.current_soft_limit = float(current_soft_limit)

        self.w_r_guard = float(w_r_guard)
        self.r_guard_m = float(r_guard_m)
        self.w_z_guard = float(w_z_guard)
        self.z_guard_m = float(z_guard_m)
        self.w_ip_guard = float(w_ip_guard)
        self.ip_guard_a = float(ip_guard_a)

        self.reach_deadline_step = int(reach_deadline_step)
        self.reach_success_r_tol = float(reach_success_r_tol)
        self.reach_success_z_tol = float(reach_success_z_tol)
        self.reach_success_ip_tol = float(reach_success_ip_tol)
        self.fast_reach_bonus = float(fast_reach_bonus)
        self.w_reach_progress = float(w_reach_progress)
        self.w_pre_hold_tracking_boost = float(w_pre_hold_tracking_boost)

        self.hold_start_step = int(hold_start_step)
        self.w_hold_r = float(w_hold_r)
        self.w_hold_z = float(w_hold_z)
        self.w_hold_ip = float(w_hold_ip)
        self.w_hold_action = float(w_hold_action)
        self.w_delta_action = float(w_delta_action)
        self.w_hold_current_drift = float(w_hold_current_drift)

        self.hold_success_bonus = float(hold_success_bonus)
        self.hold_eval_window_steps = int(hold_eval_window_steps)
        self.hold_success_r_tol = float(hold_success_r_tol)
        self.hold_success_z_tol = float(hold_success_z_tol)
        self.hold_success_ip_tol = float(hold_success_ip_tol)
        self.hold_success_action_mean_abs_max = float(hold_success_action_mean_abs_max)
        self.hold_success_current_util_max = float(hold_success_current_util_max)

        self.failure_penalty = float(failure_penalty)
        self.failure_penalty_per_remaining_step = float(failure_penalty_per_remaining_step)
        self.survival_bonus = float(survival_bonus)
        self.quality_success_bonus = float(quality_success_bonus)

        self.quality_success_r_tol = float(quality_success_r_tol)
        self.quality_success_z_tol = float(quality_success_z_tol)
        self.quality_success_ip_tol = float(quality_success_ip_tol)

        self.quality_success_max_r_error = float(quality_success_max_r_error)
        self.quality_success_max_z_error = float(quality_success_max_z_error)
        self.quality_success_max_ip_error = float(quality_success_max_ip_error)

        self.terminate_on_tsc_failure = bool(terminate_on_tsc_failure)

        self.worker_id = worker_id or f"env_{uuid.uuid4().hex[:8]}"
        self.keep_tsc_workspace = keep_tsc_workspace

        self.runner: Optional[TSCStepRunner] = None
        self.step_count = 0
        self.episode_return = 0.0

        self.last_state: Optional[Dict[str, Any]] = None
        self.last_obs: Optional[np.ndarray] = None

        self.prev_raw_values: Optional[np.ndarray] = None
        self.prev_tracking_errors: Optional[np.ndarray] = None
        self.prev_error_score: Optional[float] = None
        self.prev_action_norm = np.zeros(14, dtype=float)
        self.fast_reach_bonus_given = False

        self.hold_action_window: deque[float] = deque(maxlen=max(1, self.hold_eval_window_steps))
        self.hold_abs_r_window: deque[float] = deque(maxlen=max(1, self.hold_eval_window_steps))
        self.hold_abs_z_window: deque[float] = deque(maxlen=max(1, self.hold_eval_window_steps))
        self.hold_abs_ip_window: deque[float] = deque(maxlen=max(1, self.hold_eval_window_steps))
        self.hold_current_util_window: deque[float] = deque(maxlen=max(1, self.hold_eval_window_steps))

        self.last_reward_terms: Dict[str, float] = {}

        self.episode_max_abs_R_error = 0.0
        self.episode_max_abs_Z_error = 0.0
        self.episode_max_abs_Ip_error = 0.0
        self.episode_max_current_util = 0.0

        self.observation_space = spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(self._obs_dim(),),
            dtype=np.float32,
        )

        self.action_space = spaces.Box(
            low=-1.0,
            high=1.0,
            shape=(14,),
            dtype=np.float32,
        )

    def _obs_dim(self) -> int:
        dim = 3 + 14
        if self.include_derivatives:
            dim += 3
        if self.include_error_history:
            dim += 3
        if self.include_previous_action:
            dim += 14
        if self.include_time_fraction:
            dim += 1
        if self.include_vessel_current:
            dim += 1
        return dim

    def _ensure_runner(self) -> TSCStepRunner:
        if self.runner is None:
            self.runner = TSCStepRunner(
                self.cfg,
                worker_id=self.worker_id,
                keep_workspace=self.keep_tsc_workspace,
            )
        return self.runner

    def reset(self, *, seed: Optional[int] = None, options: Optional[dict] = None):
        super().reset(seed=seed)

        runner = self._ensure_runner()

        self.step_count = 0
        self.episode_return = 0.0

        self.prev_raw_values = None
        self.prev_tracking_errors = None
        self.prev_error_score = None
        self.prev_action_norm = np.zeros(14, dtype=float)
        self.fast_reach_bonus_given = False
        self.last_reward_terms = {}

        self.hold_action_window.clear()
        self.hold_abs_r_window.clear()
        self.hold_abs_z_window.clear()
        self.hold_abs_ip_window.clear()
        self.hold_current_util_window.clear()

        self.episode_max_abs_R_error = 0.0
        self.episode_max_abs_Z_error = 0.0
        self.episode_max_abs_Ip_error = 0.0
        self.episode_max_current_util = 0.0

        episode_name = f"{self.worker_id}_episode_{uuid.uuid4().hex[:12]}"
        self.last_state = runner.reset(episode_name=episode_name)

        self._update_episode_extrema(self.last_state)
        self.prev_error_score = self._error_score(self.last_state)

        self.last_obs = self._obs(self.last_state, action_norm=self.prev_action_norm)
        self._update_history(self.last_state, self.prev_action_norm)

        return self.last_obs, self._info(self.last_state)

    def step(self, action):
        if self.last_state is None or self.last_obs is None:
            raise RuntimeError("call reset() before step()")

        runner = self._ensure_runner()

        action = np.asarray(action, dtype=float)
        action = np.clip(action, -1.0, 1.0)

        delta_current_a_tsc = action * runner.max_delta_current_a_per_step

        try:
            state = runner.step_delta_current_a(delta_current_a_tsc)

            self.last_state = state
            self.step_count += 1

            self._update_episode_extrema(state)
            self._update_hold_windows(state, action)

            obs = self._obs(state, action_norm=action)
            reward, reward_terms = self._reward(obs, action, state)

            tsc_failed = bool(state.get("abnormal", False))
            terminated = bool(self.terminate_on_tsc_failure and tsc_failed)
            truncated = bool(self.step_count >= self.max_episode_steps)
            survived_episode = bool(truncated and not tsc_failed)
            quality_success = bool(survived_episode and self._is_quality_success(state))
            hold_success = bool(survived_episode and self._is_hold_success())

            remaining_steps = max(0, self.max_episode_steps - self.step_count)

            if tsc_failed:
                failure_extra = (
                    self.failure_penalty
                    + self.failure_penalty_per_remaining_step * remaining_steps
                )
                reward += failure_extra
                reward_terms["failure_penalty_total"] = float(failure_extra)
            else:
                reward_terms["failure_penalty_total"] = 0.0

            if survived_episode:
                reward += self.survival_bonus
                reward_terms["survival_bonus"] = float(self.survival_bonus)
            else:
                reward_terms["survival_bonus"] = 0.0

            if quality_success:
                reward += self.quality_success_bonus
                reward_terms["quality_success_bonus"] = float(self.quality_success_bonus)
            else:
                reward_terms["quality_success_bonus"] = 0.0

            if hold_success:
                reward += self.hold_success_bonus
                reward_terms["hold_success_bonus"] = float(self.hold_success_bonus)
            else:
                reward_terms["hold_success_bonus"] = 0.0

            reward_terms["success_bonus"] = reward_terms["quality_success_bonus"]

            self.episode_return += float(reward)
            self.last_reward_terms = reward_terms

            self.last_obs = obs
            self._update_history(state, action)

            info = self._info(state)
            info.update(
                {
                    "tsc_failed": tsc_failed,
                    "is_success": hold_success,
                    "survived_episode": survived_episode,
                    "quality_success": quality_success,
                    "hold_success": hold_success,
                    "failure_reason": state.get("done_reason", "") or state.get("stderr", ""),
                    "worker_id": self.worker_id,
                }
            )

            if terminated or truncated:
                info.update(
                    self._terminal_info(
                        state,
                        tsc_failed=tsc_failed,
                        survived_episode=survived_episode,
                        quality_success=quality_success,
                        hold_success=hold_success,
                    )
                )

            return obs, reward, terminated, truncated, info

        except Exception as exc:
            self.step_count += 1
            remaining_steps = max(0, self.max_episode_steps - self.step_count)
            reward = self.failure_penalty + self.failure_penalty_per_remaining_step * remaining_steps
            self.episode_return += float(reward)

            obs = self.last_obs.copy()
            terminated = True
            truncated = False

            info = self._info(self.last_state)
            info.update(
                {
                    "abnormal": True,
                    "tsc_failed": True,
                    "is_success": False,
                    "survived_episode": False,
                    "quality_success": False,
                    "hold_success": False,
                    "failure_reason": repr(exc),
                    "worker_id": self.worker_id,
                }
            )
            info.update(
                self._terminal_info(
                    self.last_state,
                    tsc_failed=True,
                    survived_episode=False,
                    quality_success=False,
                    hold_success=False,
                )
            )

            return obs, reward, terminated, truncated, info

    def _raw_values(self, state: Dict[str, Any]) -> np.ndarray:
        return np.asarray([state["R"], state["Z"], state["Ip"]], dtype=float)

    def _raw_errors(self, state: Dict[str, Any]) -> tuple[float, float, float]:
        return (
            float(state["R"] - self.target[0]),
            float(state["Z"] - self.target[1]),
            float(state["Ip"] - self.target[2]),
        )

    def _tracking_errors(self, state: Dict[str, Any]) -> np.ndarray:
        r_error, z_error, ip_error = self._raw_errors(state)
        return np.asarray(
            [
                r_error / self.r_scale,
                z_error / self.z_scale,
                ip_error / self.ip_scale,
            ],
            dtype=float,
        )

    def _error_score(self, state: Dict[str, Any]) -> float:
        err = self._tracking_errors(state)
        return float(self.w_r * err[0] ** 2 + self.w_z * err[1] ** 2 + self.w_ip * err[2] ** 2)

    def _normalized_derivatives(self, state: Dict[str, Any]) -> np.ndarray:
        if self.prev_raw_values is None:
            return np.zeros(3, dtype=float)

        raw = self._raw_values(state)
        dt_s = max(1e-12, self.cfg.dt_ms * 1.0e-3)
        deriv = (raw - self.prev_raw_values) / dt_s

        return np.asarray(
            [
                deriv[0] / self.r_velocity_scale,
                deriv[1] / self.z_velocity_scale,
                deriv[2] / self.ip_derivative_scale,
            ],
            dtype=float,
        )

    def _time_fraction_value(self) -> float:
        denom = self.time_fraction_denominator_steps or self.max_episode_steps
        tf = self.step_count / max(1, denom)
        if self.clip_time_fraction:
            tf = min(tf, 1.0)
        return float(tf)

    def _obs(self, state: Dict[str, Any], action_norm: np.ndarray) -> np.ndarray:
        parts: list[np.ndarray] = []

        err = self._tracking_errors(state)
        current_obs = np.asarray(state["currents_a_tsc"], dtype=float) / self.current_scale_a

        parts.append(err)
        parts.append(current_obs)

        if self.include_derivatives:
            parts.append(self._normalized_derivatives(state))

        if self.include_error_history:
            if self.prev_tracking_errors is None:
                parts.append(err.copy())
            else:
                parts.append(self.prev_tracking_errors.copy())

        if self.include_previous_action:
            parts.append(np.asarray(action_norm, dtype=float).copy())

        if self.include_time_fraction:
            parts.append(np.asarray([self._time_fraction_value()], dtype=float))

        if self.include_vessel_current:
            vessel = float(state.get("vessel_current_total_a", 0.0)) / self.vessel_current_scale_a
            parts.append(np.asarray([vessel], dtype=float))

        obs = np.concatenate(parts)
        obs = np.nan_to_num(obs, nan=0.0, posinf=1.0e6, neginf=-1.0e6)
        return obs.astype(np.float32)

    def _update_history(self, state: Dict[str, Any], action_norm: np.ndarray) -> None:
        self.prev_raw_values = self._raw_values(state)
        self.prev_tracking_errors = self._tracking_errors(state)
        self.prev_action_norm = np.asarray(action_norm, dtype=float).copy()
        self.prev_error_score = self._error_score(state)

    def _current_utilization(self, state: Dict[str, Any]) -> np.ndarray:
        currents = np.asarray(state["currents_a_tsc"], dtype=float)
        positive_limits = np.asarray(self.cfg.max_current_a_tsc, dtype=float)
        negative_limits = np.abs(np.asarray(self.cfg.min_current_a_tsc, dtype=float))
        limits = np.where(currents >= 0.0, positive_limits, negative_limits)
        limits = np.maximum(limits, 1.0e-9)
        return np.abs(currents) / limits

    def _update_episode_extrema(self, state: Dict[str, Any]) -> None:
        r_error, z_error, ip_error = self._raw_errors(state)
        current_util = self._current_utilization(state)

        self.episode_max_abs_R_error = max(self.episode_max_abs_R_error, abs(float(r_error)))
        self.episode_max_abs_Z_error = max(self.episode_max_abs_Z_error, abs(float(z_error)))
        self.episode_max_abs_Ip_error = max(self.episode_max_abs_Ip_error, abs(float(ip_error)))
        self.episode_max_current_util = max(self.episode_max_current_util, float(np.max(current_util)))

    def _update_hold_windows(self, state: Dict[str, Any], action: np.ndarray) -> None:
        r_error, z_error, ip_error = self._raw_errors(state)
        current_util = float(np.max(self._current_utilization(state)))
        self.hold_action_window.append(float(np.mean(np.abs(action))))
        self.hold_abs_r_window.append(abs(float(r_error)))
        self.hold_abs_z_window.append(abs(float(z_error)))
        self.hold_abs_ip_window.append(abs(float(ip_error)))
        self.hold_current_util_window.append(current_util)

    def _is_reached(self, state: Dict[str, Any]) -> bool:
        r_error, z_error, ip_error = self._raw_errors(state)
        return bool(
            abs(r_error) <= self.reach_success_r_tol
            and abs(z_error) <= self.reach_success_z_tol
            and abs(ip_error) <= self.reach_success_ip_tol
        )

    def _is_quality_success(self, state: Dict[str, Any]) -> bool:
        r_error, z_error, ip_error = self._raw_errors(state)

        terminal_ok = (
            abs(r_error) <= self.quality_success_r_tol
            and abs(z_error) <= self.quality_success_z_tol
            and abs(ip_error) <= self.quality_success_ip_tol
        )

        trajectory_ok = (
            self.episode_max_abs_R_error <= self.quality_success_max_r_error
            and self.episode_max_abs_Z_error <= self.quality_success_max_z_error
            and self.episode_max_abs_Ip_error <= self.quality_success_max_ip_error
        )

        return bool(terminal_ok and trajectory_ok)

    def _hold_window_stats(self) -> Dict[str, float]:
        def max_or_nan(values: deque[float]) -> float:
            return float(np.max(values)) if len(values) else float("nan")

        def mean_or_nan(values: deque[float]) -> float:
            return float(np.mean(values)) if len(values) else float("nan")

        return {
            "hold_window_len": float(len(self.hold_action_window)),
            "hold_window_mean_abs_action": mean_or_nan(self.hold_action_window),
            "hold_window_max_abs_R_error": max_or_nan(self.hold_abs_r_window),
            "hold_window_max_abs_Z_error": max_or_nan(self.hold_abs_z_window),
            "hold_window_max_abs_Ip_error": max_or_nan(self.hold_abs_ip_window),
            "hold_window_max_current_util": max_or_nan(self.hold_current_util_window),
            "hold_window_mean_current_util": mean_or_nan(self.hold_current_util_window),
        }

    def _is_hold_success(self) -> bool:
        stats = self._hold_window_stats()
        if stats["hold_window_len"] < min(self.hold_eval_window_steps, self.max_episode_steps):
            return False
        return bool(
            stats["hold_window_max_abs_R_error"] <= self.hold_success_r_tol
            and stats["hold_window_max_abs_Z_error"] <= self.hold_success_z_tol
            and stats["hold_window_max_abs_Ip_error"] <= self.hold_success_ip_tol
            and stats["hold_window_mean_abs_action"] <= self.hold_success_action_mean_abs_max
            and stats["hold_window_max_current_util"] <= self.hold_success_current_util_max
        )

    @staticmethod
    def _guard_penalty(error_abs: float, threshold: float, weight: float) -> float:
        threshold = max(float(threshold), 1.0e-12)
        excess = max(float(error_abs) - threshold, 0.0)
        return float(weight) * float((excess / threshold) ** 2)

    def _reward(self, obs: np.ndarray, action: np.ndarray, state: Dict[str, Any]) -> tuple[float, Dict[str, float]]:
        r_err, z_err, ip_err = obs[:3]
        r_error_raw, z_error_raw, ip_error_raw = self._raw_errors(state)

        tracking_penalty = (
            self.w_r * float(r_err**2)
            + self.w_z * float(z_err**2)
            + self.w_ip * float(ip_err**2)
        )

        pre_hold_tracking_boost_penalty = 0.0
        if self.step_count < self.hold_start_step:
            pre_hold_tracking_boost_penalty = self.w_pre_hold_tracking_boost * tracking_penalty

        action_penalty = self.w_action * float(np.mean(np.asarray(action, dtype=float) ** 2))

        current_norm = np.asarray(state["currents_a_tsc"], dtype=float) / self.current_scale_a
        current_penalty = self.w_current * float(np.mean(current_norm**2))

        action_abs = np.abs(np.asarray(action, dtype=float))
        soft_excess = np.maximum(action_abs - self.action_soft_limit, 0.0)
        action_saturation_penalty = self.w_action_saturation * float(np.mean(soft_excess**2))

        current_util = self._current_utilization(state)
        current_limit_excess = np.maximum(current_util - self.current_soft_limit, 0.0)
        current_limit_penalty = self.w_current_limit * float(np.sum(current_limit_excess**2))

        r_guard_penalty = self._guard_penalty(abs(r_error_raw), self.r_guard_m, self.w_r_guard)
        z_guard_penalty = self._guard_penalty(abs(z_error_raw), self.z_guard_m, self.w_z_guard)
        ip_guard_penalty = self._guard_penalty(abs(ip_error_raw), self.ip_guard_a, self.w_ip_guard)

        error_score_now = self._error_score(state)
        if self.prev_error_score is None:
            reach_progress_bonus = 0.0
        else:
            reach_progress_bonus = self.w_reach_progress * max(self.prev_error_score - error_score_now, 0.0)

        fast_reach_bonus_now = 0.0
        if (
            not self.fast_reach_bonus_given
            and self.step_count <= self.reach_deadline_step
            and self._is_reached(state)
        ):
            fast_reach_bonus_now = self.fast_reach_bonus
            self.fast_reach_bonus_given = True

        hold_phase = self.step_count >= self.hold_start_step
        hold_tracking_penalty = 0.0
        hold_action_penalty = 0.0
        delta_action_penalty = 0.0
        hold_current_drift_penalty = 0.0

        if hold_phase:
            hold_tracking_penalty = (
                self.w_hold_r * float(r_err**2)
                + self.w_hold_z * float(z_err**2)
                + self.w_hold_ip * float(ip_err**2)
            )
            hold_action_penalty = self.w_hold_action * float(np.mean(action_abs**2))
            delta_action = np.asarray(action, dtype=float) - self.prev_action_norm
            delta_action_penalty = self.w_delta_action * float(np.mean(delta_action**2))

            # Penalize current utilization above a comfortable region during hold,
            # and also penalize any persistent approach to the soft limit.
            hold_current_drift_excess = np.maximum(current_util - self.current_soft_limit, 0.0)
            hold_current_drift_penalty = self.w_hold_current_drift * float(np.sum(hold_current_drift_excess**2))

        reward = (
            - tracking_penalty
            - pre_hold_tracking_boost_penalty
            - action_penalty
            - current_penalty
            - action_saturation_penalty
            - current_limit_penalty
            - r_guard_penalty
            - z_guard_penalty
            - ip_guard_penalty
            - hold_tracking_penalty
            - hold_action_penalty
            - delta_action_penalty
            - hold_current_drift_penalty
            + reach_progress_bonus
            + fast_reach_bonus_now
        )

        stats = self._hold_window_stats()
        terms = {
            "tracking_penalty": float(tracking_penalty),
            "pre_hold_tracking_boost_penalty": float(pre_hold_tracking_boost_penalty),
            "action_penalty": float(action_penalty),
            "current_penalty": float(current_penalty),
            "action_saturation_penalty": float(action_saturation_penalty),
            "current_limit_penalty": float(current_limit_penalty),
            "r_guard_penalty": float(r_guard_penalty),
            "z_guard_penalty": float(z_guard_penalty),
            "ip_guard_penalty": float(ip_guard_penalty),
            "reach_progress_bonus": float(reach_progress_bonus),
            "fast_reach_bonus_now": float(fast_reach_bonus_now),
            "hold_phase": float(hold_phase),
            "hold_tracking_penalty": float(hold_tracking_penalty),
            "hold_action_penalty": float(hold_action_penalty),
            "delta_action_penalty": float(delta_action_penalty),
            "hold_current_drift_penalty": float(hold_current_drift_penalty),
            "current_util_max": float(np.max(current_util)),
            "episode_max_abs_R_error": float(self.episode_max_abs_R_error),
            "episode_max_abs_Z_error": float(self.episode_max_abs_Z_error),
            "episode_max_abs_Ip_error": float(self.episode_max_abs_Ip_error),
            "episode_max_current_util": float(self.episode_max_current_util),
            "base_reward": float(reward),
        }
        terms.update(stats)

        return float(reward), terms

    def _terminal_info(
        self,
        state: Dict[str, Any],
        tsc_failed: bool,
        survived_episode: bool,
        quality_success: bool,
        hold_success: bool,
    ) -> Dict[str, Any]:
        err = self._tracking_errors(state)
        r_error, z_error, ip_error = self._raw_errors(state)
        current_util = self._current_utilization(state)
        hold_stats = self._hold_window_stats()

        out = {
            "episode_return": float(self.episode_return),
            "episode_length": int(self.step_count),
            "episode_reward_per_step": float(self.episode_return / max(1, self.step_count)),
            "terminal_time_ms": float(state["time_ms"]),

            "terminal_R_error": float(r_error),
            "terminal_Z_error": float(z_error),
            "terminal_Ip_error": float(ip_error),

            "terminal_R_abs_error": float(abs(r_error)),
            "terminal_Z_abs_error": float(abs(z_error)),
            "terminal_Ip_abs_error": float(abs(ip_error)),

            "terminal_R_error_norm": float(err[0]),
            "terminal_Z_error_norm": float(err[1]),
            "terminal_Ip_error_norm": float(err[2]),

            "terminal_current_util_max": float(np.max(current_util)),
            "terminal_vessel_current_total_a": float(state.get("vessel_current_total_a", 0.0)),

            "episode_max_abs_R_error": float(self.episode_max_abs_R_error),
            "episode_max_abs_Z_error": float(self.episode_max_abs_Z_error),
            "episode_max_abs_Ip_error": float(self.episode_max_abs_Ip_error),
            "episode_max_current_util": float(self.episode_max_current_util),

            "tsc_failed": bool(tsc_failed),
            "survived_episode": bool(survived_episode),
            "quality_success": bool(quality_success),
            "hold_success": bool(hold_success),
            "is_success": bool(hold_success),
        }
        out.update(hold_stats)
        return out

    def _info(self, state: Dict[str, Any]) -> Dict[str, Any]:
        err = self._tracking_errors(state)
        r_error, z_error, ip_error = self._raw_errors(state)
        current_util = self._current_utilization(state)
        current_util_argmax = int(np.argmax(current_util))
        hold_stats = self._hold_window_stats()

        info = {
            "time_ms": state["time_ms"],
            "R": state["R"],
            "Z": state["Z"],
            "Ip": state["Ip"],

            "R_error": float(r_error),
            "Z_error": float(z_error),
            "Ip_error": float(ip_error),
            "R_error_norm": float(err[0]),
            "Z_error_norm": float(err[1]),
            "Ip_error_norm": float(err[2]),

            "vessel_current_total_a": float(state.get("vessel_current_total_a", 0.0)),

            "currents_a_tsc": state["currents_a_tsc"],
            "currents_a_display": state["currents_a_display"],

            "currents_kat_tsc": state["currents_kat_tsc"],
            "currents_kat_display": state["currents_kat_display"],

            "current_util_max": float(np.max(current_util)),
            "current_util_argmax": current_util_argmax,
            "current_util_argmax_name": TSC_COIL_NAMES[current_util_argmax],

            "episode_max_abs_R_error": float(self.episode_max_abs_R_error),
            "episode_max_abs_Z_error": float(self.episode_max_abs_Z_error),
            "episode_max_abs_Ip_error": float(self.episode_max_abs_Ip_error),
            "episode_max_current_util": float(self.episode_max_current_util),

            "time_fraction": self._time_fraction_value(),
            "abnormal": state.get("abnormal", False),
            "done_reason": state.get("done_reason", ""),
            "worker_id": self.worker_id,

            "tsc_failed": False,
            "is_success": False,
            "survived_episode": False,
            "quality_success": False,
            "hold_success": False,
            "episode_reward_per_step": 0.0,
            "terminal_time_ms": 0.0,
            "terminal_R_error": 0.0,
            "terminal_Z_error": 0.0,
            "terminal_Ip_error": 0.0,
            "terminal_R_abs_error": 0.0,
            "terminal_Z_abs_error": 0.0,
            "terminal_Ip_abs_error": 0.0,
            "terminal_current_util_max": 0.0,
            "terminal_vessel_current_total_a": 0.0,
        }
        info.update(hold_stats)

        for k, v in self.last_reward_terms.items():
            info[k] = v

        return info

    def close(self):
        if self.runner is not None:
            self.runner.cleanup_runtime_workspace()
            self.runner = None
        super().close()
