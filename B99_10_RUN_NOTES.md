# B99.10 Train-First — Run Notes

## Package identity

Use the config:

```text
configs/mpo_b99_10_resume_b99_9_train_first_light_transaction_runtime_only_192worker.json
```

Do not use the earlier heavy B99.10 adaptive/seven-scenario-every-transaction package.

## Recommended B99.9 checkpoints

```bash
export B99_9_RUN_DIR=/path/to/train_b99_9_resume_b99_8_transactional_line_search_ip_relaxed_runtime_only_mpo_192worker_...
export B99_9_BASE_CKPT="$B99_9_RUN_DIR/iter_000170"
export B99_9_ACCEPTED_CKPT="$B99_9_RUN_DIR/accepted_latest"
```

The periodic checkpoint supplies critic weights. `accepted_latest` supplies the tenth accepted B99.9 actor, log-eta and protected dual values.

## Start

```bash
cd /home/yangshen0711/tsc_all/tsc_rzip_rllib
unzip -o /path/to/b99_10_resume_b99_9_train_first_light_transaction_runtime_only_192worker_clean.zip -d .

chmod +x \
  run_train_b99_10_resume_b99_9_train_first_native.sh \
  run_train_b99_10_resume_b99_9_train_first_nohup.sh \
  run_resume_b99_10_latest_native.sh \
  run_resume_b99_10_latest_nohup.sh \
  run_stop_b99_10_now.sh \
  run_probe_b99_10_train_first_modes.sh

./run_train_b99_10_resume_b99_9_train_first_nohup.sh
```

## Log

```bash
tail -f logs/nohup/latest_b99_10_resume_b99_9_train_first_train.log
```

## Immediate stop

```bash
./run_stop_b99_10_now.sh
```

This does not wait for a transaction, checkpoint or final evaluation. The in-progress operation can be lost. The previous atomically completed checkpoint remains the intended recovery point.

## Resume after immediate stop

```bash
export B99_10_RUN_DIR=/path/to/train_b99_10_resume_b99_9_train_first_light_transaction_runtime_only_mpo_192worker_...
./run_resume_b99_10_latest_nohup.sh
```

The launcher uses the newest complete `iter_*` for critics and `accepted_latest` for the protected actor. Transaction baseline episodes are recomputed after process restart.

## Expected schedule

If B99.9 iter170 is used:

- B99.10 resumes around iteration 170;
- critics train on the new reward for ten iterations;
- first transaction is expected around iteration 180;
- later transactions are approximately every six iterations.

Replay is rebuilt, so the earliest resumed iteration may have no learner update until enough fragments are available.

## Transaction compute

### Normal transaction

After baseline cache initialization, typical rank-1 acceptance costs:

```text
4 fixed candidates + 1 highR/lowZ validation = 5 deterministic TSC episodes
```

If rank 1 fails, rank 2 adds one more highR/lowZ episode.

### Every third accepted update

A seven-scenario audit adds:

- five missing baseline audit episodes;
- five candidate audit episodes.

This audit is intentionally low-frequency.

## Primary metrics

### Training objective alignment

```text
worker/soft_rz_distance_mean
worker/soft_rz_progress_mean
worker/soft_rz_distance_penalty_mean
worker/soft_rz_progress_bonus_mean
worker/rz_velocity_norm_mean
worker/soft_rz_outward_velocity_penalty_mean
worker/soft_rz_near_velocity_penalty_mean
```

### Transaction

```text
actor_txn/status
actor_txn/reason
actor_txn/selected_alpha
actor_txn/selected_rank
actor_txn/aggregate_improvement
actor_txn/max_scenario_regression
actor_txn/audit_due
actor_txn/audit_aggregate
actor_txn/audit_aggregate_improvement
actor_txn/audit_max_scenario_regression
actor_txn/current_candidate_alphas
actor_txn/adaptive_alpha_mode
timing/actor_transaction_s
```

Detailed fixed/hard/audit results are in:

```text
actor_txn/detail
actor_transactions.jsonl
```

## Signals that B99.10 is helping the core task

- transaction improvement materially exceeds the B99.9 average of about `0.029`;
- soft R/Z distance decreases in both rollout and deterministic fixed/hard probes;
- late fraction within 2× tolerance begins to rise;
- late velocity RMS decreases rather than only terminal R/Z improving;
- selected alpha moves away from always sitting at the negative search boundary;
- critic proposal positive direction becomes less consistently wrong over time;
- fixed-target rollout quality improves without actor action magnitude increasing.

## Warning signals

- three consecutive rejected transactions;
- three accepted transactions below `0.008` improvement;
- soft distance improves but late velocity RMS worsens repeatedly;
- audit rejects candidates that passed fixed plus hard;
- actor action magnitude rises toward `0.5–0.6`;
- fixed-target performance does not improve after the ten-iteration critic settle period;
- positive/negative candidate ordering remains identical to B99.9 and improvement remains millimetre-scale.

## Important interpretation

The first transaction is not expected to prove success. The reward target has changed, old critic weights are only an initialization, optimizer momentum is reset and replay is rebuilt. The first useful question is whether the critic proposal ordering begins to align better with the real-TSC fixed-plus-hard score after the settle period.
