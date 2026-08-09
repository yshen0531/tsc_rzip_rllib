# Stage4.2R3c3T13S24D1R14R8R38 training-only diagonal-gain receding-controller preflight design

Status: prospectively frozen after final R8R35 was opened, but before any
R8R37 primary or independent gain fit, prediction, residual, tube, metric,
gate, route, stdout, stderr, state, or result exists. No R8R37 numerical
result informed this design.

This is a conditional design only. It may execute if and only if final R8R37
has exact primary/independent agreement and route
`TRAINING_ONLY_DIAGONAL_INNOVATION_GAIN_PASS_CONTROLLER_PREFLIGHT_DESIGN_REQUIRED`.
Every other final R8R37 route blocks R8R38 before construction or computation.

## 1. Frozen source and boundary

R8R38 must authenticate the exact final R8R37 primary summary, primary
detailed result, model artifact, independent audit, compact audit, final
report, state, and manifest. Their hashes may be transcribed after R8R37 is
opened, but no controller candidate, search, cost, tube, safety gate,
authority gate, or route in this document may then change.

R8R38 consumes only the same immutable 560-trajectory development bank:

```text
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

It executes zero Ray, `gotsc`, TSC, controller, plant step, raw, and snapshot.
All R8-family trajectories remain forbidden from expert data, BC, DAgger,
residual RL, and every other learning dataset.

## 2. Immutable predictor and trained causal adapter

Reproduce the final R8R37 exclusion model without refit choices:

```text
causal coordinate                    [visible/history 44, action 18]
coordinate dimension                                             62
coordinate scale floor                                         1e-12
stable Euclidean neighbors                                         64
neighbor weights                                                    1
slopes                                                              0
gain transitions x components                                    5 x 5
gain intercept / ridge                                            0 / 0
gain denominator floor in normalized units                       1e-12
gain projection                                                   [0,1]
```

For every held evaluation, both the local-constant cold predictor and all 25
gains must come only from that fold's complete training trajectories. Pair,
history, source, schedule, formal-outcome, future-row, held-target, and
response-dependent selection remain forbidden.

At each trajectory boundary correction is exact zero. An entire interval is
emitted before any of its targets are read. After that complete interval is
visible, and only then, the next prediction uses:

```text
innovation[c] = actual[current,last,c] - cold[current,last,c]
correction[next,c] = gain[transition,c] * innovation[c]
```

Only one completed interval is retained. Component mixing, innovation
clipping, recursion, decay, gain search, lag search, reset search, and
cross-trajectory state are forbidden. Carry the final R8R37 componentwise
maximum pair/schedule tube without shrinkage.

## 3. Fixed receding-controller construction

Only after source authentication, recreate the unchanged bounded R8R33/R8R34
first-action planner:

```text
candidate actions per decision                                  17
decision steps                              [10,12,14,16,18,22]
beam width                                                       512
measurement recentering                                    required
action applied from a completed solve                    first only
failed or unsupported solve                              forbidden
fallback                                  exact current-target hold
```

Candidate library, stable ties, target cost, tube reserve, termination, and
fallback are frozen from that planner and may not be tuned against R8R37.
Every later search starts from newly visible causal state and the single
gain-scaled last innovation. Planned states never update innovation.

Held whole-pair and whole-schedule outcomes may test a selected first action
only after selection. Current/future held targets may not enter coordinates,
neighbors, gain fit, innovation, ranking, fallback, or ties. Off-policy held
continuations may not be relabeled as consequences of different selected
actions. Counterfactual claims require the authenticated model plus full
carried tube. A violation is an integrity failure, not a controller result.

## 4. Fixed actuator, safety, and support gates

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

Unsupported or failed searches select exact hold and cannot count as
repairs. All six frozen fault injections must select hold and may never
authorize nonzero action.

## 5. Frozen authority and usefulness gates

Evaluate the same 16 baseline contexts and preserve their frozen formal
classification: six pass and ten fail. Planning opens only after complete
R8R37 source PASS and all integrity, safety, and support gates.

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

Center-only repair, later arrival, post-result fallback, and off-policy raw
continuation cannot pass. These are finite offline authority gates, not real
tracking, real MPC, or Gate A.

## 6. Routes and authorization

```text
R8R37 is not the exact independently reproduced PASS
  TRAINING_ONLY_DIAGONAL_GAIN_CONTROLLER_PREFLIGHT_BLOCKED_BY_SOURCE

source, package, causality, forbidden-input, runtime, or dual disagreement
  TRAINING_ONLY_DIAGONAL_GAIN_CONTROLLER_PREFLIGHT_EXECUTION_FAIL_STOP

model binding, tube, support, actuator, safety, or fault-injection failure
  TRAINING_ONLY_DIAGONAL_GAIN_CONTROLLER_PREFLIGHT_SAFETY_FAIL_NO_TSC

safe preflight but frozen authority/usefulness gate fails
  TRAINING_ONLY_DIAGONAL_GAIN_CONTROLLER_PREFLIGHT_AUTHORITY_INSUFFICIENT_NO_TSC

all source, integrity, safety, support, authority, and dual gates pass
  TRAINING_ONLY_DIAGONAL_GAIN_CONTROLLER_PREFLIGHT_PASS_REAL_SENTINEL_DESIGN_REQUIRED
```

A PASS authorizes only a separately frozen fresh finite real-TSC safety
sentinel design. It does not authorize that run, qualify MPC, reach Gate A,
or authorize expert data, BC, DAgger, or RL. A blocked or failed route does
not prove plant unreachability or global controller impossibility.

## 7. Formal and validation contract

```text
slew 1.0/1.1  arrive by 250 ms and hold through 350 ms
slew 0.9      arrive by 270 ms and hold through 370 ms
R/Z tolerance 0.03 m, speed 0.1 m/s, unchanged Ip and arrival streak
```

Before any R8R38 execution require project-venv compilation, focused and
full tests, exact package hashes, empty-directory direct-copy validation,
server preflight, the existing server venv, all declared `bash -n`, and full
server tests. Transfer only direct directory trees without archives. Keep
large evidence on the server and download only compact audits.
