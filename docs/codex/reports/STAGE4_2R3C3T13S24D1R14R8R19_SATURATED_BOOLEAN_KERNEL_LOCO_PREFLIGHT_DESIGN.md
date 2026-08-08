# Stage4.2R3c3T13S24D1R14R8R19 saturated Boolean kernel LOCO design

Frozen prospectively on 2026-08-08 Asia/Shanghai after final R8R18 evidence,
report, and route were sealed, but before R8R19 implementation, response fit,
LOCO output, missing-code prediction, formal result, or route. Although the
R8R18 failed-row identities are now part of the final forensic record, no
identity, residual value, response state, or formal metric selected this
model or any hyperparameter. Only the finite 16-code Boolean geometry was
used below. R8R19 is zero-new-TSC. Chat summaries are not evidence.

## 1. Scientific question and boundary

R8R18's fixed second-order hierarchical ridge passed `157/160` prospective
LOCO rows and exact formal classification `160/160`, but exceeded the
unchanged minimum-formal-margin error cap. It is immutable.

R8R19 asks:

```text
Does the saturated finite Boolean-cube kernel, with an affine null space and
one outcome-independent common penalty on every nonlinear Walsh component,
predict each of the ten measured codes from the other nine within every
unchanged physical/formal gate; and if so, does its uncertainty-discounted
completion of the six unmeasured codes predict a repair worth a fresh
physical sentinel?
```

This is a finite nonparametric lookup prior on the four-slot Boolean cube,
implemented through its complete Walsh basis. LOCO is retrospective model
validation, not an independent physical holdout. The six missing physical
outcomes remain closed. R8R19 runs no Ray, `gotsc`, TSC, controller, plant
step, raw generation, or snapshot and cannot establish MPC, physical
authority, Gate A, or plant reachability.

## 2. Immutable sources

Primary and structurally independent implementations must authenticate and
strictly parse, without modification or rerun:

1. the same final R8R7 baselines, R8R12 `UUUU`, R8R14 `VVVV`, and all final
   R8R15 measured-code trajectories;
2. final R8R16 and route
   `TEMPORAL_AFFINE_SEQUENCE_MODEL_INADEQUATE_NONLINEAR_SEQUENCE_REDESIGN_REQUIRED`;
3. final R8R17 and route
   `ADJACENT_SWITCH_INTERACTION_MODEL_INADEQUATE_HIGHER_ORDER_REDESIGN_REQUIRED`;
4. final R8R18 and route
   `SECOND_ORDER_BOOLEAN_RIDGE_MODEL_INADEQUATE_NONPARAMETRIC_SEQUENCE_REDESIGN_REQUIRED`;
5. the exact formal evaluator and immutable timing contract.

The required final R8R18 hashes are:

```text
primary detailed      d3b71fcf60a014be1f677fb1b03a5c549c467ecbf5a9fadf5f9e350fbe323fcd
primary summary       d67f2080c2256efdd6be9848d61bc88e922adaeb171f15615e7c61085e6f0e82
independent           b53cb99382b551468943148338a0c23f5b71d60761b238fe03f49af7cfd5166d
final report          cfc5c381011ffdadee311acd98478ce9a386b2173c12d2a96ae6a5c274d9bbca
R8R15 authentication  88ed50a9fbe6d303151c264309b919dd0e906be5818513626868791084e9f362
R8R16 authentication  1938c1e6772e704b37e20f26861bddd8b15c706450de42700e11496270162812
R8R17 authentication  9dec20a5e5ed802896c681db3ac4845cc578b70a6a15afb0e31c37e5e29da42d
stage manifest        50b9842de89e90849669979a19a84ba8451f6bb8fe2b590390747d2ce96ef356
stage state           660efeae771da43a966532137ba45a0344a5c95b81905e7cefc8a94ac0bb08a5
final server evidence 9d9fc1adfa0e61d9de31586df3f4e63d3b27e6e7fc87496f8acf133530cfc826
```

R8R18 must report source authentication PASS, `157/160`, exact formal
classification `160/160`, zero new raw, and zero real TSC. No R8R16/R8R17/
R8R18 coefficient or prediction is a model input. Any authentication mismatch
stops before fitting.

## 3. Frozen codes and saturated Walsh feature map

Symbols, decision states, measured order, and missing order remain:

```text
U = +1; V = -1
decision task steps = [10,14,18,22]

measured
  UUUU VVVV UVVV UUVV UUUV VUUU VVUU VVVU UVUV VUVU

never executed
  UVUU UUVU UVVU VUUV VVUV VUVV
```

For `q=(q10,q14,q18,q22)`, the exact 16-feature order is:

```text
degree 0
  1
degree 1
  q10 q14 q18 q22
degree 2
  q10*q14 q10*q18 q10*q22 q14*q18 q14*q22 q18*q22
degree 3
  q10*q14*q18 q10*q14*q22 q10*q18*q22 q14*q18*q22
degree 4
  q10*q14*q18*q22
```

This is the complete orthogonal Walsh feature map of the finite four-bit
cube and therefore a saturated finite kernel/lookup prior. No feature may be
selected, deleted, rescaled, or re-ordered after response output. No neural
feature, state-dependent bandwidth, context hyperparameter, nearest-neighbor
switch, row exclusion, or post-result ensemble is allowed.

## 4. Outcome-independent nonlinear prior

The intercept and four degree-one coefficients are unpenalized. Every one of
the eleven degree-two-through-four coefficients receives the same penalty:

```text
P = diag([0,0,0,0,0,10,10,10,10,10,10,10,10,10,10,10])
lambda_nonlinear = 10.0
```

Before any R8R19 response computation, `10.0` was fixed as the first member
of the closed ascending code-only grid `[0.1,0.3,1.0,3.0,10.0]` satisfying:

```text
maximum LOCO normal condition           <= 64
maximum LOCO prediction-weight L2       <= 1.25
```

The grid is closed and alternatives will not be evaluated against response
outcomes. For training design `X` and response `Y`, solve only:

```text
beta = argmin ||X beta - Y||_2^2 + beta^T P beta
```

The primary solve uses SVD on `[X;sqrt(P)]`. The independent solve forms
`X^T X+P` and uses direct linear solve. Neither may import the other's feature,
fit, prediction, formal-summary, or verdict implementation.

## 5. Frozen code-only geometry and stability gates

The ten-code saturated matrix has raw rank 10. Every nine-code LOCO matrix
has raw rank 9 and affine rank 5. The full cube has rank 16 and condition
`1.0000000000000009`; every regularized augmented LOCO system has rank 16.

Exact frozen caps and code-only references are:

```text
quantity                                      cap       reference maximum
LOCO normal condition                       64.0       48.08794663585858
LOCO prediction-weight L2                    1.25       1.2247448713915867
LOCO absolute prediction weight              1.01       0.9999999999999973
full-fit normal condition                    28.0       27.812808994561326
missing prediction-weight L2                 1.30       1.2649110640673527
missing absolute prediction weight           0.61       0.6000000000000005
full-cube condition                           1.01       1.0000000000000009
```

Primary and independent geometry/weights must agree within absolute `1e-12`
and relative `1e-10`. A code-only gate failure is an integrity/design failure,
not a response result.

## 6. Response construction and LOCO gate

For each of 16 contexts and each measured code, authenticate the shared
physical prefix through state 10 and construct the unchanged R/Z/Ip response
relative to its exact matched baseline from state 10 through the source
horizon. No resampling, shift, smoothing, clipping, horizon change, deadline
change, component substitution, or directly fitted velocity is allowed.

For each held code in fixed measured order, fit the other nine codes within
each context and predict the held code. Exactly `10*16=160` LOCO trajectories
must all pass:

```text
maximum absolute R error                         <= 0.003 m
maximum absolute Z error                         <= 0.003 m
maximum absolute Ip error                       <= 1000 A
maximum scaled point error                         <= 0.10
unchanged formal pass/fail classification              exact
absolute minimum-signed-margin error                <= 0.05
```

Response scales remain `[0.03 m,0.03 m,10000 A]`. The tube is exactly twice
the componentwise maximum absolute LOCO residual by relative state and must
remain within `0.01 m / 0.01 m / 3000 A`. The formal buffer is exactly twice
the maximum LOCO minimum-margin error. No fold or context may be excluded.

## 7. Conditional full fit and missing-code authority

Only after all source, geometry, stability, `160/160` calibration, exact
formal classification, tube, and independent gates pass may the same model
fit all ten measured codes and predict exactly 96 missing-code trajectories.

For every prediction:

```text
robust_lower_margin = predicted_minimum_signed_margin
                      - 2 * maximum LOCO minimum-margin error
```

A missing code is eligible only if its ordinary formal result passes and the
robust lower margin is strictly positive. Select the largest robust lower
margin per context, with ties broken by fixed missing-code order. The exact
baseline remains the do-nothing-safe evaluator fallback.

Authority requires at least `1/10` failed-baseline robust repairs, robust
oracle at least `7/16`, strict improvement over baseline `6/16`, and exact
primary/independent prediction, ranking, metric, and route agreement.
Predicted repairs are authorization evidence only, never real control or
physical authority.

## 8. Frozen routes

```text
source, geometry, stability, formal lineage, or independent disagreement:
  SATURATED_BOOLEAN_KERNEL_SOURCE_OR_INTEGRITY_FAIL_NO_TSC

source passes but any LOCO calibration or tube gate fails:
  SATURATED_BOOLEAN_KERNEL_MODEL_INADEQUATE_DIRECT_CUBE_COMPLETION_REDESIGN_REQUIRED

model passes but robust missing-code authority fails:
  SATURATED_BOOLEAN_KERNEL_AUTHORITY_INSUFFICIENT_CONTINUOUS_MULTIDIRECTION_REDESIGN_REQUIRED

all model and robust authority gates pass:
  SATURATED_BOOLEAN_KERNEL_COMPLETION_PASS_FRESH_MISSING_SEQUENCE_SENTINEL_REQUIRED
```

A model failure may authorize only a separately frozen design for direct
finite-cube physical completion; it does not authorize an outcome-tuned
replacement under R8R19. A full PASS authorizes only a separately frozen
finite real-TSC missing-sequence sentinel with safety-before-qualification,
complete dual raw authentication, and outcomes closed until all authorized
raw pass. R8R19 never authorizes direct TSC.

## 9. Safety, timing, and learning prohibition

Context labels are offline alignment keys only and forbidden future
controller inputs. No future state/action, hidden wire state, formal label,
missing-code outcome, or fabricated current path may enter the model.

The 250/270 ms deadlines, 350/370 ms endpoints, 30 mm R/Z tolerance,
0.1 m/s speed threshold, Ip threshold, and arrival streak remain unchanged.
Any future physical stage retains authentic restart, visible-state causality,
Card15/action/current/saturation, safe stop, independent raw audit, no
archives, and existing-environment-only execution.

All R8-family trajectories remain probe/control-development evidence and are
forbidden from expert, BC, DAgger, and RL data. R8R19 is not MPC or Gate A.
