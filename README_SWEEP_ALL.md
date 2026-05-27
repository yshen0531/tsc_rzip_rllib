# B83 all checkpoint sweep + stochastic eval

This wrapper runs one full pass:

- all checkpoints under the given checkpoint root (`iter_000025`, `iter_000050`, ..., `final`)
- all eval stages: `stage0,stage1,stage2,final`
- both action modes: `deterministic,stochastic`
- deterministic: 1 episode/job
- stochastic: 3 episodes/job

Default parallelism is `96` eval jobs with `2` Ray logical CPUs per job, intended to use about 192 CPUs on a 256-core server.

## Usage

```bash
chmod +x run_eval_checkpoint_sweep_all_nohup.sh

./run_eval_checkpoint_sweep_all_nohup.sh \
  ray_checkpoints/train_b83_192worker_5m_20260520_142028 \
  96 \
  2
```

If no checkpoint root is supplied, the wrapper uses the latest `ray_checkpoints/train_b83_*` directory.

## More aggressive option

If the server remains stable and you want more parallel eval processes:

```bash
./run_eval_checkpoint_sweep_all_nohup.sh \
  ray_checkpoints/train_b83_192worker_5m_20260520_142028 \
  128 \
  1
```

This starts more Ray instances, so it may not be faster even if CPU idle looks high.

## Monitor

```bash
tail -f logs/eval_sweep_nohup/latest.log
```

## Stop

```bash
bash stop_eval_checkpoint_sweep.sh
```

## Results

```bash
latest=$(ls -td eval_sweeps/*sweep_* | head -1)
column -s, -t "$latest/sweep_results.csv" | less -S
```
