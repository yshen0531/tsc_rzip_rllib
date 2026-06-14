# B92 changelog

B92 is a targeted continuation of B91.  It keeps the B91 split-vertical physics-blend model, the 192-worker limit-safe startup, and the default non-final checkpoint policy.  It changes only the pieces needed after B91 plateaued around `R_error ~= -0.17 m` while keeping `Z_error ~= +0.04 m`.

## Main changes

1. Stronger one-sided inward-R penalty
   - Stage3: `w_r_negative_bias_strong=8.0`, `r_neg_deadband_m=0.06`, `r_neg_ref_m=0.04`.
   - Stage2: `w_r_negative_bias_strong=5.0`, `r_neg_deadband_m=0.08`, `r_neg_ref_m=0.04`.

2. New signed negative-R progress reward
   - When `R_error` is already too negative, B92 rewards steps that move `R_error` toward zero and penalizes steps that push it further inward.
   - Stage3 defaults: `w_r_negative_progress=8.0`, `r_negative_progress_enable_m=-0.08`, `r_negative_progress_ref_m=0.03`, `r_negative_progress_clip=2.5`.

3. New common-mode coefficient penalties
   - Applies to `outer_pf_common_shape` and `cs_common_flux`.
   - Stage3 defaults: `w_common_mode_coeff_l2=1.5`, `w_common_mode_coeff_saturation=4.0`, `common_mode_coeff_soft_limit=0.55`.
   - This directly addresses B91 where matrix mode scales were reduced but the actor drove common-mode coefficients close to saturation.

4. Positive-Z gate retained, not strengthened
   - B91 already controlled Z. B92 does not increase Z pressure.
   - Stage3 keeps `w_z_positive_bias=2.0`, `z_pos_deadband_m=0.05`, `z_pos_gate_r_threshold_m=-0.12`, `z_pos_gate_multiplier=0.35`.

5. Startup remains limit-safe
   - `run_train_b92_native.sh` raises `ulimit -u` and `ulimit -n` before launching Python.
   - Python prints `RLIMIT_NPROC` and `RLIMIT_NOFILE` before `ray.init()`.

## Default run

Default B92 resume checkpoint:

```text
mpo_checkpoints/train_b91_rguard_from_b90_1p8m_split_vertical_mpo_192worker_probe_20260614_004723/iter_000375
```

Default config:

```text
configs/mpo_b92_resume_from_b91_iter375_to_2p8m_recurrent_192worker_probe.json
```

Default target:

```text
stop_env_steps = 2,800,000
```

## Recommended command

```bash
./run_resume_b92_from_b91_iter375.sh
```

Watch:

```bash
tail -f logs/nohup/latest_b92_resume.log
```

The first lines should show:

```text
[run_train_b92_native] limit after set : ulimit -u=30000 ulimit -n=4096
[python limits before ray.init]
[train_mpo] after ray.init; inferring spaces without env.reset
[train_mpo] loading resume checkpoint: .../iter_000375/mpo_checkpoint.pt
```
