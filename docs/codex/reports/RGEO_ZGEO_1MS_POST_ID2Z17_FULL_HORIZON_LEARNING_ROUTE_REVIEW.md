# Post-ID-2Z17 full-horizon learning route review

## Decision

ID-2Z17 closes the exact state-48, two-layer cumulative first-event beam.
It does not justify a third layer, but it also does not justify abandoning
learning: the two selected new directions changed terminal speed and distance
repeatably, while every tested fixed late schedule still rebounded far above
the capture-speed gate.

The route therefore stops the hand-authored late-macro ladder and returns to
the intended learning problem. The next real TSC identity is a fresh,
prospectively fit-eligible full-horizon development campaign. It retains an
exact source/full-F transport prefix through state 16, then interleaves exact
F transport issues with signed p06/p08 issues through state 48 and observes a
17 ms held tail. The full causal trajectory, not a label such as "history
type", is the input.

## Evidence behind the change

- The exact state-48 origin was `23.207303 mm` from source with one-step
  speed `0.218018 m/s`; the held trajectory rebounded to terminal worst speed
  `0.416472 m/s`.
- One late p08-plus layer reduced the terminal score to `3.966136`; two
  layers reduced it to `3.771440`, but terminal speed was still `0.377144
  m/s` and distance `28.167666 mm`.
- p06-plus traded more Ip for a smaller terminal distance; p08-plus reduced
  speed more. Their order had measurable but small effects. Thus there is
  finite control-relevant signal, but no demonstrated late capture grammar.
- The exact action increment columns F/p06-plus/p08-plus have numerical rank
  three and condition `2.08609`. This is input geometry only; the new
  campaign must measure their history-conditioned dynamics.
- All ID-2Z17 records were prospectively frozen with zero fit weight. Using
  them to train now would violate the data contract, so a new identity is
  required.

## What machine learning is responsible for

The project does not require complete physical causal identification before
learning. The model may learn the mapping from deployment-visible causal
history to future increments and candidate value. The experiment design only
has to prevent leakage, make actions distinguishable, and expose when the
model is outside support.

The first successor model comparison will be deliberately small:

1. a stable/regularized state-space or LPV backbone using exact current
   R_geo/Z_geo/Ip, recent velocity, actual/issued current and compressed action
   memory;
2. the same backbone plus a small persistent causal GRU/TCN residual.

Both must predict one-step increment/velocity and direct 2/4/8 ms outcomes.
Whole-history families remain intact in folds. Prediction error alone is not
enough: candidate ranking/value, OOD refusal and a fresh TSC-selected utility
sentinel are required before any controller claim.

## Frozen bounds on the next campaign

- Development now: 14 unique fit-eligible histories plus two zero-weight
  exact replays, at most 16 resets / 1040 advances / 5280 artifacts.
- Calibration and blind holdout schedules are declared now but remain
  unexecuted and unread until a model artifact is frozen.
- The data unit is a complete causal trajectory and its complete 1--8 ms
  windows. No step-wise split and no replay weighting are allowed.
- A complete execution, exact replay, usable signed signal and action/history
  support PASS may authorize only the bounded two-model development
  comparison.
- A data FAIL stops before model fitting. A later model FAIL stops capacity
  escalation and redirects to the measured failing schedules, not a larger
  recurrent network.

This is simulator-identification development, not controller-grade safety.
Exact Card15, current, slew, boundary, Ip, outer-envelope and stop-before-next
issue gates remain active. Capture, Recourse-L1, waypoint/path control and
R_mid crossing remain separate future gates.
