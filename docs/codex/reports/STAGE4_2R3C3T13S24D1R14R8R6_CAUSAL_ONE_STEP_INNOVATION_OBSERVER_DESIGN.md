# Stage4.2R3c3T13S24D1R14R8R6 causal one-step innovation observer design

Frozen prospectively on 2026-08-07 after final R8R5 primary/independent
agreement, but before any R8R6 implementation, adapted prediction, residual,
tube, metric, route, or artifact is computed.

## Purpose

R8R5 authenticated and blindly evaluated a deployable causal no-action
observer.  Its fixed point center passed every blind point gate, but its
prospectively frozen global uncertainty tube missed one per-context
containment gate.  R8R5 remains final as
`CONTEXT_ROBUST_CAUSAL_OBSERVER_HOLDOUT_FAIL_REDESIGN_REQUIRED`; its threshold
or tube may not be changed post-result.

R8R6 is a new-identity, zero-new-TSC development audit.  It asks whether the
one-step prediction error that has already become observable on the same
trajectory can improve subsequent 120 ms no-action forecasts, while a more
conservative global tube remains small enough for a future constrained
controller.  It also explicitly tests whether online adaptation has a
measurable benefit.  If the uncertainty gate passes but adaptation does not
help, the scientific route is a static robust observer rather than an
unnecessary adaptive observer.

R8R6 is not a controller, MPC, formal-control result, robustness
qualification, Gate A result, expert dataset, BC, DAgger, or RL stage.

## Immutable source evidence

R8R6 must reauthenticate every R8/R8R3/R8R4 source contract already frozen by
R8R5 and the exact completed R8R5 evidence:

```text
R8R5 server run
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s24d1r14r8r5_runs/
  stage4_2r3c3t13s24d1r14r8r5_context_robust_observer_holdout_20260807_26b96e8_v1

R8R5 stage manifest SHA-256
  d737bb77a9547fac8c1378dab3fdbd63aeca60cc30fefc38ecf5dab181d441cc
R8R5 final stage state SHA-256
  dc564ddfb9edae9b044dfa358ddb98306b56f328a8fc06c60b8c43ade772e48c
R8R5 holdout raw count / bytes / digest
  8 / 245493
  55cae64bf5b907b4cd6013615388dbb637dd2f1f14e49bda7fb49d11cf5b3d14
R8R5 holdout raw primary / independent SHA-256
  b7de85b3041f753b43a2a62cf51467a3981f558424f65c0b959bf5ba434e6193
  f9b2f69fb24e616438276c555cfd7735985ba658f67259c68be80bbd371b3379
R8R5 holdout model detailed / summary / independent SHA-256
  ff9b5bc6f9fde008b6e43ebe200c27d58a86fa82140d5d45d689777681d0f67d
  61a4cce213f74a88843f1df982037b09d0939057154ed9cc9c2491c40d3d1614
  c5089f9a69987d4c469f765369edd39d75418aa0cbcf99a0de07ecc47eb0700b
R8R5 final report SHA-256
  c2f7307dd3ea5265c6099443b9dac85365dfe70db6d7c5e0ac08c3fe4b34df65
R8R5 frozen all-development model / tube SHA-256
  d3d7ecebbe51ca20e83cdb126682d2bebad749b8fd5cb67dd57b3baf416e77e4
  3a436307a507b9aacda85321dd4d55e6bbcc996efe2e25c2b5026571c7108786
R8R5 required route
  CONTEXT_ROBUST_CAUSAL_OBSERVER_HOLDOUT_FAIL_REDESIGN_REQUIRED
```

The immutable R8R5 blind result is:

```text
point rows                                                   120 / 120
prescribed-issue point rows                                    32 / 32
aggregate tube containment                                   117 / 120
contexts satisfying every point/tube gate                         7 / 8
failed context
  p5_q2_a0p900_gap4_settle4 | plus_first
failed-context containment                                     14 / 16
required                                                       15 / 16
finite-exclusion violations                                           0
```

These numbers motivate a new design but are not an R8R6 result.

## Frozen development bank

All source baseline evidence is now consumed development evidence.  Combine:

```text
R8/R8R3 prior physical pairs                                  12
R8R4 fresh-development physical pairs                          4
R8R5 now-opened blind physical pairs                           4
total physical pairs                                          20
history contexts                                              40
causal origin rows                                           600
prescribed issue rows                                        160
```

Each pair contributes both complete hidden-history members.  Origins remain
task steps 10 through `last_state - 12`; the future forecast length remains
12 states / 120 ms.  The bank must reproduce the R8R5 development 480 rows
and blind 120 rows exactly before any R8R6 computation.

All 20 pairs, including the former R8R5 holdout, are development-only after
R8R5 was opened.  R8R6 makes no new holdout claim.  No source raw, snapshot,
model, audit, state, or manifest may be modified.

## Unchanged deployable input and fixed cold observer

The visible state, physical scales, 353-dimensional causal feature, forbidden
fields, zero-future-action contract, and exact 10 ms integration are unchanged
from R8R5.  At origin `t`, only the same trajectory's visible states through
`t`, actions through `t-1`, measured applied currents through `t`, numeric user
target, and causal task clock may be used.

Every outer fold uses the single fixed model:

```text
family                         linear
PCA rank                       32
ridge                          1e-6
candidate selection            forbidden
outer group                    complete physical pair
outer folds                    20
training pairs per fold        19
```

Pair ID, history label, source identity, partition, prefix, target ID, delay
or slew label, source outcome, formal outcome, wire current, hidden state,
future measurement/current/action, and held-out outcome remain forbidden
predictor inputs.  Pair and history identifiers are evaluator-only grouping
keys.

## Fixed causal one-step innovation

For each held context, compute the fixed cold forecast sequentially at every
origin.  Origin 10 has no earlier prediction and therefore uses the cold
forecast unchanged.

At every origin `t >= 11`, the prediction made at `t-1` for its first future
state was committed before state `t` existed.  Once state `t` is observed,
define the deployable innovation over dynamic components only:

```text
nu_t = visible_t[vR, vZ, Ip]
       - cold_prediction_from_origin_(t-1)[lag 1, vR, vZ, Ip]
```

Clip `nu_t` componentwise in physical units before use:

```text
[vR, vZ, Ip] = [0.02 m/s, 0.02 m/s, 1000 A]
```

The sole persistence factor is fixed at `rho = 0.8`.  For future lag
`h = 1..12`:

```text
adapted[vR, vZ, Ip](t+h)
  = cold[vR, vZ, Ip](t+h) + rho ** (h - 1) * clipped(nu_t)
```

R and Z are not shifted independently.  They are reconstructed from the
actually observed position at origin `t` by integrating the adapted vR/vZ
with the unchanged 10 ms interval and physical scale conversion.  This keeps
position and velocity kinematically consistent.

There is no fitted innovation coefficient, no candidate list, no smoothing
choice, no pair/history lookup, no matched trajectory, no future residual,
no outcome-conditioned reset, and no post-result clipping change.  A
non-finite innovation or prediction fails closed.  A live controller must use
the cold observer as its startup/fallback until the first committed one-step
prediction can be scored.

Expected evaluation counts are:

```text
cold-start fallback rows at origin 10                         40
adapted rows at origins 11 and later                         560
adapted prescribed issue rows at origins 14, 18, and 22      120
```

## Fixed context-robust tube

Construct one global 12-by-5 tube from the 560 outer-fold adapted residual
rows only.  No context label enters the predictor or the final tube.

For each lag/component, take the higher empirical 0.95 quantile of absolute
physical residuals and the unchanged physical floor:

```text
[R, Z, vR, vZ, Ip] = [1e-9 m, 1e-9 m, 1e-7 m/s, 1e-7 m/s, 1e-4 A]
```

For each complete row, form the maximum component/lag ratio to that base
tube.  The fixed calibration ratio is the maximum of:

```text
higher 0.95 quantile across all 560 row ratios
higher 0.90 quantile within every one of the 40 contexts
```

The single tube scalar is prospectively fixed as:

```text
max(1.0, 2.0 * calibration_ratio)
```

The factor 2.0 is a new prospective uncertainty reserve, not a relabeling or
repair of the frozen R8R5 tube.  The final tube must remain componentwise at
or below:

```text
[R, Z, vR, vZ, Ip] = [0.01 m, 0.01 m, 0.05 m/s, 0.05 m/s, 3000 A]
```

## Frozen gates

Source authentication, exact row counts, finite inputs, forbidden-field
absence, whole-pair isolation, causal one-step availability, and independent
reconstruction are hard gates.

Cold startup/fallback must pass the unchanged practical point caps for all
40 origin-10 rows:

```text
[R, Z, vR, vZ, Ip] = [0.003 m, 0.003 m, 0.02 m/s, 0.02 m/s, 1000 A]
```

For the 560 adapted rows:

```text
finite-exclusion violations                                      0
aggregate point pass rate                                    >= 95%
each context point pass rate                                 >= 90%
adapted prescribed-issue point pass rate                     >= 95%
each context adapted prescribed issues                         3 / 3
aggregate tube containment                                   >= 95%
each context tube containment                                >= 90%
global tube within the fixed component caps                    true
```

The finite-exclusion caps remain
`[0.01 m, 0.01 m, 0.05 m/s, 0.05 m/s, 3000 A]`.

Adaptation is useful only if, on exactly the same 560 held-pair predictions:

```text
adapted aggregate mean squared scaled error
  <= 0.95 * cold aggregate mean squared scaled error
each context adapted MSE
  <= 1.05 * that context's cold MSE
contexts with strictly lower adapted MSE                     >= 24 / 40
```

The uncertainty/point gates and the usefulness gates are reported separately.
No miss may be relabeled after inspection.

The structurally independent implementation must separately reconstruct the
source bank, folds, cold fits, sequential one-step availability, clipping,
adapted predictions, integration, residuals, tube, gates, artifacts, and
route.  Numerical agreement uses relative tolerance `1e-10` and absolute
tolerance `1e-12`.

## Frozen routes

```text
source, causality, identity, artifact, or independent disagreement
  CAUSAL_ONE_STEP_INNOVATION_AUDIT_FAIL_STOP

cold fallback, adapted point, finite, or tube gate fails
  CAUSAL_ONE_STEP_INNOVATION_OBSERVER_FAIL_REDESIGN_REQUIRED

observer/tube gates pass but measurable adaptation benefit fails
  CAUSAL_ONE_STEP_INNOVATION_NO_MEASURABLE_GAIN_STATIC_ROBUST_OBSERVER_SENTINEL_REQUIRED

observer/tube and measurable adaptation gates all pass
  CAUSAL_ONE_STEP_INNOVATION_PASS_FRESH_INTERACTION_SENTINEL_REQUIRED
```

Either non-audit route with every observer/tube gate passed may authorize only
a separately frozen fresh authentic interaction sentinel.  The selected
future observer is adaptive only when the measurable-benefit gate passes;
otherwise the cold static center plus the frozen robust tube is used.  The
sentinel must freeze actions, contexts, warmup/fallback, exact Card15 and
current bounds, controller information, and acceptance criteria before any
new result is opened.

## Formal and learning boundary

The immutable formal timing remains 250/270 ms arrival and 350/370 ms hold,
with 30 mm R/Z, 0.1 m/s speed, unchanged Ip and arrival streak.  A 120 ms
observer forecast does not extend those deadlines.

R8R6 executes zero Ray, `gotsc`, TSC, controller, or plant advances.  Every
source trajectory remains forbidden from expert data.  MPC, Gate A, expert
data, BC, DAgger, and bounded residual RL remain unauthorized regardless of
R8R6 outcome.
