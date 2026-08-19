# R_geo/Z_geo 1 ms ID-2Z6 early-root branch-teacher design

Date: 2026-08-19

## 1. Decision and scope

ID-2Z5 is final as
`ONE_MS_ID2Z5_DEVELOPMENT_DATA_INSUFFICIENT_ACTION_SUPPORT_REVIEW_REQUIRED`.
Its partial paths remain zero-fit design evidence.  ID-2Z6 is a new,
prospective simulator-only identity.  It tests whether the already observed
but phase-misaligned B/F effects become useful when braking starts earlier
and the macro choice is recomputed from exact current observations.

The final goal remains the fixed-1100-ms, exact-observation, one-ms,
slew-limited two-axis waypoint/path controller and later repeated
bidirectional R_mid crossing with continuous belief.  ID-2Z6 is only an
early-root finite branch teacher and development-window discriminator.  It
cannot certify hold, recovery, a controller, waypoint tracking, model
generalization, online adaptation, or reachability.

## 2. Evidence motivating the start and grammar

The exact ID-2W2 p03 stride-one prefix has no state through state 61 with
R/Z step speed at or below 0.1 m/s.  State 49 is selected prospectively
because its source distance is 23.3819 mm and its speed is 0.2271 m/s.  It
has 1.1727 mm more capture-distance margin than ID-2Z5 state 61.  This is a
candidate start, not evidence that state 49 is capturable.

ID-2Z5 showed complementary finite effects rather than a zero-action result:
B12-F12 reached 25.6655 mm and 0.112947 m/s, whereas faster B/F alternation
kept position closer but retained substantially more speed.  The failure is
therefore treated as a fixed open-loop phase failure until ID-2Z6 says
otherwise.

The only active tokens are:

- `H`: hold the current exact Card15 target;
- `B`: one exact p07-minus increment;
- `F`: one exact p03-forward increment.

Each decision compares exactly `HHHH`, `BBBB`, `FFFF`, `BBFF`, and `FFBB`.
No runner clipping, arbitrary 14-D action, or post-result token is allowed.

## 3. Finite truth-recentered branch contract

The three decision roots are logical states 49, 53, and 57.  Each branch is
reconstructed from the canonical 1100-ms source by replaying the entire
selected causal prefix.  A round executes one four-issue candidate macro and
then holds its attained target through issue 68, retaining state 69.  The
winning macro contributes only its four issued actions to the next logical
prefix; the next round is generated only after the previous round has been
fully classified.

Every issue is preceded by the exact/noiseless same-step paired-boundary
R_geo/Z_geo and Ip observation plus the complete post-takeover causal
observation and controller-owned action history.  The future successor is
unknown before issue.  The branch lookahead is causal in simulated time: it
uses rejected digital-twin futures, never a future state from the selected
logical path.  It is wall-clock-slow canonical-source shooting, not a
qualified sub-millisecond or arbitrary-snapshot Oracle.

The campaign contains at most 15 branch rollouts plus one zero-fit replay of
the final selected three-macro sequence.  It is capped at 16 resets, 1,104
advance attempts/gotsc calls/verified successors, 1,120 retained states, and
5,600 required raw artifacts if all paths complete.  Retry after any plant
advance attempt is forbidden.

## 4. Three distinct envelopes

The following claims are deliberately separate.

1. **Terminal capture set:** six states 64--69 must all have source R/Z
   Euclidean distance at most 25 mm, R/Z step speed at most 0.1 m/s, and
   absolute source-relative Ip at most 5%.
2. **Simulator-development shell:** before a novel issue, each R/Z component
   must be within 35 mm of source and Ip within 7.5%.  This leaves 15 mm per
   axis and 2.5% Ip to the unchanged hard envelope.  The separate empirical
   post-successor trips remain 2 mm R, 2 mm Z, and 150 A Ip.  The numerical
   guard is a prospective simulator-development risk limit, not a plant
   tube, recovery set, or safety proof.
3. **Hard envelope:** each R/Z component remains within 50 mm of source and
   Ip within 10%, with all existing Card15, absolute-current, slew,
   boundary, solver and abnormal-state hard stops unchanged.

Entering the development guard or exceeding an empirical successor trip
stops that branch before another issue.  It never authorizes continuation by
calling hold a recovery action.

The former 100-A scalar heuristic is not a physical invariant.  ID-2Z6
instead checks exact candidate-horizon action-set reserve: every target must
be exactly representable and inside absolute current limits; at each selected
root all five four-step macros must be representable; and the selected
successor prefix must leave `H`, `B4`, and `F4` exactly representable for the
next planned round.  No clipping or expected future learning may satisfy
this gate.

## 5. Selection and control-utility gate

All five branches in a round use the same selected prefix and common state-69
terminal horizon.  Selection is not distance-first.  For each terminal state
64--69, compute the three normalized quantities

```text
source_RZ_distance / 25 mm
RZ_step_speed / 0.1 m/s
abs(source_relative_Ip) / 5%
```

The branch score is the maximum across all three quantities and all six
terminal states.  Capture candidates precede non-capture candidates; the
remaining order is minimum score, minimum terminal-window maximum distance,
minimum terminal-window maximum speed, minimum terminal-window maximum Ip
fraction, then stable arm id.  A non-hold arm is eligible only if it improves
the matched-hold score by at least 0.02 or itself satisfies the full capture
gate.  Transient single-state improvement is insufficient.

All siblings must complete or end only in an allowed prospective
simulator-development safe stop.  A round cannot select a stopped arm.  If
the matched hold is incomplete, or no complete non-hold arm is eligible, the
teacher stops without opening the next round.

ID-2Z6 passes the finite teacher gate only when all three rounds select an
eligible arm, all selected prefixes are exact, the final selected sequence
has a byte-independent checked-trajectory replay, and either:

- the selected path satisfies the six-state terminal capture gate; or
- its terminal worst normalized score improves on the canonical state-49
  all-hold path by at least 0.25.

The second route is only sustained joint progress and development-data
readiness.  It is not capture or recovery.

## 6. Prospective data role

The fit unit is a complete causal action-conditioned window, not an entire
117-state open-loop path.  For this campaign, each complete branch contributes
its fully observed state49--69 window to development.  A later safe stop does
not retroactively invent or delete an already complete window; an incomplete
window is censored and has zero fit weight.  All sibling branches are
retained, including losers.  The final replay has zero fit weight and does
not increase the number of independent histories.

ID-2Z6 data may be used only as prospective development data after the full
raw independent audit passes.  Calibration, blind holdout, expert/teacher
labels for deployment, BC, DAgger, RL, controller qualification and safety
claims require fresh identities.  ID-2Z5 remains forbidden from fitting.

## 7. Routes and irreversible stop rules

- Offline/config/action/reserve/storage failure: zero TSC.
- Prefix, issue/effect, Card15, readback, raw, boundary, runtime or hard
  interface mismatch: stop the whole stage; do not emit a scientific FAIL.
- A prospective development-shell stop is branch evidence only.  It cannot
  be selected and cannot weaken any gate.
- No eligible arm in any round, no sustained final improvement, or replay
  mismatch closes this exact early-root B/F/H teacher identity.  Do not add
  a deeper fixed sequence or a larger network.
- A clean finite PASS authorizes only: (a) freezing the selected candidate
  for fresh replay/Recourse-L1 design, and (b) a separately frozen bounded
  comparison of a stable low-order candidate-outcome model against the same
  backbone with a small persistent GRU residual, provided the prospective
  data-readiness count is adequate.
- If the B/F/H teacher fails, the next route is one bounded action-basis /
  authority review.  It is not another B/F depth ladder and does not imply
  global plant unreachability.

No result may be reinterpreted after seeing TSC output.
