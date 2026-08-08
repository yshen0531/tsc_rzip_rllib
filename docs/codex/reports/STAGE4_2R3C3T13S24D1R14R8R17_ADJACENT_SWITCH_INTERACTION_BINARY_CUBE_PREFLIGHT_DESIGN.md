# Stage4.2R3c3T13S24D1R14R8R17 adjacent-switch interaction preflight design

Frozen prospectively on 2026-08-08 Asia/Shanghai after the final aggregate
R8R16 route was sealed, but before inspecting the identity of its single
failed calibration row, before any R8R17 implementation, fit, calibration
output, missing-code prediction, candidate ranking, formal outcome, output,
or route. R8R17 is zero-new-TSC. Chat summaries are not evidence.

## 1. Scientific question and boundary

R8R16 authenticated the ten measured binary sequences and found that its
five-parameter temporal-affine model missed only one of 64 held calibration
rows. Rank, condition, component, scaled-point, tube, and formal-
classification gates passed, but the maximum minimum-formal-margin error was
`0.05171944884413282`, above the prospectively frozen `0.05` cap. R8R16 is
immutable and may not be relaxed.

R8R17 asks one narrower, prospectively specified nonlinear question:

```text
Does adding exactly one normalized adjacent-slot persistence interaction to
the same held split reduce all calibration errors below the unchanged R8R16
caps, and if so does the uncertainty-discounted completion of the six never-
executed codes predict at least one repair worth a fresh physical sentinel?
```

The feature is fixed from sequential action structure and design-matrix
geometry only. No R8R16 per-code, per-context, per-state, residual, or failed-
row detail was inspected to choose it. R8R17 is a retrospective model
preflight, not an independent physical holdout. It runs no Ray, `gotsc`, TSC,
controller, plant step, raw generation, or snapshot and cannot establish
MPC, physical authority, Gate A, or plant reachability.

## 2. Immutable sources and authentication

R8R17 must authenticate without modifying or rerunning:

1. the exact 16 R8R7 zero-action baselines and formal lineage;
2. the 16 R8R12 v2 `UUUU` trajectories;
3. the 16 R8R14 direction-1-negative `VVVV` trajectories;
4. all 128 final R8R15 trajectories, specifications, inventories, and final
   evidence;
5. the complete final R8R16 seven-file output and route;
6. the exact deployed formal evaluator and immutable timing contract.

Required R8R16 server hashes are:

```text
primary detailed      5f8605e45982ace397b364361cb71a2249520f0686c4e39c8879f06a37ebf429
primary summary       be9a7b968a79d2cf95b3f6dd9103e9797d375448215769e53745dea46fb0cff6
independent           8f73d31dd5370a295ed4096ea77a4f8585d2d89c54b1625ecf0ae26f5a29ef7a
final report          f17c4338579fda179739630a35fcf97f07a71d261bb96eafb47f4c69680ef58e
source authentication 88ed50a9fbe6d303151c264309b919dd0e906be5818513626868791084e9f362
stage manifest        605b98ceea86edcb1b1680c87bbcd012f5a727a747c0f6a6d91988922460ef4d
stage state           7b6679436e3a8551f451356e8f817f49a36e097e71b7237ec2f61de680641af3
```

R8R16 must report the exact route
`TEMPORAL_AFFINE_SEQUENCE_MODEL_INADEQUATE_NONLINEAR_SEQUENCE_REDESIGN_REQUIRED`,
`63/64` calibration, zero new raw, and zero real TSC. R8R17 uses no R8R16
predicted trajectory or coefficient as model input. A mismatch stops before
model construction.

## 3. Frozen code split and nonlinear feature

Symbols, timing, and evidence split remain exactly:

```text
U = canonical direction 2, sign +1, scale 1.0
V = canonical direction 1, sign -1, scale 1.0
decision task steps = [10,14,18,22]

development       UUUU VVVV UVVV UUVV UUUV VUUU
calibration       VVUU VVVU UVUV VUVU
never executed    UVUU UUVU UVVU VUUV VVUV VUVV
```

Encode U as `+1` and V as `-1`. The only allowed nonlinear feature is the
normalized adjacent-slot persistence interaction:

```text
a(q) = (q10*q14 + q14*q18 + q18*q22) / 3
x(q) = [1, q10, q14, q18, q22, a(q)]
```

This feature represents whether adjacent cumulative staircase directions
persist or switch. It is bounded in `[-1,1]`, contains no measured state or
outcome, and is fully known before execution. No individual pairwise term,
endpoint term, higher-order interaction, kernel, regularizer, learned
embedding, per-context hyperparameter, or feature selection is allowed.

The geometry is frozen from code rows only:

```text
development matrix   6 x 6, rank 6, condition 6.699042762912874 <= 6.70
all measured matrix 10 x 6, rank 6, condition 2.6131259297527527 <= 2.62
full binary cube    16 x 6, rank 6, condition 1.732050807568877 <= 1.74
```

Primary and independent geometry must reproduce these ranks and conditions
within absolute `1e-12` and relative `1e-10` before loading response values.

## 4. Frozen response model

For every context and measured sequence, authenticate the common physical
prefix through state 10. For each unchanged state from 10 through that
context's 35/37 endpoint, construct only:

```text
d_s(t) = [R_s(t), Z_s(t), Ip_s(t)]
         - [R_baseline(t), Z_baseline(t), Ip_baseline(t)]
```

No resampling, time shift, smoothing, clipping, shortened horizon, later
arrival deadline, component substitution, or directly fitted velocity is
allowed. Fit ordinary least squares independently at each context, state,
and component on the six development codes:

```text
d_hat_s(t,j) = x(s) beta(t,j)
```

The six-row development system is square and full rank. The primary must use
a deterministic SVD pseudoinverse with `rcond=1e-12`; the structurally
independent implementation must build the feature rows itself and use
`numpy.linalg.lstsq`. It may reuse only audited source-loading and formal-
lineage primitives, not the primary R8R17 feature, fit, prediction, summary,
or verdict functions.

## 5. Unchanged held calibration gate

The development fit predicts the same four calibration codes without
refitting, exactly `16 * 4 = 64` trajectories. Every predicted state and
trajectory must satisfy the unchanged R8R16 caps:

```text
response scales [R,Z,Ip]                         [0.03,0.03,10000]
maximum absolute R error                              <= 0.003 m
maximum absolute Z error                              <= 0.003 m
maximum absolute Ip error                              <= 1000 A
maximum scaled point error                                <= 0.10
unchanged formal pass/fail classification                   exact
absolute minimum-signed-margin error                     <= 0.05
required trajectory pass count                            64/64
required formal-classification count                      64/64
```

The model tube is again exactly twice the componentwise maximum absolute
calibration residual at every relative state and must stay within
`0.01 m / 0.01 m / 3000 A`. The formal uncertainty buffer remains:

```text
B_margin = 2 * maximum calibration minimum-margin absolute error
```

No cap, multiplier, scale, formal threshold, or code split may be changed
after the result. R8R17 does not inherit R8R16 residuals or combine the two
models opportunistically.

## 6. Conditional refit and missing-code authority

Only if source, geometry, calibration, tube, and independent-agreement gates
all pass may the identical six-parameter feature family refit all ten
measured codes. It then predicts exactly six missing codes in all 16
contexts, 96 trajectories total.

For each prediction:

```text
robust_lower_margin = predicted_minimum_signed_margin - B_margin
```

A missing row is robustly eligible only if its ordinary formal classification
passes and `robust_lower_margin > 0`. Per context, select the largest robust
lower margin, breaking ties by the fixed missing-code order. The exact
R8R7 do-nothing baseline remains the safe evaluator fallback.

The authority gate requires:

```text
failed R8R7 baselines with robust eligible missing code   >= 1/10
robust predicted oracle over baseline + missing codes      >= 7/16
robust predicted oracle strictly above baseline                 true
primary/independent predictions, metrics, ranking, route        exact
```

Predicted repair is only authorization evidence. It is not real control or
physical plant authority.

## 7. Frozen routes

```text
source, geometry, formal lineage, or independent disagreement:
  ADJACENT_SWITCH_INTERACTION_SOURCE_OR_INTEGRITY_FAIL_NO_TSC

source passes but calibration or tube fails:
  ADJACENT_SWITCH_INTERACTION_MODEL_INADEQUATE_HIGHER_ORDER_REDESIGN_REQUIRED

model passes but robust missing-code authority fails:
  ADJACENT_SWITCH_INTERACTION_AUTHORITY_INSUFFICIENT_CONTINUOUS_MULTIDIRECTION_REDESIGN_REQUIRED

all model and robust authority gates pass:
  ADJACENT_SWITCH_INTERACTION_COMPLETION_PASS_FRESH_MISSING_SEQUENCE_SENTINEL_REQUIRED
```

A PASS authorizes only a separately frozen finite real-TSC sentinel over the
pre-ranked missing codes. That later stage must fingerprint the model, keep
formal results closed through complete dual raw authentication, and use a
safety-before-qualification partition. R8R17 itself never authorizes direct
TSC.

## 8. Safety, causality, and learning prohibition

Context labels are offline alignment keys only and remain forbidden future
controller inputs. No future state, future action, hidden wire state, formal
label, missing-code physical outcome, or fabricated current may be used to
claim deployability.

The 250/270 ms arrival deadlines, 350/370 ms hold endpoints, 30 mm R/Z
tolerance, 0.1 m/s speed threshold, Ip threshold, and arrival streak remain
unchanged. Any future physical stage retains exact authentic restart,
visible-state causality, Card15/action/current/saturation, rejected-action
safe stop, independent raw audit, no archives, and existing-environment-only
execution.

All R8-family trajectories are probe/control-development evidence and remain
forbidden from expert, BC, DAgger, and RL data. R8R17 is not MPC or Gate A.
Even a PASS would still require a fresh physical sentinel, a separately
frozen causal receding-horizon controller, and every remaining Gate A axis.
