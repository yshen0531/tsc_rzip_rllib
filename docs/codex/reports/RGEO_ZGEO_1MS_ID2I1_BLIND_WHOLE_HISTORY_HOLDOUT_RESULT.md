# R_geo/Z_geo 1 ms ID-2I1 blind whole-history holdout result

Date: 2026-08-17 Asia/Shanghai

## Verdict

ID-2I1 is final as
`ONE_MS_ID2I1_BLIND_WHOLE_HISTORY_HOLDOUT_FAIL_ROUTE_REVIEW`.

The execution/data identity passed cleanly: 32/32 rollouts, 1,088/1,088
verified one-ms plant advances, 1,120 states, all eight whole-history groups
and all 16 exact replay pairs.  Primary and independent raw parsing agreed on
5,600 required files, 65,960,074,880 bytes and inventory digest
`66bf9ddcb8733183d938253c520d46b5eac5a1f6e038baf60168f13119036f78`.
No runtime, solver, boundary, Card15, current, raw, replay or reporting error
caused the scientific failure.

## Blind result

The exact ID-2G1R1 TCN and ID-2H1 widths were loaded without fitting,
retraining, tuning, selection or recalibration.  The blind result was:

- joint frozen-width containment: `0/8` complete groups, required `>=7/8`;
- absolute-width containment considered alone: `3/8` groups;
- paired-response-width containment considered alone: `4/8` groups;
- matched-response NRMSE: `1.109016151`, required `<1.0`;
- positive peak R/Z response direction: `5/8`, required `>=7/8`.

All eight groups remained within the wider catastrophic caps.  The worst
absolute errors were `0.728276 mm R / 0.311029 mm Z / 23.299748 A Ip`, or
`1.227x / 1.293x / 0.969x` the calibrated widths.  The worst paired-response
errors were `0.702798 mm R / 0.270381 mm Z / 11.340055 A Ip`, or
`1.011x / 1.135x / 1.469x` the calibrated widths.  Thus the result is not a
catastrophic plant excursion, but the calibrated uncertainty and action-
response generalization are not valid for the blind history families.

The independent implementation reparsed the full raw tree and reproduced all
metrics and the FAIL route with maximum numeric difference zero.

## Interpretation

The useful distinction is between nominal-state prediction and
action-conditioned response.  Absolute errors exceeded the calibrated tube
only modestly, while three groups predicted the peak R/Z response in the
wrong half-plane and the aggregate paired response was worse than the
action-blind normalization.  The current global TCN has therefore not learned
a sufficiently robust history-conditioned signed response map for unseen
event timing/composition.

This does not prove that machine learning is inappropriate.  It demonstrates
why development folds and calibration families cannot replace a blind
whole-history test.  It also does not prove global plant unreachability,
controller failure, insufficient two-axis authority or impossibility of a
more structured learned model.

## Route recommendation and pause

Do not tune against ID-2I1, widen its gates after the result, start MPC, or
increase neural-network size.  Freeze ID-2I1 as consumed evaluation-only
evidence.  The next authorized decision should be a zero-new-TSC,
zero-fitting post-holdout attribution audit that separates:

1. nominal continuation error from paired action-response error;
2. sign/direction/duration effects from conditioner timing and combinations;
3. causal history-feature distance/support from model error;
4. ensemble disagreement from realized error, to test whether uncertainty
   can detect the blind failure before an action is issued.

If the failure is concentrated outside development support, the next data
stage should be a prospectively split history-composition campaign with
entire families withheld.  If equally close supported histories fail or the
ensemble is confidently wrong, the model should change to an explicit
time-indexed nominal continuation plus stable low-order action-memory state
and context-gated residual; a TCN may remain only as a small residual.  In
both cases, a fresh untouched holdout is required before any controller-grade
tube, authority or recourse stage.

This result is the requested pause point for route review.  ID-2C2 remains
unread and no controller, MPC, transport, R_mid crossing, online adaptation
or RL stage is authorized.
