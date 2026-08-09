# Stage4.2R3c3T13S24D1R14R8R42 fixed equal global/local-affine cold-ensemble receding-controller preflight design

Status: prospectively frozen after final R8R39 and the R8R41 design,
implementation, package, and deployment validation, but before any R8R41
primary or independent model fit, prediction, residual, tube, metric, gate,
route, stdout, stderr, state, or result exists. No R8R41 numerical result
informed this design.

This is a conditional design only. It may execute if and only if final R8R41
has exact primary/independent agreement and route
`FIXED_EQUAL_GLOBAL_LOCAL_AFFINE_COLD_ENSEMBLE_PASS_CONTROLLER_PREFLIGHT_DESIGN_REQUIRED`.
Every other final R8R41 route blocks R8R42 before construction or
computation.

## 1. Frozen source and zero-TSC boundary

R8R42 must authenticate the exact final R8R41 primary summary, primary
detailed result, model artifact, independent audit, compact audit, final
report, state, and manifest. Their hashes may be transcribed after R8R41 is
opened, but no controller candidate, cost, tie, fallback, tube, safety gate,
authority gate, or route below may then change.

Rebuild the same immutable development bank:

```text
trajectories                                      560
physical pairs                                      8
history contexts                                   16
schedule identities                                35
decision steps                     [10,12,14,16,18,22]
interval records                                 3360
five-component time rows                        14560
bank digest        a84995970a5c1f0f2d2e964c6b97cbaf213ac8f86d70a3666279ae144ba2de2e
feature digest     80ed0b20b99f6f277ac1e09f85ad33c6fb8a1e611824901509eaf6a3c7b830db
target digest      0f445fca5bb2dbb1da7fb1fc5e1951161322caccc4219371653ffdb55eaa8539
```

R8R42 executes zero Ray, `gotsc`, TSC, controller, plant step, raw, and
snapshot. All R8-family trajectories remain forbidden from expert data, BC,
DAgger, residual RL, and every other learning dataset.

## 2. Immutable fixed equal local-affine cold ensemble

For every held whole-pair and whole-schedule fold, independently refit only
from its complete training trajectories:

```text
global expert
  causal expanded feature dimension                                238
  centered ridge with unpenalized intercept                       1e-4

local expert
  coordinate                         [causal base 44,current action 18]
  dimension                                                           62
  scale floor                                                        1e-12
  stable Euclidean neighbors                                           64
  uniform weights                                                        1
  centered local slope ridge                                             1
  unpenalized local intercept                                             0
  inactive centered columns                              exact zero slope

ensemble prediction                         0.5 * global + 0.5 * local
```

Both weights are exact binary64 `0.5` and identical for all rows. There is
no innovation, gain, gating, distance switch, expert fallback, feature or
ridge selection, neighbor search, response weighting, clipping, or
post-result adjustment. Pair, history, source, schedule, formal outcome,
held target, future row, and residual remain forbidden predictor inputs.

Carry the final R8R41 componentwise maximum whole-pair/whole-schedule tube
without shrinkage. A planned state may be propagated only by the frozen
ensemble and this tube; it may not create synthetic measurements or update
either expert.

## 3. Fixed measurement-recentered receding construction

Only after the conditional source gate passes, recreate the unchanged
bounded R8R33/R8R34 first-action planner:

```text
candidate actions per decision                                  17
decision steps                              [10,12,14,16,18,22]
beam width                                                       512
measurement recentering                                    required
action applied from a completed solve                    first only
failed or unsupported solve                              forbidden
fallback                                  exact current-target hold
```

Candidate library, stable ties, target cost, tube reserve,
termination, and fallback are frozen from that planner. Every later search
starts from a newly visible causal state; planned states never masquerade as
measurements. Current or future held targets may test a selected first
action only after selection and may not enter ranking, fallback, or ties.
Off-policy held continuations may not be relabeled as consequences of a
different selected action.

## 4. Actuator, safety, support, and fallback gates

Every proposed first action must pass before authorization:

```text
exact Card15 issue and target refresh                      required
dynamic radius                                                   16
normalized incremental action                               <=0.25
normalized total action                                     <=1.00
current utilization                                         <=0.55
direction cosine                                            >=0.98
off-basis residual                                          <=0.10
finite / solver / saturation errors                              0
stop before failed advance                                required
observed causal transition support                           100%
```

Unsupported, non-finite, or failed searches select exact hold and cannot
count as repairs. All six frozen fault injections must select hold and may
never authorize nonzero action.

## 5. Frozen finite authority gates

Evaluate the same 16 baseline contexts and preserve their frozen formal
classification: six pass and ten fail. Planning opens only after complete
R8R41 source PASS and all integrity, safety, model-binding, and support
gates.

```text
safe searches                                                16/16
full-tube predicted repairs among ten failed baselines       >=1/10
full-tube predicted regressions among six passing baselines      0
fallback-plus-plan optimistic oracle                         >=7/16
nonzero safe first action count                                  >=1
fault-injection hold selections                                6/6
primary/independent discrete selections                       exact
maximum scaled primary/independent numeric difference         1e-9
```

Center-only repair, later arrival, post-result fallback, unsupported
extrapolation, and off-policy raw continuation cannot pass. These are finite
offline authority gates, not real tracking, real MPC, or Gate A.

## 6. Routes and authorization

```text
R8R41 is not the exact independently reproduced PASS
  FIXED_EQUAL_LOCAL_AFFINE_COLD_ENSEMBLE_CONTROLLER_PREFLIGHT_BLOCKED_BY_SOURCE

source, package, causality, forbidden-input, runtime, or dual disagreement
  FIXED_EQUAL_LOCAL_AFFINE_COLD_ENSEMBLE_CONTROLLER_PREFLIGHT_EXECUTION_FAIL_STOP

model binding, tube, support, actuator, safety, or fault-injection failure
  FIXED_EQUAL_LOCAL_AFFINE_COLD_ENSEMBLE_CONTROLLER_PREFLIGHT_SAFETY_FAIL_NO_TSC

safe preflight but frozen authority gate fails
  FIXED_EQUAL_LOCAL_AFFINE_COLD_ENSEMBLE_CONTROLLER_PREFLIGHT_AUTHORITY_INSUFFICIENT_NO_TSC

all source, integrity, safety, support, authority, and dual gates pass
  FIXED_EQUAL_LOCAL_AFFINE_COLD_ENSEMBLE_CONTROLLER_PREFLIGHT_PASS_REAL_SENTINEL_DESIGN_REQUIRED
```

A PASS authorizes only a separately frozen fresh finite real-TSC safety
sentinel design. It does not authorize that run, qualify MPC, reach Gate A,
or authorize expert data, BC, DAgger, or RL. A blocked or failed route does
not prove plant unreachability or global controller impossibility.

## 7. Formal and deployment contract

```text
slew 1.0/1.1  arrive no later than 250 ms, hold through 350 ms
slew 0.9      arrive no later than 270 ms, hold through 370 ms
R/Z tolerance 0.03 m, speed 0.1 m/s, unchanged Ip and arrival streak
```

Before any R8R42 implementation or execution require project-venv
compilation, focused and full tests, exact package hashes, empty-directory
direct-copy validation, server preflight, the existing server venv, all
declared `bash -n`, and full server tests. Transfer only direct directory
trees without archives. Keep large evidence on the server and download only
compact audits.
