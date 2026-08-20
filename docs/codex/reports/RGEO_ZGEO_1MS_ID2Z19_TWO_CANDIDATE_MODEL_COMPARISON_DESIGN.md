# ID-2Z19 two-candidate full-horizon model comparison design

Date: 2026-08-20

Identity: `rgeo-zgeo-1ms-id2z19-two-candidate-model-comparison-v1`

## Purpose and boundary

ID-2Z19 is the one development-model comparison authorized by the clean
ID-2Z18 data PASS. It runs only on the server, executes zero TSC/plant steps,
and reads only the 14 positive-weight ID-2Z18 development histories. The two
zero-weight replays authenticate source data but never enter a fit or metric.
The declared `c00--c03` calibration and `v00--v03` blind histories remain
unexecuted and unread.

This stage asks a narrow question: can a bounded, causal model predict
moving-nominal F/p06/p08 dynamics over 1/2/4/8 ms across whole unseen history
families well enough to justify a fresh calibration design? It does not test
authority, capture, recovery, a controller, MPC, waypoint/path tracking or
R_mid crossing.

## Observation and causality contract

At each prediction origin the same-step paired-boundary R_geo/Z_geo and Ip
are exact/noiseless observations. The full takeover-era causal observation,
issued Card15 and measured 14-coil-current histories are available. Future
candidate Card15 targets are known; future measured current and future RZI
are forbidden.

Allowed causal features are frozen to:

- current RZI relative to the authenticated source;
- causal one- and four-step RZI differences;
- current measured 14-coil current projected onto the frozen rank-three F/A/E
  action subspace;
- current issued target and delta in that same action coordinate;
- stable fixed-pole summaries of prior issued deltas;
- absolute issue time and prediction horizon;
- exact candidate future target/delta summaries through the requested
  horizon.

Wire current, sprsina, family/pair/sign/role/token labels, evaluator response,
future truth and future measured current are forbidden model inputs. The
current exact RZI is not a latent state estimate; latent memory represents
only unresolved dynamics/history and future response.

## Whole-history folds

There are eight fixed folds. Six hold out both signed siblings of one complete
pair (`d00` through `d05`). Two hold out one complete baseline history
(`baseline_full_f` or `baseline_half_f`). No state or window crosses a family
boundary. Training rows are complete causal windows with origin issues
16--57 and horizons 1/2/4/8; a window whose endpoint is absent is censored,
not a label.

The two exact replays have statistical weight zero in every fold and in the
final fit. Folds, scales, action basis, normalization and all gates are fixed
before any model result is inspected.

## Exactly two candidates

### Candidate A: stable regularized LPV

Candidate A is one shared, ridge-regularized multi-horizon LPV map. It uses
the frozen causal features above, fold-local centering/scaling and a fixed
stable action-memory pole set. One shared feature map predicts normalized
RZI displacement for horizons 1/2/4/8; horizon and future-action summaries
are inputs rather than eight unrelated heads. The only persistent internal
memory is the fixed-pole stable convolution. Ridge is selected from one
prospectively frozen value, not a grid.

### Candidate B: the same LPV plus a small causal GRU residual

Candidate B retains Candidate A unchanged and adds one bounded GRU residual.
The GRU width is four, its history runs chronologically from takeover through
the current origin without rewriting earlier context, and its residual head
uses the same known future-action/horizon summaries. Three fixed seeds are
averaged. Residual output is capped in normalized coordinates. No larger
network, TCN alternative, architecture sweep, seed selection or post-result
capacity increase belongs to this identity.

Candidate A is preferred whenever eligible. Candidate B may win only when it
is independently eligible, improves the worst paired-response NRMSE by at
least 10%, and worsens no worst endpoint p95 by more than 10%.

## Metrics and gates

All predictions are truth-recentered at their current origin. Each candidate
must pass all eight held-history folds:

1. finite predictions for every complete 1/2/4/8 ms endpoint;
2. endpoint R/Z p95 no larger than `0.50/0.90/1.60/3.00 mm` and Ip p95 no
   larger than `35/60/110/200 A` at horizons 1/2/4/8;
3. one-step R/Z velocity-error p95 no larger than `0.50 m/s`;
4. normalized endpoint RMSE less than `0.75` of the zero-displacement
   predictor in every fold;
5. in each signed-pair fold, paired-response NRMSE below `0.75`, positive
   R/Z endpoint-direction cosine at all four horizons, and correct better-sign
   source-directed value ranking at least three of four horizons;
6. maximum normalized value-regret at most `0.25`, where value is derived
   only from predicted/true endpoint source distance, origin-to-endpoint
   finite-horizon average speed and Ip fraction using frozen
   `25 mm / 0.1 m/s / 5%` scales;
7. fold-local feature rank and condition are reported; any nonconstant
   feature condition above `1e6` makes the candidate ineligible;
8. compared with the action-blind ablation of the same backbone, aggregate
   paired-response squared error must improve by at least 20%.

These are development-selection gates, not calibrated safety bounds. The
speed scale is deliberately reported because earlier model objectives hid
ranking failures behind position error. A PASS emits one full-development
artifact and opens only a separately frozen fresh calibration campaign using
the unchanged artifact/evaluator. A FAIL emits no model and stops before
calibration or holdout.

## Counts and stop rule

The fixed maximum is two candidates, eight folds per candidate, 16 candidate
fold fits, three fixed GRU seeds per GRU fold, and at most one final full-data
fit. New TSC resets, plant advances, calibration reads and blind-holdout reads
are all zero.

If neither candidate is eligible, this identity ends without adding model
capacity or changing a gate. The next decision must distinguish insufficient
history support, nominal/response mismatch and model-class failure before any
new TSC or model is authorized.
