# Stage4.2R3c3T13S14 same-trajectory active-calibration sentinel design

## Freeze point and question

This design is frozen after the final T13S13 training-model failure and
before any T13S14 response raw, model fit, route, Ray task, `gotsc`, or TSC
execution. T13S13 calibration and holdout data do not exist.

T13S14 asks one narrow development question: can a fixed, label-free,
same-trajectory active calibration reveal enough causal information about
the hidden vessel/eddy-current history to predict a later bounded local
response across held whole source pairs?

This is an identification sentinel, not a controller or MPC campaign.

## Prospective contexts

Selection uses source factor names only, never source acceptance, control
outcomes, hidden currents, or T13S13 response outcomes. Both authenticated
history members of these eight whole R3b pairs are included:

```text
p5_q1_a0p600_gap2_settle4
p5_q1_a0p600_gap4_settle4
p5_q2_a0p600_gap2_settle4
p5_q2_a0p600_gap4_settle4
p9_q1_a0p600_gap2_settle4
p9_q1_a0p600_gap4_settle4
p9_q2_a0p600_gap2_settle4
p9_q2_a0p600_gap4_settle4
```

After exact lexical sorting, assign regimes A/B/C/D cyclically twice:

```text
A  nominal target       delay 0  slew 1.0
B  nominal target       delay 2  slew 0.9
C  R+10/Z-10 mm target  delay 0  slew 1.0
D  R+10/Z-10 mm target  delay 2  slew 0.9
```

Whole pairs are the leave-one-pair-out units. The matrix contains 16
contexts, 16 calibrated baselines, and 128 signed probes:

```text
16 contexts x (1 baseline + 4 directions x 2 signs) = 144 real rollouts
```

## Fixed same-trajectory calibration and response schedule

The wrapper acts after the inherited software-delay queue. Every rollout,
including every baseline, executes the identical four-pulse calibration:

```text
task issue/cancel  physical effect/cancel  direction                    sign
0 / 1              1 / 2                   mode0_without_coil8          +1
2 / 3              3 / 4                   mode0_coil8_component        +1
4 / 5              5 / 6                   mode1                        +1
6 / 7              7 / 8                   mode2                        +1
```

Task steps 8 and 9 are fixed observation/settling steps. A response probe is
issued/cancelled at steps 10/11 and physically affects states 11/12. The
baseline has no response probe. Observation continues only through the
unchanged formal horizon, state 35 for slew 1.0 and state 37 for slew 0.9.

Each calibration pulse and the response probe use the frozen quantized
Card15 lattice primitive, maximum incremental normalized action `0.25`,
maximum total normalized action magnitude `1.0`, exact stored-center or
exact inverse cancellation, and exact requested/applied zero net. Maximum
current utilization remains `<=0.55`; saturation or clipping fails closed.

The calibration schedule, directions, and signs are global constants. They
may not depend on pair, history, prefix, amplitude, gap, split, hidden wire
state, source result, current-run future value, or response outcome.

## Causal observer input and forbidden information

At response issue step 10, the observer may use only states 0--10 and commands
already issued by the same current-run controller. Per state it uses the
T13S13 59-field deployable schema: target errors, backward-causal R/Z
velocity, measured 14-coil current and backward difference, previous actual
issued action, previous underlying three-mode command, known/mask fields,
task clock, declared delay/slew, and target offsets.

The active calibration actions are visible through the previous actual
issued-action field. Source actions/results, source/current wire currents,
future actions/measurements, post-response measured current, response output,
and all pair/history/prefix/amplitude/gap/split labels are forbidden model or
controller inputs.

The response action input is again the pre-action quantized-actuator nominal
readback displacement plus its interval radius. First-effect measured current
is outcome evidence only and must lie inside that pre-action box.

## Frozen model comparison

Two deterministic causal families are compared by leave-one-whole-pair-out
CV only:

1. the T13S13 zero-at-zero-action ESN interaction family with seed 20260802,
   width 32, `rho={0.35,0.65,0.85}`, `leak={0.5,1.0}`,
   observer rank `{4,8,12}`, and ridge `{1e-8,1e-6,1e-4}`;
2. a zero-at-zero-action Gaussian history-kernel/action-linear model. Its
   history kernel uses the fixed RMS distance over the padded causal sequence;
   its action kernel is the inner product in the training-only rank-4 whitened
   action coordinate. Candidate Gaussian bandwidths are
   `{0.25,0.5,1.0,2.0}` times the median nonzero eligible training history
   distance, with ridge `{1e-8,1e-6,1e-4}`.

All preprocessing, bandwidths, action bases, whitening, fits, and tubes are
fold-local. A candidate must be finite, action rank four, condition `<=30`,
and exactly zero at zero action. Eligible candidates are ordered by smallest
maximum held scaled center-relative error, then mean error, then ESN before
kernel only on an exact tie, then numerical hyperparameters in ascending
order.

The unchanged response scales are
`(0.03 m, 0.03 m, 0.1 m/s, 0.1 m/s, 2000 A)`. Every held row must have scaled
center-relative error `<=0.10`. Fold-local component tubes use the numerical
floor plus `1.5` times maximum training residual and exact interval-linear
action-radius propagation, and must contain every held response while
remaining below `(0.003 m, 0.003 m, 0.010 m/s, 0.010 m/s, 1000 A)`.

## Frozen gates

```text
source snapshot identity                              16 / 16
offline spec coverage                                144 / 144
raw parse/success/restart/causality                   144 / 144
calibration pulse-pair groups                         576 / 576
calibration issue/cancel trace events                1152 / 1152
calibration and response exact-zero-net groups         704 / 704
response issue/cancel trace events                     256 / 256
response signed groups                                  64 / 64
target action symmetry/current signal/current symmetry  64 / 64
pre-response causality/input-box containment          128 / 128
whole-pair CV response error/tube containment         128 / 128
forbidden inputs, near aliases, open-order violations           0
maximum current utilization                                <=0.55
```

The causal calibration signature for the two histories of every source pair
must be finite and not exact or near-exact at `1e-12` in fixed-scaled padded
history space. This clean-digital-twin separation is only a sentinel gate; it
does not validate measurement-noise observability.

Formal tracking is recorded but is diagnostic only for these identification
rollouts. The immutable arrival deadlines remain 250/270 ms and hold endpoints
350/370 ms. Calibration consumes real task time and receives no deadline
extension.

## Routes

```text
ACTIVE_CALIBRATION_SENTINEL_PASS_FULL_PARTITIONED_CAMPAIGN_REQUIRED
  every frozen gate passes; authorize only a separately frozen full
  train/calibration/fresh-holdout same-trajectory campaign.

ACTIVE_CALIBRATION_SENTINEL_FAIL_REDESIGN
  any gate fails; stop and redesign calibration excitation, observer, or
  uncertainty representation without dropping failed contexts.
```

Neither route authorizes a controller, MPC, expert dataset, BC, DAgger, or
bounded residual RL. Sentinel trajectories are forbidden from expert data.

The event-count wording above was corrected prospectively, before any S14
raw or TSC execution: 144 rollouts times four calibration pulse pairs is 576
calibration groups (1152 issue/cancel trace events), and the 128 nonbaseline
response pulse pairs bring the exact-zero-net total to 704 groups (1408
trace events). This arithmetic correction does not alter any rollout,
controller, model, gate threshold, or route semantics.
