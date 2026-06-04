# B86 Balanced Recurrent MPO

B86 is the follow-up to B85c.  The B85c run proved that hard action scaling and slow actor updates can prevent high-action saturation, but it also revealed a new failure mode: symmetric scalar clipping of the policy loss (`policy_loss_clip=[-5,5]`) can zero the positive policy-gradient signal and collapse the deterministic actor mean back to no-op.

B86 therefore keeps the stable engineering pieces and changes actor learning:

- removes upper clipping of positive policy loss;
- clips only the aggressive negative direction with `policy_loss_lower_clip=-8`;
- keeps `actor_update_every=4` and `actor_lr=1e-5`;
- reduces actor action regularization compared with B85c;
- uses a wider but still bounded action-scale schedule: `0.45 -> 0.55 -> 0.65`;
- reduces policy stochasticity with `log_std_max=-0.5`, `log_std_min=-3.5`, and `entropy_coeff=0.002`;
- adds both deterministic and stochastic final probes every 25 iterations;
- updates early-stop checks to detect both high-action failure and near-zero-action failure.

## Recommended first run

```bash
cd /home/yangshen0711/tsc_all/tsc_rzip_rllib
unzip -o /path/to/tsc_rzip_b86_balanced_mpo_patch.zip
chmod +x scripts/train_mpo.py scripts/eval_mpo_policy.py run_train_mpo_native.sh run_train_mpo_nohup.sh stop_train_mpo_nohup.sh run_eval_mpo_policy.sh run_eval_mpo_b86_sweep.sh
export TSC_ALL_ROOT=/home/yangshen0711/tsc_all
./run_train_mpo_nohup.sh configs/mpo_b86_balanced_recurrent_192worker_1m_probe.json
tail -f logs/nohup/latest_mpo.log
```

## What to watch

At each online probe (`iter=25,50,75,100,...`) compare:

- `eval_final_det_mean_abs_action`: target range is roughly `0.05--0.50`.
- `eval_final_det_first_reach`: should eventually become non-negative.
- `eval_final_det_terminal_Z_error`: should drop clearly below the old no-op baseline of about `0.267 m`.
- `eval_final_stoch_*`: if stochastic probe improves while deterministic does not, actor mean is still under-learning.
- `learner/policy_loss_raw` and `learner/policy_loss_used`: raw positive values should no longer be flattened to a constant upper clip.

If deterministic action remains below `0.02` and first reach remains `-1` by `iter=75/100`, stop and inspect.  If action jumps above `0.75` and first reach remains `-1`, also stop.
