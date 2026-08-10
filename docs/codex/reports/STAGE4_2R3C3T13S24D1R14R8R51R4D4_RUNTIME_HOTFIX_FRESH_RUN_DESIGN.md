# Stage4.2R3c3T13S24D1R14R8R51R4D4 runtime-hotfix fresh-run design

## Frozen evidence boundary

The first R51R4D4 real invocation is final as an execution failure.  It is
not a response-authority, formal-control, MPC, plant-reachability, restart,
causality, raw-corruption, or solver result.  No response or formal metric
was opened.

The immutable failed run is:

```text
run root
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s24d1r14r8r51r4d4_runs/
  stage4_2r3c3t13s24d1r14r8r51r4d4_center_bridged_two_pulse_response_sentinel_20260810_f553b67_v1

original implementation checkpoint                         438adab
original package checkpoint                                f553b67
reporting-only implementation checkpoint                   e9655cc
reporting-only package checkpoint                          bf3145f
failed-attempt compact server evidence SHA-256
  8dbb6b10951b57272dd46d2b5a9694d815fe49263122698df7b67cdd7e764726
final compact server evidence SHA-256
  e5b6be3b17df83959444fa4d7e495847ea642045d598b0e94421f3f1e00d4a06
raw count                                                       250
raw bytes                                                   6318347
canonical raw inventory digest
  5f4e56dda413898f2ccd40e03fbf36d9a2f1a4e0bb7c829fcd3b8342fa1d826c
independent byte-authentication digest
  4936faea52386b3422a93ce708b7163b3a876c5e49740acca8695b8d09bd92c6
```

Every raw file strictly parses.  All 250 rows have 12 states and 11
controller traces, for 2,750 actual plant steps.  Authentic initial restart,
the source state and trace prefix through the pre-q0 state, calibration, the
q0 action gate, action/detail/effect equality, q0 nominal-current equality,
and partial-trajectory finite-state checks independently pass 250/250.  The
maximum q0 action is `3.7037037048793097e-06`; the maximum q0 nominal-current
difference is `1.4210854715202004e-14 A`.  There are no abnormal states or
forbidden inputs.  No first or second candidate pulse was issued.

Primary and independent failure reports agree.  The final route is frozen:

```text
REDUCED_Q0_TRANSPORT_BRIDGE_R51R4D4_CENTER_BRIDGED_TWO_PULSE_EXECUTION_FAIL_STOP
```

The failed raw, reports, logs, state, and manifest remain in place.  They may
not be deleted, renamed into an active raw directory, or resumed.

## Root cause

`TwoPulseController` inherits the live state machine from the R51R1
`BridgeController`.  That inherited implementation owns these fields:

```text
r8r51r1_candidate_id
r8r51r1_requested_coordinate
r8r51r1_contract
r8r51r1_center_fields
r8r51r1_center_current
r8r51r1_issue_event
```

The first D4 implementation instead referenced the historical R51 names
without the `r1` component.  The inherited `_q0()` correctly populated
`r8r51r1_center_fields`; the D4 step-11 branch then tried to read the
nonexistent `r8r51_center_fields` and raised the same `AttributeError` in all
250 tasks.  Offline construction used the pure event constructors directly,
so the existing source-text-focused test did not exercise this cross-step
runtime state.

The subsequent strict-JSON error was reporting-only: the primary reporter
used `inf` for an unavailable maximum after the incomplete rows.  Checkpoint
`e9655cc` changed only that unavailable value to JSON `null`; it skipped all
250 already-completed raw files and accurately finalized the failed run.

## Prospective correction boundary

A fresh campaign is permitted only with all of the following frozen changes:

1. Every D4 access to the inherited candidate, requested-coordinate,
   contract, center, and issue fields uses the actual `r8r51r1_*` namespace.
2. The first candidate is installed into the inherited fields before the
   inherited `_issue_candidate()` at task step 12.
3. The second candidate is installed into the same inherited fields before
   the inherited `_issue_candidate()` at task step 18.
4. Holds and the bridge read the inherited center/issue/contract fields.
5. A focused zero-plant runtime test executes the q0, observation, first
   issue/holds/return, bridge, second issue/holds/return, and refresh branches
   and proves the live field namespace and event clock.
6. The already-audited `null` failure-report representation remains.

No pure event constructor, requested coordinate, Card15 conversion, event
clock, action, current target, center-return rule, causal input, hidden-state
rule, source trajectory, task matrix, formal metric, threshold, route, or
scientific gate may change.

## Fresh identity and unchanged experiment

Because the failed attempt advanced the plant, the correction is not a
resume.  It must use:

```text
campaign identity
  center_bridged_two_pulse_response_sentinel_v1_runtime_hotfix1
controller revision
  center_bridged_two_pulse_response_v42r3c3t13s24d1r14r8r51r4d4_v1_runtime_hotfix1
package revision
  r42r3c3t13s24d1r14r8r51r4d4_center_bridged_two_pulse_response_v1_runtime_hotfix1
fresh run suffix
  <new-package-checkpoint>_v2_runtime_hotfix1
```

The 250 experiment IDs may remain the same only inside this distinct campaign
identity and fresh run directory.  The failed run is an authenticated source
of failure provenance only and is never a source of response data.

The new offline construction must reproduce the already frozen values exactly:

```text
specification count                                      250
ordered candidates per context                           25
offline action-stream digest
  26823bfc79fd3ca9e40a73d471010f55fad166f4d1fede9990632101f3bc36a5
offline event-stream digest
  52a2185df769259ac15449a73b9d53751e7025c936505a7a71eca8ed89c29521
maximum incremental normalized action     0.2111111111111112
maximum current utilization                0.3912
```

Any mismatch blocks real authorization.

## Validation and execution order

Before a new real launch:

1. compile and focused tests pass in the project virtual environment;
2. the Windows-shimmed full local suite passes;
3. a new manifest and SHA256SUMS bind the design and implementation;
4. an empty direct-copy package passes hashes, JSON, compile, focused, and
   full tests;
5. direct `scp -r` transfer, staging validation, installation, and installed
   server validation pass in the existing server virtual environment;
6. a fresh output directory completes primary and independent offline
   construction with the frozen action and event digests;
7. real execution is separately authorized; and
8. the exact failed-run directory and raw digest are reauthenticated before
   launch.

Only one fresh 250-trajectory campaign is authorized.  Raw primary and
independent integrity must pass before any response/formal metric is opened.
The unchanged D4 scientific authority gate then determines whether the
already frozen D5 zero-new-TSC model/controller preflight is eligible.

All D4 and fresh-hotfix trajectories remain forbidden from expert data.  This
stage is an identification discriminator, not real MPC and not Gate A.
