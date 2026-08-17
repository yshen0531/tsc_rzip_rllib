# R_geo/Z_geo 1 ms ID-2M0 diagnostic refit attribution design

Date: 2026-08-17 Asia/Shanghai

## Purpose

ID-2L1 is final as
`ONE_MS_ID2L1_STRUCTURED_MODEL_FAIL_ROUTE_REVIEW`.  Its best
`stable_signed_even` candidate passed every held-family paired-response,
direction, free-rollout and catastrophic gate, but failed the frozen
cell-weighted one/two-ms absolute-R gates.  The saved result contains only
fold aggregates: because no candidate was eligible, no coefficient or
per-issue prediction artifact was emitted.

ID-2M0 is therefore a bounded retrospective diagnostic.  It performs the
same four frozen `stable_signed_even` ridge fits, with the same ID-2K1 data,
features, folds, normalization, paired loss and ridge value.  This is a
**deterministic diagnostic refit**, not a zero-fit audit, new model fit,
candidate search or hyperparameter sweep.  It runs no TSC and cannot change
the ID-2L1 verdict.

## Frozen inputs and exclusions

- use only the tracked ID-2K1 development compact trajectories already
  admitted by the ID-2L1 config;
- bind the tracked ID-2L1 config, primary result, independent refit report
  and implementation revision;
- refit exactly four `stable_signed_even` fold models and no other model;
- read zero ID-2I1, ID-2J0, ID-2C2, calibration or holdout records;
- generate no selected model, controller, expert, fixture or training-data
  artifact;
- do not alter any ID-2L1 gate or reinterpret its formal FAIL.

## Required reproduction

Before attribution is accepted, the diagnostic must reproduce every saved
ID-2L1 `stable_signed_even` fold aggregate and eligibility failure with a
maximum numeric difference no greater than `1e-12`.  The issue/effect rule
remains issue `k` to state `k+1`.

The diagnostic emits the frozen per-cell/per-issue prediction rows needed to
explain the aggregate result.  For every one-ms row it records:

- held fold, history, cell and issue/effect state;
- truth and predicted R_geo/Z_geo/Ip increments and signed error;
- time-nominal, signed-memory and even-memory prediction contributions;
- actual-current and issued-current innovation available before issue;
- causal action edge, dwell age, return and delayed-tail classification;
- whether the row belongs to the common conditioner prefix or the issue-25
  probe/return window.

Labels are evaluator-only descriptions.  They are never model inputs.

## Weighting audit

The original cell-weighted metrics remain authoritative for ID-2L1.  ID-2M0
also reports a diagnostic unique-causal-transition view because the baseline
and four probe siblings in each history share the exact physical prefix
through state 25.

A one-ms causal-transition key contains the exact observed states and actual
currents through the pre-issue state plus issued Card15 through the current
issue.  A multi-step key additionally contains the prospectively known
issued actions through the reported effect.  Rows sharing a key must agree
in truth and prediction; disagreement is an integrity failure.

For every fold and recenter period the result reports both:

1. the unchanged cell-weighted p95;
2. unique-key p95 and row counts;
3. worst unique event and every unique one-ms R miss above `0.300 mm`.

Unique-key results are diagnostic only.  They cannot replace the original
cell-weighted gate after the result.

## Evaluator semantics audit

ID-2M0 statically and behaviorally audits the ID-2L1 rollout implementations.
In particular it distinguishes:

- exact truth used only as a rollout origin;
- current truth/innovation used as a dynamics feature;
- a recurrent hidden state advanced using its real causal context history;
- a recomputed hidden state whose past context has been overwritten by a
  later rollout origin.

Any recurrent context rewrite is reported as an evaluator-implementation
defect affecting that candidate only.  It does not invalidate the separately
recomputed `stable_signed_even` result and may not be repaired inside the
ID-2L1 identity.

## Scientific interpretation and route

The PASS route requires exact aggregate reproduction, complete attribution,
consistent unique keys and a complete evaluator-semantics report.  PASS may
authorize only a separately frozen ID-2M1 development design with at most two
small structured candidates around the retained signed/even response
backbone:

1. explicitly separated nominal plus causal action-edge/dwell/return/tail
   memory; and
2. the same model plus a low-dimensional, stability-constrained innovation
   state using current exact R_geo/Z_geo/Ip and causally available actual-
   versus-issued current.

No history/direction/sign/conditioner/probe label may enter either model.
No larger GRU/TCN, fresh TSC, calibration, holdout, authority, recovery,
controller, MPC, crossing, adaptation or RL work is authorized by ID-2M0.

If the frozen refit does not reproduce ID-2L1, the route stops for evaluator
or evidence diagnosis.  If attribution cannot isolate a compact causal
support cell, the later route must request new matched transition data rather
than silently increasing model capacity.

