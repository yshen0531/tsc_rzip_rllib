# B99.4 Run Notes

## Run command

```bash
cd /home/yangshen0711/tsc_all/tsc_rzip_rllib
unzip -o /path/to/b99_4_stabilized_actor_dual_runtime_only_10ms_extrema_192worker_clean.zip -d .
chmod +x run_train_b99_4_native.sh run_train_b99_4_nohup.sh run_probe_b99_4_modes.sh
./run_train_b99_4_nohup.sh
```

Log:

```bash
tail -f logs/nohup/latest_b99_4_train.log
```

## Expected startup lines

You should see:

```text
[run_train_b99_4_native] nproc=... nproc_all=...
Cpus_allowed_list: ...
config=configs/mpo_b99_4_stabilized_actor_dual_runtime_only_10ms_extrema_192worker.json
========== B99.4 stabilized actor-dual runtime-only 10ms extrema MPO Ray init =========
ray_num_cpus     = 208
num_tsc_workers  = 192
obs_dim=53
```

`nproc` may still be affected by shell/cgroup reporting, but `Cpus_allowed_list` and the actual number of `gotsc` processes are the real checks.

## First things to verify

### Engineering/runtime

- `worker/runtime_only_fast_mode_mean` should be `1.0`.
- `worker/boundary_valid_mean` should be close to `1.0`.
- `worker/boundary_missing_mean` should be close to `0.0`.
- `worker/boundary_source_is_gfile_mean` should be close to `1.0`.
- `worker/runner_timing/gotsc_subprocess_s_mean` will likely dominate `worker/runner_timing/step_total_s_mean`.

### Stabilization goal

Compared with B99.3, watch especially:

- `learner/actor_mean_abs_action`
- `fragment_mean_abs_action`
- `episode_terminal_R_error_mean`
- `episode_terminal_Z_error_mean`
- `episode_terminal_Ip_error_mean`
- `learner/actor_action_l2_penalty`
- `learner/actor_action_saturation_penalty`
- `learner/actor_cost_penalty`
- `learner/dual_actor_scale`
- `learner/dual_update_scale`
- `learner/dual/lambda_R`
- `learner/dual/lambda_Z`

The desired early sign is not necessarily immediate success. The key is that the actor should not rapidly become a broad large-action template while R/Z/Ip all drift away.

## Suggested decision points

- After learner updates begin, inspect the next 10–20 iterations.
- If R/Z/Ip errors still all drift and `actor_mean_abs_action` again climbs toward `0.6–0.8`, stop early and revise.
- If R/Z improve or at least do not deteriorate while actions grow more slowly, continue toward the first deterministic probe/checkpoint.

## Important caveat

B99.4 has passed static Python/JSON checks, but it has not been run with the actual TSC/gotsc inside this packaging environment. Treat the first real launch as the integration test.
