# R_geo/Z_geo 1 ms ID-2U2 bounded causal model comparison design

Date: 2026-08-18

Identity: `rgeo-zgeo-1ms-id2u2-bounded-causal-model-comparison-v1`

## Purpose

ID-2U2 is a zero-new-TSC, development-only model discriminator over the
twenty fit-eligible ID-2U1 trajectories.  It asks whether the exact
pause/probe/return/resume grammar around the continuing p03 moving nominal
can be predicted across the four independent development histories without
turning the sparse `u00` delayed branch into either a global rule or an
ignored outlier.

Only `u00`, `u02`, `u04`, and `u06` may be read.  The paced calibration
families `u01/u03` and blind families `u05/u07` remain unopened.  No old
held-level campaign, zero-weight replay, calibration, holdout, raw server
tree, expert trajectory, or controller record may enter a fit or selection
metric.

## Observation and prediction contract

At every real decision boundary, current same-step paired-boundary
R_geo/Z_geo and same-step Ip are exact/noiseless observations.  The model is
therefore re-centered on the true current R/Z/Ip at every prediction origin;
it does not estimate those three measurements.  Its memory represents
causal response history and future/model uncertainty.

Allowed inputs are limited to information available before the issue:

- absolute time and the exact contemporaneous p03 nominal level;
- current and past exact R_geo/Z_geo/Ip and causal finite differences;
- controller-owned issued/serialized targets and exact Card15 action history;
- current and past measured/actual 14-coil currents;
- event quantities derived from that action history, including pause, pulse,
  dwell, return, resume, and age;
- the prospectively known candidate action sequence over the finite horizon.

Family IDs, role labels, response values, future R/Z/Ip, future measured
currents, wire currents, `sprsina`, evaluator labels, and future baseline
outcomes are forbidden model inputs.  Future coil current is propagated only
from the exact candidate Card15 target under the frozen issue-k to state-k+1
semantics; it is not copied from truth.

Every prediction is a one-step shared causal dynamics rollout for horizons
1--8.  Eight unrelated endpoint heads are forbidden.  A paired response is
the predicted probe continuation minus the predicted matched-baseline
continuation from the same observed origin and causal prefix.

## Exactly two candidates

### A. `stable_local_event_mixture`

The primary low-variance candidate is a support-gated local mixture.  It
uses fold-local normalization of deployable causal prefix features and
fixed stable action-memory poles.  Baseline continuation and matched action
response are represented separately, then recombined.  Local weights are
determined only by causal-prefix distance and the exact candidate Card15
sequence.  The kernel, neighbor count, ridge value, stable poles, feature
list, and support rule are frozen before evaluation; no held-family response
may tune them.

### B. `stable_local_event_gru_residual`

The second candidate adds one bounded persistent causal GRU residual to the
same candidate-A backbone.  It consumes the same normalized deployable
history in chronological order, has hidden width three, uses three frozen
seeds, and emits a capped one-step R/Z/Ip residual.  Its hidden state is
persistent across the observed prefix and is not rebuilt by rewriting past
contexts.  It may be selected only if it passes every gate and materially
improves the worst held-family response without unacceptable absolute-error
regression.  No larger GRU, TCN, architecture sweep, or post-result
hyperparameter search belongs to ID-2U2.

## Folds, duplicate weighting, and OOD

The four folds each hold out one complete family and all five siblings:
`u00`, `u02`, `u04`, or `u06`.  Training common prefixes that are byte-for-
byte identical across siblings receive one statistical weight, not five.
The full-fit artifact is emitted only after all four held-family gates pass.

OOD distance and nearest-support identities are reported for every origin.
Abstention is a controller-facing output, not a way to pass development:
all four held-family probe origins and all sixteen held probe cells must be
covered by the prospectively frozen support threshold.  Any uncovered held
family makes that candidate ineligible.

## Frozen metrics and gates

Evaluation uses origins at each matched probe issue and the next eight
one-ms effects, plus baseline-only origins from issues 16 through 32.  Every
fold must satisfy all of the following:

1. all four held probe cells covered by the support rule;
2. paired response NRMSE below `0.75`, with R/Z scaled by `0.1 mm` and Ip by
   `25 A`;
3. positive R/Z peak-direction cosine in all four held probe cells;
4. maximum four-action time-resolved utility-ranking regret fraction at most
   `0.25`;
5. exact-observation-recentered absolute endpoint p95 caps by horizon:
   R/Z `0.50, 0.75, 1.00, 1.25, 1.50, 1.75, 2.00, 2.25 mm`, and Ip
   `25, 35, 45, 55, 65, 75, 85, 100 A`;
6. maximum unique-event absolute R/Z error at most `3.0 mm` and Ip error at
   most `125 A`;
7. finite predictions, exact horizon ordering, and shared-rollout
   consistency for all 1--8 ms outputs;
8. fold-local feature rank/condition and support diagnostics within the
   frozen candidate-specific caps.

The time-resolved utility-ranking metric evaluates cumulative two-axis
progress over the full eight-step response, not a single peak.  It is a
model-comparison metric, not proof that the four-action grammar has positive
span, authority, recovery, or waypoint reachability.

Candidate A is preferred whenever eligible.  Candidate B is selected only
if its worst-fold response NRMSE improves by at least 10% relative to A and
its worst absolute endpoint p95 regresses by no more than 10%.  A PASS emits
one full-development model payload, evaluator contract, feature/support
metadata, and hashes.  The calibration design must remain a separate later
identity.

## Stop and authorization boundary

If neither candidate passes, ID-2U2 stops.  It does not add capacity, open
calibration, reuse blind data, or run a new TSC campaign automatically.  The
failure must be classified among support coverage, sparse hybrid event,
nominal continuation, response direction/ranking, or recursive stability
before a route review.

ID-2U2 performs zero TSC resets and zero plant advances.  A development PASS
authorizes only a separately frozen paced calibration over `u01/u03` with
the selected model and evaluator unchanged.  It does not establish an
uncertainty tube, two-axis authority, hold, recovery, controller, MPC,
waypoint/path tracking, R_mid crossing, adaptation, expert data, RL, or
reachability.
