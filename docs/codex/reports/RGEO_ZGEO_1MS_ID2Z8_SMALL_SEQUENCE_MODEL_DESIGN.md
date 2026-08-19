# R_geo/Z_geo 1 ms ID-2Z8 small sequence-model design

Date: 2026-08-19

## 1. Question

ID-2Z8 asks one bounded development question: can a low-capacity causal model
amortize the finite H/B/F branch evaluator across the three decision contexts
measured by ID-2Z6/ID-2Z7?

It does not fit a full plant world model and does not authorize a controller.
The data contain only three independent causal contexts (decision states
49/53/57), each with five sibling actions. The five sibling rows are not five
independent histories. This limit is part of every result and gate.

## 2. Frozen data

The only fit-weight data are the fifteen complete windows already admitted by
ID-2Z7:

- ID-2Z6 round 0: `hold4`, `b4`, `f4`, `b2f2`, `f2b2`;
- ID-2Z7 round 1: the same five arms after selected `f4`;
- ID-2Z7 round 2: the same five arms after selected `f4 -> b2f2`.

The ID-2Z7 critical replay is used only for evidence identity and receives
zero fit/evaluation weight. Interrupted ID-2Z6 round-1 paths, ID-2Z5, all
calibration/holdout records and all expert/RL records are forbidden.

Each context uses its matched `hold4` as the zero-response baseline. The four
non-hold siblings provide action-conditioned responses from the decision
through common state 69: horizons 1--20 at state 49, 1--16 at state 53 and
1--12 at state 57. Responses are scaled as
`[R/1 mm, Z/1 mm, Ip/100 A]`. Future actual current and future truth are never
features.

## 3. Causal inputs

At each root the model may use only quantities available before issuing the
candidate macro:

- exact current and previous R_geo/Z_geo/Ip;
- the preceding eight one-ms R_geo/Z_geo/Ip and actual-current history;
- controller-owned issued Card15 history;
- absolute issue index and exact current Card15 target;
- the prospective four-token H/B/F candidate, its exact Card15 realization,
  and its known future issued targets.

The current measurements are exact observations, not latent estimates.
Candidate effects and future actual/readback currents remain unknown.

## 4. Exactly two candidates

### A. `stable_local_memory`

The action is represented in the exact B/F two-vector coordinate. Four fixed
stable memories per coordinate use poles `[0, 0.5, 0.8, 0.95]`. A fold-local
one-dimensional causal context coordinate is the first principal direction of
the two training roots' pre-issue RZI, recent velocity and 14-coil actual
current vector. The response head is a fixed-ridge linear map of action memory
and action-memory times that context coordinate. There is no intercept, so a
zero candidate deviation has zero paired response. Ridge is fixed at `1.0`;
there is no hyperparameter search.

### B. `stable_local_memory_plus_gru4`

Candidate B keeps A unchanged and fits only a residual. A single-layer GRU
with hidden size four reads the true eight-step causal prefix followed by the
known candidate action sequence. It predicts a bounded residual added to A.
Three fixed seeds `[17, 29, 43]` form one ensemble candidate; their mean is the
point prediction and their spread is diagnostic. Hidden state persists from
the real prefix into the future-action segment. The evaluator may not rewrite
past context at a later origin. Training is capped at 300 epochs, Adam
`lr=0.01`, weight decay `0.01`, and residual output is bounded by `tanh` times
`[1 mm, 1 mm, 100 A]` in physical units.

No other ridge, network size, seed, feature, target or candidate may be tried
under this identity.

## 5. Evaluation

There are exactly three leave-one-context-out folds. Every sibling from a
decision context stays in the same fold. Normalization/PCA/ridge/GRU fitting
uses only the two training contexts. Each held context evaluates its four
non-hold cells through common state 69. Variable-length sequences are masked;
padding is neither a feature nor a target.

For each candidate report:

- combined and per-fold response NRMSE against the zero-response predictor;
- R/Z/Ip p95 and maximum physical response errors;
- peak-vector cosine for all twelve held action cells;
- predicted best-arm ranking and normalized-score regret in each fold;
- root support distance/extrapolation and, for the GRU, seed spread;
- feature rank/condition and parameter count.

The frozen eligibility gate requires every fold to satisfy all of:

```text
response NRMSE                 <= 0.75
R p95 / Z p95                 <= 0.30 mm
Ip p95                        <= 50 A
all four peak-vector cosines  > 0
best-arm normalized regret    <= 0.10
```

The candidate with lower mean response NRMSE wins only among eligible
candidates. A tie within `0.01` goes to `stable_local_memory`. Any candidate
with non-finite output, rank inconsistency, future leakage, rewritten history
or fold contamination is ineligible.

## 6. Routes and stop rule

- Evidence/input/causality failure: stop without a model result.
- Neither candidate eligible: `SMALL_MODEL_FAIL_TARGETED_DATA_OR_BASIS_REVIEW`.
  Do not enlarge the network or tune this dataset.
- Only the GRU candidate eligible or materially better: freeze that
  development winner, but require a fresh calibration identity and an
  unopened whole-history holdout before any TSC-selected action.
- Stable candidate eligible and tied/better: prefer it for the same fresh
  calibration/holdout route.

Even a PASS is only a development model nomination. It does not authorize
Recourse-L1, controller execution, MPC, waypoint/path control, expert data,
online adaptation or R_mid crossing. Since ID-2Z7 did not capture, the
independent authority/terminal-set problem remains open.
