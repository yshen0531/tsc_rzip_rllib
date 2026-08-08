# Stage4.2R3c3T13S24D1R14R8R18 second-order Boolean ridge LOCO design

Frozen prospectively on 2026-08-08 Asia/Shanghai after sealing the aggregate
R8R17 result, but before inspecting any R8R17 failed code, context, state,
residual row, or detailed calibration output; before R8R18 implementation,
fit, calibration metric, missing-code prediction, ranking, output, or route.
R8R18 is zero-new-TSC. Chat summaries are not evidence.

## 1. Scientific question and boundary

R8R16's affine model passed `63/64` held rows. R8R17's single adjacent-
persistence interaction passed only `61/64`. Both preserved exact formal
classification, small point/component errors, and valid tubes, but failed the
unchanged minimum-formal-margin error cap. Both identities are immutable.

Six development codes cannot identify more than six response coefficients
without an explicit prior. R8R18 therefore replaces the old one-shot 6/4
split with a prospectively fixed leave-one-code-out (LOCO) audit over all ten
already measured codes. It asks:

```text
Does a complete second-order Boolean response model, with affine terms
unpenalized and all six pair interactions subject to one outcome-independent
ridge prior, predict every measured code from the other nine within the
unchanged physical and formal caps; and if so, does its uncertainty-
discounted six-code completion predict a repair worth a fresh sentinel?
```

LOCO is retrospective model validation, not an independent physical holdout.
The six missing physical outcomes remain unobserved. R8R18 runs no Ray,
`gotsc`, TSC, controller, plant step, raw generation, or snapshot and cannot
establish MPC, physical authority, Gate A, or plant reachability.

## 2. Immutable sources

Primary and structurally independent implementations must authenticate and
strictly parse, without modification or rerun:

1. the same final R8R7 baselines, R8R12 `UUUU`, R8R14 `VVVV`, and all final
   R8R15 measured-code evidence;
2. the complete final R8R16 exact seven-file server output and
   route `TEMPORAL_AFFINE_SEQUENCE_MODEL_INADEQUATE_NONLINEAR_SEQUENCE_REDESIGN_REQUIRED`;
3. the complete final R8R17 eight-file server output and route
   `ADJACENT_SWITCH_INTERACTION_MODEL_INADEQUATE_HIGHER_ORDER_REDESIGN_REQUIRED`;
4. the exact formal evaluator and immutable timing contract.

The required R8R17 hashes are:

```text
primary detailed      b57f2afc2009e4f28ea6b90cf8034422356f6c1275c0f6a916269a0a94c49020
primary summary       da1c108b7b800c0c8ab4bc9be5325ad3445ac62f799f28ecf5e59dfec30719b8
independent           2a5e8d30db3707ccd764f4d281b32faff2b111bc4c836fc6f269e06b4264745a
final report          f87fba9b71bfebc95a8d1115c74f5aae6190b7af1e0fcc48558a04ab83356dce
R8R15 authentication  88ed50a9fbe6d303151c264309b919dd0e906be5818513626868791084e9f362
R8R16 authentication  1938c1e6772e704b37e20f26861bddd8b15c706450de42700e11496270162812
stage manifest        e0e850c3d19f945c7f53cfcf9c491a5367186d2d46b01cf45213cc4febaf4440
stage state           6b16d1ada9315276284303c52edd60a1ea5f32d0ce33fb73623d45dec4e56b47
```

R8R17 must report `61/64`, zero new raw, and zero real TSC. No coefficient,
prediction, failed-row identity, or residual from R8R16/R8R17 is an R8R18
input. Any authentication mismatch stops before fitting.

## 3. Frozen codes and full second-order feature family

Symbols and decision steps remain:

```text
U = canonical direction 2, sign +1, scale 1.0
V = canonical direction 1, sign -1, scale 1.0
decision task steps = [10,14,18,22]
```

The ordered measured and missing sets are fixed:

```text
measured
  UUUU VVVV UVVV UUVV UUUV VUUU VVUU VVVU UVUV VUVU

never executed
  UVUU UUVU UVVU VUUV VVUV VUVV
```

For U=`+1`, V=`-1`, the exact 11-feature row is:

```text
x(q) = [
  1,
  q10, q14, q18, q22,
  q10*q14, q10*q18, q10*q22,
  q14*q18, q14*q22, q18*q22
]
```

No triple or quadruple term, kernel, neural feature, code-specific offset,
state-dependent hyperparameter, feature selection, or post-result model
ensemble is allowed.

## 4. Outcome-independent hierarchical ridge prior

Affine coefficients are unpenalized. The six pair-interaction coefficients
all receive the identical penalty:

```text
P = diag([0,0,0,0,0,10,10,10,10,10,10])
lambda_pair = 10.0
```

Before any trajectory outcome was inspected, `10.0` was fixed as the first
member of the ascending code-only grid
`[0.01,0.03,0.1,0.3,1.0,3.0,10.0]` satisfying both:

```text
maximum LOCO augmented-normal condition <= 32
maximum LOCO prediction-weight L2 norm  <= 1.30
```

The grid is now closed. R8R18 does not search, report alternatives, or select
lambda from response errors.

For training design `X` and response `Y`, solve only:

```text
beta = argmin ||X beta - Y||_2^2 + beta^T P beta
```

The primary solve must use SVD on the augmented system
`[X; sqrt(P)]`; the independent path must form `X^T X + P` and use a direct
linear solve. Neither may import the other's feature, fit, prediction,
formal-summary, or verdict implementation.

## 5. Frozen code-only geometry and stability gates

The measured second-order matrix has rank 9; the full 16-code cube has rank
11 and condition `1.0000000000000007`. Every nine-code LOCO fold retains
affine rank 5 and raw feature rank 8 or 9. With the frozen penalty, every
augmented system must have rank 11.

Exact frozen stability caps are:

```text
maximum LOCO normal condition            <= 32.0
maximum LOCO prediction-weight L2 norm   <= 1.30
maximum LOCO absolute prediction weight  <= 1.01
full-fit normal condition                 <= 11.10
maximum missing prediction-weight L2     <= 1.30
maximum missing absolute weight           <= 0.67
```

Code-only reference maxima are `31.864801866585715`,
`1.2644229640823352`, `0.9999999999999976`, `11.096194077712552`,
`1.273908766556156`, and `0.6585365853658539`. Primary and independent
geometry/weights must agree within absolute `1e-12` and relative `1e-10`.

## 6. Response construction and LOCO calibration

For each of 16 contexts and each measured code, authenticate the shared
physical prefix through state 10 and construct for the unchanged state-10 to
35/37 horizon:

```text
d_s(t) = [R_s(t),Z_s(t),Ip_s(t)]
         - [R_baseline(t),Z_baseline(t),Ip_baseline(t)]
```

No resampling, shift, smoothing, clipping, shortened horizon, later arrival
deadline, component substitution, or directly fitted velocity is allowed.

For each held code in the fixed measured order, fit the other nine measured
codes independently within each context and predict the held code. This
produces exactly:

```text
10 held codes * 16 contexts = 160 LOCO trajectory predictions
```

Every one of 160 must satisfy the unchanged R8R16/R8R17 gates:

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
the maximum LOCO minimum-margin error. No fold may be excluded and no cap may
be changed after output.

## 7. Conditional full fit and missing-code completion

Only after all source, geometry, stability, `160/160` calibration, formal,
tube, and independent gates pass may the same model fit all ten measured
codes and predict the six missing codes in all 16 contexts, exactly 96
trajectories.

For every missing prediction:

```text
robust_lower_margin = predicted_minimum_signed_margin
                      - 2 * maximum LOCO minimum-margin error
```

A row is robustly eligible only if its ordinary formal result passes and the
robust lower margin is strictly positive. Select the largest robust lower
margin per context, tie-breaking by fixed missing-code order. The exact R8R7
baseline is always retained as the do-nothing-safe evaluator fallback.

Authority requires at least `1/10` failed-baseline robust repairs, robust
oracle at least `7/16`, strict improvement over baseline `6/16`, and exact
primary/independent prediction, ranking, metric, and route agreement.

Predicted repairs are authorization evidence only, never real control or
physical authority.

## 8. Frozen routes

```text
source, geometry, stability, formal lineage, or independent disagreement:
  SECOND_ORDER_BOOLEAN_RIDGE_SOURCE_OR_INTEGRITY_FAIL_NO_TSC

source passes but any LOCO calibration or tube gate fails:
  SECOND_ORDER_BOOLEAN_RIDGE_MODEL_INADEQUATE_NONPARAMETRIC_SEQUENCE_REDESIGN_REQUIRED

model passes but robust missing-code authority fails:
  SECOND_ORDER_BOOLEAN_RIDGE_AUTHORITY_INSUFFICIENT_CONTINUOUS_MULTIDIRECTION_REDESIGN_REQUIRED

all model and robust authority gates pass:
  SECOND_ORDER_BOOLEAN_RIDGE_COMPLETION_PASS_FRESH_MISSING_SEQUENCE_SENTINEL_REQUIRED
```

A PASS authorizes only a separately frozen finite real-TSC sentinel over the
pre-ranked missing codes, with safety-before-qualification, complete dual raw
authentication, and formal outcomes closed until all authorized raw pass.
R8R18 never authorizes direct TSC.

## 9. Safety, causality, and learning prohibition

Context labels are offline alignment keys only and forbidden future
controller inputs. No future state/action, hidden wire state, formal label,
missing-code outcome, or fabricated current path may enter the model.

The 250/270 ms deadlines, 350/370 ms endpoints, 30 mm R/Z tolerance,
0.1 m/s speed threshold, Ip threshold, and arrival streak remain unchanged.
Any future physical stage retains authentic restart, visible-state causality,
Card15/action/current/saturation, safe stop, independent raw audit, no
archives, and existing-environment-only execution.

All R8-family trajectories remain probe/control-development evidence and are
forbidden from expert, BC, DAgger, and RL data. R8R18 is not MPC or Gate A.
