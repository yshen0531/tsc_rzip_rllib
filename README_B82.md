# tsc_rzip_rllib B8.2-RL long training package

This package keeps the RL direction: no hand-coded coil-combination policy, no behavior cloning, no action prior.
The probe/response results are only used to improve reward density, curriculum, scaling, and exploration.

## Main entry points

Long train + automatic final eval, with nohup:

```bash
./run_train_eval_nohup.sh configs/train_b82_96worker_2m.json
```

Monitor:

```bash
tail -f logs/nohup/latest.log
```

Stop:

```bash
bash stop_train_nohup.sh
```

Shorter alternatives:

```bash
./run_train_eval_nohup.sh configs/train_b82_96worker_500k.json
./run_train_eval_nohup.sh configs/train_b82_96worker_1m.json
```

Foreground training only:

```bash
./run_train_native.sh configs/train_b82_96worker_2m.json
```

Final checkpoint eval only:

```bash
python scripts/eval_rllib_checkpoint.py \
  --config configs/rllib_sac.json \
  --override configs/train_b82_96worker_2m.json \
  --checkpoint ray_checkpoints/<run_id>/final \
  --episodes 5 \
  --out eval_results/eval_b82_final.csv
```

## What changed vs B8.1

- Dense signed progress shaping: reward is positive when the weighted R/Z/Ip score improves and negative when it gets worse.
- Easier-to-harder curriculum using per-worker local steps:
  - 200 ms deadline / loose hold;
  - 150 ms deadline;
  - 120 ms deadline;
  - final 100 ms strict hold.
- Early reach phase allows more action and less vessel penalty; hold phase ramps action/vessel/damping penalties smoothly.
- Observation includes deadline fraction and hold-weight scalar in addition to existing history stack.
- SAC exploration is strengthened with larger random warmup and initial entropy coefficient.
- `run_train_eval_nohup.sh` runs training, analyzes the run, and evaluates the final checkpoint in one background job.

## Notes

- `num_tsc_workers=96` and `num_envs_per_tsc_worker=1` remain the default because this was the measured throughput sweet spot.
- The curriculum uses `until_local_steps`, not aggregate env steps. With 96 workers, local steps are roughly aggregate steps / 96.
- This package intentionally does not encode any probe-discovered action sequence or traditional controller.
