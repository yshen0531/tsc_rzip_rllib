# Stage4.2R3c3T13S24D1R14R8R29 full-basis measurement-recentered receding-horizon feedback sentinel design

Frozen prospectively on 2026-08-09 after R8R28 final primary/independent
agreement and forensic closure at `3b7bd68`, but before R8R29 configuration,
implementation, model fit, uncertainty estimate, support result, plan,
controller action, formal metric, raw, snapshot, Ray, `gotsc`, TSC, or plant
advance.

## 1. Question and necessity

R8R28 completed `64/64` authentic fixed endpoint-timing trajectories, but
even its post-result per-context baseline-or-four-candidate oracle repaired
`0/10` failed baselines and remained `6/16`. Earlier R8R27 point-only search
had already repaired `0/10` within the four-slot U/V family. Another fixed
U/V schedule, timing, uncertainty, or context-oracle scan is therefore not
the next scientific question.

R8R14 authentically measured all eight signed canonical axes. R8R25 and
R8R26 separately established a finite accurate point model, containing tube,
and hard-safe action construction, but their planner was limited to the
supported U/V family and four decision slots. R8R29 asks:

```text
Can a whole-pair-qualified full signed-axis transition model support a
deterministic causal receding-horizon controller which re-centers on each new
visible measurement, safely executes only the first exact Card15 action, and
repairs at least one failed finite restart context without regressing a
baseline pass?
```

R8R29 is a model-gated fresh real-controller sentinel. It is not another
fixed candidate oracle, a global optimization claim, Gate A, expert-data,
imitation, policy learning, or RL. A PASS can establish only a finite causal
feedback-controller core and authorize the remaining prospectively frozen
Gate A qualifications.

## 2. Immutable sources and development-only bank

Authenticate final R8R23 as the exact 432-trajectory causal-model bank and
algorithmic source:

```text
run
  stage4_2r3c3t13s24d1r14r8r23_causal_online_innovation_receding_horizon_preflight_20260809_7b2739c_v1
route
  CAUSAL_ONLINE_FEEDBACK_MODEL_PREFLIGHT_INSUFFICIENT_REDESIGN_REQUIRED
trajectories / schedules / origins / forecast points
  432 / 27 / 1728 / 11232
feature / target digest
  14e1a15c6eb3ba305932b25918ec7127e46cd2a6f7c13ad50701545413fae849
  037be84fcce81dc97c8350d88416fc0ac42534083d1fb5688ab000dee2e81dcc
primary / summary / independent / final / manifest / state SHA-256
  a40a9b895bcfb69069fa5fe6dd7441b7159189d56f7aa50cc893db34a3bcd1a5
  4d900b3c5b477ff89dc1d62466b3d8e9ce132480f9c85ae26db91d55b1da285a
  af1b419bec6854ec901755c32f1c91131da1a09a0a0d4a1e1cc033ca6f0dd99a
  3d1c88aca308baf67b30010b25df03398dd20e1d4458dfa2413a7c65ceb174cc
  2f3aef0b48cb5d35846da3e769110fb8e514374ea7cf57c18b364d9879c5e403
  bd55964f69af3a17ce46f503ec629821c05dd54e9cbaf7ee71a9be644a227910
```

Authenticate final R8R14 and add exactly the six constant signed-axis
schedules not already represented by R8R23's UUUU/VVVV schedules:

```text
included new schedule identities
  direction 0 signs -/+
  direction 1 sign +
  direction 2 sign -
  direction 3 signs -/+
rows
  6 schedules * 16 contexts = 96 trajectories
run
  stage4_2r3c3t13s24d1r14r8r14_cumulative_multidirection_staircase_authority_identification_20260808_9874068_v1
route
  CUMULATIVE_MULTIDIRECTION_ATLAS_AUTHORITY_INSUFFICIENT_SEQUENCE_BASIS_REDESIGN_REQUIRED
final / manifest / state SHA-256
  da8420de6520e8f5fba14a9acf0489a89f7f2e1b9c2f613ebb91ef6e0b011b61
  ce980faf285b431910672cd819ea3e3b8da35d8f91507295616fda1a6df7a7f3
  27a2d6001c920aa3149c86a3bf6f52009acd42cf78bf5ac68500f6b3441b1eb3
```

Authenticate final R8R28 and add all four changed-timing U/V schedules:

```text
rows
  {g2,g3} * {UUUU,VVVV} * 16 contexts = 64 trajectories
run
  stage4_2r3c3t13s24d1r14r8r28_front_loaded_cumulative_endpoint_timing_authority_sentinel_20260809_a31262d_v1
route
  FRONT_LOADED_ENDPOINT_TIMING_AUTHORITY_INSUFFICIENT_BROADER_CAUSAL_CONTROLLER_REDESIGN_REQUIRED
final / independent / manifest / state SHA-256
  b32aaa273c17952b0f6ffc32ba907f5f78cff93e7bfa67038e042d95d3d45bc4
  ed4c8b1d997cd670aa28447ba4c012e585c92f5bd2c9420acb57e424e35405d1
  b687a127185a21127f4923303b93ec734b0b3381aaf3cad282bc2b1cb6dfbc04
  8b246c5617a0bf27a40ac02004c4c9350863ad427181cf878283529c23fa74b8
raw
  64 files / combined digest
  6ee50ed33eaee165f1543d67e669155e53acafd8cb5c67b879fcee45238a7b7f
```

The exact deduplicated development bank is therefore:

```text
physical pairs                                      8
hidden-history contexts                            16
global schedule identities                         37
trajectories                                      592
four causal origins per trajectory               2368
```

The 432 R8R23 rows, 96 added R8R14 rows, and 64 R8R28 rows are all consumed
controller-development evidence. None is a fresh holdout and none may enter
expert, BC, DAgger, residual-RL, or any other policy-learning data. Fitting a
fixed plant-transition model for constrained MPC under this document is not
authorization to learn a policy.

No R8, R8R1, or prior R8-family trajectory may be rerun. Source raw stays on
the server; only compact audits may be downloaded.

## 3. Causal state, target, and forbidden inputs

Preserve the exact R8R23 causal visible-state history and normalization. At a
decision, the controller may use only:

```text
numeric user target R/Z/Ip
visible R/Z/Ip through the current state
backward causal R/Z velocities from its own visible history
its own issued actions through the previous task step
measured TSC-order coil currents through the current state
task clock, active exact Card15 target, and prior solver/fallback status
```

The target is reconstructed by the unchanged formal evaluator from the
authenticated restart context and numeric offsets. The model uses the same
42-dimensional causal feature and 133-dimensional action-expanded feature as
R8R23, with ridge penalty `1e-4`, an intercept, no feature selection, and no
hyperparameter search.

Forbidden controller/model inputs are pair, history, partition, source
experiment identity, source outcome, formal pass/failure, future state or
action, matched member, wire/vessel current, simulator internal, and any R17
future controller output. Forbidden-input count must remain zero.

R8R23's failed additive one-step bias innovation is not reused or renamed.
R8R29 obtains feedback by rebuilding the causal origin from each newly
measured state and replanning; it performs no hidden parameter update from a
future or matched trajectory.

## 4. Fixed model and uncertainty preflight

Construct task-step-conditioned transition records at each schedule's four
real issue origins. Preserve actual causal action/current histories and
effect timing; do not stitch measured counterfactual states. Fit the unchanged
multi-output ridge family separately for each supported origin/lead mask.

Every outer and nested validation split excludes both histories of one whole
physical pair. Rebuild the R8R25 componentwise maximum residual tube using
only nested whole-pair out-of-fold residuals, multiplier `1.25`, and physical
floors:

```text
[0.015 m, 0.015 m, 3000 A, 0.05 m/s, 0.05 m/s]
```

No reserve may be clipped. The model gate is exactly:

```text
maximum held R point error                         <= 0.015 m
maximum held Z point error                         <= 0.015 m
maximum held Ip point error                        <= 3000 A
maximum held vR point error                        <= 0.05 m/s
maximum held vZ point error                        <= 0.05 m/s
reserved component containment                    100%
maximum R/Z tube half-width                        <= 0.025 m
maximum Ip tube half-width                         <= 5000 A
maximum vR/vZ tube half-width                      <= 0.08 m/s
held causal state support                          100%
finite exclusions                                  0
forbidden inputs                                   0
```

Build an exact convex action-transition support hull at each decision task
step from source requested coordinates and actual exact-Card15 transitions.
Outcome, formal margin, or residual magnitude may not select support rows.
Every candidate used by an offline or live plan must pass both state support
and the corresponding action-transition hull; unsupported candidates are
closed, never extrapolated.

Primary and structurally independent implementations must rebuild the bank,
fits, tubes, support hulls, and gates separately and agree within `1e-12`.
Any authentication, model, tube, support, finite, or independent failure ends
R8R29 before stage authorization with zero Ray, TSC, plant advance, raw, or
snapshot.

## 5. Frozen controller action family

Use the exact R8R14 canonical matrix with digest:

```text
c8cd62c00c1f60b46312927789659657dc8cc35717533193433b0e398c1ec94c
```

Freeze exactly 17 ordered incremental-coordinate candidates:

```text
0     zero incremental coordinate
1--2  direction 0, signs -/+, scale 1.0
3     direction 1, sign +, scale 1.0
4     direction 2, sign -, scale 1.0
5--6  direction 3, signs -/+, scale 1.0
7--11 U = direction 2 sign +, scales 0.50/0.75/1.00/1.25/1.50
12--16 V = direction 1 sign -, scales 0.50/0.75/1.00/1.25/1.50
```

There is no simultaneous mixed-coordinate action. Full-basis behavior arises
only by causal temporal switching among individually measured signed axes.
Support may close a candidate at a task step; it may never open an unsupported
candidate. No candidate, scale, order, or direction may be added after seeing
the preflight or real result.

Use exactly six receding decisions:

```text
[10,12,14,16,18,22]
```

Each nonzero decision constructs an exact Card15 incremental target from the
current causal measured-current center. Every intervening task step holds the
active stored target through the unchanged exact-target refresh. There are
six issues per full trajectory, 96 maximum issues over 16 contexts, and 320
expected refreshes (`80` safety, `240` qualification). A zero decision before
any active target produces the unchanged zero baseline continuation; a zero
decision after an active target preserves that exact target rather than
silently cancelling it.

Every issue and refresh must independently enforce:

```text
incremental normalized action L-infinity             <= 0.25
total normalized action absolute maximum             <= 1.0
current utilization                                  <= 0.55
desired/applied current cosine                        >= 0.98
relative off-basis residual                           <= 0.10
exact Card15 target/readback reconstruction
no action saturation or current clipping
unchanged visible-state pre-action safety envelope
safe stop before a failed plant advance
```

## 6. Measurement-recentered receding-horizon law

At each of the six decision steps, form the current causal feature from the
live history, enumerate only safe and supported remaining candidate
sequences, and run a deterministic beam search of width `512`. The model and
tube forecast through the unchanged formal endpoint. Ranking is fixed
lexicographically:

```text
1. robust formal feasibility under the full tube
2. smallest maximum normalized formal violation
3. smallest summed normalized R/Z/Ip/speed error
4. smallest summed coordinate magnitude
5. lexicographically smallest frozen candidate-index sequence
```

A robust-formal sequence always outranks a failing sequence. A nonzero first
action may be applied only when the selected remaining sequence is
robust-formal. A best failing sequence is diagnostic and forbidden from
execution. Execute only the first selected action, discard the remaining
open-loop suffix, append the actual next measurement, and solve again at the
next decision.

On model exception, non-finite value, unsupported live feature, empty safe
set, solver timeout, construction mismatch, or absence of a robust-formal
plan, use the fail-closed exact-target-hold fallback defined above. Record
the reason and do not invent a future action. Fault injection must prove the
fallback for model exception, NaN, unsupported state, no eligible action,
solver timeout, and exact-Card15 construction rejection before any TSC.

## 7. Offline authority gate before real execution

After the model gate passes, run the deterministic six-decision planner over
the 16 authenticated R8R7 causal origins using only the fitted development
model and tube. This is an offline authorization diagnostic, not a measured
controller result. It must report all plans, fallback paths, support
decisions, predicted formal metrics, and independent numerical agreement.

Real execution opens only if:

```text
all 16 searches complete safely
at least one of ten failed baselines has a predicted robust repair
zero of six baseline passes is predicted to regress under baseline fallback
baseline-fallback-plus-plan predicted oracle              >= 7/16
at least one nonzero first action is selected
all six fault injections select the exact safe fallback
primary/independent plan, action, metric, gate, route exact within 1e-12
```

Failure ends the identity with zero new TSC. Predicted repairs cannot be
called real control authority.

## 8. Prospective real-TSC execution and audit

Preserve the unchanged ordered physical pairs and histories. Execute exactly
one deterministic controller rollout per context:

```text
safety          4 contexts
qualification  12 contexts
maximum total  16 trajectories
```

The safety phase opens only runtime, authentic restart/source prefix,
causality, model identity, decision/fallback replay, exact issue/refresh,
Card15, action/current/saturation, finite-state, forbidden-input, raw,
snapshot, and count outcomes. Formal tracking remains closed. Qualification
requires exact primary/independent safety raw agreement and immutable
safety-raw authentication.

The independent raw audit must reconstruct every controller decision from
only the raw causal prefix using the independent model chain, reproduce the
selected first action and exact Card15 target, and prove that no stored plan
suffix or future measurement entered execution. A rejected action must not be
applied and no later plant step may occur. Any runtime, safety, restart,
causality, raw, or replay failure stops the stage and cannot resume under
changed semantics.

## 9. Immutable formal result gate

Formal evaluation opens only after all 16 raw files strictly parse and both
qualification audits agree. Reproduce the R8R7 baseline result exactly at
`6/16` and every saved baseline metric within `1e-12`.

The formal contract remains:

```text
slew 1.0  arrive no later than 250 ms, hold through 350 ms
slew 0.9  arrive no later than 270 ms, hold through 370 ms
R/Z tolerance 0.03 m, speed 0.1 m/s, Ip 10000 A, arrival streak 3
```

R8R29's real scientific gate passes only if:

```text
all source/model/offline/runtime/restart/causality/safety/raw/replay gates pass
failed baseline count                                             10
real failed-baseline repairs                                    >= 1/10
real formal controller passes                                   >= 7/16
baseline-pass regressions                                          0/6
primary/independent formal numerics, outcome, gate, route exact
```

Report every miss as a miss, all fallback/model-fault counts, issue/refresh
counts, current/action maxima, arrival/hold metrics, signed margins, and the
coarse user-target tracking diagnostics. Do not move a deadline, shorten a
hold, weaken a threshold, or substitute an aggregate score for a formal
pass.

## 10. Frozen routes and authorization boundary

```text
source/model/tube/support/search/fault-injection failure before TSC
  FULL_BASIS_MEASUREMENT_RECENTERED_FEEDBACK_PREFLIGHT_FAIL_NO_TSC

runtime/restart/causality/Card15/current/raw/replay/safety failure
  FULL_BASIS_MEASUREMENT_RECENTERED_FEEDBACK_EXECUTION_OR_SAFETY_FAIL_STOP

integrity passes but real formal gate fails
  FULL_BASIS_MEASUREMENT_RECENTERED_FEEDBACK_CONTROL_INSUFFICIENT_REDESIGN_REQUIRED

real formal gate passes
  FULL_BASIS_MEASUREMENT_RECENTERED_FEEDBACK_CORE_PASS_GATE_A_QUALIFICATION_REQUIRED
```

R8R29 is immutable once any model fit begins. It may not resume with a new
candidate, gain, support rule, tube, objective, decision step, fallback, or
formal gate. A PASS is a finite deterministic feedback-core result only. It
does not itself qualify continuous delay/gain/slew, model mismatch, noise,
disturbance recovery, independent long hold, residual authority, MPC expert
data, or Gate A. All those Gate A axes remain prospectively blocked.

A FAIL rejects this exact full signed-axis, six-decision, measurement-
recentered law; it does not establish global plant unreachability. Every
source and R8R29 trajectory remains forbidden from expert, BC, DAgger,
residual-RL, and every other learning dataset.
