# Stage4.2R3c3T13S24D1R14R8R51R4D5 causal two-decision model/controller preflight design

Status: conditionally and prospectively frozen on 2026-08-10 after the final
zero-TSC R51R4D3 result and after the R51R4D4 real-response design was frozen,
but before R51R4D4 implementation, authorization, TSC execution, raw creation,
response, formal outcome, or R51R4D5 model construction.

R51R4D5 runs only if final R51R4D4 reaches its exact scientific PASS route.
Otherwise D5 remains blocked and unrun.

## 1. Question and causal controller structure

D5 asks whether a model trained without a held-out physical history pair can
support a finite two-decision controller:

```text
decision 1 at state 12: choose the first of five safe pulses
observe the complete causal first-pulse response through state 18
decision 2 at state 18: choose the second of five safe pulses
```

Both actions must be chosen from the already D3-certified exact Card15 event
library. The controller may not synthesize a new action, change timing, use a
future state, inspect formal labels from its held-out pair, or index a policy
by pair/history identity.

## 2. Immutable source and no-new-TSC boundary

D5 must authenticate all 250 final D4 raw files, specs, payloads, snapshots,
primary/independent raw audits, formal reports, state, manifest, package, and
final server evidence. It runs zero Ray, `gotsc`, TSC, plant advances, raw
creation, snapshots, or real controllers.

All D4 raw are development probes. Cross-validation is an internal finite
development test, not an independent qualification or expert dataset.

## 3. Frozen five-fold split

The ten contexts are the five immutable matched physical history pairs. For
outer fold `j` in `0..4`:

```text
outer held-out pair    j
calibration pair       (j + 1) mod 5
model-fit pairs        the remaining three pairs
```

Therefore each fold contains:

```text
model fit       6 contexts x 25 rows = 150 rows
calibration     2 contexts x 25 rows =  50 rows
held-out test   2 contexts x 25 rows =  50 rows
```

Across folds every D4 row is held out exactly once. Neither fold assignment
nor calibration role may change after D4 response.

## 4. Prefix and counterfactual-support gate

For each context and first-candidate identity, the five rows differing only in
second candidate must have byte-identical physical states and causal trace
through state/task 18, apart from immutable experiment metadata. All 50 such
groups must pass. This proves that the observed state-18 prefix used by the
second decision does not depend on the unissued second action.

Every held-out decision must have all five certified candidate continuations.
No nearest unsupported action, interpolation, response-selected exclusion, or
counterfactual splice across different prefixes is allowed.

## 5. Frozen features and model family

All quantities are computed in physical TSC order and normalized from the
model-fit partition only, with fixed nonzero scale floors.

Decision-1 causal feature at state 12:

```text
R/Z/Ip at states 10, 11, 12
first differences over 10->11 and 11->12
14 visible coil currents at state 12
four-dimensional first-candidate coordinate
```

Decision-2 causal feature at state 18:

```text
the complete decision-1 feature
R/Z/Ip at states 13..18
first differences over states 12..18
14 visible coil currents at state 18
the first- and proposed second-candidate coordinates
```

Forbidden inputs include pair/history labels, experiment ID, source/D4 formal
outcome, future R/Z/Ip, wire/vessel current, another rollout, and raw filename.

Use two fixed ridge models with intercept and the same deterministic feature
map: normalized linear terms, elementwise squares, and state-by-action
interactions; no unrestricted state-by-state quadratic expansion. Ridge
coefficient is fixed at `1e-6` after feature normalization. There is no
hyperparameter or architecture selection.

The transition model predicts the state-18 visible response feature from the
state-12 feature and first action. The outcome model predicts the unchanged
formal minimum signed margin for each second candidate from a state-18 causal
feature. Fits use only the 150 model-fit rows in that outer fold. Duplicated
first prefixes are deduplicated for the transition fit.

## 6. Frozen calibration tubes and gates

For each output, the calibration half-width is the maximum absolute
calibration residual plus these fixed floors:

```text
R/Z state-18 floor         0.002 m
Ip state-18 floor          500 A
formal-margin floor        0.002
```

Caps are fixed:

```text
R/Z state-18 half-width   <= 0.030 m
Ip state-18 half-width    <= 4000 A
formal-margin half-width  <= 0.030
```

All calibration and all 250 outer-held-out predictions must be contained by
their corresponding tubes. Report point errors, tube widths, and containment
for every row; no failed row may be removed.

## 7. Frozen two-decision policy replay

At state 12, score all 25 ordered pairs using the transition-model predicted
state 18 and the outcome model. Choose the lexicographically first pair among
ties after maximizing the predicted formal-margin lower bound.

At the actual held-out state 18 produced by the selected first candidate,
discard the predicted state 18, rescore all five supported second candidates
using only the newly visible causal state, and choose the lexicographically
first maximum lower bound. This is the only allowed online innovation update.

The selected held-out D4 row is then used only to audit the already-fixed
choice. PASS requires:

```text
source/raw/prefix/support/causality integrity                 PASS
five-fold model/calibration/held-out row accounting          exact
transition and formal-margin calibration containment        all
transition and formal-margin held-out containment        250/250
all tube caps                                                PASS
selected first/second actions D3-safe                    10/10
held-out failed contexts repaired by selected policy       >= 1
baseline-plus-selected-policy measured oracle             >= 7/16
primary/independent folds, predictions, choices, route       exact
maximum primary/independent numerical difference          <= 1e-10
```

## 8. Routes and next authorization

```text
D4/source/raw/integrity authentication fails
  REDUCED_Q0_TRANSPORT_BRIDGE_R51R4D5_BLOCKED_BY_SOURCE_OR_INTEGRITY

support, tube, prediction, or selected-policy gate fails
  REDUCED_Q0_TRANSPORT_BRIDGE_R51R4D5_CAUSAL_TWO_DECISION_PREFLIGHT_INSUFFICIENT_REDESIGN_REQUIRED

all frozen gates pass
  REDUCED_Q0_TRANSPORT_BRIDGE_R51R4D5_CAUSAL_TWO_DECISION_PREFLIGHT_COMPLETE_R51R4D6_REAL_CONTROLLER_DESIGN_REQUIRED
```

A PASS authorizes only prospective freezing of a fresh R51R4D6 real causal
two-decision controller sentinel. It does not authorize D6 until its safety,
fallback, matrix, raw, independent, formal, and no-learning gates are frozen.

## 9. Scientific and learning boundary

D5 is a zero-new-TSC development preflight, not a real controller, real MPC,
independent qualification, robustness test, Gate A result, or global
reachability claim. All R51R4/D4 evidence remains forbidden from expert data,
BC, DAgger, residual RL, or other learning. Gate A and Gate B remain blocked.
