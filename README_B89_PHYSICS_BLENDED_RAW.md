# B89 Physics-Blended Raw-Action MPO

## Why B89

B86 showed that the actor can move the plasma vertically, but it often sacrificed R. B87/B88 protected R too much and failed to recover useful Z control. B89 is a compromise: it keeps the original 14-dimensional CSPF action space, but adds a weak physics-informed action branch that is blended with the raw RL action.

This is not a fixed physical controller. The neural actor still learns both:

- a raw 14D residual action head;
- coefficients for a small set of CSPF U/L common/differential physics modes.

The final normalized action is

```text
action = action_scale * clip((1 - alpha) * raw_action + alpha * physics_mode_action, -1, 1)
```

The physics modes only define a helpful action subspace. The signs, timing, and amplitudes are still learned by RL.

## Key changes from B88

1. Adds `model.physics_blend` in the MPO config.
2. Actor latent dimension becomes `14 + num_physics_modes`; the final plant action remains 14D.
3. Critic still sees the final 14D action.
4. Keeps relaxed Ip:
   - final `reach_success_ip_tol = 3000 A`
   - final `hold_success_ip_tol = 4000 A`
   - `w_ip = 0.03`, `w_hold_ip = 0.03`
5. Removes strong B87/B88 shape barriers:
   - `w_rz_max_error` mostly zero/weak
   - `w_shape_score = 0`
   - early R/Z drift protection disabled
   - R guard only acts as a wide safety corridor
6. Strengthens Z-first learning:
   - high `w_z`
   - strong `w_z_signed_progress`
   - Z zero-cross brake only very near zero

## Files

```text
scripts/train_mpo.py
scripts/eval_mpo_policy.py
configs/train_b89_physics_blended_raw_mpo_fixed_target_1ms.json
configs/mpo_b89_physics_blended_raw_recurrent_192worker_1m_probe.json
configs/mpo_b89_physics_blended_raw_recurrent_192worker_5m.json
tsc_rzip_rllib/mpo/models.py
tsc_rzip_rllib/mpo/privileged.py
tsc_rzip_rllib/mpo/replay.py
tsc_rzip_rllib/envs/rzip_env.py
tsc_rzip_rllib/envs/rllib_env.py
tsc_rzip_rllib/envs/factory.py
run_train_mpo_native.sh
run_train_mpo_nohup.sh
stop_train_mpo_nohup.sh
run_eval_mpo_policy.sh
run_eval_mpo_b89_sweep.sh
```

## Run

```bash
cd /home/yangshen0711/tsc_all/tsc_rzip_rllib
unzip -o /path/to/tsc_rzip_b89_physics_blended_raw_mpo_patch.zip

chmod +x \
  scripts/train_mpo.py \
  scripts/eval_mpo_policy.py \
  run_train_mpo_native.sh \
  run_train_mpo_nohup.sh \
  stop_train_mpo_nohup.sh \
  run_eval_mpo_policy.sh \
  run_eval_mpo_b89_sweep.sh

export TSC_ALL_ROOT=/home/yangshen0711/tsc_all
./run_train_mpo_nohup.sh configs/mpo_b89_physics_blended_raw_recurrent_192worker_1m_probe.json
tail -f logs/nohup/latest_mpo.log
```

## What to watch

B89 should be judged by online deterministic final probes, not by raw training return alone.

Good signs:

```text
iter50:  det_mean_abs_action > 0.03, Z_error < 0.24 m
iter75:  Z_error < 0.18 m, R_error > -0.14 m, |Ip_error| < 3000 A
iter100: Z_error < 0.12~0.15 m, R_error > -0.15 m, action in 0.10~0.45
```

Bad signs:

```text
Z_error stays > 0.22 m after iter75/100
R_error < -0.15 m
mean_abs_action < 0.02 or > 0.65
```

## Evaluation sweep

```bash
./run_eval_mpo_b89_sweep.sh \
  configs/mpo_b89_physics_blended_raw_recurrent_192worker_1m_probe.json \
  mpo_checkpoints/train_b89_physics_blended_raw_mpo_192worker_1m_probe_YYYYMMDD_HHMMSS \
  eval_results
```
