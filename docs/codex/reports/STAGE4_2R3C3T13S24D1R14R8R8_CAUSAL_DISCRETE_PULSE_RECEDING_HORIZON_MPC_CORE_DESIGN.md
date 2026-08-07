# Stage4.2R3c3T13S24D1R14R8R8 causal discrete-pulse receding-horizon MPC core design

Frozen prospectively on 2026-08-07 after the final R8R7 primary/independent
agreement and before any R8R8 implementation, offline candidate result,
controller decision, formal outcome, raw trajectory, or TSC plant advance was
created or inspected.

## 1. Question and scientific boundary

R8R7 qualified, over its finite fresh interaction matrix, the combination of
the fixed static causal observer and the fixed four-step R8R1 action-response
model. It did not run an optimizer or controller: formal tracking was only
`6/16` for its zero-action baselines and `12/32` for its prescribed
multipulse trajectories.

R8R8 asks the next narrow question:

```text
Can a causal four-step controller repeatedly choose and execute one safe,
exact Card15 pulse from the already qualified finite response alphabet, then
replan from the newly observed state, while passing all 16 deterministic core
formal-control cases under the immutable timing contract?
```

This is the first genuine receding-horizon MPC core in this route, but it is
deliberately modest. It is neither a continuous-input optimizer nor a claim
of global optimality. It may use only the four-step model support actually
qualified by R8R7. A PASS is a deterministic-core control qualification only;
it is not Gate A and authorizes only separately frozen continuous-parameter,
noise, disturbance, mismatch, long-hold, and residual-authority stages.

All R8, R8R1, R8R7, and R8R8 trajectories remain forbidden from expert,
BC, DAgger, residual-fitting, and RL datasets.

## 2. Frozen identity and immutable sources

```text
stage       Stage4.2R3c3T13S24D1R14R8R8
identity    causal_four_step_discrete_pulse_receding_horizon_mpc_core_v1
run stem    stage4_2r3c3t13s24d1r14r8r8_causal_discrete_pulse_receding_horizon_mpc_core
new TSC     exactly 16 trajectories, conditional on dual offline acceptance
```

Primary and structurally independent preflights must authenticate the final
R8R7 route, its accepted raw/model audit, and these exact server artifacts:

```text
R8R7 all specifications
  60e956f7297686988a6e52a236e597c3440963058ccdc3a2e22f84bc4ffa08fa
R8R7 baseline specifications
  0a1d9dc14ecfd575594895e8c6444db27179ee1b5c9a700b2f853e62f9155f53
fixed four-step response model
  d2bcca31e135c4faf99a93d64391fdc96bb5de44b8705d177e2219c6c000e84e
response tube
  c31b4d3b84bdc7ab9f399bd3563798989c94e5f373536b42ccb19f8ef06be128
combined observer-response tube
  f5afa50a149ce858187833aade6e5ef91433c42016fc7d70986543deecd74759
R8R7 final stage manifest
  ae89fb2df01cd6758676baa895880e2005a1f8967c62ea4ae671ab61ea771e24
R8R7 final stage state
  04f643e09f414c5d5a305f1a3584450e12e5a39e8d062d454480df3c8d95fe7e
```

The no-action center predictor is the R8R6-selected static observer, with
adaptation disabled:

```text
static observer model
  3ba16449086097a42513987df97c95ec6d6d0d35d572e73992fa5eafdfc15519
static observer tube
  747a6c24f9abed8a4ec6784e4699c7ebe557a049bb11e10ea9a1d5ca0254b8ea
innovation contract (disabled route)
  272c5979f0b806f228e335bbbb8db1f57df623822d8a8ffe3c797ca96b4203f5
```

No R8R8 raw may refit, widen, recenter, select, or adapt a model or tube. A
source mismatch is a source/deployment failure and authorizes zero TSC.

## 3. Fixed deterministic core matrix

The 16 R8R8 specifications are exact scientific clones of the 16 accepted
R8R7 baseline specifications: the same eight physical pairs and both
authenticated restart histories per pair. Each rollout uses a fresh
controller and a fresh TSC process and delegates the exact authenticated
physical source prefix through task step 9.

After task step 9, future R17 execution and all source future actions are
forbidden. The controller receives only the numeric user target and the
causally available physical/action/current history. Pair ID, history member,
prefix class, target ID, delay, slew, partition, source formal outcome, and
matched-source future are evaluator-only fields and may not reach the
controller, observer, response descriptor, candidate selector, or fallback.

The fixed decision task steps are:

```text
[10, 14, 18, 22]
```

Thus the campaign contains 64 online decisions. The unchanged 35/37-step
episode endpoints, 250/270 ms arrival deadlines, and 350/370 ms formal hold
endpoints remain in force.

## 4. Fixed action alphabet and receding-horizon semantics

At every decision, the controller exhaustively evaluates exactly nine
candidates:

```text
zero action
direction 0, sign -1, canonical scale 1.0
direction 0, sign +1, canonical scale 1.0
direction 1, sign -1, canonical scale 1.0
direction 1, sign +1, canonical scale 1.0
direction 2, sign -1, canonical scale 1.0
direction 2, sign +1, canonical scale 1.0
direction 3, sign -1, canonical scale 1.0
direction 3, sign +1, canonical scale 1.0
```

The canonical four-direction matrix SHA-256 remains
`c8cd62c00c1f60b46312927789659657dc8cc35717533193433b0e398c1ec94c`.
Mixed directions, continuous amplitudes, the historical direction-0 scale
1.5 replacement, response-tail extrapolation, and a learned action generator
are forbidden.

For a selected nonzero candidate, the controller issues the exact checked
Card15 pulse at the decision step, returns exactly to the stored pre-issue
center at the next task step, and emits zero action until the next decision.
Only that first pulse/cancellation pair is executed. At the next decision the
entire calculation is repeated from the newly observed causal history; no
previous open-loop plan is retained. A zero selection emits zero throughout
the same four-step interval.

## 5. Frozen causal prediction

At a decision origin, the static observer predicts absolute
`[R,Z,vR,vZ,Ip]` at relative lags 1 through 4 from the actual allowed prefix.
For a nonzero candidate, the fixed R8R1 response head for its direction/sign
and scale 1.0 is added to that center. The zero candidate uses the static
forecast unchanged.

Prior controlled pulses may influence a later decision only because their
already observed physical states, applied actions, and currents are now in
the causal history. No future measurement, future current readback, matched
baseline future, source action, result label, pair/history label, online
innovation, post-result scale change, or oracle correction is allowed.

The zero candidate uses the fixed R8R6 static tube. Each nonzero candidate
uses the fixed R8R7 combined tube. Only lags 1 through 4 are scored; no model
value is manufactured beyond the qualified horizon.

## 6. Frozen robust objective and deterministic selector

The desired physical state is the configured base target plus the numeric
user target offset, with desired velocity zero:

```text
y* = [R_target, Z_target, 0, 0, Ip_target]
```

For candidate `c`, lag `k`, and component `j`, define:

```text
u[c,k,j] = abs(predicted[c,k,j] - y*[j]) + half_width[c,k,j]
e[c,k,j] = u[c,k,j] / scale[j]

scale             = [0.03, 0.03, 0.10, 0.10, 10000]
component weight  = [4,    4,    1,    1,     0.25]
lag weight        = [1, 2, 4, 8]

J[c] = sum_k lag_weight[k]
             * sum_j component_weight[j] * e[c,k,j]^2
```

All constants are frozen here. The controller first removes every nonzero
candidate that cannot be constructed safely and exactly. Among remaining
nonzero candidates it chooses the minimum finite `J`, breaking exact ties by
the listed candidate order. It executes that candidate only when:

```text
J[best_nonzero] <= 0.995 * J[zero]
```

Otherwise it executes zero. Zero wins all ties involving zero. This fixed
0.5% robust-score improvement threshold is not tuned after offline replay or
TSC. There is no trajectory-outcome-based schedule, target-specific knob,
external nonlinear solver, warm start, or post-result candidate change.

## 7. Pure construction, hard safety, and fallback

Candidate enumeration must use a pure, side-effect-free Card15 constructor.
It may not mutate controller state, the active action, a stored center, a
delay queue, or the plant. Only the selected candidate may be committed.

Every nonzero issue and its exact stored-center cancellation retain the
unchanged R8R7 guards:

```text
maximum incremental normalized action L-infinity       0.25
maximum online cancellation incremental L-infinity     0.24
maximum total normalized action absolute value          1.0
maximum current utilization                             0.55
minimum desired/applied current cosine                  0.98
maximum relative off-basis residual                     0.10
exact Card15 representability                           required
exact stored-center cancellation                        required
exact zero target-jump net                              required
exact inherited physical prefix                         required
future R17 execution after task step 9                  forbidden
```

An infeasible nonzero candidate is excluded before selection. If every
nonzero candidate is infeasible, any model value is nonfinite, the model
cannot be authenticated, or candidate evaluation raises, the controller
must select zero without a plant advance caused by the rejected candidate
and log an exact fallback reason. Unit tests must inject every such fault and
prove safe zero fallback. The nominal scientific gate nevertheless requires
all 64 online evaluations to complete without model/evaluator fault; fallback
safety is not used to relabel a broken nominal controller as a PASS.

Any selected issue or cancellation that becomes unsafe or nonrepresentable
at commit time is rejected before the associated plant advance and no later
plant step may occur. That is an execution/safety failure, not a formal plant
or reachability conclusion.

## 8. Mandatory zero-TSC offline acceptance

Before deployment or real TSC, primary and structurally independent programs
must independently authenticate all sources and replay the fixed controller
over only the already consumed R8R7 baseline causal prefixes. They must not
inspect those baselines' future states or formal outcomes while selecting.

Required offline evidence is:

```text
specifications reconstructed and matched                  16/16
causal decision origins reconstructed                     64/64
candidate forecasts and robust scores finite            576/576
primary/independent forecast and score agreement         576/576
primary/independent exact selected candidate agreement     64/64
pure nonzero issue constructions                         512/512
corresponding exact cancellations                        512/512
Card15/action/current/cosine/off-basis guards            512/512
forbidden or future controller inputs                           0
side effects during enumeration                                 0
at least one nonzero offline selection                       true
fault-injected safe-zero fallback cases                  all/all
```

The independent audit may share immutable low-level physical constants but
must not import the primary audit, objective, candidate-selection, or report
implementation. It must rebuild descriptors, predictions, tubes, objective,
ordering, action construction, and verdict from serialized source artifacts.

Any offline mismatch, nonfinite value, side effect, source failure, or gate
failure stops the stage with zero R8R8 TSC. Frozen weights, threshold,
candidate set, model, tube, and action semantics may not be adjusted after an
offline result; a changed proposal requires a new identity and new design.

## 9. Authentic execution and deterministic core gate

Only a dual-audited offline PASS authorizes one 16-trajectory campaign. Every
specification runs once under the frozen package and records, for every
decision, the exact causal feature/descriptor hashes, nine candidate
construction statuses, forecasts, tube choice, scores, deterministic order,
selected action, score improvement, fallback reason, applied Card15 values,
current checks, and exact cancellation evidence.

Primary and independent postprocessing must recompute from raw and snapshots,
not trust `success`, a completion counter, or the controller's own verdict.
The hard execution gates are:

```text
strictly parsed complete raw                              16/16
fresh controller and fresh TSC process                    16/16
exact restart snapshot and physical source prefix         16/16
exact causal controller/action/current trace              16/16
full unchanged 35/37-step horizon                         16/16
finite state/action/current data                          16/16
online decision records                                   64/64
complete nine-candidate evaluations                       64/64
model/evaluator faults                                      0/64
forbidden/future/label inputs                                 0
selected nonzero issues passing every hard guard          all/all
selected nonzero exact stored-center cancellations        all/all
rejected candidates physically applied                         0
post-rejection plant advances                                  0
solver, saturation, runtime, or raw-integrity errors            0
at least one selected nonzero issue                         true
every selected nonzero robust improvement                 >=0.5%
primary/independent numerical and route agreement           true
```

Every trajectory must then pass the unchanged formal contract recomputed from
raw:

```text
slew 1.0: arrive no later than 250 ms; hold through 350 ms
slew 0.9: arrive no later than 270 ms; hold through 370 ms
R/Z tolerance: 30 mm
speed threshold: 0.1 m/s
Ip threshold and arrival streak: unchanged frozen baseline values

required deterministic core formal passes                 16/16
```

R8R7 baseline formal results may be reported only as a fixed diagnostic
comparison. They cannot enter the controller or replace the absolute 16/16
gate. Each miss remains a miss.

## 10. Frozen routes and interpretation

```text
source or dual-offline failure before TSC:
  CAUSAL_DISCRETE_PULSE_MPC_SOURCE_OR_OFFLINE_FAIL_NO_TSC

runtime, restart, integrity, causality, or hard-safety failure:
  CAUSAL_DISCRETE_PULSE_MPC_EXECUTION_FAIL_STOP

complete safe campaign but fewer than 16 formal passes:
  CAUSAL_DISCRETE_PULSE_MPC_CORE_FORMAL_FAIL_REDESIGN_REQUIRED

all frozen execution, independent-audit, and 16/16 formal gates pass:
  CAUSAL_DISCRETE_PULSE_RECEDING_HORIZON_MPC_CORE_PASS_ROBUSTNESS_QUALIFICATION_REQUIRED
```

A formal FAIL is a finite controller-design failure, not a runtime, restart,
reporting, global plant-reachability, or unlimited-MPC conclusion, provided
all corresponding execution/integrity gates passed. An execution failure is
kept separate and cannot be interpreted as control evidence.

Even the PASS route is not Gate A. It authorizes only new, separately
prospectively frozen qualifications for continuous delay/gain/slew,
plant/model mismatch, measurement noise, disturbance recovery, independent
long hold, and residual-authority. No expert data, BC, DAgger, or residual RL
may start until every CURRENT_TASK.md Section 0.1 axis passes and Gate A is
explicitly presented to the user for confirmation.
