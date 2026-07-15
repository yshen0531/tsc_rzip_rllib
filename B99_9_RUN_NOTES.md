# B99.9 Run Notes

## Run

```bash
cd /home/yangshen0711/tsc_all/tsc_rzip_rllib
unzip -o /path/to/b99_9_resume_b99_8_transactional_line_search_ip_relaxed_runtime_only_192worker_clean.zip -d .

chmod +x run_train_b99_9_resume_b99_8_transactional_native.sh \
         run_train_b99_9_resume_b99_8_transactional_nohup.sh \
         run_probe_b99_9_modes.sh

./run_train_b99_9_resume_b99_8_transactional_nohup.sh
```

The script selects the newest B99.8 checkpoint run and uses:

```text
base critics: final/, otherwise highest iter_*
protected actor: best_error_score/
```

To override paths:

```bash
export B99_8_RUN_DIR=/path/to/train_b99_8...checkpoint_run
export B99_8_BASE_CKPT=/path/to/final_or_iter_checkpoint
export B99_8_BEST_ERROR_CKPT=/path/to/best_error_score
./run_train_b99_9_resume_b99_8_transactional_nohup.sh
```

## Log

```bash
tail -f logs/nohup/latest_b99_9_resume_b99_8_transactional_train.log
```

Transaction records are also written to:

```text
ray_results/<B99.9 run>/actor_transactions.jsonl
```

## Expected start-up messages

```text
loading resume checkpoint: .../B99.8/final or iter_*
overriding protected policy from: .../B99.8/best_error_score
Policy override: actor optimizer reset
Policy override: loaded protected checkpoint dual values
B99.9 transactional actor guard enabled
```

## Transaction timing

The first transaction is intentionally expensive:

- 3 baseline scenarios;
- 5 line-search candidates on the fixed target;
- 2 validation scenarios for the selected candidate.

That is up to 10 deterministic TSC episodes. Later transactions reuse the accepted baseline cache and require up to 7 episodes. This is deliberate: candidate acceptance is based on real TSC behavior, not critic prediction.

## Key fields

```text
actor_txn/due
actor_txn/status
actor_txn/reason
actor_txn/attempts
actor_txn/accepted
actor_txn/rejected
actor_txn/consecutive_rejections
actor_txn/baseline_aggregate
actor_txn/best_aggregate
actor_txn/selected_alpha
actor_txn/aggregate_improvement
actor_txn/max_scenario_regression
timing/actor_transaction_s
```

Detailed per-candidate and per-scenario values are under:

```text
actor_txn/detail
```

## Interpret results

### Accepted

```text
actor_txn/status = accepted
actor_txn/aggregate_improvement > 0
actor_txn/max_scenario_regression <= 0.05
```

The actor is committed, Adam is reset, workers are synchronized, and `accepted_latest` is saved.

### Rejected

```text
actor_txn/status = rejected
```

The actor, eta, optimizers and update count are restored exactly. Critic learning from the proposal batch is retained.

### Negative alpha accepted

A selected `alpha=-0.25` is not automatically an error. It means the real TSC evaluation preferred a small step opposite to the critic-derived actor proposal. This is evidence of critic/policy-gradient mismatch and should be recorded, not hidden.

## Automatic stop

The run stops after either:

```text
12 total transactions
6 consecutive rejected/error transactions
stop_env_steps = 1,200,000
```

This avoids spending indefinitely on an actor direction that real TSC repeatedly rejects.

## What counts as progress

The primary evidence is a lower reliable three-scenario aggregate score, driven mainly by:

```text
late R RMS
late Z RMS
terminal R/Z
late hold fraction
```

Ip differences of 1000 A or several kA can be accepted when R/Z and hold behavior improve, provided Ip remains within the broad soft safety envelope.
