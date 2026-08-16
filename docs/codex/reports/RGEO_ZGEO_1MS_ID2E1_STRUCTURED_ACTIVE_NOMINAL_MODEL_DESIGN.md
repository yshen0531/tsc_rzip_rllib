# R_geo/Z_geo 1 ms ID-2E1 structured active-nominal model design

Date: 2026-08-17 Asia/Shanghai

Identity: `rgeo-zgeo-1ms-id2e1-structured-active-nominal-model-v1`

## Purpose and evidence roles

ID-2D1R1 passed its complete 24-rollout duration/time campaign and is the
only fit source for this stage.  ID-2C2 remains an immutable evaluator: it is
not used for feature design, candidate selection, scaling, regularization or
refitting.  The two exact replays in each source pair establish identity but
are collapsed to one statistical cell so deterministic duplicates cannot
inflate sample size.

This is a zero-new-TSC source-local development stage.  It fits no controller,
opens no calibration or blind context/history holdout, and makes no tube,
recourse, reachability or closed-loop claim.

## Prediction decomposition

For each state index `k`, absolute prediction is

```text
development held-nominal state[k] + predicted residual response[k]
```

The nominal is the exact repeated ID-2D1R1 held-active-nominal trajectory.
Residual truth is the action rollout minus its same-stage, same-clock nominal
baseline.  Thus nominal drift and action response have separate metrics.

The residual model receives only the complete issued virtual residual action
history through issue `k-1` and the known state clock.  It does not receive a
future actual/readback current, future state, evaluator baseline, rollout ID,
sign label, direction label, source hash, wire current or hidden TSC state.
The one-step physical effect remains `issue j -> state j+1`.

## Frozen candidate family

P04/p07 are the smooth two-coordinate channel.  Five whole schedule cells
`(issue16,duration2)`, `(issue16,duration4)`, `(issue22,duration1)`,
`(issue22,duration2)` and `(issue22,duration4)` are leave-one-cell-out folds;
all directions and signs of a cell stay together.  Fixed real poles are
`[-0.5, 0.0, 0.5, 0.8, 0.95]`; they are never learned and are strictly inside
the unit circle.  Regression has no intercept and no feature centering, so a
zero residual action gives exactly zero predicted response.

Candidates are evaluated in this predeclared simplicity order:

1. `fixed_pole_odd`;
2. `fixed_pole_signed_even`;
3. `fixed_pole_signed_even_time` (the preceding features plus their product
   with known normalized absolute state time);
4. `fir16_signed_even`.

All use fixed ridge `1e-6` after training-fold RMS column scaling.  The first
candidate passing every development fold is selected; later candidates are
not preferred merely for a smaller mean error.  The action-blind zero-
response model is a mandatory comparator and cannot be selected.

P09 is never pooled into that smooth family.  Its two issue-22 development
arms fit one fixed-pole signed/even event channel with the same fixed poles.
This gives a stable continuation beyond the ten observed event ages without
inventing a smooth p09 lag-16 support claim.

## Frozen gates and evaluator opening

Only post-effect states through state 32 are scored.  R/Z response error is
normalized by each arm's RMS response with a 25 micrometre floor.  Each
development fold must improve aggregate response RMSE over the zero-response
comparator by at least 15%, have response NRMSE at most 0.85, arm p90 NRMSE at
most 1.0, peak-vector cosine at least 0.5 for at least 75% of its arms, R/Z
error p95 at most 0.15 mm and Ip error p95 at most 15 A.

After the first eligible smooth candidate is refit on all ID-2D1R1
development cells, the model bytes and SHA-256 are frozen.  Only then may the
ID-2C2 evaluator be read.  Evaluation uses its six issue-16 one-issue p04,
p07 and p09 signed cells and its fresh active-nominal baseline.  No fallback
candidate may be opened after seeing evaluator metrics.  PASS requires:

- aggregate R/Z response NRMSE at most 0.80 and at least 20% improvement over
  zero response;
- every arm response NRMSE at most 1.10;
- peak-vector cosine at least 0.5 for at least five of six arms;
- R/Z response error p95 at most 0.025 mm and Ip response error p95 at most
  10 A;
- P09 separately satisfies NRMSE at most 0.80 and both signed peak directions;
- absolute state error p95 at most 0.25 mm for R/Z and 25 A for Ip.

These thresholds are deliberately response-sensitive: the 4 mm absolute
gate of the retired ID-2B v1 could pass while ignoring 35--52 micrometre
action signals.

## Result routing

Input/source/hash/causality failure is not a model result.  If no smooth
candidate passes grouped development, the route stops for model/data review
without reading ID-2C2.  If a frozen development model fails ID-2C2, it is a
source-local model-generalization failure; the evaluator is consumed and no
post-result candidate search is permitted.

A full PASS authorizes only design of fresh calibration and a separately
frozen context/history holdout.  It does not authorize an uncertainty tube,
controller, MPC, recovery, transport, R_mid crossing, online adaptation,
expert data or RL.  If this simple family fails, the project pauses for a
route review before any GRU/TCN or larger recurrent model.
