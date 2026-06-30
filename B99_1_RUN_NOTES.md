# B99.1 run notes

## Run

```bash
cd /home/yangshen0711/tsc_all/tsc_rzip_rllib
unzip -o /path/to/b99_1_constrained_goal_10ms_clean.zip -d .
chmod +x run_train_b99_1_native.sh run_train_b99_1_nohup.sh run_probe_b99_1_modes.sh
./run_train_b99_1_nohup.sh
```

## Log

```bash
tail -f logs/nohup/latest_b99_1_train.log
```

## First-screen checks

Look for:

```text
[run_train_b99_1_native] limit after set : ulimit -u=30000 ulimit -n=...
========== B99.1 10ms constrained goal-conditioned MPO Ray init =========
ray_num_cpus     = 136
num_tsc_workers  = 128
[train_mpo] spaces: obs_dim=... priv_dim=... action_dim=14
```

Also check the resolved TSC config:

```text
dt_ms = 10
current_slew_a_per_ms = 0.3
```

This means each policy step can request up to 3 A per single-turn channel, while respecting the same 0.3 A/ms slew under TSC linear interpolation.

## Main diagnostics

Do not judge only by fixed target early in training. Watch:

```text
eval_grid_R_target_to_terminal_R_slope
eval_grid_Z_target_to_terminal_Z_slope
dual/lambda_R
dual/lambda_Z
dual_actor_scale
dual_update_scale
actor_mean_abs_action
cost/actor_q_R and cost/actor_q_raw_R
```

A healthy B99.1 should show:

- fixed/grid eval present, not `Cannot find eval stage 'final'`;
- `dual_actor_scale` and `dual_update_scale` ramp from 0 toward 1;
- lambda values do not immediately hit max;
- action mean does not jump above 0.5 too early;
- target-grid slopes eventually become positive.
