# R_geo/Z_geo 1 ms ID-2Z10 five-context model design

Date: 2026-08-19 Asia/Shanghai

## Purpose

ID-2Z10 is the single authorized post-ID-2Z9 model comparison. It asks whether
the two unchanged ID-2Z8 low-capacity model classes become reliable after the
prospective support expansion from three to five independent decision
contexts. It runs no TSC, controller or optimizer and reads no calibration or
holdout record.

The candidates remain exactly:

1. `stable_local_memory`: four fixed stable action-memory poles, one fold-local
   context component, ridge lambda 1.0 and no intercept;
2. `stable_local_memory_plus_gru4`: the same backbone plus one bounded GRU with
   hidden size four, one layer, seeds 17/29/43, 300 epochs, learning rate 0.01
   and weight decay 0.01.

No feature, pole, hyperparameter, response scale, capacity or selection
threshold may change after seeing ID-2Z9.

## Data and folds

The five whole causal contexts are decision states 49, 53, 57, 61 and 65.
Each contains matched `hold4`, `b4`, `f4`, `b2f2` and `f2b2` siblings. All
siblings of one context remain in the same fold. The inherited state-49/53/57
records retain their original common endpoint 69 and horizons 20/16/12; the
new state-61/65 records retain their prospective common endpoint 77 and
horizons 16/12. Ranking uses each campaign's frozen last six terminal states
(64--69 or 72--77), so no unavailable future is fabricated. The ten ID-2Z9
sibling paths are prospective development records; its critical replay
remains zero weight.

Each leave-one-context-out fold trains on four contexts and evaluates the held
fifth context. Current and past exact R_geo/Z_geo/Ip and owned causal action
history are permitted. Future truth and future actual/readback current are
forbidden. Normalization and the one-component context transform are fit only
inside the training fold.

## Frozen gates

Every one of five folds must pass all unchanged ID-2Z8 gates for a candidate:

- response NRMSE <= 0.75;
- R and Z p95 <= 0.3 mm;
- Ip p95 <= 50 A;
- every nonzero peak response cosine > 0;
- best-arm normalized terminal-score regret <= 0.1;
- all predictions finite.

If both candidates pass and mean response NRMSE differs by at most 0.01, the
stable model wins. A full-five-context artifact is emitted only for an eligible
winner. A deterministic same-code replay audit is mandatory.

## Routes and stopping rule

- Input/evidence/causality failure: stop with no model claim.
- Neither candidate eligible: freeze this model-form/support route as FAIL;
  do not enlarge GRU/TCN capacity or consume calibration/holdout.
- Eligible winner: authorize only a separately frozen fresh calibration and
  blind whole-history holdout design. It does not authorize controller action,
  Recourse-L1, waypoint tracking or R_mid crossing.

This is the final model comparison on the B/F/H source-local development bank.
