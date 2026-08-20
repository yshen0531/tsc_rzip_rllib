# ID-2Z19R1 causal rank-four two-candidate model design

Date: 2026-08-20

Identity: `rgeo-zgeo-1ms-id2z19r1-causal-rank4-two-candidate-model-v1`

## Purpose and predecessor

ID-2Z19R1 supersedes the untrained ID-2Z19 v1 implementation. ID-2Z19 v1
produced no preflight evidence, fit, model artifact, calibration read,
holdout read, TSC call or plant advance. Its frozen status is a prospective
pre-fit design stop, not a model or plant failure.

ID-2Z19R1 asks one bounded development question: can either of two fixed,
causal and low-capacity predictors generalize across the eight declared
whole-history folds in the fit-eligible ID-2Z18 development bank? It runs on
the server, performs zero TSC/plant work and reads only the fourteen
positive-weight development trajectories. The two replay trajectories
authenticate input identity and retain zero statistical weight. `c00--c03`
calibration and `v00--v03` blind histories remain unexecuted and unread.

## Pre-fit readiness gate

No fit may begin unless all of the following pass:

1. the 432 nonzero complete signed Card15 deltas in issues 16--47 have
   numerical rank exactly four;
2. the fixed rank-four SVD coordinate reconstructs every complete signed
   delta within `1e-9 A` L2 and componentwise;
3. the largest residual against the superseded positive-only rank-three
   coordinate is recorded and remains at least `0.05 A`, proving that the
   repaired coordinate is materially different;
4. candidate future deltas are reconstructed recursively from the current
   active command and the proposed future targets only;
5. changing future recorded active command, actual current or RZI while
   preserving current history and candidate targets changes no feature;
6. every declared family, fold, horizon, count and source hash matches the
   frozen config; calibration and blind files are never opened;
7. the real action-blind baseline, candidate models and row ledger counts are
   fixed before any result.

The action basis is an input-only preprocessing object. It uses no RZI/Ip
outcome, evaluator response, family/sign/token label or held truth.

## Observation and causal features

At issue `k`, state `k` has exact/noiseless same-step paired-boundary
R_geo/Z_geo and Ip. The complete post-takeover RZI, measured 14-coil current,
active-command and issued-target history through `k` is available. Candidate
targets `u_k...u_{k+h-1}` are known. Future measured current, future recorded
active command, future RZI, wire current, sprsina and family/pair/sign/token
labels are forbidden.

The structured feature map contains:

- current RZI relative to source;
- causal 1 ms and 4 ms RZI differences;
- current actual and active current in the exact rank-four action coordinate;
- three fixed stable-pole summaries of past issued deltas;
- absolute issue time;
- horizon and recursively reconstructed future-target summaries.

Fold-local zero-variance columns are removed. Remaining exact linear
redundancy is removed by a fold-local training-only SVD projection. Rank,
singular values and condition are recorded. This is a numerical design
coordinate, not a learned physical mode or authority claim.

## Targets and horizons

Auxiliary fits use every complete horizon 1 through 8 ms. Qualification caps
are reported at 1/2/4/8 ms. Each row has two causal multitask targets:

- RZI displacement from origin to endpoint;
- terminal one-step RZI increment at that endpoint.

Terminal R/Z velocity is the terminal increment divided by 1 ms. Candidate
future slew and current excursion are exact deterministic action diagnostics,
not learned safety margins. Incomplete future windows are censored, not
labels.

## Exactly two candidates

Candidate A, `structured_rank4_stable_memory`, is one ridge-regularized
multitask map over the fixed stable action memory and causal features. The
ridge value and poles are frozen. “Stable” refers only to those fixed memory
poles; this identity does not call the direct map a learned stable
state-space plant or a qualified LPV controller.

Candidate B, `structured_rank4_stable_memory_plus_tcn4`, keeps Candidate A
unchanged and adds one causal two-layer TCN residual. Width, kernels,
dilations, three seeds, optimizer, epochs, residual cap and arithmetic
ensemble are fixed. There is no GRU candidate, third model, architecture
search, seed selection, ridge grid or post-result capacity increase.

A separately fitted action-blind structured model removes all issued,
active, measured-current, action-memory and future-target coordinates while
retaining current RZI, causal RZI differences, time and horizon. It is fit
once per fold and is not a selectable third candidate.

## Whole-history folds and support

The eight folds remain unchanged: two complete baseline holdouts and six
complete signed-pair holdouts. Siblings never cross splits. Replays have zero
fit/evaluation weight.

For each fold, support distance is computed in the fold-local structured
feature coordinates. Its threshold is `1.5` times the training-only 95th
percentile cross-family nearest-neighbour distance at matching horizon.
At least 90% of held rows must lie within that threshold. This is a
development support refusal gate, not a calibrated deployment OOD tube.

## Metrics and gates

Every candidate is evaluated on persisted out-of-fold rows. Required gates
are:

1. finite predictions and a complete unique ledger;
2. componentwise endpoint p95 caps at 1/2/4/8 ms;
3. terminal 1 ms R/Z velocity-error and Ip-increment-error caps;
4. normalized endpoint and terminal-increment RMSE per fold;
5. at least 90% support coverage;
6. paired response over every informative origin/horizon, not only first
   divergence;
7. paired-response NRMSE and an improvement over the fitted action-blind
   backbone;
8. positive R/Z response direction on at least 80% of rows whose true R/Z
   response exceeds the frozen `0.02 mm` signal floor; lower-signal rows use
   absolute error and do not enter cosine counts;
9. endpoint/terminal cross-horizon consistency at 2--8 ms;
10. explicit descriptive candidate-value/tie/always-plus results, which do
    not qualify the model because this development bank has no balanced
    better-sign reversals.

All component comparisons use frozen physical scales. Raw metres and amperes
are never placed in one unscaled maximum. Candidate B must independently pass
all gates, improve worst paired-response NRMSE over A by at least 10%, and
regress no component/horizon endpoint, terminal or consistency p95 by more
than 10%. Candidate A is otherwise preferred.

Persistence and constant-velocity errors are descriptive baselines. The
action-blind improvement gate uses predictions from the separately fitted
action-blind backbone, not a zero-response shortcut.

## Evidence and independent audit

Primary execution writes:

- `preflight.json` before fitting;
- `oof_predictions.json`, with every candidate/fold/family/origin/horizon
  truth and prediction;
- `result.json` with per-fold metrics, gates and selection;
- `selected_model.json` only if a candidate is eligible.

The independent audit performs no fit. It rereads the config, source compact
truth and OOF ledger, verifies every row/key/truth/action diagnostic, then
recomputes componentwise metrics, paired metrics, gates, selection and route.
A same-code deterministic refit is not accepted as the independent audit.

## Counts, routes and stop rule

The maximum is two candidates, eight folds, sixteen candidate fold fits,
eight action-blind fold fits, three fixed TCN seeds per TCN fold and at most
one final selected full-development fit. TSC calls, resets, plant advances,
calibration reads and blind reads are zero.

If readiness fails, the route is `...PREFIT_READINESS_FAIL_NO_FIT`. If no
candidate is eligible, no artifact is emitted and calibration/holdout remain
closed. Only one zero-fit failure attribution is allowed. A demonstrated
support deficit may authorize one separately frozen targeted data identity;
otherwise this model/action-data class closes. No third model, larger
network, hyperparameter search or gate relaxation is allowed.

A development PASS emits one shadow artifact and authorizes only a separately
frozen `c00--c03` calibration stage. It does not authorize `v00--v03`, a
tube, authority, capture, recovery, controller, MPC, waypoint/path, R_mid
crossing, adaptation, expert data or deployment.
