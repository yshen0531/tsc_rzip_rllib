# B97 run notes

## Install

```bash
cd /home/yangshen0711/tsc_all/tsc_rzip_rllib
unzip -o /path/to/b97_updated_files.zip -d .
chmod +x run_train_b97_native.sh run_resume_b97_from_b95_iter550.sh run_train_b97_nohup.sh run_probe_b97_modes.sh
```

## Run

```bash
./run_resume_b97_from_b95_iter550.sh
```

Default checkpoint:

```text
mpo_checkpoints/train_b95_target_curriculum_from_b93_iter500_mpo_192worker_probe_20260616_140102/iter_000550
```

Fallback if iter_000550 is missing:

```bash
./run_resume_b97_from_b95_iter550.sh \
  configs/mpo_b97_resume_from_b95_iter550_to_3p9m_recurrent_192worker_probe.json \
  mpo_checkpoints/train_b95_target_curriculum_from_b93_iter500_mpo_192worker_probe_20260616_140102/iter_000525
```

Tail log:

```bash
tail -f logs/nohup/latest_b97_resume.log
```

Expected startup lines:

```text
[run_train_b97_native] limit after set : ulimit -u=30000 ulimit -n=4096
[python limits before ray.init]
[train_mpo] after ray.init; inferring spaces without env.reset
[train_mpo] loading resume checkpoint: .../iter_000550/mpo_checkpoint.pt
[train_mpo] target_randomization_stage=stage0_b97_fixed_core_85pct_small_symmetric_jitter enabled=True
```

## What to watch

Primary fixed-target probe:

```text
eval_final_det_terminal_R_error
eval_final_det_terminal_Z_error
eval_final_det_terminal_Ip_error
eval_final_stoch_terminal_R_error
eval_final_stoch_terminal_Z_error
```

Local-grid probe diagnostics:

```text
eval_grid_R_error_abs_mean
eval_grid_Z_error_abs_mean
eval_grid_shape_score_abs_mean
eval_grid_p00_terminal_R_error ... eval_grid_p08_terminal_Z_error
```

Episode distribution diagnostics:

```text
target_fixed_probability
episode_fixed_target_frac
episode_fixed_terminal_R_error_mean
episode_fixed_terminal_Z_error_mean
episode_random_terminal_R_error_mean
episode_random_terminal_Z_error_mean
```

A useful B97 result should keep fixed-target Z near B95 quality while avoiding further overfitting to a one-sided R/Z correction.  It is acceptable if fixed-target R improves slowly; the goal is to produce a healthier backbone for later variable-target training rather than another hand-tuned local patch.
