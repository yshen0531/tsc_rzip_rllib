# tsc_rzip_rllib — B8.1 fixed-target 1 ms reach-hold

Standalone RLlib SAC project for TSC-based tokamak R-Z-Ip control. This package is meant to sit next to the old `tsc_rzip_rl` directory and does **not** import code from it at runtime.

```text
/home/yangshen0711/tsc_all/
  tsc_rzip_rl/        # old project, not imported
  tsc_rzip_rllib/     # this project
  tsc_simulation/     # shared TSC tree, unchanged
```

## What changed in B8.1

B8.1 fixes the reward loophole found in the first B8 100k run: the policy was receiving a fast-reach bonus even when it had not truly reached and slowed down. The task remains fixed-target, 1 ms control, 100 ms reach deadline, and 250 ms episode length.

Key changes:

1. Strict reach condition
   - First reach and fast-reach eligibility now require per-channel tolerances:
     `|R_error|`, `|Z_error|`, and `|Ip_error|` must all be small.
   - Reach also requires small normalized velocity, so a high-inertia pass through the target is not rewarded.
   - Default strict reach thresholds are `R/Z = 8 mm`, `Ip = 800 A`, `velocity_norm <= 0.8`.

2. Fast reach bonus disabled by default
   - `fast_reach_bonus = 0.0` in the default config.
   - The field remains supported, but should only be re-enabled after strict reach diagnostics look correct.

3. Stronger R/Z shaping, especially Z
   - Default `w_z` increased to `2.0` and `w_ip` to `0.5`.
   - Hold-stage Z penalty is also stronger.

4. Error-growth penalty
   - Penalizes the weighted tracking score when it gets worse from one step to the next.
   - Stronger before the 100 ms deadline and near the target.

5. Smooth reach-to-hold transition
   - Hold penalties ramp from 80 ms to 120 ms instead of switching abruptly at 100 ms.
   - This starts braking before the deadline and avoids a reward cliff.

6. Vessel-current handling preserved
   - Observation still exposes only scalar total vessel current, matching the planned deployable signal.
   - Reward/diagnostics may still use TSC-only `abs_sum/rms/max_abs` summaries.

7. Evaluation upgraded
   - `scripts/eval_rllib_checkpoint.py` no longer uses deprecated `local_mode=True`.
   - It uses RLlib new-stack `RLModule.forward_inference()` instead of old `compute_single_action()`.
   - Summary JSON now reports reach time, stable hold time, terminal errors, overshoot, action quietness, vessel residuals, and hold-window metrics.

8. Background training scripts added
   - `run_train_nohup.sh`
   - `stop_train_nohup.sh`

## Install

```bash
cd /home/yangshen0711/tsc_all/tsc_rzip_rllib
python3.12 -m venv venv
source venv/bin/activate
pip install -U pip setuptools wheel
pip install -r requirements.txt
```

If torch is not installed in your environment, install CPU torch separately:

```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

## Quick mock test

```bash
./run_debug_native.sh configs/debug_b8_mock.json
```

## Train B8.1 fixed target with 96 workers

Foreground:

```bash
./run_train_native.sh configs/train_b81_96worker_100k.json
```

Background/nohup:

```bash
./run_train_nohup.sh configs/train_b81_96worker_100k.json
```

Monitor:

```bash
tail -f logs/nohup/latest.log
```

Stop:

```bash
bash stop_train_nohup.sh
```

Longer short-run after the 100k sanity check:

```bash
./run_train_nohup.sh configs/train_b81_96worker_300k.json
```

## Analyze a run

```bash
latest=$(ls -td ray_results/train_b81_96worker_100k_* | head -1)
python scripts/analyze_rllib_run.py "$latest"
```

## Evaluate a checkpoint

```bash
ray stop --force
rm -rf /tmp/ry_eval_${USER}
export RAY_TMPDIR=/tmp/ry_eval_${USER}
export TMPDIR=/tmp/ry_eval_${USER}/tmp
mkdir -p "$TMPDIR"

python scripts/eval_rllib_checkpoint.py \
  --config configs/rllib_sac.json \
  --checkpoint ray_checkpoints/<run>/final \
  --episodes 3 \
  --out eval_b81_rollout.csv
```

This writes both `eval_b81_rollout.csv` and `eval_b81_rollout.summary.json`.

## Monitor Ray/TSC health

```bash
watch -n 10 'echo threads=$(ps -u $USER -L --no-headers | wc -l); echo procs=$(ps -u $USER --no-headers | wc -l); ray status | sed -n "1,40p"'
```

Check errors:

```bash
grep -RniE "nonfinite|sanitized|terminated_by_finite_guard|traceback|exception|error|failed|timeout|pthread_create|Resource temporarily unavailable" \
  /tmp/ry_${USER}/session_latest/logs | head -100
```
