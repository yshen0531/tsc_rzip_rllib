# R_geo/Z_geo 1 ms ID-2M1 bounded event/innovation model design

Date: 2026-08-18 Asia/Shanghai

## Purpose

ID-2M0 retained the ID-2L1 `stable_signed_even` model as a useful local
action-response component while locating its formal short-horizon failure in
a small number of conditioner hold/return/delayed-tail transitions. ID-2M1
tests whether a deliberately small causal structure closes that gap. It is a
development comparison, not calibration, uncertainty qualification or a
controller.

## Frozen data and folds

Use exactly the 40 unique ID-2K1 development cells and the four unchanged
whole-history folds from ID-2L1. Critical replays retain zero fit weight.
ID-2M0 predictions are evaluator evidence only; they are not new training
labels. ID-2I1, ID-2J0, ID-2C2, calibration and holdout records remain
forbidden.

The issue/effect rule remains issue `k` to state `k+1`. Current same-step
paired-boundary R_geo/Z_geo and same-step Ip are exact, noiseless causal
observations before issue. Future R_geo/Z_geo/Ip and future actual/readback
current are unavailable. Candidate Card15 actions are known prospectively.

## Common separated model

Both candidates predict normalized one-step R_geo/Z_geo/Ip increments as

```text
delta[k] = nominal[k] + action_event_features[k] B
           + optional_bounded_innovation[k] C
```

The nominal is a 34-step time-indexed intercept. It is not jointly allowed to
absorb arbitrary action coefficients. For each training fold, exact causal
transition duplicates are first collapsed. At every issue, feature and
target means are removed; the response coefficients are fitted only to the
within-issue centered rows plus the frozen issue-25 matched-baseline paired
loss. The nominal is then recovered from the issue mean. This produces an
explicit nominal/response separation without history, sign, direction,
conditioner or probe labels.

The common causal action features are:

- the existing three-dimensional exact Card15 action coordinates;
- signed and absolute level/edge fixed-pole memories at
  `0.0, 0.5, 0.8, 0.95`;
- signed and absolute exact edge lags one through four; and
- signed and absolute current-level dwell features capped at age four.

All action memory is finite or has a fixed stable pole. Coefficients use one
prospectively frozen ridge value; there is no sweep.

## Two candidates only

1. `separated_event_memory`: the common nominal plus causal action/event
   model.
2. `separated_event_bounded_innovation`: candidate 1 plus a 12-dimensional
   causal observation vector containing current R_geo/Z_geo/Ip displacement
   from the source, last-step and four-step mean velocity, and current
   actual-minus-previous-issued current projected into the three admitted
   action coordinates.

For teacher-forced one-step evaluation the second candidate uses the exact
current observation at each issue. For any multi-step segment, the vector is
sampled only at the segment origin and decays with the fixed pole `0.8`;
future truth or readback is never substituted. The correction therefore
cannot create an unstable recurrent state. It is a bounded development
approximation, not online learning.

## Evaluation and gates

The original ID-2L1 cell-weighted teacher, 1/2/4 ms recenter, state-25 free
rollout, paired-response NRMSE, peak-direction and catastrophic gates remain
unchanged for direct comparability. ID-2M1 additionally reports, per fold:

- exact unique-causal-key p95 for each recenter period;
- every unique one-step event above `0.300 mm` R;
- worst unique one-step absolute error capped at
  `0.600 mm R / 0.300 mm Z / 30 A Ip`;
- issue-25--28 probe-window maxima; and
- feature rank, singular values and condition after scaling.

The old ID-2L1 FAIL is never reinterpreted. If both candidates pass, select
the simpler event-only model. If only the bounded-innovation candidate passes,
select it. A candidate that uses future fields, evaluator labels or produces
non-finite/unstable behavior is ineligible regardless of metrics.

## Route boundary

A PASS emits one development model artifact fitted on all 40 unique cells.
It authorizes only a fresh calibration design and a new unopened
whole-history holdout design. It does not authorize using those data before
their identities are frozen, and it does not authorize TSC, authority,
recovery, controller, MPC, transport, crossing, adaptation or RL.

If neither candidate passes, stop this model family. The next route is a
fresh matched conditioner/return-tail transition design, not a larger neural
network or a relaxed post-result gate.
