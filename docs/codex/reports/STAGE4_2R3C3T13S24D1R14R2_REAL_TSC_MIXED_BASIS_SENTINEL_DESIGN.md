# Stage4.2R3c3T13S24D1R14R2 real-TSC mixed-basis sentinel design

Frozen: 2026-08-04, after D1R14R1A was frozen as a zero-TSC PASS and before
D1R14R2 implementation, controller creation, result inspection, or real TSC.

## Purpose

D1R14R2 is the fresh authentic safety and response-geometry sentinel for the
single fixed mixed basis accepted by D1R14R1A. It closes exactly the two
boundaries that R1A could not test:

1. causal state-11 exact stored-center cancellation after a real state-10
   issue and plant advance; and
2. authentic odd signal, central symmetry, rank, and conditioning of the
   mixed basis about a true zero-increment baseline.

It is not a time-distributed identification campaign, transition-model fit,
controller, MPC, robustness, expert-data, BC, DAgger, or RL stage.

## Immutable source chain

R2 authenticates the final R1A output byte-for-byte:

```text
R1A implementation checkpoint                       58912e7
R1A package checkpoint                              b8040b6
R1A package revision
  r42r3c3t13s24d1r14r1a_quantization_margin_preflight_v1
R1A detailed SHA
  a9ffc98b798d4735d7302b1ca4407dbc60266228007d82d34418a291df2b0e8d
R1A summary SHA
  77194861b0406257d055b5ebe0e087b9f9c8222e76600fa443de9d34e7fc682f
R1A manifest SHA
  d6b4c53c46b8948d979d3eaee1861885f61d33ac70097a7576110361f0bafa87
R1A required route
  QUANTIZATION_MARGIN_PREFLIGHT_PASS_R2_SENTINEL_DESIGN_REQUIRED
```

The authenticated R1A detailed output must still name the exact D1R14 v2
boundary:

```text
D1R14 package checkpoint                             d32761c
D1R14 raw files / bytes                       72 / 2,239,479
D1R14 raw inventory digest
  0433a64ebaea73186bb193d5102686721497219acfcbecbb721e7fad62e8d7a3
D1R14 final SHA
  1a65a37c301ba52325f586e0948b0b94b1266c540e2f2a332e5bc02df60a7da2
D1R14 independent audit SHA
  8e7d3d045477502c1060fe621f2c43235e1d530b59c5d22849337dd20aac3eae
```

The physical restart/source prefix remains the same eight immutable D1R13
results used by D1R14. R2 must repeat D1R14's complete D1R13/D1R11 raw,
snapshot, manifest, state, final-result, and independent-audit authentication.
R1A output is provenance and fixed-basis evidence; it is never available to
the runtime controller.

## Fixed mixed basis

No search, scale grid, alternate column, adaptive refinement, or
outcome-conditioned selection is allowed. The four requested-coordinate
columns are exactly:

```text
 0.06036182177162116   0.06409209376301149  -0.37110098238653283   0.13657703474397473
-3.921547352685623   -3.280604324442652     4.73169603859497     -3.6727205346962286
 0.49109976246409964   0.13593338869530727  -0.035003869827120934 -0.3079668079336082
-0.18672754749097395  -0.17590787535526847  -0.08626957714716102   0.19464202995789268
```

Their C-order little-endian float64 byte SHA-256 is:

```text
c8cd62c00c1f60b46312927789659657dc8cc35717533193433b0e398c1ec94c
```

Direction names are fixed as `pooled_mixed_0` through `pooled_mixed_3`.
Positive and negative members request the exact column and its exact binary64
negative, respectively.

## Fresh task matrix

The eight source contexts are unchanged and ordered exactly as D1R14/R1A:

```text
s42r3c3_7dca3ca415ee7fae3748
s42r3c3_a6b6eeea6d48d7a79585
s42r3c3_4571fd0668fa016c2636
s42r3c3_44878cc615a1d3ea18b9
s42r3c3_3a3dc1fe08a9a6984e8c
s42r3c3_f96b02b6e296f16b840c
s42r3c3_b72b7cdb52af15409a54
s42r3c3_39edf644f2fdf0ee6c5a
```

Each context has one fresh zero baseline and four directions times two signs:

```text
8 contexts x (1 baseline + 4 directions x 2 signs) = 72 rollouts
normal 35-step horizons                              36
weak-slew 37-step horizons                           36
fresh actor / TSC / controller per rollout            required
```

Every experiment ID includes the new stage, campaign, controller revision,
source D1R13 experiment ID, role, direction, sign, fixed matrix digest, and
restart snapshot digest. No D1R14 trajectory is resumed or relabelled.

## Causal controller and action semantics

Tasks 0--9 reproduce the exact authenticated D1R11/R17 source action and
controller-trace prefix through state 10. The underlying controller is not
executed after task step 9.

For every signed probe:

```text
task step 10  construct and issue the signed fixed mixed coordinate
state 11      first authentic post-issue state/current observation
task step 11  causally construct exact return to the stored Card15 center
task step 12+ exact 14-coil zero action through state 35 or 37
```

For every zero baseline, task step 10 onward is exact 14-coil zero action.
The baseline must reproduce the corresponding complete D1R13 zero-increment
trajectory and current path exactly.

The issue constructor uses only the current measured 14-coil current, causal
same-run actuator state, the fixed requested coordinate for this member,
authenticated turns/current limits, and fixed Card15/lattice rules. The
cancellation uses only the current state-11 measured current and the center
stored causally at issue. It may not use a source/current future value.

## Controller information boundary

The outer identification wrapper necessarily knows only its own fixed role,
direction, sign, and current issue request. The delegated R17 controller sees
none of those probe fields and no future schedule.

Neither layer may use pair/history/prefix/partition labels, R1/R1A/D1R14
outcomes, source action/current/wire-current values, hidden wire/vessel
currents, another member, future measurements, future executed actions, or
post-action current-step telemetry. All such accesses fail closed and are
audited per trace row.

## Safety gates before response geometry

The issue action must pass all of:

```text
finite construction                                      required
requested coordinate equals fixed signed column          required
exact Card15 center and target                           required
target reproduction by actuator primitive                required
no saturation or current clipping                        required
incremental normalized action                         <= 0.25
total normalized action abs                           <= 1.0
predicted current utilization                         <= 0.55
desired/applied current cosine                        >= 0.98
relative off-basis residual                           <= 0.10
exact actuator gate                                      required
```

The state-11 cancellation must pass all inherited exact-return gates:

```text
exact stored-center target reproduction                  required
exact Decimal issue-plus-return target net zero          required
no saturation or current clipping                        required
online cancellation incremental normalized action     <= 0.24
original incremental normalized action                <= 0.25
total normalized action abs                           <= 1.0
predicted current utilization                         <= 0.55
exact actuator gate                                      required
```

Every task must additionally pass exact restart, state/action/trace prefix,
calibration, full horizon, finite R/Z/Ip/coil/wire currents, no abnormal plant
state, current utilization, exact post-cancel zero action/current increment,
strict raw, snapshot, manifest, package, complete-log, and forbidden-input
checks. Any safety/prefix/runtime failure prevents response geometry from
being evaluated.

## Frozen response geometry

The geometry is unchanged from D1R14, evaluated from state 11 through each
trajectory's authentic 35/37 endpoint in normalized `(R,Z,vR,vZ,Ip)` units:

```text
output scales                     0.03 m, 0.03 m, 0.1 m/s, 0.1 m/s, 10000 A
signed pairs per context/direction                                  32 total
minimum odd peak                                                   >= 0.005
maximum even/odd peak ratio                                         <= 0.5
per-context normalized-column rank                                    4 / 4
rank relative tolerance                                               1e-10
per-context condition number                                         <= 20
```

Matched-hidden-history odd-response differences are report-only because the
eight contexts are still a finite clean same-source development envelope.
They cannot independently certify hidden-history robustness.

## Formal timing and interpretation

The formal contract is unchanged:

```text
normal/strong slew  arrival by state 25, hold through state 35
weak slew 0.9       arrival by state 27, hold through state 37
R/Z tolerance       0.03 m
speed tolerance     0.1 m/s
Ip tolerance        10000 A
arrival streak      3 states
```

Formal tracking is recomputed and reported per raw trajectory but remains a
diagnostic only. It neither passes nor fails this identification sentinel.
There is no longer observation horizon and no long-hold claim.

## Execution, audit, and storage contract

Before real TSC, R2 must pass local compile/JSON, focused and complete tests,
source-fingerprint/resume tests, import closure, manifest/checksums, and an
empty-directory deployment simulation. The installed server package must pass
path preflight, `bash -n`, package verification, server-virtualenv import and
compile, and a zero-plant 72-spec offline gate.

The primary postprocessor and a structurally separate independent raw and
snapshot forensic must both be present, hashed, tested, and packaged before
any response outcome opens. The independent tool must strictly parse and hash
all 72 raw files, authenticate snapshots and source prefixes, reconstruct all
issue/cancel/zero/current/forbidden gates, recompute geometry directly from
raw, and compare the saved state/manifest/final output.

Large raw, snapshots, and trajectory trees remain on the server. Only compact
audit JSON, inventories/hashes, state/manifest/config/summary/verdict, and
complete logs are transferred directly without compression.

## Routes

```text
offline/source/spec/package failure before real TSC
  MIXED_BASIS_SENTINEL_OFFLINE_FAIL_NO_TSC

runtime/raw/restart/prefix/causality failure
  MIXED_BASIS_SENTINEL_RUNTIME_OR_PREFIX_FAIL_STOP

issue/cancel/current/full-horizon safety failure
  MIXED_BASIS_SENTINEL_ACTION_SAFETY_FAIL_REDESIGN_REQUIRED

all safety passes but response geometry fails
  MIXED_BASIS_SENTINEL_RESPONSE_GEOMETRY_FAIL_REDESIGN_REQUIRED

all frozen gates pass
  MIXED_BASIS_SENTINEL_PASS_TIME_DISTRIBUTED_ID_DESIGN_REQUIRED
```

A PASS authorizes only prospective design of a separate time-distributed
zero-baseline identification campaign. It does not authorize that campaign,
model fitting, MPC implementation or execution, expert data, BC, DAgger, or
bounded residual RL. Probe trajectories are permanently forbidden from
expert datasets.
