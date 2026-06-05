# B88 Z-Recovery Relaxed-Ip-Lite MPO

This patch follows B87. B87 protected R but suppressed useful vertical correction.
B88 keeps the B86/B87 recurrent MPO learner settings, keeps Ip relaxed, weakens the heavy B87 R/shape barriers, and adds explicit signed Z-error progress reward.

## Key changes

- New configs:
  - `configs/train_b88_z_recovery_relaxed_ip_mpo_fixed_target_1ms.json`
  - `configs/mpo_b88_z_recovery_relaxed_ip_recurrent_192worker_1m_probe.json`
  - `configs/mpo_b88_z_recovery_relaxed_ip_recurrent_5m.json`
- New environment reward terms:
  - `w_z_signed_progress`
  - `w_z_signed_progress_early`
  - `z_signed_progress_ref`
  - `z_signed_progress_early_until_step`
  - `z_signed_progress_clip`
  - `early_rz_drift_enable_z_abs_lt`
  - `z_zero_cross_enable_abs_lt`
- Weak R corridor protection instead of B87 strong R lock:
  - `w_negative_r_bias` reduced to ~0.6--1.2
  - `negative_r_bias_threshold_m` relaxed to -0.09/-0.10 m
  - `w_rz_max_error` and `w_shape_score` reduced strongly
- Relaxed Ip remains:
  - final `reach_success_ip_tol = 3000 A`
  - final `hold_success_ip_tol = 4000 A`
  - `w_ip = 0.05`
- Actor settings remain balanced:
  - no upper scalar policy-loss clip
  - `policy_loss_lower_clip = -8.0`
  - action scale schedule `0.45 -> 0.55`, no `0.65` stage

## Run

```bash
cd /home/yangshen0711/tsc_all/tsc_rzip_rllib
unzip -o /path/to/tsc_rzip_b88_z_recovery_relaxed_ip_mpo_patch.zip
chmod +x scripts/train_mpo.py scripts/eval_mpo_policy.py run_train_mpo_native.sh run_train_mpo_nohup.sh stop_train_mpo_nohup.sh run_eval_mpo_policy.sh run_eval_mpo_b88_sweep.sh
export TSC_ALL_ROOT=/home/yangshen0711/tsc_all
./run_train_mpo_nohup.sh configs/mpo_b88_z_recovery_relaxed_ip_recurrent_192worker_1m_probe.json
tail -f logs/nohup/latest_mpo.log
```

## Probe criteria

- iter50: `|Z_error|` should start dropping below about 0.24 m.
- iter75: `|Z_error|` should be below about 0.18--0.20 m, while `R_error > -0.10 m`.
- iter100: target `|Z_error| < 0.12--0.15 m`, `R_error > -0.11 m`, `|Ip_error| < 3000 A`.
- Stop if deterministic mean action collapses below 0.02 or grows above 0.60.
