# Fixed-1000 Authority A0 sequential feedback design

## Identity and purpose

This is a new fixed-1000 identity.  It does not inherit any fixed-1100
scientific result.  The byte-frozen V0 response-set model has already passed
development, fresh calibration, and unopened mixed-history blind evaluation.
A0 asks the next narrower question: can that fixed model nominate two
successive, control-aligned, exact-Card15 macros when the second nomination is
made only after observing the real state produced by the first?

A0 is an `Authority-L0` sentinel.  It is not path tracking, capture, hold,
Recourse-L1, a transition tube, or a controller qualification.

## Causal observation and decision contract

The authentic source is `1000ms`.  Before each issue the current same-step
paired-boundary `R_geo/Z_geo` and same-step `Ip` are exact/noiseless
observables.  The full controller-owned causal state/action/current history
from 1000 ms is available.  No future TSC state, future actual current, or
rejected-branch result may enter a decision.

Each macro is the already qualified D1 twelve-issue ramp/plateau/exact-return
sequence.  At issue 24, the controller records the current state, creates the
rollout's relative waypoint, and uses only the frozen V0 h8 centers to choose
the candidate with maximum dot product against the remaining R/Z error.  At
issue 36 it reads the newly observed state and repeats the same calculation.
The candidate set is exactly `even_plus/even_minus/odd_plus/odd_minus`; ties
are resolved lexicographically.  The frozen V0 file is neither refit nor
widened.

Two relative waypoint commands are preregistered:

- positive path: `(+0.8 mm R, +0.2 mm Z)`;
- negative path: `(-0.9 mm R, -1.0 mm Z)`.

The waypoint is anchored to the exact state observed at issue 24 of that
rollout.  Thus A0 tests local sequential displacement authority, not tracking
an absolute machine coordinate.

## Six-rollout matrix and budget

Every rollout starts from a fresh authentic 1000-ms reset and advances exactly
60 one-ms issues when complete:

1. matched q0 baseline;
2. positive path, first nomination only;
3. positive path, first and second nominations;
4. negative path, first nomination only;
5. negative path, first and second nominations;
6. integrity replay of the complete positive path.

The hard budget is six resets and 360 advance attempts/gotsc calls/verified
successors.  No retry is allowed after any advance attempt.  All action
targets, Card15 fields, issued and observed slew, current bounds, paired
boundary, Ip, solver/runtime state, and the 50-mm/10%-Ip hard envelope remain
fail closed.  A macro must return exactly to q0 before a following macro.

## Scientific comparisons and gates

The first nomination is measured against the q0 rollout at h4/h8 (states
28/32).  The second nomination is measured against the corresponding
first-only rollout at h4/h8 (states 40/44).  Each measured R/Z/Ip response must
lie inside the frozen V0 center plus halfwidth for the selected candidate.
Each decision must achieve at least `0.10 mm` measured h8 projection along the
remaining-error direction recorded before that decision.  Absolute paired Ip
response must not exceed 400 A.

The complete positive replay must be exact for checked R/Z/Ip, 14-coil,
48-wire, action and semantic-artifact fields.  All completed paths retain a
q0 active target and a 16-state post-second-decision tail through state 60.

PASS establishes only finite two-decision, two-waypoint-direction Authority-L0
and validates the frozen V0 as a candidate nominator in these histories.  It
may authorize a separately frozen moving-reference feedback/Recourse design.
FAIL closes this exact macro/phase/model nomination contract; it does not prove
global plant unreachability and must not trigger model-capacity expansion.

## Data roles

All A0 trajectories are zero-fit qualification evidence.  They may not be
used to refit V0, train a controller, expert/Oracle/BC/DAgger/RL data, or tune
gates.  The replay has integrity-only weight.  A future model identity would
need a prospectively declared role and fresh calibration/holdout.

