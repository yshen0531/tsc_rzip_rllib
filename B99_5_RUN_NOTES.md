# B99.5 Run Notes

## Launch

```bash
cd /home/yangshen0711/tsc_all/tsc_rzip_rllib
unzip -o /path/to/b99_5_terminal_late_cost_runtime_only_10ms_extrema_192worker_clean.zip -d .
chmod +x run_train_b99_5_native.sh run_train_b99_5_nohup.sh run_probe_b99_5_modes.sh
./run_train_b99_5_nohup.sh
```

## Monitor

```bash
tail -f logs/nohup/latest_b99_5_train.log
```

Expected launch banner:

```text
========== B99.5 terminal/late constrained actor-dual runtime-only 10ms extrema MPO Ray init =========
ray_num_cpus     = 208
num_tsc_workers  = 192
obs_dim=53
```

## What should still be true from B99.4

```text
worker/boundary_valid_mean ≈ 1
worker/runtime_only_fast_mode_mean ≈ 1
worker/runner_timing/runtime_only_mean ≈ 1
worker/runner_timing/gotsc_subprocess_s_mean ≈ worker/runner_timing/step_total_s_mean
```

If boundary validity collapses to 0, stop and inspect GEQDSK reading. That would be an engineering regression.

## What is new to watch

B99.5 is specifically testing whether stronger terminal/late costs can pull the actor out of B99.4's biased basin.

Watch:

```text
cost/observed_R
cost/observed_Z
cost/observed_Ip
learner/actor_cost_penalty
learner/dual/lambda_R
learner/dual/lambda_Z
learner/dual/lambda_Ip
episode_terminal_R_error_mean
episode_terminal_Z_error_mean
episode_terminal_Ip_error_mean
learner/actor_mean_abs_action
fragment_mean_abs_action
```

A useful early sign is that `actor_cost_penalty` is no longer near zero while R/Z errors are large. R/Z/Ip should not settle around the B99.4 pattern:

```text
R_error ≈ -0.15~-0.16 m
Z_error ≈ -0.14 m
Ip_error ≈ -400~-550 A
```

## Decision points

- Around iter 25: verify engineering metrics, cost values, and no immediate actor/action blow-up.
- Around iter 50: compare R/Z/Ip against B99.4. If all remain in the same biased basin, stop and reassess.
- Around iter 75: if errors are moving toward zero together, continue; if the policy only trades one error for another, stop before spending another full run.

## Important limitations

The package was statically checked in the packaging environment, but it was not run against the real TSC/gotsc backend here. The first cluster launch remains the integration test.
