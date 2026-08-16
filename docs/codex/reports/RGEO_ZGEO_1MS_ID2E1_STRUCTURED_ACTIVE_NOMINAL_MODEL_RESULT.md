# R_geo/Z_geo 1 ms ID-2E1 structured active-nominal model result

Date: 2026-08-17 Asia/Shanghai

Design / implementation / independent-audit revisions:
`02a7f113 / 59d2790a794eef4f8ff9c73f375068aed08f310c /
d8bb8dc33f8bf09fb86e043d6645dceda06de220`.

## Execution and integrity

The server passed `bash -n`, Python compilation, 7/7 focused ID-2E1 tests
and 147/147 complete one-ms regression tests.  The model stage performed
zero reset, `gotsc`, TSC or plant advance.  It read ID-2D1R1 development
records, fit the frozen grouped candidates, and stopped before reading any
ID-2C2 evaluator trajectory.

Primary result SHA-256 is
`b0fb654f9f1e5a1f947740a1c5012669f863518dcfd975f00d8c8cb642e38062`.
The strengthened independent entrypoint separately rebuilt all feature
matrices, refit every fold and recomputed every development metric.  It
selected no model and agreed to maximum numeric difference
`2.7755575615628914e-17`; its SHA-256 is
`80b31220b0d7a3d89a0652d4da2b98b6a31ff11d85bd7f9bc4a90fd2f1523078`.

Final route:
`ONE_MS_ID2E1_GROUPED_DEVELOPMENT_MODEL_FAIL_ROUTE_REVIEW`.
No model artifact was emitted and `evaluator_opened=false`.

## Model result

No smooth p04/p07 candidate passed all five whole-schedule folds.

| candidate | best fold NRMSE / improvement | worst fold NRMSE / improvement | result |
|---|---:|---:|---|
| fixed-pole odd | 0.9674 / +3.26% | 1.0288 / -2.88% | FAIL |
| fixed-pole signed/even | 0.9451 / +5.49% | 1.0410 / -4.10% | FAIL |
| fixed-pole signed/even/time | 1.0561 / -5.61% | 1.2188 / -21.88% | FAIL |
| FIR16 signed/even | 0.8057 / +19.43% | 1.9159 / -91.59% | FAIL |

The p09 event channel is qualitatively different: its development response
NRMSE is `0.1717123`, improvement over zero response is `80.36%`, R/Z error
p95 is `0.006280 mm`, Ip error p95 is `0.3530 A`, and both peak directions
pass.  Therefore the failure is not a blanket inability to fit any action
response or an excessively strict absolute-state gate.

## Load-bearing forensic pattern

The p04/p07 failure is dominated by isolated, sign-dependent excursions at
absolute states 19 and 27.  Eight minus-sign cells contain one or two states
above 0.3 mm; their event vectors cluster near `(-0.6 to -0.70 mm,
+0.25 to +0.28 mm)`.  Every plus-sign cell remains below 0.161 mm.  Examples:

- p04-minus issue16 duration4: 0.6332 mm at state19;
- p04-minus issue22 duration2: 0.7377 mm at state27;
- p07-minus issue16 duration2: 0.7452 mm at state27;
- p07-minus issue16 duration4: 0.6483 mm at state19 and 0.7273 mm at state27;
- all p07-minus issue22 durations: 0.6704--0.7498 mm at state27.

This explains why an odd model stays near the zero-response comparator, why
adding a linear even/time interaction does not help, and why the flexible
FIR extrapolates badly on the unseen issue22-duration1 fold.  It does not yet
prove whether the excursions are a repeatable hybrid plasma/boundary event,
a deterministic TSC numerical branch, or a causally predictable threshold
of action history.  The boundary contract remained valid and the source raw
audit passed, so they cannot be discarded as reporting noise.

## Required route review

Do not open ID-2C2, loosen gates, select a runner-up, or train a larger
GRU/TCN on this result.  The next recommended discriminator is first a
zero-new-TSC raw event-attribution audit of ID-2D1R1: full paired-boundary
shape/extrema continuity, state19/state27 timing, action-age/cumulative-sign
conditions, actual current/Ip and near-matched non-event cells.  Its outcome
should route prospectively to one of two paths:

1. if a small causal event state is separable, design a hybrid continuous
   residual plus event/hazard model and fresh event-cell validation;
2. if event identity or repeatability is unresolved, run a small fresh
   matched replay sentinel before any new model class.

If allowed causal features contain indistinguishable event/non-event cases,
the route needs richer history/latent-state identification rather than a
post-hoc classifier.  This is now a genuine model/experiment architecture
decision, so development pauses for user review.

ID-2E1 is not a calibration, holdout, tube, controller, MPC, recovery,
transport, crossing or global reachability result.  The final safe two-axis
path/waypoint goal remains unchanged.
