# Stage4.2R3c3T13S24D1R14R8R51R1 q0 gate integration sentinel design

Status: prospectively frozen on 2026-08-09 after final R8R51 failure
forensics, but before any R8R51R1 implementation, config, package, offline
construction, controller, Ray, `gotsc`, TSC, plant step, raw trajectory, or
response outcome.

## 1. Source failure and new identity

R8R51 is immutable at:

```text
REDUCED_Q0_TRANSPORT_BRIDGE_SENTINEL_IMPLEMENTATION_GATE_FAIL_NEW_IDENTITY_REQUIRED
```

All 208 R8R51 tasks stopped before the task-step-10 q0 action was applied.
The only false event criterion was the undeclared binary64 exact-zero
predicate; every frozen Card15/action/current/saturation criterion passed.
R8R51R1 is a new stage, campaign, controller revision, run directory, spec
namespace, and raw inventory. R8R51 must not resume or be relabeled.

Before any offline or real execution, R8R51R1 must authenticate at least:

```text
R8R51 raw inventory
  count 208 / bytes 5,155,700
  ea6ba731534adc810adac98172971aed031a42355ac8c443a3aceab6831751dd
R8R51 raw primary
  330c572182048cc3360b9061a153ab995b508263d45de666ffcf3bb76d9f0b55
R8R51 raw independent
  0468f446ed8cfb3a21e985c0006e2293bfbb218892458107f37513d49e8b6472
R8R51 partial-prefix forensics
  daf7018de334fe0f7ee5bae561d4f26df02de569033ffe953526244d43ead414
R8R51 failure compact audit
  e376c5b4c1f1e8654d8dd5fd985d55a3efad0de64139e65c48c5c97a11f0a086
R8R51 failure final report
  41b2c79591c3a4dafe522dad994a14ddcc3b0cb5395bbe01afab747044dc8d2c
R8R51 state / manifest
  1307d2f8cda12ae43c1beffa4f088640bf21025ef24720b7356ba43097d7dcae
  80eeec45e7816d97d635dec070f0e3eef4199443be84a95885a2e1c49a2dd994
R8R51 implementation / config
  4a936b7577585d5dc5ee66f9a4a35f93bd043c6198ba66b016983c1eac62be0a
  4dd3bbee2bc83560f2319807b91939373014690141ab977bc7d82ff0f0962b30
```

Any mismatch blocks the new stage before TSC.

## 2. Frozen matrix and schedule

Retain exactly the same 16 authenticated physical contexts and the same 13
candidate IDs, order, q values, and requested physical coordinates:

```text
d0m d0p d1p d2m d3m d3p
u1p00 u1p25 u1p50
v0p75 v1p00 v1p25 v1p50
```

```text
8 physical pairs x 2 histories x 13 candidates = 208 fresh trajectories
q-matrix rank                                             4
q-matrix SHA-256
  5d6b6c20a704eceda43db7cbaece445d1655a4d62da16d185b308bc27ed4b674
requested-coordinate matrix SHA-256
  82e26d01b53fc8bb986ab5a127f8400bc10dcd823a879450ab54275fc2e50543
```

The causal schedule is unchanged:

```text
source controller prefix                          task steps 0..9
exact Card15 q0 current-target issue               task step 10
q0 observation hold                               task step 11
fixed assigned candidate issue                    task step 12
candidate first/second response                    states 13/14
exact stored pretransport-center return            task step 14
exact center refresh                               steps 15..end
unchanged horizon                                  35 or 37 steps
```

The effect contract remains issue plus one. Pair/history/partition labels,
future measurement/action, wire/vessel current, source result, formal label,
or another rollout remain forbidden controller inputs. Every worker uses a
fresh controller actor, fresh TSC process, and authentic full plant snapshot.

## 3. Only authorized integration correction

The exact q0 target is the Card15 representation of the visible current. It
is not required to be a binary64 all-zero normalized action. The key
`q0_zero_target` is forbidden from the new source, config, trace criteria,
offline audit, real gate, and independent audit.

Implement one shared pure q0-event constructor. Both the offline construction
and real controller `_q0` path must call that same constructor with the same
visible current, actuator, current bounds, Card15 target fields, lattice, and
frozen controller contract. Neither path may append or remove a criterion or
recompute `passed` afterward.

The dual offline gate must prove for all 208 specs:

```text
shared-constructor offline/real event parity                       208/208
criterion-key identity                                             208/208
q0_zero_target key absent                                          208/208
exact Card15 target/stored/actuator fields                         208/208
exact q0 action reproduced from authenticated source current       208/208
q0 incremental normalized Linf <= 1e-5                            208/208
all original R8R51 q0/issue/observe/return/refresh gates           208/208
```

The extra `1e-5` q0 bound is a new fail-closed integration assertion inside
the much wider unchanged `0.25` action limit; it does not weaken any gate.
R8R51 observed the prospective same-context range
`3.3333333296544274e-06 .. 3.7037037048793097e-06` without applying it.

Tests must exercise a nonzero exact Card15 q0 action, prove that it passes all
frozen gates, prove that exact binary64 zero is not required, and prove that
offline and controller paths cannot diverge in criterion keys or `passed`.

No other candidate, coordinate, schedule, action, observation, effect,
return, horizon, formal, safety, current, or causality semantic may change.

## 4. Unchanged action and safety contract

Primary and structurally independent offline construction must pass all 208
cells before real authorization:

```text
exact Card15 q0, issue, observation, return, refresh               208/208
candidate identity and exact frozen coordinate                    208/208
incremental normalized action Linf <= 0.25                        208/208
total normalized action abs <= 1.0                                208/208
predicted current utilization <= 0.55                             208/208
desired/applied current cosine >= 0.98                            208/208
relative off-basis residual <= 0.10                               208/208
no current clipping or saturation                                 208/208
```

No threshold may be widened. Every real event repeats the same gates before
plant advance. A failed candidate is rejected and no later plant step may
occur.

## 5. Single real campaign and audit

Only after exact primary/independent offline agreement may one fresh
208-trajectory R8R51R1 campaign run. R8R51 raw cannot be resumed or reused as
the new raw inventory. A complete R8R51R1 trajectory must never rerun.

Primary and independent raw audits require:

```text
strict parse and immutable new spec identity                      208/208
authentic restart and source semantic states 0..10                208/208
source semantic trace 0..9; differences only new wrapper metadata 208/208
calibration and forbidden-input prefix                            208/208
q0 trace event at task step 10; no exact-zero predicate           208/208
q0 physical effect at state 11                                   208/208
within-context q0 state/action prefix through state 12            208/208
exact assigned candidate at task step 12                          208/208
candidate first effect at state 13                                208/208
finite state-13/state-14 R/Z/Ip/current response                   208/208
exact stored-center return at task step 14                        208/208
full unchanged 35/37-step safe horizon                            208/208
all current/clipping/saturation/abnormal gates                    208/208
all 16 x 13 bridge cells                                          208/208
primary/independent raw, prefix, and response digests               exact
```

## 6. Routes

```text
R8R51 source/hash/raw identity mismatch
  REDUCED_Q0_TRANSPORT_BRIDGE_Q0_GATE_INTEGRATION_BLOCKED_BY_SOURCE

offline construction, parity, exact-action, or independent failure
  REDUCED_Q0_TRANSPORT_BRIDGE_Q0_GATE_INTEGRATION_OFFLINE_FAIL_NO_REAL_TSC

runtime, raw, restart, causality, or integrity failure
  REDUCED_Q0_TRANSPORT_BRIDGE_Q0_GATE_INTEGRATION_EXECUTION_FAIL_STOP

real action/current/return/plant safety gate failure
  REDUCED_Q0_TRANSPORT_BRIDGE_Q0_GATE_INTEGRATION_SAFETY_FAIL_REDESIGN

all offline, execution, raw, and independent gates pass
  REDUCED_Q0_TRANSPORT_BRIDGE_Q0_GATE_INTEGRATION_COMPLETE_R51R2_MODEL_PREFLIGHT_REQUIRED
```

A PASS is only a finite q0-to-first-transport identification result and may
authorize only the separately frozen conditional R8R51R2 zero-new-TSC model
preflight.

## 7. Formal and learning boundary

Arrival remains no later than 250 ms with hold through 350 ms for slew
1.0/1.1 and no later than 270 ms with hold through 370 ms for slew 0.9, with
30 mm R/Z, 0.1 m/s speed, unchanged 10 kA Ip threshold, and the frozen
three-sample arrival streak. The 35/37-step observation horizon does not
relax these deadlines.

Every R8R51R1 trajectory is an identification probe and is forbidden from
all learning data. Even PASS is not a model, controller, MPC, formal-control,
long-hold, robustness, plant-reachability, or Gate A qualification. Gate A,
expert data, BC, DAgger, residual RL, and Gate B remain blocked.
