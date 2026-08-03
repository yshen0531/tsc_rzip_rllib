# Stage4.2R3c3T13S24D1R3 causal split-return preflight design

Status: prospectively frozen after final D1R2 forensics and before D1R3
implementation, candidate replay, or any new TSC execution.

## Purpose and scope

D1R2 completed 54 authentic real-TSC raw trajectories. Forty-five reached
full horizon; nine stopped before applying the task-step-18 slot-3
`++--=0.290` stored-center cancellation because its incremental normalized
action was 0.2409719853--0.2787208138. Four violated only the prospective
0.24 margin and five also violated the unchanged 0.25 original cap. The
failed action was never returned or applied.

D1R3 is a zero-new-TSC causal construction preflight. It tests whether the
same direct stored-center action can be decomposed into a bounded intermediate
Card15 target at task step 18 and an exact stored-center finish at task step
19. Existing raw can validate only the first split action. A D1R3 pass may
therefore authorize only a separately frozen nine-context D1R4 real-TSC
sentinel; it cannot authorize full identification, a transition model, MPC,
expert data, BC, DAgger, or RL.

## Immutable source boundary

```text
D1R2 run
  stage4_2r3c3t13s24d1r2_geometry_restored_amplitude_safety_sentinel_20260803_160327_9e6bba2_v2

D1R2 execution package
  r42r3c3t13s24d1r2_geometry_restored_amplitude_safety_sentinel_v2
  implementation checkpoint 9a8ce4d

D1R2 raw count / bytes
  54 / 3,078,383

D1R2 raw inventory digest
  eb4ac8c0e606ce0d8899f0a512b594877f59cc9424c0f6a87e3450bcd036cc83

D1R2 normalized spec digest
  50832fadb244bbd338bd7c5cd5f9ff136eedce498d920f416458516d7655648f

D1R2 prospective independent audit SHA-256
  a506dde9cf0f57607cda8af3e12c7e26c2f0e731f32e6b1da74ab8c3016a6dcd

D1R2 all-prefix retrospective audit SHA-256
  d6ea5fed0aa943c16ce850b80c9786556a9cd5e0de26a2e19d7a18d5d88914ec

D1R2 complete log SHA-256
  89b23c022580ec70fb4df1d8367759685b610ccd319eb59b6383a3c14e5321ff
```

D1R3 must authenticate these exact files, hashes, counts, identities, all 18
restart snapshots, the final D1R2 FAIL route, 45 full successes, nine
structured safe stops, and the exact failure localization. A changed source
boundary stops before any candidate construction.

## Controller-visible contract

The proposed primitive receives only the current rollout's causal controller
state, current visible plant state, measured coil currents, current task step,
the active issue's stored center and target Card15 fields, and the underlying
controller's action computed at the same task step. It may not receive or use:

```text
pair/history/partition/target labels
D1R2 outcome or failure class
source or current wire currents
source action, result, or coil current
future measurement, state, action, or requested schedule
current-run state 19 when choosing the state-18 split start
```

The offline audit may select the nine failed raw identities as future sentinel
tasks, but those identities and labels must remain outside the controller.

## Frozen split-start construction

At every scheduled cancellation, compute using the unchanged D1R2 functions:

```text
b = underlying causal baseline action at the current task step
d = exact action that returns the measured current to the stored center fields
delta = ||d - b||_infinity
```

If `delta <= 0.24 + 1e-12`, return the original direct cancellation exactly.
There must be bitwise/numeric-array equality with D1R2 on all previously safe
paths.

If `delta > 0.24 + 1e-12`, construct exactly:

```text
split construction target increment = 0.175
alpha = min(1, 0.175 / delta)
c = b + alpha * (d - b)
```

Apply `c` only to the unchanged quantized actuator predictor at the current
measured state. The predicted intermediate target must be a complete set of
14 exact ten-character Card15 fields. The returned split-start action must
equal `c`; no optimizer, grid search, outcome label, future state, or adaptive
constant is allowed.

The split-start gates are frozen as:

```text
direct cancellation increment                         > 0.24
split construction target increment                    0.175 exactly
returned split-start incremental action               <= 0.18
returned split-start total normalized action          <= 1.0
predicted current utilization                         <= 0.55
no saturation or current clipping                       true
intermediate Card15 target exact/reproducible            true
intermediate differs from issue target and center       true
alpha                                                   0 < alpha < 1
controller uses only current causal inputs               true
```

The 0.18 gate is a new conservative sub-cap; it does not replace or weaken the
0.24 prospective margin or original 0.25 cap. The 0.005 gap between the 0.175
construction target and 0.18 acceptance gate is fixed numeric headroom.

## Frozen split-finish semantics for the future D1R4 sentinel

This section defines what D1R3 may authorize but D1R3 cannot validate. After
the plant advances once under `c`, task step 19 recomputes the underlying
baseline action from the new causal visible state and uses the unchanged exact
stored-center action to return to the original center fields. It must pass:

```text
finish incremental normalized action                  <= 0.24
original incremental cap                              <= 0.25
total normalized action                               <= 1.0
predicted current utilization                         <= 0.55
exact stored-center Card15 target and reproduction      true
no saturation or current clipping                       true
active issue cleared only after the exact finish        true
```

Let `C` be the issue center, `T` the issue target, and `M` the intermediate
target, all parsed as exact Decimal Card15 values. D1R4 must prove on every
coil:

```text
(T - C) + (M - T) + (C - M) == 0
```

This telescoping identity preserves exact target-jump net zero; it changes the
cancellation duration, not the net target. The physical action semantics and
event schedule therefore require fresh D1R4 identities and cannot resume
D1R2.

## D1R3 replay matrix and gates

D1R3 must read all 54 raw JSON.GZ directly on the server. It must reconstruct
a fresh proposed controller for each raw and feed only successive recorded
causal states. It must not advance a plant.

For the 45 full-success raws:

```text
all returned actions through full horizon equal D1R2 exactly      45 / 45
all controller event details remain direct one-step returns       45 / 45
no split branch selected                                           45 / 45
```

For the nine structured safe-stop raws:

```text
steps 0--17 returned actions/traces equal D1R2 exactly               9 / 9
direct state-18 cancellation reproduces the saved failure value      9 / 9
state-18 split-start construction passes every frozen gate           9 / 9
no plant advance, state-19 value, or split-finish claim               true
```

Across all rows, restart, snapshot, calibration, phase causality,
forbidden-input, finite-number, Card15, current, source/package/spec, and raw
inventory authentication must remain exact. The expected candidate sentinel
table is exactly nine unique fresh D1R4 identities for the saved failure
contexts, sequence rows 6, 10, and 18.

## Output and routes

D1R3 writes only a new compact audit directory. It creates no raw trajectory,
snapshot, Ray session, controller rollout, `gotsc`, TSC process, or plant
advance. Raw and snapshots remain on the server and are forbidden from expert
datasets.

```text
source/raw/package/replay mismatch
  CAUSAL_SPLIT_RETURN_PREFLIGHT_SOURCE_STOP

direct reproduction or split-start construction failure
  CAUSAL_SPLIT_RETURN_PREFLIGHT_FAIL_REDESIGN

all 54 replays and all 9 split starts pass
  CAUSAL_SPLIT_RETURN_PREFLIGHT_PASS_REAL_SENTINEL_REQUIRED
```

A pass freezes only the construction and nine D1R4 sentinel specs. Before any
new TSC result opens, D1R4 must separately freeze its controller identity,
runtime/raw schema, full-horizon event gates, independent raw audit, fixed
nine-worker capacity, stop/resume semantics, and complete-log contract.

## Formal timing and learning veto

The observation horizons remain 35/37 states. The extra cancellation state is
inside that existing horizon and does not change:

```text
slew 1.0/1.1: arrive by 250 ms, evaluate through 350 ms
slew 0.9:     arrive by 270 ms, evaluate through 370 ms
R/Z tolerance 30 mm, speed threshold 0.1 m/s, Ip gate unchanged
```

D1R3 is not a long-hold test and cannot authorize BC, DAgger, residual RL, or
expert data. RL remains blocked until a reliable MPC expert has completed the
full restart, hidden-history, target, continuous-parameter, noise,
disturbance-recovery, and independent long-hold roadmap.
