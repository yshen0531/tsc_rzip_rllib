# Stage4.2R3c3T13S24D1R14R4 real-TSC time-shifted sign-split sentinel design

Frozen: 2026-08-04, after final D1R14R3 primary/independent forensics and
before D1R14R4 implementation, task generation, controller creation, or new
TSC execution.

## Purpose

D1R14R4 is a fresh authentic safety and identification sentinel for the
piecewise-sign local response architecture accepted only at one issue time by
D1R14R3. It adds three fixed issue times along each authenticated zero-action
context and combines them with the already authenticated D1R14R2 time-10
responses.

It asks whether each context, issue time, and input sign retains four finite,
signal-bearing, conditioned response directions under exact causal
stored-center cancellation. It does not assume positive/negative central
symmetry and does not require response invariance across time.

D1R14R4 is not a response-model fit, superposition test, multi-step control
test, MPC, hidden-history robustness result, expert dataset, BC, DAgger, or RL
stage. Every probe trajectory is permanently forbidden from expert data.

## Immutable source chain

The corrected D1R14R3 boundary is:

```text
R3 design checkpoint                                      343a516
R3 source-hash erratum checkpoint                         aa3325a
R3 final package checkpoint                               ca49a36
R3 primary SHA-256
  30755ebccee65a5bcfd08d04632368979ec1c309ac42d4a46df49b3b921cd590
R3 independent SHA-256
  f138611d56b77839bb3d87744b49eb08df4c4409947038e25b520f8d43764d90
R3 compact evidence manifest SHA-256
  cd8c6c679cbe78b02141358a55928896be6623488b81de73b8bd876a5a6d546f
R3 required route
  SIGN_SPLIT_RESPONSE_FEASIBILITY_PASS_TIME_SHIFT_SENTINEL_DESIGN_REQUIRED
```

R3's initial source-hash-failure output and the separately recorded erratum
must also authenticate exactly. They are evidence that the single corrected
fingerprint predates the R3 result and that no scientific gate changed.

The immutable authentic time-10 source remains D1R14R2:

```text
R2 package checkpoint                                     ca2815a
R2 raw files / bytes                               72 / 2,254,876
R2 raw inventory digest
  c210f959e5ce85739dd0b1f70a2513f64f40c6697d01bf7b56db9621759a1649
R2 primary SHA-256
  3df193e52ee0ce8fe72620af9f72597f58af4419c6386c37d62fb051bcefd79a
R2 independent SHA-256
  68f21e95694c607084b9cc7d39732bcda05d57a14f6f3cc4f1e78e8941e7e2df
fixed mixed-basis matrix digest
  c8cd62c00c1f60b46312927789659657dc8cc35717533193433b0e398c1ec94c
```

R4 must repeat the complete R3, R2, R1A, D1R13, D1R11, snapshot, package,
state, manifest, raw, and log authentication. It may not accept a verdict or
summary without raw reconstruction. The eight physical source contexts and
the four fixed requested-coordinate columns remain byte-identical.

## Fixed task matrix

The source time-10 bank is read-only and creates no new task:

```text
8 contexts x 4 directions x 2 signs                         64 source probes
8 matching source zero baselines                              8 source baselines
```

The fresh R4 task matrix is fixed as:

```text
issue task steps                                      14, 18, 22
8 contexts x 1 fresh zero baseline                              8
8 contexts x 3 issue times x 4 directions x 2 signs           192
fresh authentic R4 rollouts total                              200
normal 35-step horizons                                        100
weak-slew 37-step horizons                                     100
maximum Ray workers                                             96
fresh actor / TSC / controller per rollout                required
```

No time, context, direction, sign, amplitude, or member may be selected or
removed after outcomes. Every experiment ID includes the R4 stage, campaign,
controller revision, source D1R13 experiment, role, fixed issue time,
direction, sign, fixed matrix digest, and restart snapshot digest. No R2 raw
is resumed or relabelled as R4 raw.

## Causal controller and action semantics

Every fresh task reproduces the exact authenticated D1R11/R17 action and
controller-trace prefix through task step 9. The R17 controller is never
executed after step 9.

For a zero baseline, task step 10 onward is exact 14-coil zero action through
the unchanged state-35/37 endpoint. It must reproduce the complete matching
D1R13 zero-increment trajectory and current path exactly.

For a signed probe with issue time `s`:

```text
task steps 10 through s-1     exact 14-coil zero action
task step s                   construct and issue fixed signed mixed coordinate
state s+1                     first authentic post-issue observation
task step s+1                 causally return to center stored at issue
task step s+2 onward          exact 14-coil zero action through state 35 or 37
```

The issue constructor uses only the current measured 14-coil currents,
causal same-run actuator state, this member's fixed requested coordinate,
authenticated turns/current limits, and frozen Card15/lattice rules. The
cancellation uses only the current state-`s+1` measured current and the center
stored causally at issue. It may not use a current-run future value or a source
future current.

## Controller information boundary

The outer identification wrapper necessarily knows only its own fixed role,
issue time, direction, sign, and requested coordinate. The delegated R17
controller sees none of these fields and no future schedule.

Neither layer may use pair/history/prefix/partition labels, R2/R3 outcomes,
source action/current/wire-current values, hidden wire/vessel currents,
another member, future measurements, future executed actions, or post-action
current-step telemetry. Every prohibited access fails closed and is audited
per trace row.

## Frozen action and execution gates

Every issue must pass the unchanged R2 gates:

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

Every online cancellation must pass:

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

All 200 tasks must additionally pass exact restart, source state/action/trace
prefix, calibration, pre-issue zero action/current increments, full horizon,
finite R/Z/Ip/coil/wire currents, no abnormal plant state, exact post-cancel
zero action/current increment, strict raw, snapshot, manifest, package,
complete-log, and forbidden-input gates. Response geometry is not evaluated
unless all 200 safety rows pass.

## Frozen combined time-shifted sign-split geometry

The combined bank has issue times `10, 14, 18, 22`. Time 10 is reconstructed
from the exact R2 baseline/probes; times 14/18/22 use only the matching fresh
R4 baseline and probes.

For context `c`, issue time `s`, direction `d`, and trajectory outputs `Y`,
construct from authentic state `s+1` through the actual endpoint:

```text
positive branch d = normalize_outputs(Y(c,s,+d) - Y0(c))
negative branch d = normalize_outputs(Y0(c) - Y(c,s,-d))
```

Output scales remain `(0.03 m, 0.03 m, 0.1 m/s, 0.1 m/s, 10000 A)` for
`(R,Z,vR,vZ,Ip)`. Flatten each complete response in fixed state-major/
output-major order, normalize each column to unit L2, and apply SVD. Rank uses
relative tolerance `1e-10` times the largest singular value.

The frozen gates are:

```text
contexts x issue times x signs                     8 x 4 x 2 = 64 branches
branch-direction columns                         64 x 4 = 256 columns
minimum peak absolute normalized response per column           >= 0.005
nonzero finite L2 norm per column                              required
rank per sign branch                                                 4 / 4
unit-column condition number per branch                              <= 20
```

The actual requested coordinates and actual four physical effect fields must
be exact sign opposites for all 96 new signed pairs; the combined source/new
count is 128/128. This authenticates the action. Cross-sign plant response
symmetry remains explicitly false as an architectural assumption and is not
an acceptance gate.

Matched-hidden-history differences, cross-time response differences, formal
tracking, and comparison of fresh R4 baselines with R2 baselines are reported.
Only exact baseline reproduction is a gate. No cross-time invariance,
interpolation, linear superposition, amplitude scaling, or model accuracy is
claimed or tested here.

## Formal timing

The immutable formal contract remains:

```text
slew 1.0/1.1: arrive no later than state 25, hold through state 35
slew 0.9:     arrive no later than state 27, hold through state 37
R/Z tolerance 0.03 m, speed 0.1 m/s, Ip 10000 A, arrival streak 3
```

Formal tracking is recomputed per raw trajectory but is diagnostic only. R4
does not lengthen a horizon or deadline and is not a long-hold test.

## Execution, independent audit, and storage

Before real TSC, R4 must pass local compile/JSON, focused and complete tests,
import closure, source-fingerprint and resume tests, manifest/checksums, an
empty-directory deployment simulation, installed-server `bash -n`, package
verification, server-virtualenv import/compile, and a zero-plant 200-spec
offline source/safety gate.

The primary postprocessor and a structurally separate independent raw and
snapshot forensic must be implemented, hashed, tested, and packaged before
any R4 outcome opens. Both must strictly parse and hash all 200 new raw plus
the 72 source raw, repeat all safety and forbidden-input gates, recompute all
64 branches directly, and compare saved state/manifest/final output.

Large raw, snapshots, and trajectory trees remain server-side. Only compact
JSON, inventories/hashes, configs, state/manifest/final outputs, and complete
logs are transferred directly without compression.

Resume is permitted only after an infrastructure interruption when controller
semantics, task matrix, experiment identity, package/source fingerprints,
formal gates, and physical actions are unchanged. Any scientific or action
change requires a new run identity.

## Frozen routes

```text
offline/source/spec/package failure before real TSC
  TIME_SHIFTED_SIGN_SPLIT_SENTINEL_OFFLINE_FAIL_NO_TSC

runtime/raw/restart/prefix/causality failure
  TIME_SHIFTED_SIGN_SPLIT_SENTINEL_RUNTIME_OR_PREFIX_FAIL_STOP

issue/cancel/current/full-horizon safety failure
  TIME_SHIFTED_SIGN_SPLIT_SENTINEL_ACTION_SAFETY_FAIL_REDESIGN_REQUIRED

all safety passes but any signal/rank/condition branch fails
  TIME_SHIFTED_SIGN_SPLIT_SENTINEL_GEOMETRY_FAIL_REDESIGN_REQUIRED

all frozen gates pass
  TIME_SHIFTED_SIGN_SPLIT_SENTINEL_PASS_CAUSAL_MODEL_FIT_DESIGN_REQUIRED
```

A PASS authorizes only prospective design of a zero-new-TSC causal
piecewise-sign response-model fit with a frozen context/time training and
holdout split. It does not authorize that fit, MPC implementation or real
control, expert data, BC, DAgger, or bounded residual RL.

