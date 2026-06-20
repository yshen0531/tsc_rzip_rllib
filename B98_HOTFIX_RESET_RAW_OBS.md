# B98 hotfix: reset raw_obs bug

Fixes `UnboundLocalError: cannot access local variable raw_obs` in `MpoRolloutWorker._reset_env_for_next_episode()` when `env.reset()` is called without a seed.

The previous code assigned `self.obs, self.info = self.env.reset()` in the seed=None branch, then tried to call `augment_observation_with_goal(raw_obs, ...)`. The fix is to assign `raw_obs, self.info = self.env.reset()` consistently in both branches.

No algorithm/config changes. Re-run B98 from the original B97 `iter_000575` checkpoint, not from the broken partial B98 run.
