# B99.6 changelog — resume B99.5 iter25, actor-slow terminal/late cost

B99.6 is a stability patch on top of B99.5.  It is intended to resume from the
B99.5 `iter_000025` checkpoint, before the B99.5 actor grew into the later
inward/downward/low-Ip biased action template.

## Kept from B99.5

- Runtime-only TSC execution.
- GEQDSK `nbbbs` plasma-boundary compact extrema in the observation.
- Boundary validity and runner timing diagnostics.
- Stage0-only 10 ms control period.
- 192 rollout workers.
- No symlink workspace and no persistent TSC daemon.
- No contact feature and no full 36-point boundary observation.
- No directional R/Z hand patch.

## Main training changes

- Resume run script defaults to:
  `mpo_checkpoints/train_b99_5_terminal_late_cost_runtime_only_10ms_extrema_from_scratch_mpo_192worker/iter_000025`.
- Actor update is slowed further:
  - `actor_update_every: 6 -> 8`
  - `policy_loss_lower_clip: -8 -> -5`
- Actor mean-action regularization is strengthened moderately:
  - `actor_action_l2_coeff: 0.003 -> 0.008`
  - `actor_action_saturation_coeff: 0.005 -> 0.015`
  - `actor_action_soft_limit: 0.85 -> 0.75`
- Ip late/terminal cost is tightened:
  - `late_tol: 3000 A -> 1500 A`
  - `terminal_tol: 3000 A -> 1500 A`
  - `terminal_multiplier: 2.0 -> 2.5`
- R/Z terminal costs are strengthened:
  - `terminal_multiplier: 2.5 -> 3.5`
  - `late_multiplier: 1.5 -> 1.7`
- R/Z dual targets are tightened:
  - `target_R/Z: 0.5 -> 0.4`
- Checkpointing is denser:
  - `checkpoint_every_iters: 25 -> 10`

## Resume-specific code controls

B99.6 adds explicit resume controls in `scripts/train_mpo.py`:

- `resume.restore_optimizer_state=false`: reset optimizer state from the current
  B99.6 config instead of carrying B99.5 optimizer momentum.
- `resume.load_cost_critics=false`: do not load stale B99.5 cost critics after
  changing cost definitions.
- `resume.dual_load_mode=values_only_current_config`: load only the lambda values
  but reapply B99.6 dual target/lr/min/max from config.
- `resume.reset_update_count=true`: restart the actor update cadence for the new
  `actor_update_every=8` schedule.

## Best checkpointing

B99.6 adds lightweight best-checkpoint saving:

- `best_error_score`: lower-is-better normalized terminal R/Z/Ip/action score.
- `best_return`: highest mean episode return.

This is only checkpoint selection.  It does not affect rewards, costs, or policy
updates.
