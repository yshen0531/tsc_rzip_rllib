# Stage4.2R3c3T13S11 causal calibration-conditioned braking preflight design

## Status and purpose

This design is frozen after the final T13S10 output and failure forensics,
and before any T13S11 feature extraction, PCA, fit, prediction, or route
output is computed. T13S11 is a zero-new-TSC development preflight over the
consumed T13S5 q2 and T13S9 q1 raw.

T13S10 proved that all held current inputs are supported in the unified
post-queue coordinate, but no static same-stratum map bank covers all
responses. T13S11 asks a narrower causal question: can one early, safe,
observable calibration transition provide enough state information to
condition a later braking-transition model across the eight q1/q2 contexts?

A positive result does not authorize a controller. It only permits a new
authentic dual-window campaign in which calibration and braking occur on
the same physical trajectory.

## Immutable source authentication

```text
T13S5 q2 raw files / digest
  68 / 09ee846d2fd8c2a516ec01f1b91bcbf8f303885c2377373000ab85dfc45e0f01
T13S5 independent audit SHA-256
  dc4d0147ce4fdd8a00105f8fc8ad45466513bac8b012f6843327b1efc271b033
T13S9 q1 raw files / digest
  68 / 9ccc67d5eda2b0710d658812207d99666a50af352e42d950086b694a3fa928ad
T13S9 independent audit SHA-256
  df4d7982f98a6216997d89ac5adea9ca2e3b2bf367451c3412d5458ccc5c60e0
T13S10 audit SHA-256
  f24768f7b4899c73f68fd0a4e3991f524239951883abf3d2809461b5ab82509b
```

Both source campaigns remain consumed development evidence. No T13S11
result may be described as an independent holdout.

## Frozen calibration observation

Use exactly the positive `mode0_coil8_component` transport probe as the
calibration action in every context. This direction was selected using the
consumed T13S10 result because it had the strongest finite consistency and
small single-coil support. That development choice is disclosed and must be
confirmed in a new campaign before controller use.

For delay 0, the calibration issue/effect/cancel-effect states are 2/3/4.
For delay 2, the post-queue states are 0/1/2. At the first effect state,
construct the controller-observable signature:

```text
z = (
  delta R / 0.03 m,
  delta Z / 0.03 m,
  delta vR / 0.1 m/s,
  delta vZ / 0.1 m/s,
  delta Ip / 2000 A,
  measured coil-8 current delta / declared coil-8 half-range,
  delay / 2,
  (slew - 1.0) / 0.1
)
```

Every delta is the absolute causal change from the issue state to its first
effect state on the same calibration trajectory. It is not a difference
against the unavailable no-probe counterfactual. Velocity uses only current
and past R/Z. The cancellation or any future state may not enter `z`.

The calibration trace, current effect, visible effect, pre-effect causality,
Card15/current interval, and absence of clipping must all authenticate. The
signature must be finite and nonzero in its measured current and visible
response parts.

## Training-only state coordinate and braking model

There are eight leave-one-context-out folds, four contexts in each easy/hard
stratum. For each held context:

1. Use only the three same-stratum training calibration signatures.
2. Center their physically scaled eight-dimensional `z` values using the
   training mean.
3. Compute a training-only rank-2 SVD basis. No held signature or label may
   affect the basis. Project the held signature only after the basis is
   frozen.
4. Build a training-only rank-4 SVD basis from the measured 14-coil braking
   first-effect current inputs.
5. For each signed training braking row, let `u` be its four input-basis
   coordinates and `s` its two calibration-state coordinates. Fit
   `y = kron((1, s1, s2), u) @ J` by minimum-norm least squares.

The 12-column interaction design must have exact rank 12, finite condition
`<=30`, and nonzero signal. No intercept independent of current is allowed,
so the incremental effect remains zero at zero incremental current.

Use the same single-state response, floors, residual multiplier, scales, and
component caps as T13S10:

```text
y scales              (0.03 m, 0.03 m, 0.1 m/s, 0.1 m/s, 2000 A)
tube radius            numerical floor + 1.5 * max training residual
tube caps              (0.003 m, 0.003 m, 0.01 m/s, 0.01 m/s, 1000 A)
extended support       row-space residual <= 0.15
scaled center error    <= 0.10
```

Do not apply support to the 12-column interaction design itself: exact rank
12 would span that whole coordinate and make the gate vacuous. Before any
prediction, require both of these independent non-vacuous gates:

```text
held centered z residual to the training rank-2 affine subspace   <= 0.15
held 14-coil braking input residual to the training rank-4 space  <= 0.15
```

Each residual is its Euclidean projection residual divided by the norm of
the held vector with only a numerical zero floor. The state residual is
computed in the original physically scaled eight-dimensional signature
space; the current residual is computed in the original measured 14-coil
space. The two values are reported separately. Both must pass before the
held calibration coordinates and braking input are combined into the frozen
12-column interaction row for prediction.

## Exact gates

```text
source raw authentication                              68 / 68, 68 / 68
source trace identity                                          136 / 136
causal calibration signature authentication                       8 / 8
calibration pre-effect causality                                   8 / 8
signed braking first-effect extraction                           64 / 64
braking pre-effect causality                                     64 / 64
training-only calibration PCA rank                                 8 / 8
training-only current basis rank                                   8 / 8
interaction design rank/condition/signal                           8 / 8
non-vacuous interaction tube                                       8 / 8
held calibration-state affine support                              8 / 8
held braking-current support                                     64 / 64
held componentwise containment                                   64 / 64
held scaled relative error <= 0.10                               64 / 64
disjoint exact causal signature/input aliases                            0
forbidden feature/trace/model inputs                                     0
```

Unsupported rows fail closed. Nonfinite condition/error values serialize as
JSON `null` and fail. No threshold, direction, sign, fold, scaling, basis
rank, or effect state may change after output.

Pair, q/history/prefix/source identity, source actions/results, current-run
future values, no-probe counterfactual response, source/current wire or
vessel currents, and outcome labels are forbidden from the signature,
basis, fit, support, prediction, and model selection. Labels may be opened
only after all fold predictions are frozen for forensic composition counts.

## Routes

```text
CAUSAL_CALIBRATION_CONDITIONED_BRAKING_PREFLIGHT_CANDIDATE_DUAL_WINDOW_TSC_REQUIRED
  every gate passes;
  authorize only a prospectively frozen authentic campaign where the same
  calibration and later braking probes execute on one trajectory.

CAUSAL_CALIBRATION_CONDITIONED_BRAKING_PREFLIGHT_INSUFFICIENT_PERSISTENT_OBSERVER_REDESIGN
  any gate fails;
  require a longer causal observation sequence, multiple safe calibration
  actions, or a persistent nonlinear observer before another campaign.
```

The separate source trajectories do not prove that calibration leaves the
later braking plant state unchanged. Only a fresh dual-window trajectory can
test that interaction. Neither route authorizes a real controller, MPC,
expert data, BC, DAgger, or bounded residual RL. Formal arrival and hold
timing is unchanged.
