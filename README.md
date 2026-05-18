# tsc_rzip_rllib — B8 fixed-target 1 ms reach-hold

Standalone RLlib SAC project for TSC-based tokamak R-Z-Ip control.  This package is meant to sit next to the old `tsc_rzip_rl` directory and does **not** import code from it at runtime.

```text
/home/yangshen0711/tsc_all/
  tsc_rzip_rl/        # old project, not imported
  tsc_rzip_rllib/     # this project
  tsc_simulation/     # shared TSC tree, unchanged
```

## What changed in the B8 version

B8 is aimed at fixed-target reach-hold control with a 1 ms control cycle and a 100 ms reach deadline.

Key changes:

1. `configs/tsc_low_field_side_118.json`
   - `dt_ms` changed to `1`.
   - Coil slew rate remains `0.3 A/ms`, therefore action=1 now corresponds to `0.3 A/step` single-turn current increment.

2. `configs/train_b8_fixed_target_1ms.json`
   - New default training task.
   - Fixed target remains `R=0.75, Z=0, Ip=29779.724 A`.
   - Episode length is `250 ms` / `250 steps`.
   - Reach deadline is `100 ms`.
   - Hold starts at `100 ms` and is evaluated over an `80 ms` window.

3. Observation upgrade
   - Keeps deployable scalar vessel-current observation only: `vessel_current_total_a`.
   - Adds short history stack for MLP policy memory: recent errors, derivatives, previous actions, and scalar vessel-current proxy.
   - Does **not** expose full vessel-current distribution to the policy.

4. Reward upgrade
   - Error tracking: R/Z/Ip.
   - Damping: penalizes R/Z/Ip normalized velocity, especially near target.
   - Overshoot: penalizes fast target crossing near target.
   - Action quietness: penalizes action and action change, especially during hold.
   - Coil limits: penalizes soft current/action saturation.
   - Vessel-current penalty: observation uses total scalar only, while reward/diagnostics can use richer TSC summaries: signed total, abs-sum, rms, and max-abs.
   - Hold success now requires small error, small velocity, small action, acceptable coil utilization, and low residual vessel current.

5. Runtime robustness
   - `run_train_native.sh` raises soft `ulimit` where possible, uses short `/tmp/ry_$USER` Ray temp path, and limits BLAS/OpenMP/Torch thread fan-out.
   - `scripts/train_rllib_sac.py` also sets CPU-cluster thread defaults before importing Ray.

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

## Train B8 fixed target with 96 workers

```bash
./run_train_native.sh configs/train_b8_96worker_100k.json
```

Equivalent:

```bash
./run_train.sh
```

## Monitor

```bash
watch -n 10 'echo threads=$(ps -u $USER -L --no-headers | wc -l); echo procs=$(ps -u $USER --no-headers | wc -l); ray status | sed -n "1,40p"'
```

Check errors:

```bash
grep -RniE "nonfinite|sanitized|terminated_by_finite_guard|traceback|exception|error|failed|timeout|pthread_create|Resource temporarily unavailable" \
  /tmp/ry_${USER}/session_latest/logs | head -100
```

Analyze a run:

```bash
latest=$(ls -td ray_results/train_b8_fixed_target_1ms_96worker_100k_* | head -1)
python scripts/analyze_rllib_run.py "$latest"
```

Evaluate a checkpoint:

```bash
python scripts/eval_rllib_checkpoint.py \
  --config configs/rllib_sac.json \
  --checkpoint ray_checkpoints/<run>/final \
  --episodes 3 \
  --out eval_b8_rollout.csv
```

This writes both `eval_b8_rollout.csv` and `eval_b8_rollout.summary.json`.

## Notes on vessel-current observability

Deployment observation intentionally contains only a scalar total vessel-current proxy, because the real controller may only have access to a total vessel-current estimate.  Reward and diagnostics may use richer TSC-only summaries because reward is not deployed as a sensor input.
