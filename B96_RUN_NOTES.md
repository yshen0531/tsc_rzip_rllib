# B96 run notes

## Recommended command

```bash
cd /home/yangshen0711/tsc_all/tsc_rzip_rllib
unzip -o /path/to/b96_updated_files.zip -d .
chmod +x run_train_b96_native.sh run_resume_b96_from_b95_iter550.sh run_train_b96_nohup.sh run_probe_b96_modes.sh
./run_resume_b96_from_b95_iter550.sh
```

Watch logs:

```bash
tail -f logs/nohup/latest_b96_resume.log
```

## First-screen checks

Confirm these lines appear:

```text
[run_train_b96_native] limit after set : ulimit -u=30000 ulimit -n=4096
[python limits before ray.init]
[train_mpo] after ray.init; inferring spaces without env.reset
[train_mpo] loading resume checkpoint: .../iter_000550/mpo_checkpoint.pt
[train_mpo] target_randomization_stage=stage0_b96_mix_50pct_fixed_outward_random enabled=True
```

## Key metrics

For fixed-target deterministic/stochastic probes:

```text
eval_final_det_terminal_R_error
eval_final_det_terminal_Z_error
eval_final_det_terminal_Ip_error
eval_final_stoch_terminal_R_error
eval_final_stoch_terminal_Z_error
```

For mixed curriculum diagnostics:

```text
target_randomization_stage
target_fixed_probability
episode_fixed_target_frac
episode_random_target_frac
episode_fixed_terminal_R_error_mean
episode_fixed_terminal_Z_error_mean
episode_random_terminal_R_error_mean
episode_random_terminal_Z_error_mean
```

## Decision rule

A useful B96 run should move the fixed-target deterministic probe toward:

```text
R_error > -0.13 m
Z_error < +0.06 m
Ip_error < 2000 A
```

If B96 remains around R_error=-0.15 and Z_error=+0.05 after about 3.9M env steps, the next step should not be another small reward/gate tweak.  The next step should be a more control-oriented strategy, such as explicit short-horizon R-correction training or a reworked action basis.
