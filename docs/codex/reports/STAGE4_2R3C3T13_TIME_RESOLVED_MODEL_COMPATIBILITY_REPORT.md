# Stage4.2R3c3T13 time-resolved model compatibility report

## 1. Result

The frozen V4 read-only audit completed against all 1,408 authenticated
R3c3/T1/T2/T6/T9/T11 raw trajectories. It ran no controller, optimizer,
Ray task, `gotsc`, TSC plant step, or snapshot creation.

The result is unambiguous:

```text
signed differential comparisons                 0 / 576 PASS
finite measured-node comparisons                 0 / 896 PASS
T9 Walsh interaction comparisons                  0 / 32 PASS
causality gates                                1504 / 1504 PASS
first physical effect-state matches            1504 / 1504 PASS
Stage3.4 fixed lifted Jacobian as an
  unqualified restart-envelope predictor              VETOED
```

All 1,504 prediction comparisons fail the prospectively frozen relative
time-series error gate. This is a prediction-model/design gap, not a
runtime, restart, causality, raw-corruption, statistics, or reporting error.
It does not establish global plant unreachability and it is not a new real
closed-loop result.

The T13 route is therefore:

```text
MINIMAL_SENTINEL_REQUIRED
```

The one missing task-relevant object is a state- and issue-time-conditioned
single-step transition response around an authentic restart, including the
actual actuator delay queue and matched hidden histories. The separately
frozen T13S1 sentinel tests only that object. It does not authorize a full
32-context campaign or a real controller.

## 2. Exact code, design, and evidence identity

```text
local branch
  codex/stage4_2r3c3t12-formal-gap-discriminator

V4 implementation checkpoint
  a97332d fix(stage4.2r3c3t13): authenticate weak formal horizon

V4 design SHA-256
  946993c085d04c3d8eb9030f5b5502e1eb02a0238ba0deb2aea7f43fd154bd3c

audit implementation SHA-256
  6ec7bf9c921aab184da5d6f87bb6f96478f2961e02c0267fc3a9cb725e0a9649

focused test SHA-256
  52c543d99e4134210485535f00bed37a2f6bebed75b0426656d6f6ff6a2059f4
```

The authenticated Stage3.4 model identities are:

```text
full_horizon_bundle.json, shape 175 x 105
  7b307e82c35bc12beea51be303be90d0a5dd7554f54156e3684b167f37ee8987

Stage3.4 source
  a6097b8dea3293bdccf0e742ee86dc9df65b5318f2bd700ee4e5e81d72968f27

resolved config
  6d705aaad12bc6872af776a0adf041041cbda38a4d545581017ad5ecdc7b34b4

environment
  a0ed368a4aeb93b0073ff46f90583a8d63c3ef076eeef6400460ec0cb50c546a

manifest
  f66b84d59f53ecc665571337726f2ad6c77a749059abc06ff96995589e9af460

14 x 3 float64 mode matrix
  a6438d4d32cb00a391e0f4f1f9341b8ba162aeddf75cacb599ac433fe4af0b54
```

The mode Gram-matrix maximum error is `9.99e-16`; the nominal maximum
14-coil delta is `3 A`. The Stage3.4 bundle was identified one variable at a
time around its original nominal. Its own metadata marks online feedback and
robustness as unvalidated.

No new package manifest was built for this read-only patch deployment. The
server base files and each transferred T13 file were authenticated by exact
hash before invocation. This is narrower than a complete package deployment
and is reported as such.

## 3. Exact server and compact local paths

```text
canonical project
  /home/yangshen0711/tsc_all/tsc_rzip_rllib

Stage3.4 bundle
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/stage3_4_runs/
  stage3_4_late_arrival_continuation_mpc_350ms_20260724_030829/
  stage3_4_identification/full_horizon_bundle.json

V4 audit output
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13_model_audits/
  stage4_2r3c3t13_time_resolved_model_compatibility_v4_20260801_a97332d

compact local evidence
  docs/codex/audits/
  stage4_2r3c3t13_time_resolved_model_compatibility_v4_20260801/
```

Only the 1,189-byte route and 719-byte manifest were downloaded. The
1,858,077-byte detailed audit and all 62,444,406 bytes of raw evidence remain
on the server and were postprocessed there with Python.

## 4. Expected versus actual inventory

| Source stage | Expected/actual raw | Bytes | Immutable inventory digest |
|---|---:|---:|---|
| R3c3 | 256 / 256 | 8,933,607 | `88bcd02a5dd2ec4def60c1f2e7f2304fb57859836d3b9a34b090bfd91e00e563` |
| T1 | 128 / 128 | 4,505,015 | `f19a04dcb6b597e97517482d602a6cfdb3c0a1f0b4bfd7a1507b90ae2cc0876f` |
| T2 | 160 / 160 | 7,404,198 | `e40dbf9b531886344bd97a18590db342897570ec8f21b18a37d16c4fb528c90f` |
| T6 | 224 / 224 | 11,124,363 | `594b4333eb848c762aec557744fe2dcef9101e1cc495f8713ed8bbe2f2913f61` |
| T9 | 224 / 224 | 11,204,025 | `e53f06fc772682d85144b578a915e614b1a5d24b34aea6dfa77ab35f5091eea2` |
| T11 | 416 / 416 | 19,273,198 | `f84fd31fcbe6db03bd9db0a1d694097b8532120915ec0e3e03668cff0dd908c3` |
| total | 1,408 / 1,408 | 62,444,406 | six exact stage digests above |

All 1,408 experiment IDs are unique. Every raw member is successful,
completed, parseable, source-authenticated, and clean under the forbidden
controller-input contract.

The exact full raw shapes were authenticated before selecting the common
Stage3.4 model slice:

```text
R3c3/T1 normal actuator              36 states / 35 trace rows
R3c3/T1 weak actuator                38 states / 37 trace rows
T2/T6/T9/T11                        51 states / 50 trace rows
model input for every comparison     states 0--35 / actions 0--34
```

The weak state-37 formal hold endpoint remains real and authenticated, but
the 175-row Stage3.4 model ends at state 35. V4 did not silently extend it.

## 5. Input reconstruction and raw integrity

The native model input is the recorded causal trace command multiplied by
the actual slew and projected into the authenticated three-mode basis. The
maximum command subspace residual is:

```text
observed maximum                         1.0244892712e-7 A
frozen acceptance gate                   1.0e-6 A
```

The adjacent trajectory coil-current difference is a finite-precision TSC
observation, not the native pre-Card-15 command. Its maximum difference from
the command is `0.0500082884 A`, and its maximum mode-subspace residual is
`0.0467069413 A`. Those values are reported diagnostics; they were not used
to tune or choose the predictor.

Raw files copied or modified by T13: `0`.

## 6. Frozen prediction gates and exact result

The prospectively frozen per-comparison gates were:

```text
velocity-component RMSE                       <= 0.008 m/s
endpoint-late response-speed error             <= 0.004 m/s
final response-speed error                     <= 0.010 m/s
position RMSE                                  <= 0.001 m
Ip RMSE                                        <= 30 A
scaled relative response L2                    <= 0.10
```

Results:

| Tier | Comparisons | Causal | Absolute gates | Relative L2 pass | Relative L2 min/median/max |
|---|---:|---:|---|---:|---:|
| signed | 576 | 576 | every metric 576/576 | 0/576 | 0.145529 / 0.760916 / 3.602284 |
| finite node | 896 | 896 | 892/896 endpoint-late; all other metrics 896/896 | 0/896 | 0.222657 / 0.864391 / 4.948025 |
| interaction | 32 | 32 | every metric 32/32 | 0/32 | 0.546690 / 1.049997 / 2.360715 |

The four finite-node endpoint-late misses reach `0.0041151268 m/s`, just
above the unchanged `0.004 m/s` gate. They are not what drives the universal
failure: all 1,504 comparisons independently fail the relative shape gate.

Failure counts are exactly symmetric because the relative failure is
universal:

```text
signed:       prefix p5/p9 288/288; target 288/288; actuator 288/288
finite node:  prefix p5/p9 448/448; target 448/448; actuator 448/448
interaction:  prefix p5/p9   16/16; target   16/16; actuator   16/16
```

Every reconstructed first effect state equals the preregistered physical
effect state. Every pre-effect R/Z, velocity, and Ip difference passes its
causality floor.

## 7. Retrospective scalar-repair diagnostic

After the frozen V4 verdict, a separately labeled retrospective diagnostic
asked whether a single optimal scalar could repair each predicted response.
It did not alter a gate or route identity.

Across all 1,504 comparisons, zero optimal-scaled predictions reached
relative residual `<= 0.10`. Representative signed-response median cosine /
optimal-scaled residual values were:

```text
R3c3       0.789 / 0.615
T1         0.896 / 0.443
T11        0.669 / 0.738
T2         0.811 / 0.585
T6         0.749 / 0.663
T9         0.757 / 0.652
T9 Walsh   0.330 / 0.944
```

Median norm ratios are approximately `0.95--1.21`, while some cosines are
near zero or negative. The mismatch is therefore predominantly response
direction and time shape, not a global amplitude calibration. Amplitude-only
rescaling is vetoed.

## 8. V1--V3 audit-design corrections

Three prospective audit implementations stopped before any Jacobian
multiplication and before creating an output identity:

1. V1 incorrectly required a post-Card-15 observed current difference to
   equal the pre-Card-15 trace command at `1e-9 A`.
2. V2 used the correct trace command, but its `1e-9 A` subspace gate was
   below the source-defined float32 command precision. An input-only
   preflight measured `3.81e-8 A`; the source-derived upper bound is
   `6.7e-7 A`.
3. V3 assumed a fixed R3c3/T1 36/35 schema and stopped on the authentic weak
   38/37 trajectory before prediction.

V4 changed only those pre-prediction schema/numerical contracts. No output
threshold, formal gate, model, comparison, or route rule was changed after
seeing a prediction error. V1, V2, and V3 have no audit output directory and
no scientific model result.

## 9. Required error classification

```text
runtime or environment error                         none
packaging or import error                            none
raw-data or snapshot corruption                      none
statistics or reporting error                        none
audit-design/schema corrections                      V1--V3, pre-prediction
prediction-model/design gap                          yes
plant restart failure tested by T13                  no
real closed-loop control tested by T13               no
global reachability tested by T13                    no
```

The prior R3c1/T11 unprobed baseline remains a genuine 16/32 closed-loop
controller result. T13 neither reran nor reinterpreted it.

## 10. Architecture implication

The fixed Stage3.4 lifted Jacobian cannot be promoted to an unqualified
restart predictor. Its 175 outputs also stop two states before the weak-slew
formal hold endpoint. The current source's soft least-squares solve,
post-solve scheduler, and coupled model/formal clock therefore cannot form a
defensible restart MPC by packaging changes alone.

This does not imply that a relinearizing, state-conditioned MPC is
infeasible. It means that the missing transition object must be measured or
otherwise identified before such a controller can be implemented
scientifically.

## 11. Validation and commands actually run

Repository-side validation for the final V4 implementation:

```text
Python compileall                                   PASS
all repository JSON parse                    2,507/2,507
focused T13 tests                                  8/8 PASS
```

The complete Windows discovery invoked 263 tests but reported 27 imports of
the Linux-only `resource` module. This is a local platform limitation and is
not claimed as a complete local pass. The same exact V4 files in the server
Linux virtual environment passed:

```text
focused T13 tests                                  8/8 PASS
complete Linux suite                            632/632 PASS
compact-evidence test                         1 expected skip
```

Commands used were repository-local Git/Python/PowerShell checks and direct
`ssh`/`scp` transfer using the user-authorized fixed non-interactive endpoint
fallback. No archive was created or extracted. Server-side Python read the
large raw and audit JSON in place. The final read-only verification
recomputed the three output hashes and downloaded only route/manifest.

## 12. Compact output hashes

```text
stage4_2r3c3t13_time_resolved_model_audit_v4.json
  bytes   1,858,077
  sha256  af644ef8e342e03b9b72215eb518b62ea9e7898842851681e5b0cc585d160b0d

stage4_2r3c3t13_time_resolved_model_route_v4.json
  bytes   1,189
  sha256  b143ecf0e4cb6065940488c4b2ebc901c8a61b06372234bce245bde0b5ad8ccc

stage4_2r3c3t13_time_resolved_model_manifest_v4.json
  bytes   719
  sha256  aae0217f02f18a54abad13c8b2ed0903678d5e1552c58c1703e00e7f703460d8

provenance digest
  fe92e5cc4e8ce6a282c24cc1e05bd27ab1fd6a52d3e591fafe25c7cf8fe46e01
```

The route JSON intentionally marked the T13 final route as not yet made; it
was the model-audit output. This report, the architecture specification, and
the separately prospective sentinel design make the final T13 decision.

## 13. Frozen scope, unvalidated scope, and next action

Frozen:

- R17 remains an 18/18 finite static-grid source, not a robust restart MPC.
- R1 means Stage4.2R1 authentic plant restart; R17 means Stage4.1R17.
- R1c/R2 exact finite restart facts remain unchanged.
- R3c1 remains 16/32 and R3c2 remains 12/32 real development control.
- T11 remains a clean 25/32 identification-design FAIL.
- T12 vetoes the fixed condition-first response-basis route.
- T13 vetoes the fixed Stage3.4 Jacobian as the unqualified restart predictor.
- Arrival remains 250/270 ms and hold remains 350/370 ms, with unchanged
  physical thresholds.

Not validated:

- a new restart MPC or any new real closed loop;
- an arbitrary per-step prediction model;
- independent hidden-history robustness or an observer;
- unseen targets or continuous actuator/plant variation;
- noise, disturbance recovery, or independent long hold;
- expert-dataset readiness.

Next action: implement or execute nothing until the separately frozen T13S1
sentinel package passes all offline validation and receives explicit run
authority. T13S1 PASS would authorize only an offline local-transition model
step; T13S1 FAIL would stop the identification route. R3c4, BC, DAgger, and
bounded residual RL remain unauthorized.
