# Stage4.2R3c3T13S24D1R14R8R36 causal last-innovation local-constant receding-controller preflight design

Status: prospectively frozen after the R8R35 primary and independent
processes ended with all stdout, stderr, wrapper exit codes, state, summaries,
models, predictions, metrics, gates, and routes still unopened. No R8R35
result informed this design.

This is a conditional design only. It may execute if and only if the final
R8R35 evidence has exact primary/independent agreement and route
`CAUSAL_LAST_INNOVATION_LOCAL_CONSTANT_PASS_CONTROLLER_PREFLIGHT_DESIGN_REQUIRED`.
Any other source route blocks R8R36 before construction or computation.

## 1. Frozen source and scientific boundary

R8R36 must authenticate the exact final R8R35 primary detailed result,
summary, model, independent audit, compact audit, final report, state, and
manifest. Their hashes may be transcribed after R8R35 is opened, but no
controller, model, gate, candidate, or route in this document may then
change.

R8R36 may consume only the same immutable 560-trajectory development bank:

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

It runs zero Ray, `gotsc`, TSC, controller, plant step, raw, and snapshot.
All R8-family trajectories remain forbidden from expert data, BC, DAgger,
residual RL, or any other learning dataset.

## 2. Immutable predictor and causal adapter

Use the R8R35 model byte-for-byte in semantics:

```text
causal coordinate                    [visible/history 44, action 18]
coordinate dimension                                             62
coordinate scale floor                                         1e-12
neighbors                                                         64
weights                                                           1
slopes                                                             0
response-dependent selection                               forbidden
```

At each trajectory start, correction is exact zero. Every interval is
predicted before reading any target in that interval. Only after the complete
interval is physically visible may the next decision use:

```text
correction[next] = actual[current,last] - cold[current,last]
```

Gain is one, memory is one completed interval, and component mixing,
clipping, decay, lag search, gain search, reset search, and cross-trajectory
state are forbidden. The R8R35 passed pair/schedule tube is carried without
refit or shrinkage and the controller tube is the componentwise maximum of
the passed pair and schedule tubes.

## 3. Fixed receding-controller construction

Only after source authentication, recreate the unchanged bounded R8R33/R8R34
controller search:

```text
candidate actions per decision                                  17
decision steps                              [10,12,14,16,18,22]
beam width                                                       512
measurement recentering                                    required
action applied from a completed solve                    first only
failed or unsupported solve                              forbidden
fallback                                  exact current-target hold
```

The candidate library, stable tie order, target cost, tube reserve,
termination, and fallback must be copied from the previously frozen planner;
they may not be tuned against R8R35 predictions. At every later decision,
the search is rebuilt from the newly visible causal state and the single
R8R35 last-innovation correction. A planned future state is never treated as
a measurement and never updates innovation.

The offline preflight must keep policy evaluation separated from evidence:

- held whole-pair and whole-schedule outcomes may test the fixed first-action
  selector only after their action is selected;
- a current or future held target may not enter coordinate construction,
  neighbor choice, innovation, candidate ranking, fallback, or tie breaking;
- an off-policy held continuation may not be relabeled as the consequence of
  a different selected action;
- every counterfactual claim must come from the authenticated fixed model and
  full carried tube, not from future raw rows.

Any violation is an integrity failure, not a controller result.

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

Unsupported or failed searches select the exact hold fallback and cannot be
counted as repairs. All six frozen fault injections must select hold and must
never authorize a nonzero action.

## 5. Fixed authority and usefulness gates

Evaluate the same 16 baseline controller contexts and preserve their frozen
formal classification: six passes and ten failures. Opening planning requires
complete R8R35 source PASS and all R8R36 integrity/safety/support gates.

The preflight passes only if all hold simultaneously:

```text
safe searches                                                16/16
predicted repairs among ten failed baselines                 >=1/10
predicted regressions among six passing baselines                0
fallback-plus-plan optimistic oracle                         >=7/16
nonzero safe first action count                                  >=1
fault-injection hold selections                                6/6
primary/independent discrete selections                       exact
maximum scaled primary/independent numeric difference         1e-9
```

Prediction uses the full carried tube. A center-only repair, a later arrival
deadline, or an off-policy raw continuation cannot pass. These are offline
finite authority gates, not real tracking or Gate A.

## 6. Routes and authorization

```text
R8R35 source is not the exact independently reproduced PASS
  CAUSAL_LAST_INNOVATION_CONTROLLER_PREFLIGHT_BLOCKED_BY_SOURCE

source, package, causality, forbidden-input, runtime, or dual disagreement
  CAUSAL_LAST_INNOVATION_CONTROLLER_PREFLIGHT_EXECUTION_FAIL_STOP

model binding, tube, support, actuator, safety, or fault-injection failure
  CAUSAL_LAST_INNOVATION_CONTROLLER_PREFLIGHT_SAFETY_FAIL_NO_TSC

safe preflight but frozen authority/usefulness gate fails
  CAUSAL_LAST_INNOVATION_CONTROLLER_PREFLIGHT_AUTHORITY_INSUFFICIENT_NO_TSC

all source, integrity, safety, support, authority, and dual gates pass
  CAUSAL_LAST_INNOVATION_CONTROLLER_PREFLIGHT_PASS_REAL_SENTINEL_DESIGN_REQUIRED
```

A PASS authorizes only design of a separate fresh finite real-TSC safety
sentinel. It does not authorize that sentinel automatically, does not qualify
MPC, does not reach Gate A, and does not authorize expert data, BC, DAgger,
or RL. A blocked or failed route does not prove plant unreachability or global
controller impossibility.

## 7. Formal and validation contract

Formal timing remains unchanged:

```text
slew 1.0/1.1  arrive by 250 ms and hold through 350 ms
slew 0.9      arrive by 270 ms and hold through 370 ms
R/Z tolerance 0.03 m, speed 0.1 m/s, unchanged Ip and arrival streak
```

Before any R8R36 execution, require project-venv compilation, focused and
full tests, exact package hashes, empty-directory direct-copy validation,
server preflight, the existing server venv, all declared `bash -n`, and full
server tests. Transfer only direct directory trees without archives. Keep
large evidence on the server and download only compact audits.
