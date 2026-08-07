# Stage4.2R3c3T13S24D1R14R8R3 causal history no-action observer design

Frozen prospectively after final R8R2 primary/independent agreement, but
before any R8R3 feature matrix, fit, cross-validated prediction, observer
metric, route, or model artifact is computed.

## Purpose

R8R2 rejected its fixed four-point affine no-action forecast: only 17/96
windows remained inside the frozen component caps.  Because that prerequisite
failed, R8R2 never evaluated the separately frozen same-trajectory innovation
adapter.  R8R3 replaces only the rejected no-action forecast with a causal,
history-conditioned dynamics observer trained on already opened baseline raw.

R8R3 asks whether a deployable observation at a candidate issue state can
forecast the next 120 ms of the same trajectory under the already authenticated
zero-future-increment contract.  It is a zero-new-TSC development observer
audit.  It is not an action-response result, controller, MPC, formal-control,
calibration, holdout, robustness, or Gate A result.

## Immutable source evidence

R8R3 must authenticate the unchanged R8, R8R1, and R8R2 sources before any
fit.  The controlling source hashes are:

```text
R8 source run
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s24d1r14r8_runs/
  stage4_2r3c3t13s24d1r14r8_partitioned_broad_response_identification_20260804_5e57f60_v2
R8 stage state SHA-256
  9fff80668023f17d3be273f9cd9694e21b401a5f668c60c1e03508a164c6d5d3
R8 manifest SHA-256
  67d1dc0604aa241161850578fb75c6f04bb140a1f791a5246b9f24c8d8df9f90
R8 training raw count / bytes / digest
  624 / 19725920
  b5de1cabe0bd47b0d3a3b26aff04714ca0c05653483cd4c92403dc5867eeb762

R8R1 primary detailed / summary / independent / final state SHA-256
  bd0041c3e16b56fce28abb80526bb5f1628ee74f6f5b52a70aaa07019e86a1ee
  5d6c2eb4282dba1ba29e25624b147af8b760c8cfbe5fd085374cf54110de6204
  3f378dba6eb1304422397b44a347e34d35827624ca6ea61791e85f16e7a5341c
  3f25e7070fd56243b1581b7da17cb433e0876821437bc9e7e098cdf4626d869f

R8R2 config SHA-256
  43e513942b66bdae94d8089b5885455f148c961b2a68be03a879444859149fe1
R8R2 primary detailed / summary / independent / final state SHA-256
  ad04374987ce4de599d71f4673ac110fe763928831e4c9610cdb117efd7977cf
  05d761ef64c9e7c2373a6754184ecf42cf0a250d26ee235293e768c0416c0bb2
  2ca90fab851c4131f7242bd9a5331286bde15ccaf47d251348b7d80a4597066c
  ee06726c8a5170ffd03a9465432ceed6f42053e2db8f710442c80c7809f07670
R8R2 required route
  CAUSAL_ONLINE_INNOVATION_BASELINE_FORECAST_FAIL_OBSERVER_IDENTIFICATION_REQUIRED
```

The R2/R4/R6 source runs used by R8 must also pass their unchanged R8 source
contracts.  R8 calibration and holdout raw must remain zero, heldout outcomes
must remain unopened, and no source raw or snapshot may change.

Before this design was frozen, a structure-only server read using the existing
server virtual environment reconstructed the unchanged R8R2 bank without a
fit or observer metric:

```text
physical pairs                                      12
history contexts                                    24
R8 response records                                912
prescribed issue windows                            96
baseline visible lengths                         36 / 38
causal 10-history / 12-future origin rows           360
```

## Zero-future-input baseline contract

Every baseline raw must independently retain the R8 audit property:

```text
action_norm_tsc[task step 10:]               exactly zero
diff(currents_a_tsc[state 10:])              exactly zero
```

Thus a forecast made at origin `t >= 10` has a fixed, known future input:
zero incremental action and unchanged applied coil-current target.  No future
action or future current readback is supplied to the observer.

For each of the 24 contexts, construct one causal origin row for every
integer:

```text
t = 10 ... (number of trajectory states - 1 - 12)
```

The expected total is exactly 360 rows.  Source selection is frozen so that
each prescribed R8R2 target is reproduced exactly:

```text
new R8 training-extension context
  use its R8 baseline for every origin

consumed R2/R4/R6 context, origin 10
  use its R2 baseline

consumed R2/R4/R6 context, origin 11 or later
  use its R4 baseline
```

The R6 source remains authentication evidence for the combined response bank
but does not supply a baseline target.  At prescribed origins 10, 14, 18, and
22, the selected baseline visible arrays must be byte-for-byte numerically
identical to the 96 arrays reconstructed by R8R2.

## Deployable causal feature

Visible state and scales remain:

```text
[R, Z, causal backward-difference vR, causal backward-difference vZ, Ip]
scales = [0.03 m, 0.03 m, 0.1 m/s, 0.1 m/s, 10000 A]
dt = 0.01 s
```

At origin `t`, construct the fixed 353-dimensional feature solely from
information available at that origin:

```text
visible states t-10 ... t                         11 * 5 = 55
already issued action_norm_tsc rows t-10 ... t-1 10 * 14 = 140
measured currents_a_tsc states t-10 ... t          11 * 14 = 154
numeric user target R/Z/Ip offsets, fixed scales               3
relative task clock (t - 10) / 15                              1
total                                                        353
```

All origins are at least 10, so there is no padding or availability inference.
The action at task step `t` is not included.  The current at state `t` is an
already observed plant-interface value; current at state `t+1` or later is
forbidden.  Per-fold standardization and PCA parameters are learned only from
that fold's training pairs.

For every one of the 912 probe responses, independently reconstruct the same
353-dimensional issue feature from that probe's own prefix.  Equality to the
matched baseline feature is an audit assertion only.  The live feature must
not be copied from the baseline, and neither future trajectory may be opened
to construct it.

Pair, history, source stage, partition, prefix, target ID, regime, delay/slew,
experiment ID, source outcome, formal outcome, hidden or wire current, matched
baseline future, future measurement, future probe state, and future executed
action are forbidden predictor inputs.  Pair and history identifiers may be
used only for split enforcement, source selection, equality auditing, and
stratified reporting.  The numeric user target offsets and relative clock are
allowed deployable inputs; categorical labels are not.

## Prediction target and kinematic reconstruction

For training/evaluation only, the target at origin `t` is the next 12 baseline
visible states.  The learned multi-output target contains only the causal-
origin-relative changes:

```text
[vR(t+k)-vR(t), vZ(t+k)-vZ(t), Ip(t+k)-Ip(t)]
for k = 1 ... 12
```

The model emits all 36 values in one direct prediction.  Add the predicted
changes to the observed origin vR/vZ/Ip.  Reconstruct R/Z from the observed
origin R/Z by integrating predicted vR/vZ with the exact 10 ms and physical-
scale conversion.  No independent learned R/Z head, future-state reset,
clipping, smoothing, recursive outcome input, or post-result correction is
allowed.

## Frozen candidate family

Every candidate uses fold-local feature mean/standard deviation, a standard-
deviation floor of `1e-12`, and fold-local PCA.  PCA signs are canonicalized
by making each component's largest-absolute loading positive; exact ties use
the lowest feature index.  Candidate ranks are:

```text
[8, 16, 24, 32]
```

For every rank, fit both prospectively declared kernel families:

```text
linear kernel
  K(x,y) = dot(x,y) / rank
  ridge in [1e-6, 1e-3, 1e-1]

RBF kernel
  bandwidth = multiplier * median positive training-pair distance
  multiplier in [0.5, 1.0, 2.0]
  ridge in [1e-6, 1e-3, 1e-1]
```

Each candidate subtracts the training-target mean, solves kernel ridge by
least squares, and adds the training-target mean at prediction.  The bandwidth
floor is `1e-12`.  There are exactly 48 candidates.  No architecture,
feature, rank, bandwidth, ridge, blend, neighbor count, output transform, or
threshold may be added after viewing an R8R3 result.

## Whole-pair nested validation

There are twelve outer folds.  Each holds one complete physical pair: both
history members, every available origin, and all prescribed issue windows.

Inside each outer fold, select one candidate using leave-one-training-pair-out
predictions over all available origin rows from the remaining eleven pairs.
The lexicographic selection score is:

1. number of rows with any physical component-cap violation;
2. total component-by-future-state cap violations;
3. maximum absolute scaled point error;
4. 95th percentile of per-row maximum scaled point error;
5. mean squared scaled error;
6. family order `linear`, then `rbf`;
7. increasing PCA rank;
8. increasing bandwidth multiplier, with linear treated as zero; and
9. increasing ridge.

Fit the selected candidate on all eleven outer-training pairs, then predict
the complete held pair.  A held-pair target cannot affect its preprocessing,
PCA, bandwidth, target mean, kernel coefficients, candidate selection, or
uncertainty tube.

## Fold-local uncertainty tube

For the selected candidate in each outer fold, retain its inner whole-pair
out-of-fold residuals.  For each of the 12 future lags and five physical
components, freeze the half-width as:

```text
1.25 * maximum absolute inner residual + component floor
```

where physical component floors are:

```text
[1e-9 m, 1e-9 m, 1e-7 m/s, 1e-7 m/s, 1e-4 A]
```

There is no clipping to the deployment caps.  Each fold-local tube must be
finite, no wider than the unchanged component cap at every lag, and contain
every corresponding held-pair value.  This is a finite development tube, not
a probabilistic or unseen-distribution guarantee.

## Frozen observer gates

The primary outer predictions must reconstruct exactly:

```text
outer folds                                          12
outer origin rows                                   360
prescribed issue rows                                96
future states per row                                12
probe-prefix features reconstructed                  912
forbidden predictor inputs                             0
matched-baseline future predictor inputs               0
```

All 360 outer rows and all their future states must be finite and remain
inside the unchanged physical absolute-error caps:

```text
[R, Z, vR, vZ, Ip]
[0.003 m, 0.003 m, 0.01 m/s, 0.01 m/s, 1000 A]
```

In addition:

```text
rows with any cap violation                           0 / 360
prescribed issue rows with any cap violation           0 / 96
fold-local tubes within caps                         12 / 12
outer rows contained by fold-local tubes            360 / 360
each physical pair origin-row pass count        all available / all
each history-member origin-row pass count       all available / all
probe-prefix feature equality to its baseline       912 / 912
```

The caps are deterministic observer-development gates and do not change the
formal tracking tolerance.  Every miss remains a miss.  No average, pair
aggregate, post-result tube expansion, or practical-policy exception can
convert an R8R3 miss into a pass.

## All-development artifact

Only after every outer gate passes, select the all-development candidate by
the same leave-one-pair-out rule over all 360 rows, fit it on all twelve pairs,
and derive its 1.25-times leave-one-pair-out component tube.  The serialized
artifact must contain the feature contract, preprocessing/PCA arrays, kernel
family and hyperparameters, training projected features, bandwidth when
applicable, target mean, coefficients, tube, source hashes, and exact model
SHA-256.  The all-data fit is not validation.

If any gate fails, no deployable observer artifact is emitted.  Diagnostics
may preserve fold selections and prediction errors but may not be relabeled
as a qualified model.

## Independent recomputation

A structurally independent implementation must separately reconstruct source
authentication, baseline selection, 360 causal origin rows, all 912 probe
features, fold splits, PCA sign convention, candidate scores, nested
predictions, tubes, physical errors, route, and artifact-presence decision.
It may import only immutable low-level raw parsing/visible-state helpers, not
the primary observer fit, prediction, selection, evaluation, or routing
functions.  Numerical agreement uses relative tolerance `1e-10` and absolute
tolerance `1e-12`; categorical, count, hash, and route agreement is exact.

## Frozen routes

```text
source/raw/identity/causality/feature/independent disagreement
  CAUSAL_HISTORY_NO_ACTION_OBSERVER_AUDIT_FAIL_STOP

any model, component-cap, tube-cap, containment, or coverage gate fails
  CAUSAL_HISTORY_NO_ACTION_OBSERVER_FAIL_FRESH_IDENTIFICATION_REQUIRED

every frozen observer gate and independent recomputation passes
  CAUSAL_HISTORY_NO_ACTION_OBSERVER_PASS_COMBINED_ADAPTATION_FREEZE_REQUIRED
```

A failure rejects this finite 353-feature, 48-candidate development observer;
it does not prove global unobservability, controller failure, plant
unreachability, or formal-control failure.  The failure route requires a
separately frozen fresh causal observer-identification campaign before new
TSC.

A pass authorizes only a separately frozen R8R4-style zero-TSC combination
with the already specified R8R2 innovation architecture.  R8R2 itself remains
immutable.  No action-response model, controller, or authentic interaction is
authorized directly by R8R3.

## Formal and learning boundary

The formal contract remains unchanged:

```text
normal slew: arrive by state 25; hold/evaluate through state 35
weak slew:   arrive by state 27; hold/evaluate through state 37
R/Z tolerance 0.03 m; speed 0.1 m/s; Ip 10000 A; streak 3
```

The 120 ms observer window never extends an arrival deadline.  R8R3 runs zero
controller, Ray, `gotsc`, TSC, or plant steps.  Probe trajectories remain
forbidden from expert datasets.  MPC, Gate A, expert data, BC, DAgger, and
bounded residual RL remain unauthorized regardless of R8R3 outcome.
