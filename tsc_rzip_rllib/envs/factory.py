from __future__ import annotations

from pathlib import Path
from typing import Any

from tsc_rzip_rllib.envs.rzip_env import TscRzipEnv


def env_kwargs_from_train_config(train_cfg: dict[str, Any], worker_id: str) -> dict[str, Any]:
    """Build TscRzipEnv kwargs from the old SB3-style train config.

    This function is intentionally kept inside the new project so the RLlib
    project does not import anything from the old sibling tsc_rzip_rl project.
    """
    target = train_cfg["target"]
    ep = train_cfg["episode"]
    norm = train_cfg["normalization"]
    obs_cfg = train_cfg.get("observation", {})
    rew = train_cfg["reward"]
    failure = train_cfg.get("failure", {})

    return dict(
        config_path=str(train_cfg["env_config"]),
        target=(target["R"], target["Z"], target["Ip"]),
        max_episode_steps=ep["max_episode_steps"],

        r_scale=norm["r_scale"],
        z_scale=norm["z_scale"],
        ip_scale=norm["ip_scale"],
        current_scale_a=norm["current_scale_a"],
        r_velocity_scale=norm.get("r_velocity_scale", 1.0),
        z_velocity_scale=norm.get("z_velocity_scale", 1.0),
        ip_derivative_scale=norm.get("ip_derivative_scale", 1.0e5),
        vessel_current_scale_a=norm.get("vessel_current_scale_a", 1.0e5),

        include_derivatives=obs_cfg.get("include_derivatives", True),
        include_error_history=obs_cfg.get("include_error_history", True),
        include_previous_action=obs_cfg.get("include_previous_action", True),
        include_time_fraction=obs_cfg.get("include_time_fraction", True),
        include_vessel_current=obs_cfg.get("include_vessel_current", True),
        time_fraction_denominator_steps=obs_cfg.get("time_fraction_denominator_steps", None),
        clip_time_fraction=obs_cfg.get("clip_time_fraction", True),

        w_r=rew["w_r"],
        w_z=rew["w_z"],
        w_ip=rew["w_ip"],
        w_action=rew.get("w_action", 1.0e-2),
        w_current=rew.get("w_current", 1.0e-4),
        w_action_saturation=rew.get("w_action_saturation", 8.0e-2),
        action_soft_limit=rew.get("action_soft_limit", 0.75),
        w_current_limit=rew.get("w_current_limit", 15.0),
        current_soft_limit=rew.get("current_soft_limit", 0.75),
        w_r_guard=rew.get("w_r_guard", 2.0),
        r_guard_m=rew.get("r_guard_m", 0.08),
        w_z_guard=rew.get("w_z_guard", 2.0),
        z_guard_m=rew.get("z_guard_m", 0.08),
        w_ip_guard=rew.get("w_ip_guard", 0.5),
        ip_guard_a=rew.get("ip_guard_a", 2500.0),

        reach_deadline_step=rew.get("reach_deadline_step", 60),
        reach_success_r_tol=rew.get("reach_success_r_tol", 0.045),
        reach_success_z_tol=rew.get("reach_success_z_tol", 0.045),
        reach_success_ip_tol=rew.get("reach_success_ip_tol", 1800.0),
        fast_reach_bonus=rew.get("fast_reach_bonus", 120.0),
        w_reach_progress=rew.get("w_reach_progress", 0.35),
        w_pre_hold_tracking_boost=rew.get("w_pre_hold_tracking_boost", 0.7),

        hold_start_step=rew.get("hold_start_step", 120),
        w_hold_r=rew.get("w_hold_r", 4.0),
        w_hold_z=rew.get("w_hold_z", 4.0),
        w_hold_ip=rew.get("w_hold_ip", 0.4),
        w_hold_action=rew.get("w_hold_action", 0.05),
        w_delta_action=rew.get("w_delta_action", 0.03),
        w_hold_current_drift=rew.get("w_hold_current_drift", 0.12),
        hold_success_bonus=rew.get("hold_success_bonus", 700.0),
        hold_eval_window_steps=rew.get("hold_eval_window_steps", 100),
        hold_success_r_tol=rew.get("hold_success_r_tol", 0.04),
        hold_success_z_tol=rew.get("hold_success_z_tol", 0.04),
        hold_success_ip_tol=rew.get("hold_success_ip_tol", 1200.0),
        hold_success_action_mean_abs_max=rew.get("hold_success_action_mean_abs_max", 0.40),
        hold_success_current_util_max=rew.get("hold_success_current_util_max", 0.8),

        failure_penalty=failure.get("failure_penalty", -1000.0),
        failure_penalty_per_remaining_step=failure.get("failure_penalty_per_remaining_step", -5.0),
        survival_bonus=failure.get("survival_bonus", 100.0),
        quality_success_bonus=failure.get("quality_success_bonus", failure.get("success_bonus", 500.0)),
        quality_success_r_tol=failure.get("quality_success_r_tol", 0.05),
        quality_success_z_tol=failure.get("quality_success_z_tol", 0.05),
        quality_success_ip_tol=failure.get("quality_success_ip_tol", 1500.0),
        quality_success_max_r_error=failure.get("quality_success_max_r_error", 0.08),
        quality_success_max_z_error=failure.get("quality_success_max_z_error", 0.08),
        quality_success_max_ip_error=failure.get("quality_success_max_ip_error", 2500.0),
        terminate_on_tsc_failure=failure.get("terminate_on_tsc_failure", True),

        worker_id=worker_id,
        keep_tsc_workspace=None,
    )


def make_tsc_rzip_env(train_cfg: dict[str, Any], worker_id: str, seed: int | None = None) -> TscRzipEnv:
    env = TscRzipEnv(**env_kwargs_from_train_config(train_cfg, worker_id=worker_id))
    if seed is not None:
        env.action_space.seed(seed)
        env.observation_space.seed(seed)
    return env
