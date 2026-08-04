# Stage4.2R3c3T13S24D1R14R7 causal deconfounded response-model design

Frozen prospectively on 2026-08-04 after the final D1R14R6 primary and
independent evidence and before R7 implementation, model fitting, or route
evaluation.

## Purpose and boundary

R7 is a zero-new-TSC development study. It asks whether the authenticated
R2/R4/R6 isolated-pulse response bank supports a causal, sign-aware,
time-varying response model that generalizes when both hidden-history members
of one whole physical pair are excluded from fitting.

R7 may not model the absolute future closed-loop trajectory. D1R11/D1R12
already proved that target confounds plant response with continuing R17
feedback and moving Card15 centers. R7 models only the signed visible-state
increment between a probe and its exact matched zero-increment baseline.

The 256 probes and eight baselines are identification-development evidence
and are forbidden from expert datasets. R7 runs no controller, Ray, `gotsc`,
TSC, or plant step. A pass is not an MPC or control result.

## Immutable authenticated source bank

Before fitting, R7 must authenticate in place:

```text
R2 raw count / bytes / digest
  72 / 2,254,876 /
  c210f959e5ce85739dd0b1f70a2513f64f40c6697d01bf7b56db9621759a1649
R4 raw count / bytes / digest
  200 / 6,285,765 /
  44a7eb8e677f88f32c57a6be59273501e73f7657527371e1b59578a95c2ae7a9
R6 raw count / bytes / digest
  48 / 1,509,679 /
  c743eff98395325e4da35a28d2e646aacffb00e678753ceb0faf4b86a64aeb83
R6 primary final SHA-256
  5c9669818249e8146b6f63d6e50e54f482cb27e64a809fb857bdf64ed617f016
R6 independent final SHA-256
  a705aa669aaafd9b6708d6915655498f3f4f443ab37683eaa5ae5a8902ae9b1f
R6 combined bank
  signal 256/256, rank 64/64, condition 64/64, antipodality 128/128
```

R7 reconstructs the exact frozen bank:

```text
R2 issue step 10, four directions, two signs, eight contexts        64
R4 issue 14/18/22, directions 1--3, two signs, eight contexts      144
R6 issue 14/18/22, replacement direction 0, two signs, contexts     48
total signed probe responses                                       256
```

Every response is `probe - matched zero baseline` from first effect state
`issue + 1` through the unchanged 35/37-state horizon. The visible order and
scales remain:

```text
[R / 0.03 m, Z / 0.03 m, vR / 0.1 m/s, vZ / 0.1 m/s,
 Ip / 10000 A]
```

## Causal predictor interface

At a proposed issue task step, a response head may receive only:

1. visible R/Z/derived-vR/derived-vZ/Ip states already observed at indices
   `issue`, `issue-1`, `issue-2`, `issue-4`, and `max(0, issue-8)`;
2. numeric R/Z/Ip target offsets;
3. the current task clock;
4. the already revealed requested four-dimensional basis coordinate; and
5. its sign and direction, which are properties of that requested action.

The five visible snapshots use the response scales above. Numeric target
offsets use `[0.03 m, 0.03 m, 10000 A]`. The task clock is
`(issue_step - 10) / 12`.

Pair ID, history member, prefix label, target ID, regime label, source
outcome, matched future baseline value, source/current coil or wire-current
files, hidden vessel state, current-run future measurement, and future
executed action are forbidden predictor inputs. Pair/history fields may be
used only by the audit harness to create whole-pair folds and report errors.

## Fixed model family

The model has eight fixed heads: two action signs by four fixed basis
directions. It is piecewise linear in requested basis coefficients at later
controller use; R7 evaluates only the exact isolated basis actions present in
the bank. Sign is separated because the already frozen source evidence shows
genuine sign dependence.

For each head and each relative response lag:

1. Standardize the causal descriptor using training rows only, with standard
   deviation floor `1e-12`.
2. Fit training-only PCA by deterministic SVD.
3. Use an RBF kernel on the retained PCA coordinates.
4. Fit centered multi-output kernel ridge targets for only
   `[vR, vZ, Ip]` signed response.
5. Reconstruct R and Z response exactly by 10 ms discrete integration from
   zero response at the issue state.

When a late lag is absent for an earlier-ending trajectory, only rows that
actually contain that lag enter that lag's fit. No padding, future baseline,
or future measurement is allowed.

The complete fixed candidate grid is:

```text
PCA rank                   [2, 4, 6]
RBF median-distance scale  [0.5, 1.0, 2.0]
kernel ridge               [1e-6, 1e-3, 1e-1]
total candidates           27
```

For a candidate and lag, the RBF bandwidth is the candidate multiplier times
the median nonzero Euclidean distance among the training-only PCA rows. A
`1e-12` floor is used only if that median vanishes. Kernel ridge is solved by
deterministic least squares; no random seed or optimizer is involved.

## Frozen nested whole-pair protocol

The eight contexts comprise four physical pair IDs, each with both
`plus_first` and `minus_first` histories.

For each of four outer folds:

1. Hold out both histories of one whole pair: 64 responses.
2. On the remaining three pairs only, evaluate all 27 candidates by three
   inner leave-one-whole-pair-out folds.
3. Select one candidate by the following deterministic order:
   response-gate failure count, maximum scaled point error, 95th-percentile
   relative L2 error, mean squared scaled error, PCA-rank order, bandwidth
   order, then ridge order.
4. Refit the selected candidate using only the three outer-training pairs.
5. Predict the unopened outer pair.

Thus every reported outer prediction is produced by a candidate and all
preprocessing chosen without its pair's two histories or outcomes. The four
outer folds produce exactly 256 out-of-fold response predictions.

Only after all outer predictions are frozen may one final candidate be
selected from complete four-fold candidate development scores and fitted to
all eight contexts. That final all-data model is not counted as validation;
its hash can only identify a candidate for a separate fresh campaign.

## Frozen response and tube gates

All 256 outer predictions must be finite and preserve exact R/Z kinematic
construction. For each full signed response trajectory:

```text
relative L2 error                              <= 0.75
response cosine                                >= 0.80
predicted/actual peak ratio              within [0.50, 1.50]
```

The denominator for relative L2 is the actual response L2 norm, already
proved nonzero by R6. Cosine is computed on the flattened five-output
trajectory. The peak ratio uses maximum absolute scaled output. These gates
exclude the otherwise deceptively favorable all-zero predictor.

Across all points, the unchanged maximum scaled point-error limit remains
`0.1`. The componentwise out-of-fold residual envelope forms a conservative
precursor tube:

```text
response floor physical  [1e-9 m, 1e-9 m, 1e-7 m/s, 1e-7 m/s, 1e-4 A]
tube multiplier          2.0
tube caps physical       [0.003 m, 0.003 m, 0.01 m/s, 0.01 m/s, 1000 A]
```

Every component tube must remain within its cap. In addition, the 64
predicted context/time/sign four-direction branches must each preserve:

```text
four nonzero finite response columns                      64/64
predicted peak >= 0.0025 for every direction             256/256
rank four at relative SVD tolerance 1e-10                 64/64
condition number <= 20                                    64/64
```

The `0.0025` predicted floor is half the authenticated actual `0.005` floor
and is redundant with the per-response peak-ratio gate, but is recomputed
independently to fail closed on aggregation errors.

Primary and structurally separate implementations must agree on source
inventory, fold membership, selected candidates, all 256 row metrics,
component envelopes, predicted geometry, hashes, and route.

## Formal timing and scientific scope

R7 does not execute a tracking controller. The immutable timing contract is
unchanged and may not be evaluated on predicted isolated-probe responses as
if they were closed-loop trajectories:

```text
slew 1.0/1.1: arrive by 250 ms, evaluate through 350 ms
slew 0.9:     arrive by 270 ms, evaluate through 370 ms
R/Z <= 30 mm, speed <= 0.1 m/s, Ip threshold and streak unchanged
```

## Routes

```text
any source/package/bank mismatch before fitting
  CAUSAL_RESPONSE_MODEL_SOURCE_FAIL_NO_TSC

source passes, but any nested response/tube/geometry/independent gate fails
  CAUSAL_RESPONSE_MODEL_DEVELOPMENT_FAIL_BROADER_DECONFOUNDED_IDENTIFICATION_REQUIRED

all gates pass and independent replay agrees
  CAUSAL_RESPONSE_MODEL_DEVELOPMENT_PASS_FRESH_MULTIPULSE_VALIDATION_DESIGN_REQUIRED
```

Even a pass does not validate superposition after prior nonzero controls.
It authorizes only prospective design of a fresh authentic multi-pulse
sequence validation campaign with its own unopened whole-pair holdout. Real
MPC, expert data, BC, DAgger, bounded residual RL, continuous actuator/plant
variation, noise, disturbance recovery, and independent long hold remain
blocked.
