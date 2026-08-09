# Stage4.2R3c3T13S24D1R14R8R50 q0-transport bridge whole-pair causal transition-model preflight design

Status: conditionally and prospectively frozen on 2026-08-09 after the R8R49
implementation checkpoint `6fd0610`, but before any R8R49 server offline
construction, Ray, `gotsc`, TSC, controller, plant step, raw trajectory,
state-13/state-14 response, primary raw audit, or independent raw audit was
generated or opened.

## 1. Conditional source gate and scope

R8R50 is authorized only if final primary and independent R8R49 agree exactly
on:

```text
Q0_TO_TRANSPORT_BRIDGE_IDENTIFICATION_COMPLETE_MODEL_PREFLIGHT_REQUIRED
```

The later R8R50 config must bind the exact final R8R49 primary detailed,
primary summary, independent, compact-audit, final-report, stage-state, and
stage-manifest hashes plus the immutable 256-file raw inventory. Any other
R8R49 route permanently blocks this design.

R8R50 runs zero Ray, `gotsc`, TSC, controller, plant advance, or snapshot. It
tests one fixed finite causal response model and one training-only uncertainty
tube. It does not select a controller, optimize tracking, execute MPC, qualify
Gate A, or authorize learning. All R8R49 trajectories remain identification
probes forbidden from expert, BC, DAgger, residual-RL, and other learning data.

## 2. Immutable rows, inputs, and outputs

Authenticate and strictly parse exactly the frozen R8R49 matrix:

```text
8 physical pairs x 2 histories x 16 nonzero fixed candidates = 256 rows
```

No row, context, candidate, direction, amplitude, or response may be excluded.
The candidate coordinate is the exact binary64 four-vector `q` already frozen
by R8R31/R8R49. The model makes no interpolation or extrapolation claim beyond
these 16 candidates and 16 contexts.

For each row, construct at completed state 12 the same causal 44-vector used by
the inherited transport architecture:

```text
last four completed visible R/Z/Ip triples                    12
completed state-12 14-coil current / source current scales   14
(state-12 current - completed task-10 current) / scales       14
previous coordinate q0 / 1.5                                  4
                                                               --
                                                               44
```

Only completed visible state, completed coil-current readback, frozen current
scales, the known q0 previous coordinate, assigned candidate `q`, and task
clock are inputs. Pair/history identity, wire/vessel current, source result,
future state/action, evaluator outcome, another rollout, and formal label are
forbidden model inputs.

The six outputs are the measured physical response relative to the
authenticated same-context q0 reference:

```text
state 13: delta R, delta Z, delta Ip
state 14: delta R, delta Z, delta Ip
```

R8R50 must recompute these outputs from immutable raw rather than trust R8R49
derived response fields.

## 3. Fixed model family

Whiten the 44 causal features using mean and componentwise standard deviation
computed from the current training fold only. A component with training
standard deviation below `1e-12` uses scale one. Scale `q` by the fixed value
1.5. The predictor has no intercept and no feature-only term:

```text
x = [q / 1.5, vec(whitened_feature outer-product (q / 1.5))]
dimension = 4 + 44*4 = 180
```

Fit all six normalized outputs jointly with a fixed ridge penalty `1e-4`.
Normalize R and Z by 0.03 m and Ip by 10,000 A independently at each response
state. The missing intercept is intentional: the model is exactly zero at q0
by construction. No nonlinear kernel, neural network, ensemble choice,
feature selection, hyperparameter search, clipping, outcome-dependent
regularization, context label, or post-result route change is allowed.

## 4. Frozen whole-pair validation and tube

Use exactly eight outer folds. Each fold holds both histories and all 16
candidates of one physical pair (32 rows). Train on the other seven physical
pairs (224 rows).

For each outer fold, construct its tube only from the 224 outer-training rows:

1. run seven nested whole-pair fits inside the outer-training set;
2. collect the resulting out-of-pair residual for every outer-training row;
3. for each of the six outputs take the larger of the physical point-error
   floor and `1.25 * maximum absolute nested residual`;
4. refit the fixed ridge model on all seven outer-training pairs;
5. predict the untouched outer pair and test it against that frozen tube.

The physical point-error floors are:

```text
[0.015 m, 0.015 m, 3000 A] at state 13
[0.015 m, 0.015 m, 3000 A] at state 14
```

The tube half-width caps are:

```text
[0.025 m, 0.025 m, 5000 A] at state 13
[0.025 m, 0.025 m, 5000 A] at state 14
```

Every normalization, whitening statistic, coefficient, and tube value used
for an outer row must therefore exclude its entire physical pair. Primary and
independent implementations must reproduce all folds, coefficients,
predictions, residuals, tubes, counts, digests, and route within absolute
tolerance `1e-12`.

## 5. Frozen gates and routes

PASS requires:

```text
strict source/raw/spec/restart/causality authentication       256/256
finite causal-feature and response rows                       256/256
outer whole-pair prediction coverage                          256/256
absolute point error within the frozen physical floors        256/256
training-only nested-tube containment                         256/256
all six outer-fold tube half-widths within frozen caps             8/8
forbidden model-input count                                        0
source or row exclusion count                                      0
primary/independent numerical and discrete agreement              exact
new TSC/raw/snapshot/controller/plant/model-selection count            0
```

Routes are frozen as:

```text
R8R49 route/hash/raw identity fails
  Q0_TRANSPORT_BRIDGE_MODEL_PREFLIGHT_BLOCKED_BY_SOURCE

runtime, strict parse, causality, fold, or evidence-integrity failure
  Q0_TRANSPORT_BRIDGE_MODEL_PREFLIGHT_EXECUTION_FAIL_STOP

any point, containment, or tube-cap gate fails
  Q0_TRANSPORT_BRIDGE_WHOLE_PAIR_CAUSAL_MODEL_INSUFFICIENT_NONLINEAR_REDESIGN_REQUIRED

all gates pass
  Q0_TRANSPORT_BRIDGE_WHOLE_PAIR_CAUSAL_MODEL_COMPLETE_CONTROLLER_PREFLIGHT_REQUIRED
```

A PASS certifies only this finite state-12 q0-to-first-transport response
model and training-only tube. It authorizes only a separately frozen zero-TSC
controller/MPC preflight. It does not authorize a real controller or relax
the formal timing, safety, restart, causality, current, or Card15 contracts.

## 6. Formal and qualification boundary

The immutable formal contract remains arrival by 250 ms and hold through
350 ms for slew 1.0/1.1, arrival by 270 ms and hold through 370 ms for slew
0.9, with 30 mm R/Z, 0.1 m/s speed, 10 kA Ip, and the three-sample arrival
streak. R8R50 does not evaluate or weaken that contract. It is not a
long-hold, disturbance, noise, continuous-parameter, restart-robustness,
closed-loop control, real-MPC, or Gate A result.
