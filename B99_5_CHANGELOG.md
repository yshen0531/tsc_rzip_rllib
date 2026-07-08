# B99.5 Changelog — terminal/late constrained actor-dual run

B99.5 is based on B99.4. It keeps the B99.4 runtime-only TSC file flow, GEQDSK plasma-boundary observation, worker timing, and learner timing. The change is focused on the training failure mode observed in B99.4:

- R/Z/Ip stopped improving together by about iteration 79.
- The policy settled in a biased basin around R error ≈ -0.15~-0.16 m, Z error ≈ -0.14 m, and Ip error ≈ -400~-550 A.
- Duals were active, but the actor-side cost pressure remained too weak to pull the policy out of that basin.

## Main changes

### 1. New symmetric terminal/late cost type

`scripts/train_mpo.py` now supports:

```text
max_abs_error_late_terminal
```

This cost type keeps the same cost dimensions, e.g. `R`, `Z`, `Ip`, but computes each value as the maximum of:

```text
global instantaneous abs-error excess
late/hold-phase abs-error excess
terminal abs-error excess
```

It uses absolute errors, so it penalizes both signs. It is not a directional R/Z hand patch.

### 2. R/Z/Ip costs changed from plain abs_error

B99.4 used ordinary `abs_error` costs for R/Z/Ip. B99.5 uses the new terminal/late cost:

- R: global tol 0.05 m, late/terminal tol 0.04 m.
- Z: global tol 0.05 m, late/terminal tol 0.04 m.
- Ip: global tol 5000 A, late/terminal tol 3000 A.

R/Z terminal multiplier is stronger than the global term so terminal/hold errors are no longer washed out by whole-trajectory averages.

### 3. Stronger actor-side cost pressure

```text
actor_cost_coeff: 0.01 -> 0.03
```

The B99.4 logs showed `actor_cost_penalty` was still too small relative to the clipped policy loss. B99.5 makes the learned cost critics/duals more visible in the actor objective.

### 4. Tighter R/Z dual targets and stronger initial R/Z duals

```text
R/Z target: 0.7 -> 0.5
R/Z init lambda: 0.08 -> 0.12
R/Z dual lr: 0.0008 -> 0.0012
```

Ip is also strengthened mildly:

```text
Ip init lambda: 0.04 -> 0.05
Ip dual lr: 0.0005 -> 0.0008
```

### 5. Actor update slowed further

```text
actor_update_every: 4 -> 6
policy_loss_lower_clip: -10 -> -8
```

The goal is to prevent the actor from locking into a fixed biased action template before the strengthened cost signal has enough influence.

### 6. Denser checkpointing

```text
checkpoint_every_iters: 50 -> 25
```

B99.4 showed useful intermediate windows can appear before the end of training. B99.5 saves more frequent checkpoints so we can inspect or recover better intermediate policies.

## What B99.5 deliberately does not change

- No runtime/symlink rewrite.
- No persistent TSC daemon.
- No 20 ms control-period change.
- No contact feature.
- No full 36-point boundary observation.
- No stage1 / 400 ms curriculum.
- No directional one-sided R/Z reward patch.
- No stronger action suppression beyond B99.4's mild regularization.

## Expected diagnostic signals

Early B99.5 should be judged by:

```text
cost/observed_R
cost/observed_Z
cost/observed_Ip
learner/actor_cost_penalty
learner/dual/lambda_R
learner/dual/lambda_Z
learner/dual/lambda_Ip
episode_terminal_R_error_mean
episode_terminal_Z_error_mean
episode_terminal_Ip_error_mean
learner/actor_mean_abs_action
fragment_mean_abs_action
```

The desired behavior is not simply lower action. The desired behavior is that R/Z/Ip terminal and late-hold errors stop settling into a fixed biased basin.
