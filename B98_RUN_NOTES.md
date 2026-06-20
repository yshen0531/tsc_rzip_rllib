# B98 run notes

## Recommended command

```bash
cd /home/yangshen0711/tsc_all/tsc_rzip_rllib
unzip -o /path/to/b98_updated_files.zip -d .
chmod +x run_train_b98_native.sh run_resume_b98_from_b97_iter575.sh run_train_b98_nohup.sh run_probe_b98_modes.sh
./run_resume_b98_from_b97_iter575.sh
```

## Check first log lines

```text
[run_train_b98_native] limit after set : ulimit -u=30000 ulimit -n=4096
[python limits before ray.init]
[train_mpo] after ray.init; inferring spaces without env.reset
[train_mpo] spaces: obs_dim=<old+3> priv_dim=... action_dim=14
[train_mpo] loading resume checkpoint: .../iter_000575/mpo_checkpoint.pt
Adapted actor checkpoint for obs_dim <old> -> <old+3>
Adapted q1 checkpoint for obs_dim <old> -> <old+3>
Optimizer states are intentionally not restored because B98 expanded observation inputs.
```

## Primary success criteria

B98 is not judged only by fixed-target terminal errors.  It should show improved target sensitivity:

```text
eval_grid_R_target_to_terminal_R_slope > 0.3
eval_grid_Z_target_to_terminal_Z_slope > 0.5
```

Fixed-target deployable probes should not collapse:

```text
eval_final_det_terminal_R_error roughly no worse than B97 iter575
eval_final_det_terminal_Z_error roughly no worse than B97 iter575
```

If slopes remain near zero, the actor is still ignoring target commands and the next step should be stronger goal-conditioned training or supervised auxiliary target-response regularization, not more one-sided R/Z reward patches.
