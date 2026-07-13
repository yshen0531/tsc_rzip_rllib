# B99.8 Run Notes

## Run

```bash
cd /home/yangshen0711/tsc_all/tsc_rzip_rllib
unzip -o /path/to/b99_8_resume_b99_6_best_error_actor_guard_ip_relaxed_runtime_only_192worker_clean.zip -d .
chmod +x run_train_b99_8_resume_b99_6_best_error_native.sh \
         run_train_b99_8_resume_b99_6_best_error_nohup.sh \
         run_probe_b99_8_modes.sh
./run_train_b99_8_resume_b99_6_best_error_nohup.sh
```

The script searches for the newest:

```text
mpo_checkpoints/train_b99_6_resume_b99_5_iter25_actor_slow_ip_tight_runtime_only_mpo_192worker_*/best_error_score
```

To specify it manually:

```bash
export B99_6_BEST_ERROR_CKPT=/path/to/best_error_score
./run_train_b99_8_resume_b99_6_best_error_nohup.sh
```

## Watch log

```bash
tail -f logs/nohup/latest_b99_8_resume_b99_6_best_error_train.log
```

## Key diagnostics

Actor guard:

```text
actor_guard/eval_score
actor_guard/eval_reliable
actor_guard/eval_reliable_reason
actor_guard/action
actor_guard/restored_best_actor
actor_guard/allowed_until_iter
learner/actor_guard_update_allowed
learner/actor_frozen
learner/actor_update_applied
learner/eta_update_applied
```

Best checkpoint:

```text
best/error_score_source
best/error_score
best/error_score_reliable
best/error_score_improved
best/error_score_best_so_far
best/error_score_iters_since_improvement
```

Core control metrics:

```text
episode_terminal_R_error_mean
episode_terminal_Z_error_mean
episode_terminal_Ip_error_mean
learner/actor_mean_abs_action
fragment_mean_abs_action
hold_success_mean
quality_success_mean
```

Final eval:

```text
eval_final_det_terminal_R_error
eval_final_det_terminal_Z_error
eval_final_det_terminal_Ip_error
eval_best_error_det_terminal_R_error
eval_best_error_det_terminal_Z_error
eval_best_error_det_terminal_Ip_error
```

## Interpretation

B99.8 intentionally accepts larger Ip error than B99.6/B99.7.  The main question is whether it can keep R/Z closer while avoiding actor overshoot.  A policy with R/Z clearly better and Ip error of 1000--3000 A may be preferable to one with good Ip but poor R/Z.

Stop/modify if:

```text
actor_guard repeatedly restores best actor;
actor_mean_abs_action still climbs above 0.55;
reliable guard eval score stops improving for many evals;
R/Z deterministic best eval remains poor;
hold_success stays zero after the actor has had several guarded trial windows.
```
