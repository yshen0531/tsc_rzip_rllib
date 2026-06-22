# B99 run notes

## Run

```bash
cd /home/yangshen0711/tsc_all/tsc_rzip_rllib
unzip -o /path/to/b99_constrained_goal_from_scratch_clean.zip -d .
chmod +x run_train_b99_native.sh run_train_b99_nohup.sh run_probe_b99_modes.sh
./run_train_b99_nohup.sh
```

## First log checks

```text
[run_train_b99_native] limit after set : ulimit -u=30000 ulimit -n=4096
[python limits before ray.init]
========== B99 constrained goal-conditioned MPO Ray init =========
[train_mpo] after ray.init; inferring spaces without env.reset
[train_mpo] spaces: obs_dim=... priv_dim=... action_dim=14
```

## Main diagnostics

Watch these fields in `train_results.jsonl/csv`:

- `learner/cost/observed_R`, `learner/cost/observed_Z`, `learner/cost/observed_Ip`
- `learner/dual/lambda_R`, `learner/dual/lambda_Z`, `learner/dual/lambda_Ip`
- `learner/actor_cost_penalty`
- `eval_grid_R_target_to_terminal_R_slope`
- `eval_grid_Z_target_to_terminal_Z_slope`
- `eval_final_det_terminal_R_error`, `eval_final_det_terminal_Z_error`

## Success criteria for this first B99 run

The first B99 run should be judged less by final fixed-target error and more by whether goal response becomes learnable:

- `eval_grid_R_target_to_terminal_R_slope > 0.2`
- `eval_grid_Z_target_to_terminal_Z_slope > 0.4`
- dual variables move in sensible directions instead of staying flat
- fixed-target deterministic errors do not catastrophically collapse

If target slopes become positive, B100 should fine-tune fixed-target performance.  If slopes remain near zero or negative, the next step should be a stronger architecture change such as a goal-residual actor head or partial actor reset.
