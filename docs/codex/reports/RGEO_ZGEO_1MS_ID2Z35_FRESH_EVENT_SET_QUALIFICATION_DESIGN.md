# ID2Z35 fresh event-set qualification design

## Purpose and immutable model

ID2Z35 is one staged fresh-TSC qualification of the frozen ID2Z34 payload
`7f4ea48fc0117a77a23c7df378748a0cbac2f3194a6a47e254ba1bcd472df846`.
The point centers, q_R-minus/effect-age-13 event cell and its development
half-widths are immutable.  No model coefficient, event location, threshold
or candidate class may change after calibration.

The experiment uses the same exact moving-center Card15 allocation and
eight-issue signed branch plus eight-issue exact return semantics as ID2Z33,
but on new intermediate phases.  Phase 52 is calibration; phase 54 is a
whole-phase blind family and must remain unexecuted unless every calibration,
replay, interface, raw and model gate passes.

## Rollout order and data roles

1. one fresh matched moving-center baseline, zero fit weight;
2. phase-52 q_R/q_Z, plus/minus calibration families;
3. one phase-52 q_Z-plus exact replay, zero fit weight;
4. only after calibration PASS, four unopened phase-54 blind families.

The maximum is ten resets and 730 plant advances.  Each complete rollout has
73 advances and 74 states.  There is no retry or resume after any plant
advance.  All siblings remain together by phase.  The calibration and blind
rows are qualification evidence only and may never be used to refit this
artifact.

## Model evaluation

For each branch and effect age 1--17, the observed response is the difference
from the same-state fresh baseline.  At the single frozen event cell
`q_r:minus, age 13`, the observation must lie inside the ID2Z34 development
set without widening it.

Every other cell is a point-center residual.  Calibration requires maxima no
larger than 0.05 mm R, 0.05 mm Z and 25 A Ip.  If it passes, a non-event tube
is frozen once as 1.25 times the larger of the development and phase-52
absolute residual maxima plus fixed numerical floors.  Its half-width caps
are 0.075 mm R, 0.075 mm Z and 30 A Ip.  The phase-54 blind family must have
100% cell containment under that frozen non-event tube plus the unchanged
event set.

This deliberately tests whether the action-age-indexed empirical event set
survives a new absolute phase.  A large response at another age is a model
FAIL; it may not be relabelled into a second event cell after observation.

## Execution and safety

Before TSC, all ten streams must pass exact action separation, Card15
serialization, exact return, `<=0.3 A` per-coil slew, absolute-current,
storage and canonical-prefix gates.  Runtime uses same-step paired-boundary
R_geo/Z_geo and Ip truth, issue k to effect state k+1, no added software queue
and fail-closed post-successor empirical/hard envelopes.  Exact action return
is not state recovery.

Any calibration execution, raw, prefix, replay, event containment or
non-event cap failure stops before blind.  Any blind failure preserves the
frozen model FAIL and authorizes only a bounded event-coordinate redesign; it
does not permit refit on blind rows.

## Claim boundary

PASS would certify only a finite canonical-history phase-52/54 calibrated
response set.  It would not certify feedback, Authority-L0, capture,
recovery, Recourse-L1, waypoint/path tracking, position/history
generalization or R_mid crossing.  Those remain independent gates.
