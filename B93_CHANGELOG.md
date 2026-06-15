# B93 changelog

B93 is based on B92 and keeps the B91/B92 radial reward shaping, limit-safe Ray startup, and default non-`final` resume behavior.  The motivation is that B92 kept `Z_error` small but did not move deterministic `R_error` away from the inward plateau near `-0.174 m`; the common/vertical physics-mode coefficients also remained close to saturation.

## Key changes

1. **Actor-side mode coefficient gates**
   - Added `physics_blend.mode_coeff_scales` in `tsc_rzip_rllib/mpo/models.py`.
   - These scales are applied to the learned physics-mode coefficients before constructing `physics_action`.
   - B93 default scales:
     - `outer_pf_common_shape`: `0.35`
     - `cs_common_flux`: `0.40`
     - `pf2_vertical_diff`: `0.75`
     - `pf34_vertical_diff`: `0.75`
     - `mixed_pf_z_shape`: `0.60`

2. **Lower late-stage physics alpha**
   - B93 alpha schedule ends at `0.10` after `2.3M env_steps`.
   - Since B93 resumes after B92 `iter_000450`, the run should use the lower final alpha immediately.

3. **Actor-loss common-mode regularization**
   - Added `mpo.actor_mode_coeff_l2` and `mpo.actor_mode_coeff_saturation`.
   - These act directly on the actor loss instead of only through reward/critic learning.
   - Default regularized modes:
     - `outer_pf_common_shape`
     - `cs_common_flux`

4. **Diagnostics**
   - Training now logs effective mode coefficients and raw mode coefficients:
     - `learner/actor_mode_coeff_mean/<mode>`
     - `learner/actor_mode_coeff_raw_mean/<mode>`
   - Eval CSV also writes `mode_coeff/<mode>` and `mode_coeff_raw/<mode>`.

5. **Resume defaults**
   - Default checkpoint is B92 `iter_000450`, not `final/`.
   - Target stop is `3.1M env_steps`.

## Files changed

- `tsc_rzip_rllib/mpo/models.py`
- `scripts/train_mpo.py`
- `scripts/eval_mpo_policy.py`
- `configs/train_b93_actor_limited_modes_mpo_fixed_target_1ms.json`
- `configs/mpo_b93_resume_from_b92_iter450_to_3p1m_recurrent_192worker_probe.json`
- `configs/override_b93_resume_disable_early_stop.json`
- `run_train_b93_native.sh`
- `run_resume_b93_from_b92_iter450.sh`
- `run_train_b93_nohup.sh`
- `run_probe_b93_modes.sh`

