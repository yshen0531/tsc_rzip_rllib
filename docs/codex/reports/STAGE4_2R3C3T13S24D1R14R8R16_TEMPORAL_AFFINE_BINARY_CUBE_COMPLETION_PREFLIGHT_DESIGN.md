# Stage4.2R3c3T13S24D1R14R8R16 temporal-affine binary-cube completion preflight design

Frozen prospectively on 2026-08-08 Asia/Shanghai before R8R16
implementation, model fitting, calibration metric, missing-code prediction,
candidate ranking, formal outcome, output, or route. R8R16 is zero-new-TSC.
Chat summaries are not evidence for this design.

## 1. Scientific question and boundary

R8R15 measured ten four-decision U/V staircase sequences in all sixteen
accepted contexts. Every measured sequence passed exactly the same six formal
contexts as the baseline, but all ten failed contexts had a positive best
minimum-margin gain. The final route requires model-based sequence redesign:

```text
BINARY_TEMPORAL_SWITCHING_STAIRCASE_AUTHORITY_INSUFFICIENT_MODEL_BASED_SEQUENCE_REDESIGN_REQUIRED
```

The complete four-slot binary cube contains sixteen codes. Ten are measured
and six have never been executed. R8R16 asks a narrow model-compatibility and
authority question:

```text
Does a prospectively fixed five-parameter temporal-affine response model
predict held measured codes accurately enough, and does its uncertainty-
discounted completion of the six never-executed codes predict at least one
formal repair worth testing in a separately frozen real-TSC sentinel?
```

R8R16 is a retrospective development-data preflight. Its calibration codes
were already seen scientifically in R8R15, so calibration is not called an
independent physical holdout. The six missing-code physical outcomes are
genuinely unobserved and remain closed. R8R16 runs no controller, Ray,
`gotsc`, TSC, plant step, or snapshot and cannot establish MPC, control,
physical authority, Gate A, or plant reachability.

## 2. Immutable sources

Primary and a structurally independent implementation must authenticate and
strictly parse, without modifying or rerunning:

1. the 16 final R8R7 zero-action baseline raw files and exact formal lineage;
2. the 16 final R8R12 v2 `UUUU` raw files;
3. the 16 direction-1-negative R8R14 `VVVV` raw files and the complete R8R14
   source authentication;
4. all 128 final R8R15 raw files, specifications, source authentication,
   final report, manifest, state, and compact server evidence;
5. the exact deployed formal evaluator and immutable timing contract.

The accepted R8R15 evidence includes:

```text
primary detailed
  d840d54ab1be6e3aef318d7b7859dd58a450b5b478c2bb736d8900be2bd9f024
primary summary
  2c5b7e10c74295f82cc54769fee51a87bea69682d7b5992963b99ff33845cde6
final independent
  cf896933a7b8d911027389018d1668adda1d04de1e17822b9bb83ee4d493ea34
final report
  cd1c37589955137c0b5d38c4f6e410b77a83ddb0d7c55dc803153bd8c0549664
stage manifest
  3d704e4167738575d4ee9417ae48f2ee732a1645feee6b357cc3f45f80665ffb
stage state
  71d4a0d3472e073ee423a8e0ae305999525264cf217b91dd5e2fbae17e2fce18
safety raw
  32 files / 1059431 bytes
  7d7a2b4f4ba946fb365db282fc7b3967e0e9b512cd241a6ea7c25071b47c21ad
qualification raw
  96 files / 3201665 bytes
  a909e034711b3539630a2d63db9786df0272c7358406476bae3463cd75f3f118
```

A source mismatch or strict-JSON/inventory disagreement stops R8R16 before
model construction. R8R16 must not rewrite any source artifact.

## 3. Frozen symbols and evidence split

The exact R8R15 symbols remain:

```text
U = canonical direction 2, sign +1, scale 1.0
V = canonical direction 1, sign -1, scale 1.0
decision task steps = [10,14,18,22]
```

The ten measured codes are partitioned before fitting as follows:

```text
model development, six codes
  UUUU  VVVV  UVVV  UUVV  UUUV  VUUU

fixed retrospective calibration, four codes
  VVUU  VVVU  UVUV  VUVU

never-executed physical intervention set, six codes
  UVUU  UUVU  UVVU  VUUV  VVUV  VUVV
```

The development/calibration split follows the already frozen candidate order
and is not changed after any fit. No measured code may move between sets.
The missing set is the exact complement of the ten measured codes in the
sixteen-code binary cube. No additional code, direction, sign, amplitude,
decision time, context, or post-result family expansion is allowed under
R8R16.

For code `s`, encode the model row as:

```text
x(s) = [1, q10, q14, q18, q22]
q = +1 for U and -1 for V
```

The six-row development matrix and ten-row full measured matrix must both
have rank five. Their two-norm condition numbers must be at most `3.25` and
`2.62`, respectively. Every structurally independent calculation must agree
within absolute `1e-12` and relative `1e-10`.

## 4. Frozen response construction

For each of the sixteen contexts, source baseline, and measured sequence,
authenticate the common physical prefix through state 10. For each state
from 10 through that context's unchanged 35/37 endpoint, construct only:

```text
d_s(t) = [R_s(t), Z_s(t), Ip_s(t)]
         - [R_baseline(t), Z_baseline(t), Ip_baseline(t)]
```

No resampling, time shift, smoothing, clipping, trajectory shortening, later
arrival deadline, or component substitution is allowed. Formal velocity is
always reconstructed by the unchanged evaluator from the resulting R/Z
trajectory; it is not independently fitted.

For every context, state, and component, fit ordinary least squares on the
six development codes:

```text
d_hat_s(t,j) = x(s) beta(t,j)
```

The primary solve uses a deterministic SVD pseudoinverse with `rcond=1e-12`.
The independent implementation must build the rows and solve the same stated
least-squares problem independently, without importing the primary model,
fit, prediction, formal summary, or verdict implementation.

There is no ridge grid, kernel, nonlinear term, pair/history feature,
candidate-specific correction, per-context hyperparameter, post-result tube
widening, or formal-outcome weighting. The per-context model is an offline
authority diagnostic; it is not a deployable context selector.

## 5. Fixed calibration gate

The six-code development fit predicts all four fixed calibration codes
without refitting. This yields exactly:

```text
16 contexts * 4 calibration codes = 64 trajectory predictions
```

For every predicted state, compute component errors and the maximum scaled
point error using:

```text
scales [R,Z,Ip] = [0.03 m, 0.03 m, 10000 A]
```

Every one of the 64 calibration trajectories must satisfy all of:

```text
finite prediction and residual                         true
maximum absolute R error                         <= 0.003 m
maximum absolute Z error                         <= 0.003 m
maximum absolute Ip error                       <= 1000 A
maximum scaled point error                         <= 0.10
unchanged formal pass/fail classification              exact
absolute minimum-signed-margin error                <= 0.05
```

The model-calibration tube is fixed after the predictions as twice the
componentwise maximum absolute calibration residual at every relative state.
It must remain within the unchanged conservative physical caps:

```text
R <= 0.01 m, Z <= 0.01 m, Ip <= 3000 A
```

The formal-margin calibration buffer is exactly:

```text
B_margin = 2 * maximum absolute calibration
                 minimum-signed-margin error
```

The multiplier, caps, and thresholds are frozen now. They may not be widened
after the calibration outcome. Calibration formal metrics use the exact
source baseline plus the predicted response and the unchanged evaluator.
They are diagnostics of this model only and do not relabel R8R15.

## 6. Full refit and missing-code completion

Only if every source, rank, condition, construction, and calibration gate
passes may the model refit the identical five-parameter family on all ten
measured codes. It then predicts all six missing codes in all sixteen
contexts, exactly 96 predicted trajectories.

For each missing prediction, compute the unchanged formal metrics and:

```text
robust_lower_margin = predicted_minimum_signed_margin - B_margin
```

A predicted missing-code row is robustly eligible only when its ordinary
formal result passes and `robust_lower_margin > 0`. For reporting, choose the
largest robust lower margin per context, with ties broken by the listed
missing-code order. The do-nothing baseline is always retained as the safe
evaluation fallback.

The R8R16 authority gate requires all of:

```text
source/inventory/formal lineage authentication             PASS
development/full design rank and condition                 PASS
calibration trajectories                                  64/64
calibration formal classification                         64/64
tube within frozen caps                                      true
primary/independent fits, predictions, margins, rankings    exact
failed R8R7 baselines with robust eligible missing code    >= 1/10
robust predicted oracle over baseline + missing codes       >= 7/16
robust predicted oracle strictly above baseline                true
```

The missing-code prediction is a preregistered model-based authorization
test, not a physical result. Predicted repair cannot be reported as actual
control or plant authority.

## 7. Frozen routes

```text
source, raw, matrix, formal-lineage, or independent disagreement:
  TEMPORAL_AFFINE_BINARY_CUBE_SOURCE_OR_INTEGRITY_FAIL_NO_TSC

source passes but any fit/calibration/tube gate fails:
  TEMPORAL_AFFINE_SEQUENCE_MODEL_INADEQUATE_NONLINEAR_SEQUENCE_REDESIGN_REQUIRED

model/calibration passes but robust predicted repair/oracle gate fails:
  TEMPORAL_AFFINE_BINARY_CUBE_AUTHORITY_INSUFFICIENT_CONTINUOUS_MULTIDIRECTION_REDESIGN_REQUIRED

all model, calibration, independent, and robust predicted-authority gates pass:
  TEMPORAL_AFFINE_BINARY_CUBE_COMPLETION_PASS_FRESH_MISSING_SEQUENCE_SENTINEL_REQUIRED
```

A PASS authorizes only a separately written and committed prospective real-
TSC sentinel design. That design must keep the missing-code set and model
fingerprints frozen, use safety then qualification with dual raw audits, keep
formal outcomes closed until all authorized raw authenticate, and distinguish
model prediction error from physical controller failure. R8R16 itself never
authorizes direct TSC.

## 8. Causality, safety, and learning prohibition

R8R16 may use context labels only for offline row alignment and scientific
grouping. It must mark them forbidden for any future controller input. It may
not use a future measurement, future action, hidden wire state, source result
label, formal pass label, missing-code outcome, or fabricated current path to
claim deployability.

The immutable 250/270 ms arrival deadlines, 350/370 ms hold endpoints, 30 mm
R/Z tolerance, 0.1 m/s speed threshold, Ip threshold, and arrival streak do
not change. Any future sentinel retains exact authentic restart, visible-
state causality, Card15/action/current/saturation, rejected-action safe stop,
primary/independent, and no-archive/no-global-Python contracts.

All R8-family raw are probe/control-development evidence and remain forbidden
from expert, BC, DAgger, and RL data. R8R16 is not MPC or Gate A. Even a later
missing-code sentinel PASS would authorize only a separately frozen causal
selector/receding-horizon controller and the remaining Gate A qualification
axes.
