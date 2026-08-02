# Stage4.2R3c3T13S19 prospective pooled observer campaign design

## Status and purpose

This design is frozen after the final S18 development result and before S19
implementation or any S19 rollout.  S19 is an identification-only prospective
training, calibration, and fresh whole-pair holdout campaign.  It validates a
local causal set-valued response model; it is not MPC and cannot authorize RL.

A server-side freshness scan parsed 900 existing T13 identification raw files
without error.  None contains any of the 20 selected pair IDs below.  Their R3b
state-generation trajectories and authenticated restart snapshots exist, but
their identification response outcomes have not been opened.

## Immutable context split

Every pair contains both `plus_first` and `minus_first` hidden-history members.
The split is by whole pair, was chosen from pair metadata only, and may not be
changed after outcomes appear.

Training pairs and regime assignment:

```text
p5_q1_a0p750_gap2_settle4  A
p5_q1_a0p750_gap3_settle4  B
p5_q1_a0p900_gap4_settle4  C
p5_q2_a0p750_gap2_settle4  D
p5_q2_a0p750_gap4_settle4  A
p5_q2_a0p900_gap3_settle4  B
p9_q1_a0p750_gap3_settle4  C
p9_q1_a0p900_gap2_settle4  D
p9_q1_a0p900_gap4_settle4  A
p9_q2_a0p750_gap4_settle4  B
p9_q2_a0p900_gap2_settle4  C
p9_q2_a0p900_gap3_settle4  D
```

Calibration pairs:

```text
p5_q1_a0p900_gap3_settle4  A
p5_q2_a0p750_gap3_settle4  B
p9_q1_a0p900_gap3_settle4  C
p9_q2_a0p750_gap3_settle4  D
```

Fresh holdout pairs:

```text
p5_q1_a0p750_gap4_settle4  C
p5_q2_a0p900_gap4_settle4  D
p9_q1_a0p750_gap4_settle4  A
p9_q2_a0p900_gap4_settle4  B
```

The regimes remain:

```text
A  nominal target, delay 0, slew 1.0
B  nominal target, delay 2, slew 0.9
C  RZ_p10_m10 target, delay 0, slew 1.0
D  RZ_p10_m10 target, delay 2, slew 0.9
```

This gives 12/4/4 training/calibration/holdout pairs, 24/8/8 contexts, and
192/64/64 signed response rows.

## Fixed authentic rollout

Each context uses the unchanged S16 causal active-calibration and response
primitive:

```text
calibration issues       steps 0, 2, 4, 6
calibration cancels      steps 1, 3, 5, 7
settling observations    states 8, 9
response issue/cancel    steps 10, 11
response effect          state 11
four fixed QR directions, two response signs
one separately executed baseline per context
```

The fixed basis scale factors remain `(1, 1, 1, 0.6)`, field-basis condition
must be at most `1.1`, response cosine at least `0.98`, off-basis residual at
most `0.15`, current utilization at most `0.55`, and all exact Card15,
zero-net, causality, solver, restart, saturation, and corruption gates remain
unchanged.  Probe trajectories are permanently forbidden from expert data.

Expected real rollout counts are:

```text
training       24 baselines + 192 probes = 216
calibration      8 baselines +  64 probes =  72
holdout          8 baselines +  64 probes =  72
total                                         360
```

Every rollout requires a fresh controller and fresh TSC process from the
authenticated snapshot.  Phases use fixed Ray capacity 128 and distinct
baseline/probe batches.  A phase failure stops before the next partition.

## Frozen causal model

The predictor has exactly the S18 nine features:

```text
five degree-three state-11 point coordinates
  fit from the same trajectory's visible R/Z/backward-vR/backward-vZ/Ip
  at states 1 through 10 and the fixed input schedule

four issued-action coordinates
  reconstructed from the already issued response action in the fixed basis
```

Its feature radius is the exact same-trajectory nominal-center plus issued-
action Card15 interval propagated through the degree-three input sensitivity.
Pair, history, partition, prefix, amplitude, gap, target, delay, slew, response
label, wire current, future value, source result/action, matched-baseline value,
and post-effect current are forbidden predictor inputs.  Pair labels may be
used only for offline splitting.  Matched baselines are outcome labels only.

After all 216 training rollouts complete, select one ridge from
`(0, 1e-8, 1e-6, 1e-4, 1e-2, 1, 100)` by 12 whole-pair OOF folds using the
lexicographic tuple `(maximum absolute scaled OOF error, mean squared scaled
OOF error, ridge)`.  Scaling uses training rows only.  Fit the final model on
all training rows and hash the scaler, model, sensitivity, ridge, training
IDs, OOF predictions, and componentwise maximum OOF residual before any
calibration rollout is launched.

## Frozen calibration and tube

After the training artifact is frozen, execute calibration.  No coefficient,
feature, scaler, or ridge may change.  Define the calibrated residual as the
componentwise maximum of the training whole-pair OOF residual and calibration
absolute point residual.  Before any holdout rollout, hash the training model
and the following fixed tube rule:

```text
response floor
+ 4.0 * calibrated componentwise residual
+ abs(physical-output feature sensitivity) @ causal feature radius
```

The response floor remains `(1e-9 m, 1e-9 m, 1e-7 m/s, 1e-7 m/s, 1e-4 A)`.
The component caps remain `(0.003 m, 0.003 m, 0.010 m/s, 0.010 m/s, 1000 A)`.
The point-error scales remain `(0.03 m, 0.03 m, 0.1 m/s, 0.1 m/s, 2000 A)`
and the maximum absolute scaled point error is fixed at `0.1` for training
OOF, calibration, and fresh holdout.

Calibration must pass 64/64 point, containment, cap, and joint gates before
holdout may open.  Although calibration containment follows from the fixed
maximum-residual rule, its point and cap gates are non-vacuous and mandatory.

## Frozen final gates

```text
freshness audit over prior T13 identification raw                pass
authenticated snapshots                                  40 / 40
training/calibration/holdout whole-pair split          12 / 4 / 4
real rollouts                                      216 / 72 / 72
exact execution/restart/causality/Card15/current           360 / 360
training whole-pair OOF point gate                          192 / 192
training model hash before calibration outcomes                     yes
calibration point/containment/cap/joint                       64 / 64
calibrated tube hash before holdout outcomes                         yes
holdout point/containment/cap/joint                           64 / 64
forbidden predictor inputs                                           0
raw parse/corruption errors                                          0
independent raw recomputation exact                                 yes
```

The immutable 250/270 ms arrival deadlines and 350/370 ms hold endpoints are
unchanged.  Formal control is recorded only as a diagnostic because S19 is an
identification campaign.

## Routes

```text
PROSPECTIVE_POOLED_CAUSAL_OBSERVER_HOLDOUT_PASS_LOCAL_SET_MODEL_ONLY
  All gates pass.  Freeze the local causal model and authorize only an offline
  finite-horizon robust-transport MPC feasibility design.  Do not claim MPC,
  long-hold, noise, disturbance, continuous-parameter, or RL readiness.

PROSPECTIVE_POOLED_CAUSAL_OBSERVER_TRAINING_FAIL_STOP
PROSPECTIVE_POOLED_CAUSAL_OBSERVER_CALIBRATION_FAIL_STOP
PROSPECTIVE_POOLED_CAUSAL_OBSERVER_HOLDOUT_FAIL_REDESIGN
  Stop at the named boundary.  Do not change the split, features, multiplier,
  caps, point threshold, or formal timing after seeing outcomes.
```

No S19 probe trajectory may enter an expert dataset.  BC, DAgger, and bounded
residual RL remain prohibited.
