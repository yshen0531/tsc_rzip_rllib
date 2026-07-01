from __future__ import annotations

from typing import Any

from tsc_rzip_rllib.envs.rzip_env import TscRzipEnv


def env_kwargs_from_train_config(train_cfg: dict[str, Any], worker_id: str) -> dict[str, Any]:
    """Build TscRzipEnv kwargs from project JSON config.

    This file intentionally lives inside the new project so runtime never imports
    from the old sibling tsc_rzip_rl tree.
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

        include_boundary_extrema=obs_cfg.get("include_boundary_extrema", False),
        boundary_source=obs_cfg.get("boundary_source", "gfile_boundary"),
        boundary_r_ref=obs_cfg.get("boundary_r_ref", 0.75),
        boundary_z_ref=obs_cfg.get("boundary_z_ref", 0.0),
        boundary_r_scale=obs_cfg.get("boundary_r_scale", 0.20),
        boundary_z_scale=obs_cfg.get("boundary_z_scale", 0.20),
        boundary_width_ref=obs_cfg.get("boundary_width_ref", 0.0),
        boundary_height_ref=obs_cfg.get("boundary_height_ref", 0.0),
        boundary_width_scale=obs_cfg.get("boundary_width_scale", 0.40),
        boundary_height_scale=obs_cfg.get("boundary_height_scale", 0.60),
        boundary_min_points=obs_cfg.get("boundary_min_points", 4),
        boundary_clip=obs_cfg.get("boundary_clip", 20.0),

        include_derivatives=obs_cfg.get("include_derivatives", True),
        include_error_history=obs_cfg.get("include_error_history", True),
        include_previous_action=obs_cfg.get("include_previous_action", True),
        include_time_fraction=obs_cfg.get("include_time_fraction", True),
        include_deadline_fraction=obs_cfg.get("include_deadline_fraction", False),
        include_hold_weight=obs_cfg.get("include_hold_weight", False),
        include_vessel_current=obs_cfg.get("include_vessel_current", True),
        time_fraction_denominator_steps=obs_cfg.get("time_fraction_denominator_steps", None),
        clip_time_fraction=obs_cfg.get("clip_time_fraction", True),
        include_history_stack=obs_cfg.get("include_history_stack", True),
        history_stack_steps=obs_cfg.get("history_stack_steps", 8),
        history_include_error=obs_cfg.get("history_include_error", True),
        history_include_derivative=obs_cfg.get("history_include_derivative", True),
        history_include_action=obs_cfg.get("history_include_action", True),
        history_include_vessel_current=obs_cfg.get("history_include_vessel_current", True),

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

        reach_deadline_step=rew.get("reach_deadline_step", 100),
        reach_success_r_tol=rew.get("reach_success_r_tol", 0.035),
        reach_success_z_tol=rew.get("reach_success_z_tol", 0.035),
        reach_success_ip_tol=rew.get("reach_success_ip_tol", 800.0),
        reach_success_velocity_norm_max=rew.get("reach_success_velocity_norm_max", 0.8),
        fast_reach_bonus=rew.get("fast_reach_bonus", 0.0),
        w_reach_progress=rew.get("w_reach_progress", 0.35),
        signed_progress_reward=rew.get("signed_progress_reward", False),
        w_pre_hold_tracking_boost=rew.get("w_pre_hold_tracking_boost", 1.0),
        w_error_growth=rew.get("w_error_growth", 1.2),
        w_error_growth_near_target=rew.get("w_error_growth_near_target", 1.0),
        error_growth_near_norm=rew.get("error_growth_near_norm", 4.0),
        error_growth_deadline_multiplier=rew.get("error_growth_deadline_multiplier", 1.5),

        hold_start_step=rew.get("hold_start_step", 100),
        hold_ramp_start_step=rew.get("hold_ramp_start_step", 80),
        hold_ramp_end_step=rew.get("hold_ramp_end_step", 120),
        w_hold_r=rew.get("w_hold_r", 4.0),
        w_hold_z=rew.get("w_hold_z", 4.5),
        w_hold_ip=rew.get("w_hold_ip", 0.6),
        w_hold_action=rew.get("w_hold_action", 0.08),
        w_delta_action=rew.get("w_delta_action", 0.05),
        w_hold_current_drift=rew.get("w_hold_current_drift", 0.12),

        w_derivative=rew.get("w_derivative", 0.25),
        w_near_target_derivative=rew.get("w_near_target_derivative", 0.75),
        near_target_norm_sigma=rew.get("near_target_norm_sigma", 1.0),
        w_overshoot=rew.get("w_overshoot", 1.2),
        overshoot_near_norm=rew.get("overshoot_near_norm", 2.0),
        w_rz_max_error=rew.get("w_rz_max_error", 0.0),
        w_hold_rz_max_error=rew.get("w_hold_rz_max_error", 0.0),
        rz_max_error_r_ref=rew.get("rz_max_error_r_ref", 0.05),
        rz_max_error_z_ref=rew.get("rz_max_error_z_ref", 0.05),
        w_max_error=rew.get("w_max_error", 0.0),
        max_error_r_ref=rew.get("max_error_r_ref", 0.05),
        max_error_z_ref=rew.get("max_error_z_ref", 0.05),
        max_error_ip_ref=rew.get("max_error_ip_ref", 6000.0),
        w_negative_r_bias=rew.get("w_negative_r_bias", 0.0),
        negative_r_bias_threshold_m=rew.get("negative_r_bias_threshold_m", -0.05),
        w_z_zero_cross_overshoot=rew.get("w_z_zero_cross_overshoot", 0.0),
        w_ip_zero_cross_overshoot=rew.get("w_ip_zero_cross_overshoot", 0.0),
        zero_cross_near_rz_m=rew.get("zero_cross_near_rz_m", 0.20),
        zero_cross_near_ip_a=rew.get("zero_cross_near_ip_a", 6000.0),
        early_drift_protect_until_step=rew.get("early_drift_protect_until_step", 0),
        w_early_rz_drift=rew.get("w_early_rz_drift", 0.0),
        early_rz_drift_r_ref=rew.get("early_rz_drift_r_ref", 0.04),
        early_rz_drift_z_ref=rew.get("early_rz_drift_z_ref", 0.04),
        w_shape_score=rew.get("w_shape_score", 0.0),
        shape_score_r_ref=rew.get("shape_score_r_ref", 0.05),
        shape_score_z_ref=rew.get("shape_score_z_ref", 0.05),
        w_z_signed_progress=rew.get("w_z_signed_progress", 0.0),
        w_z_signed_progress_early=rew.get("w_z_signed_progress_early", 0.0),
        z_signed_progress_ref=rew.get("z_signed_progress_ref", 0.05),
        z_signed_progress_early_until_step=rew.get("z_signed_progress_early_until_step", 160),
        z_signed_progress_clip=rew.get("z_signed_progress_clip", 2.0),
        early_rz_drift_enable_z_abs_lt=rew.get("early_rz_drift_enable_z_abs_lt", -1.0),
        z_zero_cross_enable_abs_lt=rew.get("z_zero_cross_enable_abs_lt", -1.0),
        w_vessel_total=rew.get("w_vessel_total", 0.04),
        w_vessel_abs_sum=rew.get("w_vessel_abs_sum", 0.01),
        w_vessel_rms=rew.get("w_vessel_rms", 0.08),
        w_vessel_max_abs=rew.get("w_vessel_max_abs", 0.08),
        w_vessel_delta=rew.get("w_vessel_delta", 0.03),
        w_hold_vessel_multiplier=rew.get("w_hold_vessel_multiplier", 4.0),

        hold_success_bonus=rew.get("hold_success_bonus", 900.0),
        hold_eval_window_steps=rew.get("hold_eval_window_steps", 80),
        hold_success_r_tol=rew.get("hold_success_r_tol", 0.025),
        hold_success_z_tol=rew.get("hold_success_z_tol", 0.025),
        hold_success_ip_tol=rew.get("hold_success_ip_tol", 900.0),
        hold_success_velocity_norm_max=rew.get("hold_success_velocity_norm_max", 0.35),
        hold_success_action_mean_abs_max=rew.get("hold_success_action_mean_abs_max", 0.25),
        hold_success_current_util_max=rew.get("hold_success_current_util_max", 0.78),
        hold_success_vessel_total_a_max=rew.get("hold_success_vessel_total_a_max", 8000.0),
        hold_success_vessel_abs_sum_a_max=rew.get("hold_success_vessel_abs_sum_a_max", 80000.0),

        failure_penalty=rew.get("failure_penalty", failure.get("failure_penalty", -1000.0)),
        failure_penalty_per_remaining_step=rew.get("failure_penalty_per_remaining_step", failure.get("failure_penalty_per_remaining_step", -5.0)),
        survival_bonus=rew.get("survival_bonus", failure.get("survival_bonus", 100.0)),
        quality_success_bonus=rew.get("quality_success_bonus", failure.get("quality_success_bonus", failure.get("success_bonus", 500.0))),
        quality_success_r_tol=rew.get("quality_success_r_tol", failure.get("quality_success_r_tol", 0.04)),
        quality_success_z_tol=rew.get("quality_success_z_tol", failure.get("quality_success_z_tol", 0.04)),
        quality_success_ip_tol=rew.get("quality_success_ip_tol", failure.get("quality_success_ip_tol", 1200.0)),
        quality_success_max_r_error=rew.get("quality_success_max_r_error", failure.get("quality_success_max_r_error", 0.08)),
        quality_success_max_z_error=rew.get("quality_success_max_z_error", failure.get("quality_success_max_z_error", 0.08)),
        quality_success_max_ip_error=rew.get("quality_success_max_ip_error", failure.get("quality_success_max_ip_error", 2500.0)),
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
