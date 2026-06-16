# B94 run notes

## Install/update files

```bash
cd /home/yangshen0711/tsc_all/tsc_rzip_rllib
unzip -o /path/to/b94_updated_files.zip -d .
chmod +x run_train_b94_native.sh run_resume_b94_from_b93_iter500.sh run_train_b94_nohup.sh run_probe_b94_modes.sh
```

## Default run

```bash
./run_resume_b94_from_b93_iter500.sh
```

Default checkpoint:

```text
mpo_checkpoints/train_b93_actor_limited_modes_from_b92_iter450_mpo_192worker_probe_20260615_135541/iter_000500
```

Default stop:

```text
3.35M env_steps
```

## Log

```bash
tail -f logs/nohup/latest_b94_resume.log
```

Expected startup lines:

```text
[run_train_b94_native] limit after set : ulimit -u=30000 ulimit -n=4096
[python limits before ray.init]
[train_mpo] after ray.init; inferring spaces without env.reset
[train_mpo] loading resume checkpoint: .../iter_000500/mpo_checkpoint.pt
```

## What to judge first

- `eval_final_det_terminal_R_error` should move from about `-0.160 m` toward `>-0.135 m`.
- `eval_final_det_terminal_Z_error` should remain below about `+0.06 m`.
- Effective mode coefficients for `pf2_vertical_diff`, `pf34_vertical_diff`, and `mixed_pf_z_shape` should drop versus B93.
- `learner/actor_raw_pf_vertical_diff_penalty` should be nonzero if the raw residual branch is still using large PF U/L differences in the inward-R region.
- `learner/actor_raw_mean_abs_action` should not keep increasing while R stays stuck.
