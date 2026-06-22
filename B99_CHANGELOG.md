# B99 constrained goal-conditioned MPO from scratch

This package is intentionally clean: it includes only the B99 configs, required scripts, and the package code needed to run them.  Historical B8x/B9x configs are not included.

## Algorithmic change

B99 is not a resume/fine-tune patch.  It is a from-scratch run that keeps the Ray/TSC/replay/eval infrastructure but changes the RL objective layer:

- explicit goal-conditioned observation features from the start of training;
- no checkpoint resume by default;
- physics blend disabled by default to provide a clean algorithmic baseline;
- engineering-spec costs for R, Z, Ip, action magnitude, and vessel current;
- learned multiplicative dual variables for those costs;
- reward critic retained as the task/return critic;
- one cost critic per constraint cost;
- actor loss includes learned-dual-weighted predicted cost values instead of newly hand-picked R/Z/action reward weights;
- expanded local target grid evaluation for target-sensitivity diagnostics.

## New files

- `tsc_rzip_rllib/mpo/constrained_dual.py`
- `configs/mpo_b99_constrained_goal_from_scratch_192worker_probe.json`
- `configs/train_b99_constrained_goal_from_scratch_1ms.json`
- `run_train_b99_native.sh`
- `run_train_b99_nohup.sh`
- `run_probe_b99_modes.sh`

## Files intentionally not included

The previous historical configs and run scripts are intentionally not included in this clean B99 package, including B81--B98 configs and `run_resume_b98_from_b97_iter575.sh`.  They are not needed for this from-scratch B99 run.

## Default command

```bash
./run_train_b99_nohup.sh
```

This starts a new B99 run from scratch with 192 workers.  It does not use `final/` or any previous checkpoint.
