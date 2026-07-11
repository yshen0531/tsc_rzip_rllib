# B99.7 run notes

B99.7 should be run after stopping B99.6.  It resumes from the B99.6
`best_error_score` checkpoint rather than from the latest B99.6 checkpoint.

## Run

```bash
cd /home/yangshen0711/tsc_all/tsc_rzip_rllib
unzip -o /path/to/b99_7_resume_b99_6_best_error_actor_freeze_runtime_only_192worker_clean.zip -d .
chmod +x run_train_b99_7_resume_b99_6_best_error_native.sh \
         run_train_b99_7_resume_b99_6_best_error_nohup.sh \
         run_probe_b99_7_modes.sh
./run_train_b99_7_resume_b99_6_best_error_nohup.sh
```

The script auto-detects the newest B99.6 best-error checkpoint matching:

```text
mpo_checkpoints/train_b99_6_resume_b99_5_iter25_actor_slow_ip_tight_runtime_only_mpo_192worker_*/best_error_score
```

If needed, override it explicitly:

```bash
export B99_6_BEST_ERROR_CKPT=/path/to/best_error_score
./run_train_b99_7_resume_b99_6_best_error_nohup.sh
```

## Monitor

```bash
tail -f logs/nohup/latest_b99_7_resume_b99_6_best_error_train.log
```

Expected banner:

```text
B99.7 resume-B99.6-best-error actor-freeze runtime-only 10ms extrema MPO Ray init
```

## Important expected behavior

The first resumed iteration may have few or zero updates if replay needs to be
refilled.  This is normal because the replay buffer is not restored.

During the actor-freeze window, expect:

```text
learner/actor_frozen = 1
learner/actor_update_applied = 0
learner/eta_update_applied = 0
learner/actor_freeze_remaining_env_steps > 0
```

Critic, cost critic, and dual updates should still run.

When the freeze ends, expect:

```text
learner/actor_frozen = 0
```

Actor updates then happen only every 16 learner updates.

## Key metrics

Watch:

```text
best/error_score
best/error_score_improved
best/error_score_iters_since_improvement
learner/actor_frozen
learner/actor_mean_abs_action
episode_terminal_R_error_mean
episode_terminal_Z_error_mean
episode_terminal_Ip_error_mean
learner/dual/lambda_R
learner/dual/lambda_Z
learner/dual/lambda_Ip
worker/boundary_valid_mean
worker/runner_timing/gotsc_subprocess_s_mean
```

Good signs:

- `best/error_score` improves beyond the resumed best;
- actor mean action stays moderate, ideally not quickly exceeding 0.35--0.45;
- R remains around -0.13 m or improves;
- Z stays near zero instead of drifting strongly negative;
- Ip stays within several hundred amps;
- hold_success begins to appear.

Stop signs:

- no best-error improvement for 30 iterations, which should trigger automatic
  stop;
- actor mean action climbs again to 0.6+;
- R/Z/Ip all drift away from the B99.6 best-error region.

## Probe

After a run, probe the best checkpoint with:

```bash
./run_probe_b99_7_modes.sh
```

or specify a checkpoint:

```bash
B99_7_PROBE_CKPT=/path/to/checkpoint_dir ./run_probe_b99_7_modes.sh
```
