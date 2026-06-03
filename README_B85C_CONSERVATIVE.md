# B85c Conservative Recurrent MPO

This patch is the follow-up to B85-stable.  B85-stable fixed the worst engineering
problems of B85-current (slow learner, critic/eta explosion), but the actor still
moved toward high normalized actions and final deterministic eval did not reach or
hold the target.  B85c therefore directly constrains actor updates, instead of
only changing the environment reward.

## Main changes

1. Hard actor output scale schedule
   - action = action_scale * tanh(raw_action)
   - default schedule: 0.35 until 300k env steps, 0.45 until 700k, then 0.55.
   - This prevents the actor from using near ±1 action early in training.

2. Slower actor updates
   - updates_per_iter remains 24, but actor_update_every=4.
   - Critics update every learner step; actor updates only once per 4 critic updates.

3. Conservative actor loss
   - actor_lr=1e-5.
   - policy_loss_clip=[-5, 5].  When the MPO weighted log-likelihood term becomes
     too aggressive, its gradient is clipped out and regularization dominates.
   - actor_action_saturation_coeff=40 and actor_action_soft_limit=0.35.

4. More conservative distribution
   - model log_std_min=-2.0, log_std_max=0.2.
   - entropy_coeff=0.02 to discourage premature collapse.

5. Online deterministic final probe
   - Every 25 iterations, the trainer runs one deterministic final-stage episode
     and writes eval_final_det_* metrics into train_results.jsonl.
   - This is single-episode by design for the current fixed-target deterministic
     plant.

6. Optional early stop
   - Enabled in B85c config.
   - After min_iteration=75, two consecutive bad deterministic probes can stop the run.

## Recommended command

```bash
cd /home/yangshen0711/tsc_all/tsc_rzip_rllib
export TSC_ALL_ROOT=/home/yangshen0711/tsc_all
./run_train_mpo_nohup.sh configs/mpo_b85c_conservative_recurrent_192worker_1m_probe.json
tail -f logs/nohup/latest_mpo.log
```

## Evaluation sweep

```bash
./run_eval_mpo_b85c_sweep.sh \
  configs/mpo_b85c_conservative_recurrent_192worker_1m_probe.json \
  train_b85c_conservative_recurrent_mpo_192worker_1m_probe_YYYYMMDD_HHMMSS \
  final deterministic 1 \
  "000025 000050 000075 000100"
```

## Health criteria

The run is promising only if deterministic final probe starts showing at least one of:

- first_reach >= 0,
- terminal |Z_error| consistently below about 0.10 m with moderate action,
- mean_abs_action below 0.55 after the 0.45 scale phase,
- no drift back to high-action early failure.

If mean_abs_action rises above 0.7 and final probe still has first_reach=-1, stop and tighten the scale/actor update further.
