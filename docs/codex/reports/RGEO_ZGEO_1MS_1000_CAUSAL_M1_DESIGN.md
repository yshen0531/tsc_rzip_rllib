# Fixed-1000 causal M1 event-aware model design

## Purpose

M0 failed because a smooth fixed-feature ridge averaged deterministic radial
events into the wrong sign. M1 is the one allowed point-model successor. It
uses exactly the same 25 fixed-1000 development trajectories, the same six
whole-family folds and the same physical error gates. It runs no TSC.

M1 is not a controller and is not a search over model capacity. Its narrow
question is whether explicit absolute event phase plus nonlinear interaction
with causal state/action history is enough to predict the existing finite
development envelope.

## Frozen model

The known q0 transition at each issue is the nominal prediction. A compact
two-hidden-layer `tanh` network predicts only the response relative to that
same-issue q0 transition. Inputs are:

- all 56 M0 causal features, including current exact R/Z/Ip, 1/4 ms
  velocities, actual current, exact target/delta and stable action memories;
- the difference of those features from the same-issue q0 causal row;
- a one-hot encoding of absolute issue 0 through 63.

Future plant state, future actual/readback current, family, schedule, phase,
rollout identity and result labels are forbidden. Exact duplicate causal rows
are counted once. The network widths are 64 and 32, with fixed Adam settings,
1,200 epochs and seeds 11/23/37. Predictions are the arithmetic ensemble
mean. There is no early-stopping choice, hyperparameter sweep or second M1
candidate.

## Evaluation and routes

The six M0 whole-family folds remain unchanged. Each fold must satisfy the
same R/Z/Ip p95, R maximum, paired-response NRMSE and peak-direction gates.
The paired response must improve at least 10% over the zero-response/q0-only
comparator. Passing development emits one frozen artifact and authorizes only
the design of fresh calibration and unopened whole-family holdout.

Failure permanently stops this fixed-1000 one-step point-prediction ladder.
The next route is a set-valued hybrid-risk/support model plus direct
candidate-value or feedback evidence; gates may not be widened and another
MLP/TCN/GRU may not be tried on the same rows. Authority, Recourse, capture,
hold and controller execution remain independent.
