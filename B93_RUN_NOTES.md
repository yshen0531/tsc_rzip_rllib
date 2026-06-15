# B93 run notes

## Recommended run

```bash
cd /home/yangshen0711/tsc_all/tsc_rzip_rllib
unzip -o /path/to/b93_updated_files.zip -d .
chmod +x run_train_b93_native.sh run_resume_b93_from_b92_iter450.sh run_train_b93_nohup.sh run_probe_b93_modes.sh
./run_resume_b93_from_b92_iter450.sh
```

Default resume checkpoint:

```text
mpo_checkpoints/train_b92_rprogress_commonmode_from_b91_iter375_mpo_192worker_probe_20260614_233859/iter_000450
```

This intentionally does not use `final/`.

## First log checks

You should see:

```text
[run_train_b93_native] limit after set : ulimit -u=30000 ulimit -n=4096
[python limits before ray.init]
[train_mpo] after ray.init; inferring spaces without env.reset
[train_mpo] loading resume checkpoint: .../iter_000450/mpo_checkpoint.pt
```

## Main metrics to inspect

- `eval_final_det_terminal_R_error`
- `eval_final_det_terminal_Z_error`
- `learner/actor_mode_coeff_mean/outer_pf_common_shape`
- `learner/actor_mode_coeff_raw_mean/outer_pf_common_shape`
- `learner/actor_mode_coeff_mean/cs_common_flux`
- `learner/actor_mode_coeff_raw_mean/cs_common_flux`
- `learner/actor_mode_coeff_l2_penalty`
- `learner/actor_mode_coeff_saturation_penalty`
- `learner/actor_physics_blend_alpha`

## Desired B93 behavior

- `R_error` should move from about `-0.17 m` toward `>-0.13 m`.
- `Z_error` should remain below about `+0.08 m`.
- Effective common-mode coefficients should no longer sit near `±1`.
- Raw common-mode coefficients may remain larger than effective coefficients because B93 gates them actor-side.
