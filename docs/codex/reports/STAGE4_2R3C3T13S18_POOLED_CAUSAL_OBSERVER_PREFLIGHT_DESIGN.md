# Stage4.2R3c3T13S18 pooled causal observer preflight design

## Status and scope

This design is frozen after the final S17 failure and its explicitly
retrospective architecture screen, but before S18 audit implementation or
formal output.  S18 is a zero-new-TSC development preflight over the already
consumed S16/S17 evidence.  It is not an independent holdout and cannot
validate an observer or authorize MPC.

S18 asks one narrow question: can the fixed degree-three same-trajectory
causal predictor plus the known four-dimensional issued-action coordinate be
pooled across whole hidden-history pairs, with a fixed 4x inner-OOF residual
tube and causal Card15 sensitivity propagation, while covering every outer
whole-pair response inside the unchanged component caps?

## Immutable sources

The only raw source is the completed S16 run:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
stage4_2r3c3t13s16_runs/
stage4_2r3c3t13s16_orthogonal_fixed_basis_identification_20260802_165232
```

S18 must authenticate the 144-file S16 inventory digest
`b0bf9c03b94cd353b3ccb68b0de318c46285a4805acfb0c25016704f79057668`
and the exact S17 causal artifact and final result:

```text
causal artifact
  d8c8ee8f0c3f2e80cb1642c7f6400f47d5280e47459361dfa274421c37fdca76
final result
  98afee17ff682326853e7caa708264186c87ccf88bec92ddf2cd3275855b9a69
```

The S17 post-failure screen may document why the architecture was chosen,
but may not be treated as independent validation.

## Causal feature contract

Each signed response row has exactly nine predictor features:

```text
five degree-three state-11 response coordinates
  fitted only from this trajectory's visible R/Z/backward-vR/backward-vZ/Ip
  at states 1 through 10 and the fixed causal calibration schedule

four issued-action coordinates
  least-squares coordinates of the current trajectory's already issued
  signed delta in the frozen S16 four-column field basis
```

The issued-action coordinate must be reconstructed from the same trajectory's
`r3c3t13s9_signed_issue_delta_kAt_tsc`, frozen basis, and turn counts.  A
matched baseline rollout may not be used to construct the feature.

The feature interval contains:

```text
degree-three input radius
  absolute degree-three action sensitivity times current-run coordinate radius

coordinate radius
  current-run causal nominal-center plus issued-action quantized-readback
  uncertainty, projected through the fixed basis pseudoinverse
```

The nominal center is available from the same trace's frozen Card15 center
fields and must be passed through the exact frozen quantized actuator.  A
matched baseline readback interval, post-effect current, or future
measurement is forbidden.

Pair ID, history member, prefix, target, delay, slew, response direction/sign
labels, wire/vessel currents, source action/result, matched-baseline values,
and future probe schedule are forbidden predictor inputs.  Pair ID is allowed
only as an offline fold-assignment key.  The numeric issued action is a model
query input, not a label.

## Fixed whole-pair folds and fit

The eight lexicographically sorted S16 pair IDs are eight outer folds.  Each
fold holds both history members and all 16 signed response rows for that pair.
No row may be dropped.

For each outer fold:

1. Open outcomes for only the other seven whole pairs.
2. Standardize each feature using only those seven pairs.  A feature standard
   deviation at or below `1e-12` is replaced by one.
3. Divide targets by the unchanged response scales
   `(0.03, 0.03, 0.1, 0.1, 2000)`.
4. Select one ridge value from the fixed grid
   `(0, 1e-8, 1e-6, 1e-4, 1e-2, 1, 100)` by seven inner whole-pair OOF folds.
5. The deterministic selection tuple is lexicographic
   `(maximum absolute scaled OOF error, mean squared scaled OOF error,
   ridge value)`.
6. Recompute inner OOF predictions at that selected ridge.  The componentwise
   maximum absolute physical residual is the calibration residual.
7. Fit the final outer-fold model on all seven training pairs.

For each outer fold, the scaler, ridge, coefficients, inner predictions,
training IDs, forbidden held IDs, access log, calibration residual, and
feature-sensitivity matrix must be serialized and hashed before any of that
fold's 16 outcomes are opened.  Training outcomes used by another fold do not
count as leakage; held-out outcome access is audited separately for every
fold.

## Fixed tube

The S18 response halfwidth is frozen as:

```text
response floor
+ 4.0 * componentwise maximum inner whole-pair OOF residual
+ abs(physical-output feature sensitivity) @ causal feature radius
```

The response floor remains `(1e-9 m, 1e-9 m, 1e-7 m/s, 1e-7 m/s, 1e-4 A)`.
The multiplier `4.0` and the original caps may not be altered after S18
outcomes are opened.  The S17 one-trajectory hull remains failed and is not
reinterpreted.

## Frozen gates

```text
authenticated S16 raw                                144 / 144
outer whole-pair folds                                  8 / 8
response rows                                         128 / 128
held rows per fold                                      16 / 16
causal nine-feature extraction                         128 / 128
same-trajectory action-coordinate reconstruction       128 / 128
finite scaler/model/sensitivity/tube                    128 / 128
held-out outcome access before fold artifact hash               0
forbidden predictor inputs                                      0
outer response inside fixed tube                       128 / 128
fixed tube inside unchanged caps                       128 / 128
all gates jointly                                      128 / 128
new TSC, plant steps, raw, or snapshots                          0
```

The unchanged caps are `(0.003 m, 0.003 m, 0.010 m/s, 0.010 m/s,
1000 A)`.  All output must be independently recomputed from S16 raw and the
hashed fold artifacts.

## Routes

```text
POOLED_CAUSAL_OBSERVER_PREFLIGHT_PASS_FRESH_CAMPAIGN_REQUIRED
  Every gate passes.  Authorize only a separately frozen campaign with new
  whole-pair training, calibration, and unopened fresh-context holdout.  The
  S18 fit itself may not enter MPC.

POOLED_CAUSAL_OBSERVER_PREFLIGHT_FAIL_EXCITATION_OR_OBSERVER_REDESIGN
  Any gate fails.  Do not fit around failures, drop pairs, enlarge the tube,
  or open MPC.  Redesign the prospective excitation or causal observer.
```

S18 runs no controller, optimizer, Ray, `gotsc`, TSC, plant step, or snapshot
creation.  Neither route authorizes expert data, BC, DAgger, or bounded
residual RL.  The 250/270 ms arrival and 350/370 ms hold timing is unchanged.

