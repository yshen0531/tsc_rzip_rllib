# Stage4.2R3c3T13S24D1R14R8R2 causal online innovation/adaptation design

Frozen prospectively after final R8R1 primary/independent agreement, but
before R8R2 implementation, any R8R2 fit, rolling prediction, metric, route,
or artifact is computed.

## Purpose

R8R1 proved that the fixed R8-selected cold-start response center is not
controller-useful even at a common 80 ms horizon. It did not test whether
measurements from the same trajectory can causally identify and correct the
context-dependent response error after an action begins to take effect.

R8R2 is a zero-new-TSC deployability discriminator. It asks whether a simple,
bounded, same-trajectory innovation anchor can turn the fixed cold-start
candidate into a useful rolling 80 ms predictor after at most 20 or 40 ms of
real observations. It explicitly separates:

```text
matched no-action trajectory
  evaluator-only response label; unavailable to a live controller

same probe trajectory prefix
  deployable causal input available by the current task step
```

R8R2 is not a controller, MPC, closed-loop, formal-control, calibration,
holdout, robustness, or Gate A result.

## Immutable evidence

R8R2 uses only the already opened twelve-pair training bank authenticated by
R8R1. It must reauthenticate:

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
R8 primary detailed / summary SHA-256
  797c862666a7bf8f770816bfa83d20f9b2cedea8dfa4be49f061d81680578a50
  2538601ff1086357a96a1f9646a0f9368108fe648b0897da2d987624db111968
R8 independent SHA-256
  cfb4ad0aebc838045468e6dd9e5937007c06a07458a458f253a0dd411861cba0

R8R1 output
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s24d1r14r8r1_runs/
  stage4_2r3c3t13s24d1r14r8r1_fixed_candidate_short_horizon_discriminator_20260805_c2ed69f_v1
R8R1 primary detailed / summary / independent / final state SHA-256
  bd0041c3e16b56fce28abb80526bb5f1628ee74f6f5b52a70aaa07019e86a1ee
  5d6c2eb4282dba1ba29e25624b147af8b760c8cfbe5fd085374cf54110de6204
  3f378dba6eb1304422397b44a347e34d35827624ca6ea61791e85f16e7a5341c
  3f25e7070fd56243b1581b7da17cb433e0876821437bc9e7e098cdf4626d869f
```

The combined bank must reconstruct exactly:

```text
physical pairs                                      12
history contexts                                    24
action responses                                   912
responses per pair                                  76
responses per context                               38
no-action origin windows                            96
causal descriptor dimension                        142
relative response minimum length                    12
```

R8 calibration and holdout raw must remain zero before and after R8R2,
`heldout_outcomes_opened` must remain false, and no source raw may change.

## Deployable observation contract

The visible state is unchanged:

```text
[R, Z, causal backward-difference vR, causal backward-difference vZ, Ip]
scales = [0.03 m, 0.03 m, 0.1 m/s, 0.1 m/s, 10000 A]
dt = 0.01 s
```

At the issue task step, the 142-dimensional descriptor must be reconstructed
from that probe trajectory's own visible prefix, availability mask, declared
target offsets, and relative issue time. Any probe/baseline preissue equality
is audit evidence only; the implementation must always construct the live
descriptor from the probe prefix and must not read the matched baseline to
obtain or correct it.

The only post-issue predictor inputs are:

```text
the same probe trajectory's visible states through the current update lag
the known issued action sign, direction, and scale
the fixed cold-start prediction made at issue time
the fixed causal no-action forecast defined below
```

Pair, history, source-stage, partition, prefix, target ID, regime, delay/slew
labels, hidden/current/source coil or wire current, matched-baseline future,
future probe state, source outcome, and future executed action are forbidden
predictor inputs. Pair and history identifiers may be used only to enforce
whole-pair folds and report strata.

The matched no-action trajectory remains permitted only after prediction as
the evaluator's ground-truth response label. It is never an online feature,
normalizer, anchor, or candidate-selection input for its own held pair.

## Fixed cold-start response model

Every outer and inner fit retains the R8R1 candidate without new model search:

```text
PCA rank                         4
RBF median-distance multiplier  2.0
kernel ridge                    0.1
action sign/direction heads     unchanged
```

The model is trained only on complete non-held physical pairs. Its output is
the issue-origin response prediction at all required relative lags. R8R2 may
adapt this prediction causally; it may not replace it with another cold-start
architecture or use R8R1 results to add capacity.

## Fixed causal no-action forecast

The no-action forecast has no learned parameter. At each issue state:

1. take scaled causal `vR`, `vZ`, and `Ip` at task steps `issue-3` through
   `issue` from the same trajectory;
2. fit an ordinary least-squares affine trend versus offsets `[-3,-2,-1,0]`
   independently for those three components;
3. extrapolate the three components at future relative lags 1 through 12;
4. initialize R/Z at the issue state and integrate the forecast vR/vZ with
   the exact 10 ms and physical-scale conversion; and
5. perform no clipping, outcome-conditioned reset, smoothing choice, or
   post-result refit.

Every no-action forecast is made before reading its future. Non-finite or
ill-shaped input/output fails closed.

The 96 evaluator windows comprise four issue origins for each of the 24
contexts. A matched no-action trajectory may be used only to score the frozen
forecast after it is emitted.

## Fixed same-trajectory innovation anchor

The tested causal update lags are:

```text
observed relative states    elapsed warmup    future prediction window
2                           20 ms             next 8 states / 80 ms
4                           40 ms             next 8 states / 80 ms
```

At an update lag `m`, construct for each already observed lag `j <= m`:

```text
proxy_response[j]
  = observed_probe_visible[issue + j] - frozen_no_action_forecast[j]

innovation[j, vR/vZ/Ip]
  = proxy_response[j, vR/vZ/Ip] - cold_start_response[j, vR/vZ/Ip]
```

The only adapter candidates are the preregistered recency factors:

```text
lambda in [0.0, 0.5, 0.8]
weight(j) proportional to lambda ** (m - j)
lambda = 0.0 means the latest innovation only
```

The weighted innovation mean is held constant over the next eight predicted
states for vR, vZ, and Ip. Future R/Z response is anchored at the current
causal `proxy_response[m, R/Z]` and integrates the corrected future response
velocities using the exact 10 ms and scale conversion. No future observation,
matched baseline value, adaptive clipping, nonlinear tail, or outcome label
may enter the update.

This deliberately small adapter tests observability and local correction. It
is not an unrestricted sequence model and cannot own the 14-coil action.

## Whole-pair nested validation

There are twelve outer folds. Each holds one complete physical pair, both of
its histories, all issue times, signs, directions, and action scales.

For each update lag separately, select `lambda` using only the other eleven
pairs. Selection uses leave-one-training-pair-out inner predictions and the
following lexicographic score:

1. hard-envelope failure count;
2. unchanged response-gate failure count;
3. maximum absolute scaled point error;
4. 95th percentile relative L2 error;
5. numerical `lambda` as deterministic tie-breaker.

Then fit the unchanged cold-start model on all eleven outer-training pairs and
evaluate the fixed selected adapter on the held pair. A candidate may differ
between outer folds and update lags only through this frozen nested rule. No
held-pair outcome participates in selection.

The structurally independent implementation must separately reconstruct raw,
visible state, descriptors, no-action forecasts, cold predictions, nested
selection, online innovations, response predictions, metrics, geometry, and
route. Complete numerical agreement uses relative tolerance `1e-10` and
absolute tolerance `1e-12`.

## Hard no-action forecast gate

All 96 no-action origin windows must be finite and must individually remain
inside the unchanged physical component bounds throughout the required future
window:

```text
[R, Z, vR, vZ, Ip]
[0.003 m, 0.003 m, 0.01 m/s, 0.01 m/s, 1000 A]
```

This is a deployability gate, not an average score. A failure means the
existing visible history does not support this frozen online innovation proxy
and routes to a causal baseline-observer/new-identification design.

## Hard adapted-prediction envelope

At a candidate update lag, all 912 outer predictions must satisfy:

```text
finite target and prediction                               912 / 912
maximum absolute scaled point error                         <= 0.10
componentwise floor + 2 * maximum absolute residual
  within [0.003 m, 0.003 m, 0.01 m/s, 0.01 m/s, 1000 A]
response cosine for every row                                >= 0.00
predicted/actual peak ratio for every row            within [0.25, 2.00]
actual and predicted peak                                      >= 0.0025
actual and predicted canonical geometry               rank 4, cond <= 20
actual and predicted operational geometry             rank 4, cond <= 20
```

These hard bounds prevent an aggregate score from hiding non-finite,
wrong-direction, vanishing, explosive, or ill-conditioned predictions. They
do not replace the unchanged response-quality gates below.

## Prospectively relaxed useful-performance gate

The practical application allows a bounded local performance gap, so R8R2
does not require every deterministic development row to meet the stricter
shape-quality thresholds. Each row is still scored without relabeling under
the unchanged R8/R8R1 response gates:

```text
relative L2 error                              <= 0.75
response cosine                                >= 0.80
predicted/actual peak ratio              within [0.50, 1.50]
maximum absolute scaled point error              <= 0.10
```

An update lag is controller-useful only if, in addition to every hard gate:

```text
unchanged all-response gate                   >= 867 / 912  (95%)
each complete physical pair                    >= 69 / 76   (90%)
each pair-history context                       >= 34 / 38
gain over its rolling cold-start comparator     >= 46 rows   (5% of 912)
per-pair pass count versus comparator            no regression
```

The rolling cold-start comparator is the unchanged fixed-candidate prediction
at the identical future relative lags `m+1` through `m+8`, scored against the
same evaluator-only response target without a causal innovation correction or
current-response anchor. It is recomputed inside the same outer fold and may
not reuse R8R1 aggregate counts.

Every miss remains a recorded miss. These aggregate criteria are frozen
before R8R2 results and do not weaken the immutable formal timing, safety,
restart, causality, or integrity gates. They only define whether the
development predictor is useful enough to justify an authentic sentinel.

Select the earliest passing update lag in order 2 then 4. If only lag 4
passes, any future sentinel must preregister a hard-safe 40 ms warmup/fallback;
the adapter may not control before its first allowed update.

## Frozen routes

```text
source, raw, identity, causality, or independent disagreement
  CAUSAL_ONLINE_INNOVATION_AUDIT_FAIL_STOP

96-window no-action forecast gate fails
  CAUSAL_ONLINE_INNOVATION_BASELINE_FORECAST_FAIL_OBSERVER_IDENTIFICATION_REQUIRED

no update lag satisfies the hard and useful gates
  CAUSAL_ONLINE_INNOVATION_ADAPTATION_FAIL_NEW_IDENTIFICATION_REQUIRED

update lag 2 or 4 satisfies every frozen gate
  CAUSAL_ONLINE_INNOVATION_ADAPTATION_PASS_FRESH_INTERACTION_SENTINEL_REQUIRED
```

A PASS may emit a development artifact containing the all-training fixed
cold-start model, selected recency factor by update lag, and immutable
no-action/anchor contract. It authorizes only a separately frozen fresh
authentic multipulse or receding interaction sentinel. That sentinel must
test the online proxy without a matched baseline input, exact Card15 actions,
hard current/action bounds, fallback, and first-update timing.

A FAIL does not prove global unobservability or plant unreachability. It
rejects this finite same-trajectory affine innovation anchor and routes to a
new observer/identification design, not post-result threshold changes.

## Formal and learning boundary

The formal contract remains unchanged:

```text
normal slew: arrive by state 25; hold/evaluate through state 35
weak slew:   arrive by state 27; hold/evaluate through state 37
R/Z tolerance 0.03 m; speed 0.1 m/s; Ip 10000 A; streak 3
```

The rolling 80 ms model window never extends an arrival deadline. R8R2 runs
zero controller, Ray, `gotsc`, TSC, or plant steps. Probe trajectories remain
forbidden from expert datasets. MPC, Gate A, expert data, BC, DAgger, and
bounded residual RL remain unauthorized regardless of R8R2 outcome.
