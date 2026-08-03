# Stage4.2R3c3T13S24D1R4 real-TSC split-return safety sentinel design

Status: prospectively frozen after final D1R3 forensics and before D1R4
implementation, package construction, source preflight, or any D1R4 response
outcome.

## Purpose and claim boundary

D1R3 proved that the nine D1R2 task-step-18 structured safe stops admit a
causal exact-Card15 intermediate action with incremental normalized action
exactly 0.175. D1R3 did not advance the plant under that action, so it could
not evaluate the new state-19 baseline or exact-center finish.

D1R4 is a new-identity nine-case authentic real-TSC safety sentinel. It tests
only whether the frozen split start can be followed, after one real plant
advance, by a causal exact stored-center finish inside the unchanged safety
envelope and existing 35-step formal observation horizon. A pass may authorize
only a separately frozen full replacement sequential transition-identification
campaign. It cannot authorize a transition model, MPC, expert data, BC,
DAgger, residual RL, robustness, or long hold.

## Immutable source boundary

```text
D1R2 source run
  stage4_2r3c3t13s24d1r2_geometry_restored_amplitude_safety_sentinel_20260803_160327_9e6bba2_v2

D1R2 raw count / bytes / inventory digest
  54 / 3,078,383
  eb4ac8c0e606ce0d8899f0a512b594877f59cc9424c0f6a87e3450bcd036cc83

D1R3 final package checkpoint
  93afef5

D1R3 config / implementation SHA-256
  358ca26ab1690f714b2690b58d5457204704d51bd9a7a183aec1c3936fb75e56
  f1d0877a0a901680319417de3148971be621962b1aff4fe25b600ba8bb7d8e18

D1R3 primary output
  stage4_2r3c3t13s24d1r3_causal_split_return_preflight_20260803_170619_93afef5

D1R3 detailed / summary / manifest SHA-256
  812c8fccbe5246e7149bced28ec746b7c15c91e241f2feaeda9a6c9f8033909a
  6c1edd1235d57560bbf5fd2b630f620dc8919045dbab70c3d67eac70969e17e5
  dc66a3dc9427468d8fea17bc892682a213322b58e18e89ac451d15fcf10cdb59

D1R3 candidate sentinel file / canonical table digest
  5c26680bc1483148a95cca9a06bb4eb546d01e385af6a907941d4b74b82a0d1a
  143d0c8e5fa2678e2d7519cba22441a24f6274e39457d18c85fb92fc57c9e1ec

D1R3 independent forensic SHA-256
  4325003dfd6d3bbcb5e0f89f605450bd274fb8466062b488b8edaf797dc164ae

D1R3 primary / deterministic-repeat log SHA-256
  d6c863bcee14b324122e5b0b4ed50db3d54a9187acd2fbf002598e26596a4fa3
  8f325f4bea1866af1a5e8a6b6617b456ca511b511a22489b2bb831f3865ebcec
```

D1R4 must authenticate these exact sources before materializing a run. It
must reproduce D1R3's route, all 54 source rows, 45/9 source classification,
nine split-start passes, candidate table and digest, three unique selected
restart snapshots, and every candidate's source-raw hash. Any mismatch is a
source-stop before TSC.

## Frozen identity and task matrix

```text
stage
  Stage4.2R3c3T13S24D1R4

campaign identity
  causal_split_exact_return_safety_sentinel_v1

controller revision
  causal_split_exact_return_probe_v42r3c3t13s24d1r4_v1

run name prefix
  stage4_2r3c3t13s24d1r4_causal_split_return_safety_sentinel

task count
  9

normal 35-step / weak 37-step horizons
  9 / 0

unique restart snapshots
  3

sequence rows
  6, 10, 18 exactly three times each
```

The candidate table is immutable. No additional context, repeat, amplitude,
target, restart, or failure can be added after observing a result. Each task
uses one fresh Ray actor, one fresh TSC process, and one fresh causal
controller. Fixed campaign capacity is nine actors.

## Controller-visible and forbidden information

The controller may use only the current rollout's causal controller state,
current visible plant state, measured coil currents, current task step, the
active issue's internally stored exact center/target fields, its own pending
split state, and the underlying controller action computed at the same step.

It may not receive or use pair, history, target, partition, source-failure,
sequence-selection, or outcome labels; source/current wire currents; source
actions/results/coil currents; current-run future measurements or actions;
or the candidate table. The offline task selector may use source identities,
but `_controller_spec` must strip every selection label before controller
construction.

## Frozen causal state machine

All steps before task step 18 use the exact D1R2 controller semantics and must
reproduce the corresponding D1R2 source action/trace prefix through step 17.

At task step 18, the active slot-3 cancellation recomputes:

```text
b18 = underlying causal baseline action at state 18
d18 = exact stored-center action at state 18
delta18 = ||d18 - b18||_infinity
alpha = min(1, 0.175 / delta18)
c18 = b18 + alpha * (d18 - b18)
```

It must select the split branch because `delta18 > 0.24`, return `c18`, keep
the active issue and exact center/target fields private in controller state,
and set a one-shot pending finish flag. Every D1R3 split-start predicate is
unchanged:

```text
incremental normalized action                         <= 0.18
total normalized action                              <= 1.0
predicted current utilization                        <= 0.55
exact 14-field Card15 intermediate                      true
no saturation or clipping                               true
intermediate differs from target and center             true
alpha                                            0 < alpha < 1
```

After exactly one authentic plant advance, task step 19 first computes the
underlying causal baseline action from the new current state. It then computes
the exact stored-center action with the unchanged actuator function:

```text
b19 = underlying causal baseline action at state 19
f19 = exact_stored_center_action(C, measured_current19, b19, ...)
```

The finish must pass:

```text
incremental normalized action                         <= 0.24
unchanged original incremental cap                    <= 0.25
total normalized action                              <= 1.0
predicted current utilization                        <= 0.55
exact stored-center Card15 target/reproduction          true
no saturation or current clipping                       true
finish occurs at task step 19, slot 3                   true
one and only one plant state separates start/finish     true
active issue cleared only after every finish gate       true
```

The controller must fail closed before returning an action if any start or
finish gate fails. It may not retry, search, clip, or defer the finish.

For exact Decimal Card15 fields `C` (center), `T` (issue target), and `M`
(intermediate), every coil must satisfy:

```text
(T - C) + (M - T) + (C - M) == 0
```

No float-tolerance substitute is permitted for this net-zero identity.

## Full-horizon raw gates

Every task must produce one strict JSON.GZ result with exactly 36 trajectory
states and 35 controller trace rows. Expected sequential events are:

```text
slot 0 issue / direct finish
slot 1 issue / direct finish
slot 2 issue / direct finish
slot 3 issue / split start / split finish
```

All four issue gates, the first three direct cancellation gates, the split
start, and the split finish must pass. The complete raw audit must also prove:

```text
fresh actor / TSC / controller                              9 / 9
authentic sprsina plant restart                             9 / 9
restart snapshot exactness                                  9 / 9
causal calibration and exact calibration net                9 / 9
controller causal/online and all forbidden-input flags       9 / 9
finite TSC states, no abnormal state, no solver/runtime error 9 / 9
source action/trace prefix through step 17 exact              9 / 9
split-start action equals D1R3 construction                   9 / 9
full event schedule and controller pending-state closure      9 / 9
raw identity/spec, manifest, state, package and log integrity 9 / 9
```

The unchanged formal metric must be recomputed from every complete raw and
reported by pair/history/sequence, but it is a diagnostic in this safety
sentinel. It is not a D1R4 PASS condition and may not be presented as a real
MPC result.

## Timing contract

All nine cases have the unchanged 35-step horizon:

```text
arrival no later than 250 ms
hold/evaluate through 350 ms
R/Z tolerance 30 mm
speed threshold 0.1 m/s
Ip threshold and arrival streak unchanged
```

The step-19 finish is within this existing horizon. It does not shift the
formal clock or arrival deadline and is not a long-hold test.

## Packaging, execution, and independent forensics

Before any response outcome opens, the package must contain the D1R4 config,
controller/runner, launcher common/native/nohup/offline/self-test/postprocess,
independent raw forensic implementation, tests, design, manifest, and checksums.
It must pass local compile/JSON/focused/full tests, import closure, exact
inventory, source fingerprints, an empty-directory deployment, and then the
same checks plus `bash -n` and complete tests in the installed server virtual
environment.

Execution phases are:

```text
offline source/snapshot/spec/package preflight, zero plant
fresh nine-actor real-TSC rollout
prospective postprocess from all raw
separately implemented independent raw/log/snapshot recomputation
```

The complete stdout/stderr log must cover capacity initialization, all nine
actor results, postprocess, and final process exit. Raw and snapshots remain
on the server. Only compact audits and logs are downloaded directly without
an archive.

## Stop and resume semantics

Missing raw and genuine runtime/environment failures may resume only under
the exact same D1R4 package, config, task table, controller semantics, source
fingerprints, run identity, and formal contract. Existing strict-valid raw
must be preserved.

A structured split-start or split-finish action-gate failure, changed physical
action, source mismatch, restart/causality failure, raw corruption, or any
scientific gate failure stops D1R4. It may not be retried or resumed under the
same identity after a code or semantics change.

## Frozen routes

```text
source/package/snapshot preflight mismatch before TSC
  CAUSAL_SPLIT_RETURN_SENTINEL_SOURCE_STOP

runtime or incomplete raw under unchanged semantics
  CAUSAL_SPLIT_RETURN_SENTINEL_RUNTIME_INCOMPLETE

structured start/finish, restart, causality, raw or safety failure
  CAUSAL_SPLIT_RETURN_SENTINEL_FAIL_REDESIGN_REQUIRED

all nine complete full-horizon safety gates pass
  CAUSAL_SPLIT_RETURN_SENTINEL_PASS_FULL_REPLACEMENT_CAMPAIGN_DESIGN_REQUIRED
```

A PASS authorizes design work only. The full replacement campaign must receive
a new identity and prospectively freeze its complete 1,000-rollout matrix,
whole-pair split, model family, recursive prediction, calibration/tube,
holdout, stop/resume, and independent forensic contracts before any new
response opens.

## Learning veto

D1R4 raw is development/safety-sentinel evidence and is forbidden from model
training and expert datasets. D1R4 cannot authorize BC, DAgger, or RL. Those
remain blocked until the reliable MPC expert and all restart, hidden-history,
new-target, continuous-parameter, model-error, noise, disturbance-recovery,
and independent long-hold gates are complete.
