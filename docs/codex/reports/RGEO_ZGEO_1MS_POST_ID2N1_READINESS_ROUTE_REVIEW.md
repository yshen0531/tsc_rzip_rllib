# Post-ID-2N1 readiness route review

## Decision

ID-2N1 remains final as
`ONE_MS_ID2N1_CALIBRATION_MODEL_OR_TUBE_FAIL_HOLDOUT_UNOPENED`. Its execution,
Card15/queue semantics, raw inventory and independent audit passed; the blind
holdout did not run. The next stage is ID-2O0, a zero-new-TSC,
zero-model-fit readiness audit. This report authorizes design, implementation
and server execution of that audit only.

The high-level architecture is retained: exact actuator/queue semantics,
exact current R_geo/Z_geo/Ip observations, causal history/belief, calibrated
uncertainty and constrained rolling control. The current gap is whether the
available independent history families support the next learned response
model.

## Evidence that motivates the audit

- K1 contains eight independent history families and 40 fit-weighted unique
  cells. Its many transitions and multi-horizon endpoints are correlated
  observations, not additional independent histories.
- N1 completed four new calibration families, 12 unique cells and two exact
  replays. Its R tube exceeded 1.5 mm only at horizons 1--4; all four maxima
  came from `c01__p07_minus_i26_d2` at state-27 origin.
- The broader failure is response generalization: combined paired-response
  NRMSE was 2.843308, every fresh family exceeded one, and the two wrong-way
  probes were p04-plus and p07-minus within the same c01 family.
- A baseline/paired algebraic decomposition attributes about 20.6% of scaled
  squared probe error to the matched baseline continuation and 79.6% to the
  paired response term. Absolute prediction alone can therefore hide a wrong
  response through cancellation.
- The selected M1 model uses an explicit time nominal and fixed action/event
  features; current exact R_geo/Z_geo/Ip and actual current do not condition
  its learned response. Its development response NRMSE 0.055671 became
  2.843308 on fresh histories.

These observations support neither a position-only explanation nor a theorem
of hidden unobservability. They show that the tested context-invariant event
map and its current development support are insufficient.

## ID-2O0 contract

ID-2O0 reads the tracked K1 compact trajectories and the retained N1
calibration raw in place on the server. It runs no TSC, does not open N1
holdout, and fits no predictive model. It must independently report:

1. whole-family, unique-cell and exact causal-prefix counts;
2. exact and relaxed support for conditioner timing/order, sign, duration,
   probe issue/duration and return/tail age;
3. nearest deployable causal-prefix distances using only current/past
   R_geo/Z_geo/Ip, finite differences, actual current and owned issued action
   history;
4. baseline versus paired response by R, Z and Ip, event edge and horizon;
5. no-fit nearest-supported response direction/NRMSE and p04/p07 action
   ranking regret;
6. whether shared 1--8 ms latent/direct outputs have enough independent
   family and duration support.

The audit is not an attempt to recover a full physical causal graph. It is a
bounded learnability and control-utility discriminator.

## Frozen routes

`SUPPORT_SUFFICIENT_FOR_BOUNDED_MODEL_COMPARISON` requires all preregistered
support, direction/response, ranking and independent-family gates. It may
authorize at most two small models sharing an explicit nominal and stable
latent dynamics.

Otherwise the route is `MATCHED_FACTORIAL_DEVELOPMENT_DATA_REQUIRED`. It may
authorize only a new, prospectively fit-eligible campaign with matched
baselines and factorial variation of conditioner timing/order, p04/p07 sign,
duration 1/2/3, probe time and complete return/tail observation. It must not
become a one-successor ladder or a broad 14-dimensional random sweep.

K1 remains fit-eligible. N1 calibration remains consumed redesign/challenge
evidence under its frozen no-refit contract; replays carry zero statistical
weight. N1 v00--v03 stay unopened and may not execute under N1. Any future
model needs new calibration and a genuinely new whole-history blind holdout.

Neither ID-2O0 route authorizes a tube, authority, recovery, controller, MPC,
transport, crossing, adaptation, expert data or RL.

The frozen ID-2O0 config SHA-256 is
`2dbf33e6a3480de1592fc38a38869804523be34772391f605e1bc2f25e29928e`.
