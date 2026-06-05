# B87 Shape-First Relaxed-Ip Recurrent MPO

## Why B87

B86 restored deterministic actor learning and avoided the B85c no-op collapse, but the final deterministic trajectories showed a new failure mode:

- Iter 75: gentle action, good Ip, but R/Z remain far from target.
- Iter 100: useful medium action, better return, but R drifts negative and Z/Ip overshoot after zero-crossing.

B87 keeps the B86 actor mechanism, but changes the task objective to shape-first relaxed-Ip control.

## Key changes

1. Ip is relaxed so it does not dominate the reward:
   - final reach Ip tolerance: 3000 A
   - final hold Ip tolerance: 4000 A
   - quality Ip tolerance: 3000 A
   - max Ip trajectory tolerance: 6000 A
   - w_ip: about 0.08
   - w_hold_ip: about 0.12

2. R/Z are prioritized:
   - stronger w_r and w_z
   - stronger hold R/Z weights
   - negative-R bias penalty when R_error < -0.05 m
   - R guard starts at 0.05 m

3. New B87 reward terms in `rzip_env.py`:
   - `w_rz_max_error`
   - `w_hold_rz_max_error`
   - `w_max_error` with relaxed Ip reference
   - `w_negative_r_bias`
   - `w_z_zero_cross_overshoot`
   - `w_ip_zero_cross_overshoot`
   - `w_early_rz_drift`
   - `w_shape_score`

4. Actor settings remain balanced:
   - no symmetric policy-loss clip
   - `policy_loss_lower_clip = -6.0`
   - action scale schedule: 0.45 -> 0.55 only
   - no 0.65 scale in this probe

5. Online probes and early stop now log/use shape-first scores:
   - `eval_final_det_shape_score`
   - `eval_final_det_ip_score`
   - `eval_final_det_relaxed_score`
   - early stop catches R going too negative and shape score getting too bad.

## Run

```bash
cd /home/yangshen0711/tsc_all/tsc_rzip_rllib
unzip -o /path/to/tsc_rzip_b87_shape_first_relaxed_ip_mpo_patch.zip
chmod +x scripts/train_mpo.py scripts/eval_mpo_policy.py run_train_mpo_native.sh run_train_mpo_nohup.sh stop_train_mpo_nohup.sh run_eval_mpo_policy.sh run_eval_mpo_b87_sweep.sh
export TSC_ALL_ROOT=/home/yangshen0711/tsc_all
./run_train_mpo_nohup.sh configs/mpo_b87_shape_first_relaxed_ip_recurrent_192worker_1m_probe.json
tail -f logs/nohup/latest_mpo.log
```

## What to watch

At iter 75 / 100:

- `eval_final_det_terminal_R_error` should stay above about -0.08 m, and must not go below -0.12 m.
- `eval_final_det_terminal_Z_error` should approach |Z| < 0.08--0.10 m without overshooting too far negative.
- `eval_final_det_terminal_Ip_error` only needs to be within about ±3000 A during reach.
- `eval_final_det_mean_abs_action` should stay around 0.10--0.40.
- `eval_final_det_shape_score` should improve compared with B86.

