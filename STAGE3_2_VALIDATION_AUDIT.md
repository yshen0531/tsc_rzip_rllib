# Stage3.2 validation audit

## Validation scope

This audit covers package completeness, source-data recovery, control-vector reconstruction, metric/gate logic, finite-difference construction, local SQP mechanics, long-hold flow, full-controller identification, feedback-scale selection, serialization, resume integrity, and a deterministic no-gotsc end-to-end mock.

It does not replace a real Stage3.2 campaign using the user's working gotsc binary.

## 1. Complete standalone tree

The package contains the full inherited Stage2/2.1/2.2/3.0/3.1 code and all Stage3.2 files.  The launch path does not use Git, network access, an external base tree, or runtime code recovery.

## 2. Actual Stage3.1 source audit

The uploaded completed Stage3.1 run was loaded directly.  The prepare path recovered:

```text
all catalog rows                 918
successful Stage3.1 rows         498
strict source candidates          46
best source candidate            s31r999p_6de147eb9cfd6186
best hard signed margin           0.028515736666666625
best internal signed margin      -0.05980101454545461
fingerprinted files               515
fingerprinted bytes          16,755,556
logical-path source digest        bae82a085acfc8e2ef7f5e009384056a2cbc5e04905c7a5fa18d9d10973ee705
```

The first 15 action steps decoded by Stage3.2 were compared to the saved Stage3.1 action sequence; the maximum absolute difference was zero in the integration check.

## 3. Gate regression

Tests verify that Stage3.2 rejects changes to:

```text
30 mm precise R/Z box
40 mm relaxed R/Z box
0.10 m/s endpoint speed
0.10 m/s RMS speed
10000 A Ip tolerance
three-sample arrival streak
arrival deadline at 150 ms
```

A synthetic trajectory that remains safe through 250 ms passes.  The same trajectory with post-150 ms drift fails, confirming that Stage3.2 does not merely recheck the old 150 ms endpoint.

## 4. Candidate dimensions and probe counts

Validated dimensions:

```text
margin variables                         21
long-hold tail variables                 30
full-feedback variables                  75
margin finite-difference probes          84
hold finite-difference probes           120
full-identification probes               150
extension templates per source           12
feedback scenarios                        33
feedback validation rollouts              99
```

Probe IDs are unique.  Variables at coefficient bounds produce nonzero inward secant probes.

## 5. Unit and static tests

The final build passes:

```text
Python compileall                         PASS
all configuration JSON parsing           PASS
all shell scripts with bash -n            PASS
complete unittest suite                   92 tests PASS
Stage3.2 scientific tests                  21 tests PASS
Ray-capacity regression tests               7 tests PASS
strict JSON nonfinite rejection           PASS
source logical-path fingerprinting        PASS
```

The complete suite includes inherited Stage2/2.1/2.2/3.0/3.1 regression tests.

## 6. No-gotsc end-to-end mock

A deterministic local mock ran the full Stage3.2 flow:

```text
margin SQP                                complete
48-candidate extension screen             complete
long-hold SQP                             complete
150-probe full identification             complete
125×75 Jacobian numerical rank             75
batch retained rank                        52
99 feedback rollouts                       complete
open-loop and feedback confirmation        complete
analysis/report generation                 complete
strict JSON/JSON.GZ re-read                complete
new optimization/identification rows       300
```

The mock is an integration test only.  Its scientific verdict is intentionally not treated as evidence about TSC control performance.

## 7. Known boundaries

The package has not been executed here against the user's real gotsc environment for 250 ms episodes.  The following are therefore unknown until server execution:

- whether the Stage3.1 nominal can be held through 250 ms;
- whether margin SQP reaches the 27.5 mm / 0.07 m/s internal target;
- whether the 125×75 real-TSC Jacobian has sufficient reliable rank;
- whether one global feedback scale preserves/recoveries the configured scenarios;
- whether any Stage3.2 final verdict passes.

Even a successful target/disturbance verdict does not establish robustness to different initial states, plant parameters, measurement noise, delay, or vessel/eddy-state variation.

## 8. Ray-capacity hotfix validation

The observed production stall was reproduced from the saved wave sizes and the original scheduler logic:

```text
configured workers                         96
first margin-probe wave                    84
old Ray initialization capacity            84 CPUs
later long-hold probe wave                120
actors created for later wave              96
actors that could receive CPU resources    84
completed first tasks                      84
completed queued second tasks              24
permanently unschedulable actor tasks      12
observed terminal progress                108/120
```

The corrected planner is tested without importing a real Ray cluster by a deterministic fake-Ray harness.  Regression tests verify:

```text
84 pending, 96 requested  -> ray.init(num_cpus=96), 84 actors
120 pending, same process -> no reinit, 96 actors
12 pending on resume      -> ray.init(num_cpus=96), 12 actors
24 pending next wave      -> no reinit, 24 actors
150 pending next wave     -> no reinit, 96 actors
existing 84-CPU cluster with 96 requested -> immediate RuntimeError
```

The full unit-test count after the hotfix is 92, including seven Ray-capacity regression tests.  The package verification script also requires the new runtime helper and regression test file.


## 8. Real-run Ray deadlock forensic audit and regression

The interrupted real Stage3.2 run was inspected directly:

```text
hold manifest candidates            120
successful persisted results        108
missing results                      12
missing population indices        84-95
successful result wall time range  387.3-602.4 s
```

The 12 missing tasks are exactly those assigned to actors 84-95.  The first Stage3.2 evaluation wave had 84 candidates, so the old code initialized Ray with 84 logical CPUs.  The later 120-candidate wave created 96 actors; actors 84-95 never received a CPU resource.  This proves the incident was an unschedulable-actor deadlock rather than slow gotsc execution.

The fixed package now passes 92 unit tests, including dedicated tests that verify:

```text
84-candidate first wave initializes 96 Ray CPUs and 84 actors
120-candidate later wave uses 96 actors without reinitialization
12-candidate resume initializes 96 Ray CPUs and 12 actors
24- and 150-candidate later waves retain access to all 96 CPUs
an existing 84-CPU Ray cluster is rejected for a 96-worker campaign
all open-loop and feedback evaluation paths use the shared capacity helper
```

The interrupted run remains resume-compatible: 108 completed hold probes are reused and only the 12 missing probes are rerun.
