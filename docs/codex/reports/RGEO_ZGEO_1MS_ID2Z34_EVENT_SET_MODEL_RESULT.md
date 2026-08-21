# ID2Z34 bounded event-set response model result

## Verdict

The server passed seven focused tests and the complete 697-test one-ms
regression suite.  ID2Z34 then fit exactly two frozen development candidates
with zero TSC, zero plant advances and zero calibration/holdout reads.
Independent recomputation agrees on
`ONE_MS_ID2Z34_EVENT_SET_MODEL_PASS_FRESH_QUALIFICATION_DESIGN_ONLY`.

The smooth point template failed its preregistered maximum-R gate: the
q_R-minus effect-age-13 cell has 0.319267 mm maximum point error, above the
0.300 mm cap.  This FAIL is retained; it is not repaired by averaging or a
global wider tube.

The sparse event-set candidate passed.  The uniform rule admitted exactly one
of 68 axis/sign/age cells, `q_r:minus` at effect age 13.  Its finite empirical
R full width is 0.704388 mm, below 0.750 mm, and contains both development
observations.  Outside that cell, maxima are 0.019447 mm R, 0.014427 mm Z and
0.95555 A Ip; the maximum scaled error is 0.1944675.  The set-valued candidate
is selected with payload SHA-256
`7f4ea48fc0117a77a23c7df378748a0cbac2f3194a6a47e254ba1bcd472df846`.

## Evidence

- Implementation revision:
  `e04aeb0811dcb81d1122a29a237d4c1aeaf86a1b`.
- Config SHA-256:
  `d682466c791b158ffada26aefcaae8d46f64b3f2434444a7a982e71bf9d3958b`.
- Primary SHA-256:
  `0c58ea1a8c1bc48c316dcf153de4ce7af326493371a6980cb707875349c6c641`.
- Independent SHA-256:
  `ecef293d6205cfbd5f1e88456e2f44f7ebc7a2b14796b975f3a61e40114e5f9d`.
- Fit families: eight prospective ID2Z33 branches.
- Zero-fit families: matched baseline and exact replay; all ID2Z32 rows remain
  forbidden.
- Models fit: two; TSC/plant calls: zero; qualification reads: zero.

## Boundary and next gate

This is a finite development selection, not calibrated uncertainty or a
transition tube.  The model has only seen one canonical moving-center history
at phases 50 and 56.  Its sparse set is indexed by observed action age and
does not prove whether the physical event follows absolute clock, action age,
or another causal history variable.

The next identity must freeze this payload and execute a fresh intermediate-
phase calibration followed, only if calibration passes, by an unopened
whole-phase blind family.  The model center and event cell may not be refit.
Calibration may only produce a preregistered bounded margin; blind failure
closes the model.  No feedback, Authority-L0, capture, recovery or Recourse
claim is opened by this result.
