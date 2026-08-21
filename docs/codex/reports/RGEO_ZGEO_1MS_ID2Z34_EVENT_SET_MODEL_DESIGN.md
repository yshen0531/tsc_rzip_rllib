# ID2Z34 bounded event-set response model design

## Purpose

ID2Z34 is a zero-new-TSC, server-only development fit over the eight
prospectively fit-eligible ID2Z33 signed branch families.  It does not read a
calibration or holdout identity.  The matched baseline and exact replay are
integrity references with zero fitting weight; every ID2Z32 row remains
forbidden.

The model predicts the finite response relative to the matched moving center
for effect ages 1 through 17, including active allocation, exact return and
delayed tail.  Current same-step R_geo/Z_geo/Ip remain exact observations;
future RZI and future actual current are forbidden.  Candidate target/action
streams and absolute effect clock are known causal inputs.

## Exactly two candidates

Candidate A is a phase-pooled, sign-specific finite response template.  It
aligns responses by effect age and averages the issue-50 and issue-56 rows for
each q axis and sign.  It makes one point prediction and is the deliberately
low-variance smooth baseline.

Candidate B has the identical point center, plus a sparse set-valued event
head.  The event rule is applied uniformly to every axis/sign/age cell:

1. the cross-phase R spread is at least 0.30 mm;
2. the immediately adjacent ages, when present, each have R spread at most
   0.10 mm;
3. no more than two of the 68 axis/sign/age cells may be admitted.

For an admitted cell, the output set is the point center plus the symmetric
per-output half-width needed to contain both development observations,
inflated once by 10% and a fixed numerical floor.  The event width is local;
it must not widen non-event states.  Candidate B is an empirical finite set,
not a calibrated transition tube, probability model, hidden-state proof or
Recourse set.

There is no hyperparameter search, phase-specific hand exception, third
candidate, neural-network capacity ladder or post-result gate change.

## Frozen development gates

Candidate A is eligible only if its maximum R point error is at most 0.30 mm,
its maximum Z point error is at most 0.10 mm and its maximum Ip point error is
at most 25 A.

Candidate B is eligible only if:

- exactly one or two isolated event cells are detected;
- all development observations are contained at event cells;
- maximum event R full width is at most 0.75 mm;
- outside event cells, maximum errors are at most 0.05 mm R, 0.05 mm Z and
  25 A Ip;
- the maximum outside-event scaled absolute error is at most 0.50 under
  scales 0.10 mm, 0.10 mm and 25 A;
- model payload, data-role counts and exact replay identity are deterministic.

Selection is minimum complexity: select A if A passes; otherwise select B
only if B passes.  If neither passes, the stage fails and may only design one
targeted fresh event/history data campaign.  It may not add model capacity.

## Authorization boundary

A development PASS freezes one model artifact and may design a fresh
calibration followed by an unopened whole-family blind holdout.  It does not
authorize feedback, Authority-L0, source capture, recovery, Recourse-L1,
waypoint/path control, position/history generalization or R_mid crossing.
Authority and Recourse remain parallel controller prerequisites.  A real
in-loop controller requires fresh model qualification, Authority-L0,
Recourse-L1 and the independent hard interface to pass together.
