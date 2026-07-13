# B99.8 Changelog — resume B99.6 best-error, actor guard, Ip relaxed

## Purpose

B99.8 is built from B99.7 after analyzing the B99.7 run.  B99.7 showed that actor freezing helped, but also exposed two failures:

1. `best_error_score` could be polluted by unreliable rollout episode statistics, especially very short episodes.
2. After actor unfreeze, even conservative actor updates could push the policy past the good region and into a bad R/Z basin.

B99.8 implements Scheme C: actor updates are guarded by reliable deterministic evaluation probes.

## Main changes

### 1. Actor guard based on deterministic eval

New config block: `actor_guard`.

- Runs a deterministic guard probe every 5 iterations.
- Computes a lower-is-better score from R, Z, relaxed Ip, and mean action.
- Only reliable probes can update `best_error_score`.
- Actor updates are allowed only in bounded trial windows after an improved or near-best reliable eval.
- If reliable eval degrades beyond the allowed margin, the actor is restored from the protected best checkpoint and actor updates are frozen again.

### 2. Best checkpoint uses guard eval only

`best_checkpoint.score_source = "guard_eval"`.

Rollout episode summaries can no longer overwrite `best_error_score`.  This fixes the B99.7 issue where a few very short rollout episodes produced a fake best.

### 3. Ip priority relaxed

Ip is no longer treated as a hard target.  This reflects the working assumption that TSC heating/current evolution can dominate Ip, so forcing the RL policy to match Ip too tightly can harm R/Z control.

Changes:

- Ip reward weights reduced.
- Ip success tolerances relaxed.
- Ip constrained cost late/terminal tolerances relaxed to 5000 A.
- Ip dual target relaxed and max lambda reduced.
- Best/eval score uses `Ip_a = 5000 A` and `Ip weight = 0.08`.

Ip is still monitored; it is not removed entirely.

### 4. Longer actor freeze and slower actor updates

- Resume from B99.6 `best_error_score`.
- Freeze actor/eta for 220k env steps after resume.
- After freeze, actor update cadence is very conservative:
  - `actor_update_every = 32`
  - `policy_loss_lower_clip = -1.0`
  - `actor_lr = 3e-5`

### 5. Final eval includes protected best actor

Final evaluation now evaluates:

- latest actor
- protected `best_error_score` actor

This avoids the B99.7 ambiguity where final eval only showed latest policy, not the best saved policy.

## Kept unchanged

- runtime-only TSC mode
- GEQDSK plasma-boundary extrema observation
- stage0-only curriculum
- 10 ms control period
- 192 rollout workers
- no symlink / no persistent TSC daemon
- no contact feature
- no 36-point boundary observation
- no directional hand-coded R/Z action patch
