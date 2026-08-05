# Stage4.2R3c3T13S24D1R14R8R1 fixed-candidate short-horizon design

Frozen prospectively after the final R8 primary and independent results, but
before R8R1 implementation, source reconstruction, any truncated-horizon
metric, route evaluation, or model artifact construction.

## Purpose

R8 proved that its fixed action-conditioned full-history kernel does not pass
the unchanged response gates over the complete 130--270 ms response tails.
It did not prove a point-error, signal, response-geometry, authority,
restart, causality, plant-reachability, or short-receding-horizon failure.

R8R1 is a zero-new-TSC development discriminator.  It asks whether the one
fixed candidate selected by R8 before this design can pass every unchanged
response, tube, signal, and geometry gate over a controller-useful common
short prediction horizon.  It does not tune another candidate and does not
open R8 calibration or holdout outcomes.

## Immutable source evidence

Canonical R8 run:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
stage4_2r3c3t13s24d1r14r8_runs/
stage4_2r3c3t13s24d1r14r8_partitioned_broad_response_identification_20260804_5e57f60_v2
```

Required R8 artifacts and values:

```text
stage state bytes / SHA-256
  908
  9fff80668023f17d3be273f9cd9694e21b401a5f668c60c1e03508a164c6d5d3
stage manifest bytes / SHA-256
  124409
  67d1dc0604aa241161850578fb75c6f04bb140a1f791a5246b9f24c8d8df9f90
training raw count / bytes / digest
  624 / 19725920
  b5de1cabe0bd47b0d3a3b26aff04714ca0c05653483cd4c92403dc5867eeb762
primary detailed SHA-256
  797c862666a7bf8f770816bfa83d20f9b2cedea8dfa4be49f061d81680578a50
primary summary SHA-256
  2538601ff1086357a96a1f9646a0f9368108fe648b0897da2d987624db111968
independent model audit bytes / SHA-256
  188290
  cfb4ad0aebc838045468e6dd9e5937007c06a07458a458f253a0dd411861cba0
```

The authenticated R8 terminal state must remain:

```text
phase_status                         training_model_failed
new_raw_count                                           624
training_model_sha256                                 empty
calibrated_tube_sha256                                empty
heldout_outcomes_opened                               false
calibration raw count                                     0
holdout raw count                                         0
route
  PARTITIONED_BROAD_RESPONSE_TRAINING_MODEL_FAIL_STOP
```

The independent audit must have `passed=true`,
`scientific_gate_passed=false`, exact numerical/outcome/artifact agreement,
and an empty training model hash.  R8R1 must authenticate the complete R2,
R4, R6, and R8 training raw contracts in place and reconstruct exactly 912
responses, twelve physical pairs, and 24 pair-history contexts.

No R8 calibration or holdout path may contain a raw result before or after
R8R1.  Those prospective outcomes remain unopened and are not R8R1 data.

## Fixed model candidate

R8R1 fixes the R8 all-training candidate without selection or tuning:

```text
PCA rank                         4
RBF median-distance multiplier  2.0
kernel ridge                    0.1
action sign/direction heads     unchanged eight heads
descriptor                      unchanged 142-dimensional causal descriptor
```

Pair, history, partition, prefix, target ID, regime, delay/slew labels,
source/current coil or wire currents, hidden state, source result/action,
future measurement, and future executed action remain forbidden predictor
inputs.  They may be used only for orchestration, whole-pair partitioning,
source authentication, and reporting.

For each of the twelve outer folds, fit this exact candidate on the other
eleven complete pairs.  Candidate selection inside or outside a fold is
forbidden.  Prediction uses the unchanged velocity/Ip lag heads and exact
10 ms R/Z integration.  No full-horizon polynomial tail is needed within the
common horizons below.

## Fixed horizons and route order

Every response has at least twelve post-issue states.  R8R1 evaluates the
common relative-lag prefixes:

```text
relative states   elapsed horizon   route role
4                 40 ms             diagnostic only
6                 60 ms             diagnostic only
8                 80 ms             controller-useful candidate
10               100 ms             controller-useful candidate
12               120 ms             controller-useful candidate
```

For each horizon, truncate both the actual response and the independently
generated prediction to exactly that number of post-issue states before
computing any metric.  Never shift the origin by an effect, delay, regime,
or observed-outcome label.  Never exclude a zero/weak early segment.

Select the largest of 12, 10, then 8 that passes every gate.  Horizons 4 and
6 are always diagnostic and can never produce a route PASS.  This deterministic
order is frozen before any R8R1 metric is computed.  A horizon result is
development evidence only; it is not fresh calibration or holdout validation.

## Unchanged gates at every horizon

All 912 outer predictions must individually pass:

```text
relative L2 error                              <= 0.75
response cosine                                >= 0.80
predicted/actual peak ratio              within [0.50, 1.50]
maximum absolute scaled point error              <= 0.10
finite prediction and actual response                 true
```

The componentwise precursor remains the unchanged physical floor plus twice
the maximum absolute outer residual and must fit inside:

```text
[0.003 m, 0.003 m, 0.01 m/s, 0.01 m/s, 1000 A]
```

Actual and predicted signal must pass 912/912 at `>=0.0025`.  Truncated
canonical and operational predicted response geometry must each pass all
192 context/issue/sign branches at rank four and condition at most 20.  The
same two geometry families are recomputed from actual truncated responses
and must independently pass 192/192.

No threshold is relaxed because full-horizon R8 failed.  A shorter horizon
is a different prospective controller-use contract, not a later arrival
deadline or a reinterpretation of an unrun phase.

## Primary and independent implementations

The primary implementation must:

1. authenticate every source artifact and prove calibration/holdout raw zero;
2. reconstruct all 912 responses from raw, never from verdicts;
3. fit the fixed candidate independently in twelve whole-pair outer folds;
4. compute complete row, tube, signal, and dual-geometry results for all five
   horizons; and
5. write a compact summary plus server-resident row-level output.

The structurally independent implementation must separately reconstruct the
response bank, preprocessing, PCA, RBF kernels, outer predictions, R/Z
integration, row metrics, tube, and both geometry families.  It must compare
the complete primary numerical output within the unchanged `1e-10` relative
and `1e-12` absolute tolerances and independently derive the route.

If a controller-useful horizon passes, the primary may fit the same fixed
candidate on all twelve training pairs and emit a new R8R1 model artifact
truncated to the selected horizon.  The independent implementation must
recompute and authenticate all-data predictions and the artifact contract.
No artifact is allowed on a route failure.

## Frozen routes

```text
source, raw, identity, or independent disagreement
  FIXED_CANDIDATE_SHORT_HORIZON_AUDIT_FAIL_STOP

largest controller-useful horizon 8/10/12 passes
  FIXED_CANDIDATE_SHORT_HORIZON_PASS_MULTIPULSE_SENTINEL_REQUIRED

no controller-useful horizon passes
  FIXED_CANDIDATE_SHORT_HORIZON_FAIL_CAUSAL_INNOVATION_REQUIRED
```

A PASS may authorize only a separately prospectively frozen fresh authentic
multipulse superposition/interaction sentinel.  It does not authorize R8
calibration/holdout, MPC control, expert data, BC, DAgger, or RL.

A FAIL rules out this fixed cold-start response kernel for a common 80--120
ms receding horizon.  It routes to causal online innovation/adaptation or a
new identification design.  It does not authorize post-result candidate
tuning, horizon-origin shifting, label inputs, more capacity in the failed
long-horizon architecture, or a plant-unreachability claim.

## Formal timing and scientific boundary

The formal timing remains immutable:

```text
normal slew: arrive by state 25; hold/evaluate through state 35
weak slew:   arrive by state 27; hold/evaluate through state 37
R/Z tolerance 0.03 m; speed 0.1 m/s; Ip 10000 A; streak 3
```

The 80--120 ms prediction horizon is receded in a future controller design;
it never extends an arrival deadline.  R8R1 runs zero controller, Ray,
`gotsc`, TSC, or plant steps.  It is not a real-MPC or closed-loop result.
All probe trajectories remain forbidden from expert datasets.
