# Stage4.2R3c3T13S24D1R14R8R51R2 reduced q0-transport bridge whole-pair causal model preflight design

Status: conditionally and prospectively frozen on 2026-08-09 with R8R51R1,
before any R8R51R1 implementation, offline construction, controller, Ray,
`gotsc`, TSC, plant step, raw trajectory, candidate response, primary audit,
or independent audit was generated or opened.

## 1. Conditional source gate

R8R51R2 is authorized only if final primary and independent R8R51R1 agree
exactly on:

```text
REDUCED_Q0_TRANSPORT_BRIDGE_Q0_GATE_INTEGRATION_COMPLETE_R51R2_MODEL_PREFLIGHT_REQUIRED
```

It must bind the final R8R51R1 primary detailed/summary, independent audit,
compact audit, final report, state, manifest, exact 208-file raw inventory,
13 candidate identities, and q0 prefix/event digests. Any other route
permanently blocks R8R51R2.

R8R51R2 supersedes only the source identity of the blocked R8R52 design. Its
rows, inputs, outputs, folds, model, hyperparameters, tubes, caps, gates, and
scientific scope are unchanged. It runs zero Ray, `gotsc`, TSC, controller,
plant advance, snapshot, or new raw.

## 2. Immutable rows, causal inputs, and outputs

Strictly parse all:

```text
8 physical pairs x 2 histories x 13 candidates = 208 rows
```

No row, context, history, candidate, direction, amplitude, or response may be
excluded. At completed state 12 construct the frozen 44-vector:

```text
last four completed visible R/Z/Ip triples                    12
completed state-12 14-coil current / source current scales   14
(state-12 current - completed task-10 current) / scales       14
previous coordinate q0 / 1.5                                  4
                                                               --
                                                               44
```

Inputs may contain only completed visible states/readbacks, frozen scales,
known q0 previous coordinate, assigned candidate q, and task clock.
Pair/history/partition identity, wire/vessel current, source outcome, future
state/action, evaluator outcome, another rollout, and formal labels are
forbidden.

Recompute six outputs directly from immutable R8R51R1 raw relative to the
authenticated same-context q0 reference:

```text
state 13: delta R, delta Z, delta Ip
state 14: delta R, delta Z, delta Ip
```

## 3. Fixed model family

Within each training fold, whiten the 44 causal features with training-only
mean and componentwise standard deviation; a standard deviation below
`1e-12` uses scale one. Scale q by fixed 1.5. Fit no intercept and no
feature-only term:

```text
x = [q / 1.5, vec(whitened_feature outer-product (q / 1.5))]
dimension = 4 + 44*4 = 180
```

Fit all six normalized outputs jointly with fixed ridge penalty `1e-4`.
Normalize R/Z by 0.03 m and Ip by 10,000 A at each state. Zero q predicts
exactly zero. No kernel, neural network, ensemble, feature selection,
hyperparameter search, clipping, context label, or post-result change is
allowed.

## 4. Frozen whole-pair validation and tube

Use exactly eight outer folds. Each holds both histories and all 13
candidates of one physical pair: 26 untouched rows. Train on the other seven
pairs: 182 rows.

For each outer fold:

1. run seven nested whole-pair fits, each using six pairs/156 rows and
   predicting the seventh training pair/26 rows;
2. collect one out-of-pair residual for every outer-training row;
3. take per output the larger of its physical point-error floor and
   `1.25 * maximum absolute nested residual`;
4. refit the fixed ridge model on all 182 outer-training rows;
5. predict the untouched outer pair against that frozen training-only tube.

Point-error floors:

```text
[0.015 m, 0.015 m, 3000 A] at state 13
[0.015 m, 0.015 m, 3000 A] at state 14
```

Tube half-width caps:

```text
[0.025 m, 0.025 m, 5000 A] at state 13
[0.025 m, 0.025 m, 5000 A] at state 14
```

Primary and structurally independent implementations must reproduce folds,
coefficients, predictions, residuals, tubes, counts, digests, and route
within absolute tolerance `1e-12`.

## 5. Gates and routes

PASS requires:

```text
strict R8R51R1 source/raw/spec/restart/causality authentication 208/208
finite causal-feature and response rows                          208/208
outer whole-pair prediction coverage                             208/208
absolute point error within frozen physical floors               208/208
training-only nested-tube containment                            208/208
all six tube widths within caps in every outer fold                  8/8
forbidden model-input count                                           0
source/row exclusion count                                            0
primary/independent numerical and discrete agreement                 exact
new TSC/raw/snapshot/controller/plant/model-selection count               0
```

```text
R8R51R1 route/hash/raw identity fails
  REDUCED_Q0_TRANSPORT_BRIDGE_R51R2_MODEL_PREFLIGHT_BLOCKED_BY_SOURCE

runtime, parse, causality, fold, or evidence-integrity failure
  REDUCED_Q0_TRANSPORT_BRIDGE_R51R2_MODEL_PREFLIGHT_EXECUTION_FAIL_STOP

any point, containment, or tube-cap gate fails
  REDUCED_Q0_TRANSPORT_BRIDGE_R51R2_WHOLE_PAIR_CAUSAL_MODEL_INSUFFICIENT_NONLINEAR_REDESIGN_REQUIRED

all gates pass
  REDUCED_Q0_TRANSPORT_BRIDGE_R51R2_WHOLE_PAIR_CAUSAL_MODEL_COMPLETE_CONTROLLER_PREFLIGHT_REQUIRED
```

A PASS certifies only this finite state-12 q0-to-first-transport response
model and its training-only tube. It may authorize only a separately frozen
zero-new-TSC controller/MPC preflight, never direct real control.

## 6. Formal and learning boundary

The immutable 250/270 ms arrival and 350/370 ms hold endpoints, 30 mm R/Z,
0.1 m/s speed, unchanged 10 kA Ip threshold, and frozen three-sample arrival
streak remain unchanged. R8R51R2 does not evaluate them. It is not long-hold,
noise, disturbance, continuous-parameter, restart-robustness, closed-loop
control, real MPC, or Gate A evidence. All R8R51/R8R51R1 data remain
forbidden from learning, and Gate A plus Gate B remain blocked.
