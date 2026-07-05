# B99.4 Changelog — stabilized actor/dual runtime-only run

B99.4 is based on the B99.3 runtime-only/gfile-boundary code path. It does **not** rewrite the RL problem and does **not** add directional R/Z hand patches. The purpose is to stabilize the actor and make learned constraints active early enough after B99.3 showed large-action bias with R/Z/Ip all drifting.

## Kept from B99.3

- `runtime_only_fast_mode = true`.
- GEQDSK `nbbbs` plasma-boundary parsing for compact extrema.
- Boundary validity/timing diagnostics.
- 10 ms control period.
- Slew limit: `0.3 A/ms`, so each coil can change by up to `3 A` per policy step.
- Full actor action authority: `actor_output_scale = 1.0` from the start.
- No contact features.
- No full 36-point boundary observation.
- No online grid probe; final grid only.
- No symlink workspace and no persistent TSC daemon.

## Main changes vs B99.3

### Parallelism

- `num_tsc_workers`: `224 -> 192`.
- `ray_num_cpus`: `240 -> 208`.

B99.3 showed that 224 workers worked but did not materially improve total throughput because per-worker `gotsc` step time increased.

### Curriculum

- Stage1 400 ms is disabled for this run.
- The 500 ms stage0 is held until stop.
- `stop_env_steps = 1_000_000`.

B99.3 did not stabilize stage0 before the scheduled transition. B99.4 should not make the task harder before the 500 ms target is learned.

### Actor stabilization

- `actor_update_every`: effectively `2 -> 4` relative to B99.3 behavior, so actor optimizer steps are less frequent.
- `policy_loss_lower_clip`: `-15.0 -> -10.0` to reduce aggressive negative policy-loss updates.
- Mild actor-side action regularization:
  - `actor_action_l2_coeff = 0.003`
  - `actor_action_saturation_coeff = 0.005`
  - `actor_action_soft_limit = 0.85`

This is intentionally mild. It is not meant to remove full action authority; it only discourages early broad quasi-saturation when tracking is not improving.

### Earlier learned-constraint pressure

- `actor_cost_coeff`: `0.003 -> 0.01`.
- `dual_actor_warmup_env_steps`: `300000 -> 100000`.
- `dual_actor_ramp_env_steps`: `900000 -> 400000`.
- `dual_update_warmup_env_steps`: `400000 -> 100000`.
- `dual_update_ramp_env_steps`: `1000000 -> 500000`.
- R/Z duals start at `0.08`, use `lr=0.0008`, and `max=6.0`.

B99.3 showed that R/Z costs were already above target while duals and actor-cost pressure were still nearly inactive. B99.4 makes the generic learned constraints participate much earlier.

## What B99.4 deliberately does not change

- No directional R/Z one-sided patch.
- No physics blend.
- No 20 ms control period.
- No change to `updates_per_iter` or `num_action_samples` yet.
- No change to TSC internals.

If B99.4 still runs slowly, B99.3 already showed that `gotsc_subprocess_s` dominates the step time. The next speed-oriented test should be a controlled 10 ms vs 20 ms experiment or a learner-cost reduction experiment, not more file-copy optimization.
