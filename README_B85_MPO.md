# B85 Asymmetric Recurrent MPO patch

This patch adds a new training path for **Asymmetric Recurrent MPO** without removing the existing SAC/RLlib path.

## Core design

- **Actor**: recurrent Gaussian policy, deployable observation only.
- **Critic**: recurrent Q critics, asymmetric input = deployable obs + TSC privileged info + action.
- **Rollout**: 192 independent TSC workers through one Ray cluster.
- **Replay**: sequence replay buffer for recurrent off-policy training.
- **MPO update**:
  - critic TD learning with target critics;
  - E-step candidate action sampling and Q-weighted action distribution;
  - adaptive eta dual update;
  - M-step weighted log-likelihood with KL trust penalty.

The first B85 config uses single-frame deployable observation plus GRU memory.  Critic-only privileged features are built from env `info`, including tracking diagnostics, vessel current summaries, and coil currents.

## Files

```text
configs/mpo_b85_recurrent_192worker_5m.json
configs/mpo_b85_recurrent_192worker_1m_probe.json
configs/train_b85_mpo_fixed_target_1ms.json
scripts/train_mpo.py
scripts/eval_mpo_policy.py
tsc_rzip_rllib/mpo/__init__.py
tsc_rzip_rllib/mpo/models.py
tsc_rzip_rllib/mpo/privileged.py
tsc_rzip_rllib/mpo/replay.py
run_train_mpo_native.sh
run_train_mpo_nohup.sh
run_eval_mpo_policy.sh
stop_train_mpo_nohup.sh
```

## Install

```bash
cd /home/yangshen0711/tsc_all/tsc_rzip_rllib
unzip -o /path/to/tsc_rzip_b85_asym_recurrent_mpo_patch.zip
chmod +x run_train_mpo_native.sh run_train_mpo_nohup.sh run_eval_mpo_policy.sh stop_train_mpo_nohup.sh scripts/train_mpo.py scripts/eval_mpo_policy.py
```

## Run full 5M training

```bash
./run_train_mpo_nohup.sh configs/mpo_b85_recurrent_192worker_5m.json
tail -f logs/nohup/latest_mpo.log
```

## Optional 1M probe

```bash
./run_train_mpo_nohup.sh configs/mpo_b85_recurrent_192worker_1m_probe.json
```

## Evaluate checkpoint

```bash
./run_eval_mpo_policy.sh \
  configs/mpo_b85_recurrent_192worker_5m.json \
  mpo_checkpoints/<run_name>/final \
  eval_results/b85_mpo_final_deterministic.csv \
  final \
  deterministic \
  5

./run_eval_mpo_policy.sh \
  configs/mpo_b85_recurrent_192worker_5m.json \
  mpo_checkpoints/<run_name>/final \
  eval_results/b85_mpo_final_stochastic.csv \
  final \
  stochastic \
  5
```

## Main early success indicators

Before demanding final hold success, check:

- reach-phase `mean_abs_action` is no longer near zero;
- `terminal_Z_error` and `Z_error@100ms` improve versus B83;
- checkpoint deterministic eval no longer collapses to no-op.

If learner update becomes the bottleneck, first reduce `num_action_samples` from 32 to 16 or reduce `updates_per_iter`; do not reduce TSC workers unless Ray/OS resources are overloaded.
