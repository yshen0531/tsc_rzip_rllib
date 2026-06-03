# B85-stable recurrent MPO patch

This patch replaces the B85-current MPO hyperparameters that produced saturated deterministic actions with a more conservative B85-stable setup.

## Main files

- `scripts/train_mpo.py`: B85-stable learner updates.
- `scripts/eval_mpo_policy.py`: MPO policy evaluation with path macro resolution.
- `tsc_rzip_rllib/mpo/*.py`: recurrent actor/critic, privileged vector, replay buffer.
- `tsc_rzip_rllib/envs/rzip_env.py`: B83/B85 env with reach-hold reward and failure penalty support.
- `tsc_rzip_rllib/envs/rllib_env.py`: RLlib/native wrapper with global-env-step curriculum support.
- `tsc_rzip_rllib/envs/factory.py`: maps stable reward/failure config keys into `TscRzipEnv` kwargs.
- `configs/train_b85_stable_mpo_fixed_target_1ms.json`: stable train env/reward/curriculum config.
- `configs/mpo_b85_stable_recurrent_192worker_1m_probe.json`: recommended first run.
- `configs/mpo_b85_stable_recurrent_192worker_5m.json`: longer run only if the 1M probe looks healthy.
- `run_train_mpo_native.sh`, `run_train_mpo_nohup.sh`: foreground/background training.
- `stop_train_mpo_nohup.sh`: root-safe stop helper.
- `run_eval_mpo_policy.sh`: single checkpoint eval.
- `run_eval_mpo_stable_sweep.sh`: small checkpoint eval sweep.

## Recommended run

```bash
cd /home/yangshen0711/tsc_all/tsc_rzip_rllib
unzip -o /path/to/tsc_rzip_b85_stable_mpo_patch.zip
chmod +x scripts/train_mpo.py scripts/eval_mpo_policy.py run_*.sh stop_train_mpo_nohup.sh

export TSC_ALL_ROOT=/home/yangshen0711/tsc_all
./run_train_mpo_nohup.sh configs/mpo_b85_stable_recurrent_192worker_1m_probe.json
tail -f logs/nohup/latest_mpo.log
```

## Health checks for B85-stable

Stop and revise again if, after about 500k-1M env steps:

- `fragment_mean_abs_action` remains above `0.85` for many iterations.
- `learner/actor_mean_abs_action` remains above `0.75`.
- `learner/critic_loss` still grows monotonically by orders of magnitude.
- `learner/eta` stays pinned near `eta_max`.
- `episode_hold_success_mean` and `episode_time_to_first_reach_step_mean` remain at 0 / -1 with no improvement.

Promising signs:

- `fragment_mean_abs_action` falls into roughly `0.15-0.65`.
- episode length tends to 320 rather than early failure around 100-180.
- terminal Z error is consistently smaller than B85-current.
- at least occasional valid `time_to_first_reach_step` appears.
