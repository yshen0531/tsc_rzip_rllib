# B94 changelog

B94 is based on B93.  B93 successfully suppressed the common-mode saturation
seen in B92, but the final deterministic probe still had `R_error≈-0.160 m`.
The remaining saturated channels were mainly PF vertical-difference modes and the
raw residual branch.  B94 therefore changes actor/model-side constraints rather
than simply increasing the reward penalty again.

## Main changes

1. **Tighter actor-side mode coefficient gates**

   B94 changes `physics_blend.mode_coeff_scales` to:

   ```json
   {
     "pf2_vertical_diff": 0.55,
     "pf3_vertical_diff": 0.65,
     "pf4_vertical_diff": 0.65,
     "pf23_vertical_diff": 0.60,
     "pf34_vertical_diff": 0.55,
     "outer_pf_common_shape": 0.30,
     "cs_common_flux": 0.35,
     "mixed_pf_z_shape": 0.45
   }
   ```

   This keeps the successful B93 common-mode gate and now also constrains the
   PF vertical channels that remained large in B93.

2. **Actor-mode regularization expanded to selected vertical modes**

   The actor loss now regularizes:

   - `outer_pf_common_shape`
   - `cs_common_flux`
   - `pf2_vertical_diff`
   - `pf34_vertical_diff`
   - `mixed_pf_z_shape`

   with L2 weights and a saturation soft limit of `0.50`.

3. **Raw PF vertical-difference guard**

   `scripts/train_mpo.py` adds `actor_raw_pf_vertical_diff_when_r_neg`.  It
   penalizes deterministic raw residual PF U/L half-differences when the first
   observation component indicates `R_error < -0.10 m` using
   `obs[0] * 0.05 m`.

   Default pairs:

   - `PF2U - PF2L`
   - `PF3U - PF3L`
   - `PF4U - PF4L`

4. **Policy-loss lower clip relaxed**

   B93 often hit `policy_loss_lower_clip=-8`.  B94 uses `-10` to make the actor
   update slightly less blunt while keeping a guardrail.

5. **Default resume checkpoint**

   B94 defaults to B93 `iter_000500`, not `final/`:

   ```text
   mpo_checkpoints/train_b93_actor_limited_modes_from_b92_iter450_mpo_192worker_probe_20260615_135541/iter_000500
   ```

## Updated files

- `scripts/train_mpo.py`
- `scripts/eval_mpo_policy.py`
- `scripts/probe_mpo_action_modes.py`
- `tsc_rzip_rllib/mpo/models.py`
- `tsc_rzip_rllib/mpo/privileged.py`
- `tsc_rzip_rllib/mpo/replay.py`
- `tsc_rzip_rllib/mpo/__init__.py`
- `configs/train_b94_vertical_rawguard_mpo_fixed_target_1ms.json`
- `configs/mpo_b94_resume_from_b93_iter500_to_3p35m_recurrent_192worker_probe.json`
- `configs/override_b94_resume_disable_early_stop.json`
- `run_train_b94_native.sh`
- `run_resume_b94_from_b93_iter500.sh`
- `run_train_b94_nohup.sh`
- `run_probe_b94_modes.sh`
