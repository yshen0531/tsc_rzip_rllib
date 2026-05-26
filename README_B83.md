# B83: 192-worker / 5M final-stage curriculum run

This patch moves B82 to a B83 training plan focused on actually training the final 100 ms reach-hold objective.

## Main changes

1. **5M env-step default run**
   - `configs/train_b83_192worker_5m.json`
   - `stop_env_steps = 5_000_000`

2. **Aggressive CPU parallelism**
   - `num_tsc_workers = 192`
   - `ray_num_cpus = 200`
   - `num_envs_per_tsc_worker = 1`
   - `num_cpus_per_tsc_worker = 1`

3. **Global-env-step curriculum**
   - Stage thresholds are now specified with `until_global_env_steps`, not per-worker local steps.
   - This prevents curriculum timing from changing when worker count changes.
   - Default B83 schedule:
     - stage0: < 0.4M steps, deadline 200 ms
     - stage1: < 1.0M steps, deadline 150 ms
     - stage2: < 1.8M steps, deadline 120 ms
     - stage3/final: 1.8M–5M steps, deadline 100 ms strict hold

4. **Evaluation is fixed by stage**
   - `scripts/eval_rllib_checkpoint.py` supports `--eval-stage stage0|stage1|stage2|final`.
   - `run_train_eval_native.sh` evaluates all stages after training by default:
     `stage0 stage1 stage2 final`.

5. **Bigger history stack**
   - `history_stack_steps = 16`.

6. **SAC settings adjusted for 192 workers**
   - `train_batch_size_per_learner = 8192`
   - `num_steps_sampled_before_learning_starts = 100000`
   - replay buffer capacity = 1.5M

7. **Ray-worker thread clamps**
   - Thread-limit env vars are propagated through `ray.init(runtime_env={...})`.
   - `RllibTscRzipEnv.__init__()` also calls `torch.set_num_threads(1)` and `torch.set_num_interop_threads(1)` when available.

## Run

```bash
./run_train_eval_nohup.sh configs/train_b83_192worker_5m.json
```

Monitor:

```bash
tail -f logs/nohup/latest.log
```

After training, stage-wise eval files are written under `eval_results/`.
