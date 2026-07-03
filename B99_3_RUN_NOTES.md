# B99.3 run notes

## Start

```bash
cd /home/yangshen0711/tsc_all/tsc_rzip_rllib
unzip -o /path/to/b99_3_fast_runtime_only_10ms_extrema_224worker_clean.zip -d .
chmod +x run_train_b99_3_native.sh run_train_b99_3_nohup.sh run_probe_b99_3_modes.sh
./run_train_b99_3_nohup.sh
```

Watch:

```bash
tail -f logs/nohup/latest_b99_3_train.log
```

Expected startup lines include:

```text
[run_train_b99_3_native] nproc=256 nproc_all=256
Cpus_allowed_list: 0-255
config=configs/mpo_b99_3_fast_runtime_only_10ms_extrema_224worker.json
ray_num_cpus = 240
num_tsc_workers = 224
obs_dim=53
```

`obs_dim=53` means the 9 compact boundary-extrema features are included.

## First things to check

### Boundary actually working

Look for columns like:

```text
worker/boundary_valid_mean
worker/boundary_num_points_mean
worker/boundary_R_left_mean
worker/boundary_R_right_mean
worker/boundary_Z_bottom_mean
worker/boundary_Z_top_mean
worker/boundary_source_is_gfile_mean
```

Healthy behavior should normally have `boundary_valid_mean` near 1 and `boundary_num_points_mean` well above the configured minimum.  If `boundary_valid_mean` is 0, compact extrema are present in the observation dimension but not receiving real plasma-boundary points.

### Runtime-only timing

Look for columns like:

```text
worker/runner_timing/gotsc_subprocess_s_mean
worker/runner_timing/write_input_s_mean
worker/runner_timing/restart_update_s_mean
worker/runner_timing/read_state_after_s_mean
worker/runner_timing/save_artifacts_s_mean
worker/runner_timing/step_total_s_mean
```

Interpretation:

- If `gotsc_subprocess_s_mean` dominates `step_total_s_mean`, the remaining bottleneck is TSC itself.
- If `restart_update_s_mean`, `read_state_after_s_mean`, or `save_artifacts_s_mean` are large, the file/runtime flow is still worth optimizing.
- With `save_step_artifacts=false`, `save_artifacts_s_mean` should normally be near zero except sampled/error cases.

### Learner timing

After replay warmup, inspect:

```text
timing/learner_train_s
timing/learner_sample_batch_s
timing/learner_update_call_s
learner/timing_update_total_s
learner/timing_critic_s
learner/timing_candidate_q_s
learner/timing_actor_loss_s
learner/timing_actor_opt_s
```

B99.3 does not reduce `updates_per_iter`; it only measures the learner more clearly.

## Stop criteria

Stop and inspect if:

- `boundary_valid_mean` stays 0.
- `gotsc_subprocess_s_mean` or `step_total_s_mean` is much worse than B99.2.
- `gotsc` worker count is far below 224 for long periods.
- Learner losses produce NaN.
- Ray fd or process count errors reappear.

## Notes on artifacts

Runtime-only mode still reads current `runtime/geqdsk`.  It only stops saving historical copies of every step's large files.  If TSC fails, current runtime files are saved under a failure artifact directory for debugging.
