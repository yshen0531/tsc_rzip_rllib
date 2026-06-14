# B91 R-Guard Split-Vertical MPO

## Why B91

B90/B90-resume fixed the main B89 failure mode: Z was pulled down from the +0.25 m range to roughly +0.05--0.10 m.  The new failure mode is an inward radial bias: deterministic probes after B90-resume stayed near R_error ≈ -0.19 m while Z remained small.  B91 therefore keeps the B90 split PF vertical modes and focuses on radial correction.

## Main changes

1. **Strong one-sided negative-R shaping**
   - New reward keys:
     - `w_r_negative_bias_strong`
     - `r_neg_deadband_m`
     - `r_neg_ref_m`
     - `r_neg_power`
   - Implemented in `scripts/train_mpo.py` and mirrored in `scripts/eval_mpo_policy.py`.

2. **Positive-Z penalty gating and annealing**
   - New reward keys:
     - `z_pos_gate_r_threshold_m`
     - `z_pos_gate_multiplier`
   - If `R_error` is already too negative, the effective positive-Z penalty is reduced so the policy does not keep sacrificing R just to suppress Z.

3. **Weakened common physics modes**
   - `outer_pf_common_shape` row scaled by `0.45`.
   - `cs_common_flux` row scaled by `0.55`.
   - Implemented via `physics_blend.mode_scales` in `tsc_rzip_rllib/mpo/models.py`.

4. **Checkpoint-compatible physics-mode refresh**
   - `RecurrentGaussianActor.reset_physics_modes_from_config()` re-applies the current config after loading a checkpoint.
   - This prevents a B90 checkpoint's old `physics_mode_matrix` buffer from silently overriding B91's mode scaling.

## Recommended run

Resume from the B90-resume 1.8M checkpoint:

```bash
./run_resume_b91_from_b90_1p8m.sh
```

If the checkpoint directory differs:

```bash
./run_resume_b91_from_b90_1p8m.sh \
  configs/mpo_b91_resume_from_b90_1p8m_to_2p4m_recurrent_192worker_probe.json \
  mpo_checkpoints/<B90_RESUME_RUN>/final
```

## Success criteria for the first diagnostic

- Good: `eval_final_det_terminal_R_error > -0.13` and `eval_final_det_terminal_Z_error < 0.10`.
- Needs tuning: R improves but Z rises above about `0.15`.
- Bad: R remains below `-0.16` despite B91's strong R corridor.


## Correction: B90-resume checkpoint path

B90-resume stopped at iteration 293 but checkpoint_every_iters=25, so the periodic checkpoint directories are iter_000225, iter_000250, and iter_000275. Although a final/ directory may exist, B91 v3 intentionally defaults to iter_000275 to avoid relying on final/.


## B91 v3 startup-limit fix

- Default resume checkpoint is now `iter_000275`, not `final/`.
- `run_train_b91_native.sh` now raises and prints shell limits before launching Python:
  - `ulimit -u 30000`
  - `ulimit -n 4096`
- `scripts/train_mpo.py` keeps unbuffered progress prints around `ray.init()` and infers spaces without calling `env.reset()`.
- Intended usage: resume B91 from B90-resume `iter_000275` with 192 workers after verifying Ray can initialize at `num_cpus=192` under the raised limits.
