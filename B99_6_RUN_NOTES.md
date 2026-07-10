# B99.6 run notes

## Intended run mode

B99.6 is intended to be run as **Scheme B**: resume from the B99.5 `iter_000025`
checkpoint.

Default resume checkpoint:

```bash
mpo_checkpoints/train_b99_5_terminal_late_cost_runtime_only_10ms_extrema_from_scratch_mpo_192worker/iter_000025
```

If your checkpoint is elsewhere, set:

```bash
export B99_5_RESUME_CKPT=/absolute/or/relative/path/to/iter_000025
```

## Start training

```bash
cd /home/yangshen0711/tsc_all/tsc_rzip_rllib
unzip -o /path/to/b99_6_resume_b99_5_iter25_actor_slow_ip_tight_runtime_only_192worker_clean.zip -d .
chmod +x run_train_b99_6_resume_b99_5_iter25_native.sh run_train_b99_6_resume_b99_5_iter25_nohup.sh run_probe_b99_6_modes.sh
./run_train_b99_6_resume_b99_5_iter25_nohup.sh
```

Watch:

```bash
tail -f logs/nohup/latest_b99_6_resume_b99_5_iter25_train.log
```

Expected banner:

```text
B99.6 resume-B99.5-iter25 actor-slow terminal/late cost runtime-only 10ms extrema MPO Ray init
```

## Important resume behavior

The checkpoint resume restores model weights and statistics, but the replay buffer
is not restored.  Therefore the first resumed iteration may have
`updates_this_iter = 0` or fewer updates until the new replay buffer has enough
fresh fragments.  This is expected.

B99.6 deliberately resets optimizer state and cost critics because cost definitions
changed relative to B99.5.  It loads only dual lambda values and reapplies B99.6
dual target/lr/max values from config.

## What to watch

Primary success signs:

- `learner/actor_mean_abs_action` stays below roughly `0.4-0.5` in the early/mid run.
- `episode_terminal_R_error_mean` does not slide past `-0.18 m` and ideally returns toward `-0.12 m` or better.
- `episode_terminal_Z_error_mean` stays within roughly `±0.08 m`.
- `episode_terminal_Ip_error_mean` stays within roughly `±500-1000 A` and does not drift to `-2000 A`.
- `cost/observed_Ip` is no longer nearly zero when Ip is off by ~2000 A.
- `learner/policy_loss_used` does not sit at the lower clip for many consecutive iterations while the actor grows.

Engineering sanity checks:

- `worker/boundary_valid_mean = 1.0`
- `worker/runner_timing/runtime_only_mean = 1.0`
- `worker/runner_timing/gotsc_subprocess_s_mean` still dominates step time.

Best checkpoint paths:

```bash
mpo_checkpoints/train_b99_6_resume_b99_5_iter25_actor_slow_ip_tight_runtime_only_mpo_192worker/best_error_score
mpo_checkpoints/train_b99_6_resume_b99_5_iter25_actor_slow_ip_tight_runtime_only_mpo_192worker/best_return
```

Probe default:

```bash
./run_probe_b99_6_modes.sh
```

Override probe checkpoint:

```bash
B99_6_PROBE_CKPT=mpo_checkpoints/.../iter_000040 ./run_probe_b99_6_modes.sh
```
