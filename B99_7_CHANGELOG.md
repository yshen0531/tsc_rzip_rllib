# B99.7 changelog — resume B99.6 best-error and freeze actor

B99.7 is a stability patch on top of B99.6.  It is intended to resume from the
B99.6 `best_error_score` checkpoint, which was around the best observed
R/Z/Ip compromise before the actor continued updating into a bad high-action
basin.

## Why B99.7 exists

B99.6 successfully found a good mid-run policy region:

- around the B99.6 best-error checkpoint: R error about -0.13 m, Z error about
  +0.03 m, Ip error about a few hundred amps, and actor mean action still modest;
- after that, continued actor updates pushed the policy into a large-action
  template with R/Z/Ip all biased.

So B99.7 is designed to **preserve and consolidate** the B99.6 best-error policy,
not to re-explore aggressively.

## Main changes from B99.6

### 1. Resume source changed

B99.6 resumed from B99.5 iter25.  B99.7 resumes from:

```text
B99.6 best_error_score checkpoint
```

The run script auto-detects the newest matching B99.6 `best_error_score` folder,
or you can provide:

```bash
export B99_6_BEST_ERROR_CKPT=/path/to/best_error_score
```

### 2. Actor freeze after resume

B99.7 freezes actor updates for 120k env steps after the resumed checkpoint:

```json
"actor_freeze_after_resume_env_steps": 120000
```

During this window:

- reward critic updates continue;
- cost critic updates continue;
- dual variable updates continue;
- actor parameter updates are skipped;
- eta update is also skipped by default (`actor_freeze_eta=true`).

This lets critic/cost/dual estimates catch up around the already-good policy
instead of immediately pushing the actor past it.

### 3. Conservative actor after freeze

When the freeze window ends, actor updates resume but are more conservative than
B99.6:

```json
"actor_update_every": 16,
"policy_loss_lower_clip": -2.5
```

### 4. Slightly stronger action regularization

```json
"actor_action_l2_coeff": 0.012,
"actor_action_saturation_coeff": 0.025,
"actor_action_soft_limit": 0.70
```

The goal is not to forbid strong action; it is to avoid drifting back into the
0.6--0.8 actor-mean basin before the controller actually holds R/Z/Ip.

### 5. Seed best checkpoint from resume

B99.7 seeds its new `best_error_score` checkpoint from the resume checkpoint, so
if the resumed policy is already better than later rollouts, it is preserved.

### 6. Stop on no best-error improvement

B99.7 adds a best-error no-improvement stop:

```json
"stop_if_no_best_error_improvement_iters": 30
```

If no new `best_error_score` is found for 30 iterations, training exits rather
than spending many more hours in a bad basin.

## Preserved from B99.6

- runtime-only TSC execution;
- GEQDSK `nbbbs` plasma-boundary compact extrema;
- no contact features;
- no full 36-point boundary;
- stage0 only;
- 10 ms control period;
- 192 workers;
- terminal/late R/Z/Ip cost definitions;
- best-error and best-return checkpointing;
- detailed gotsc/learner/boundary timing logs.

## Not changed

B99.7 does not change TSC internals, does not introduce symlinks, does not use a
persistent TSC daemon, and does not enter stage1.
