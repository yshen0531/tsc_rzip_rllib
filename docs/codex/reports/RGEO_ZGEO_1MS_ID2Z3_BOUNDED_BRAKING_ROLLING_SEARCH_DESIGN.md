# ID-2Z3 bounded braking rolling-search design

## Purpose

ID-2Z2 established two consecutive, finite canonical-source transport
decisions.  It did not establish a hold: the logically executed path reaches
state 77 after the second selected four-issue macro, while the retained
state-81 samples are look-ahead hold observations.  ID-2Z3 starts from that
exact logical state-77 causal prefix and asks one narrower control question:
can repeated measured decisions brake the source-local path into a finite,
coarse stabilization corridor?

This is still TSC-only empirical sequence search.  It fits no model, reads no
calibration or holdout data, and is not controller, recovery, recourse,
waypoint, position-generalization or R_mid-crossing qualification.

## Exact observation and action contracts

At every issue boundary the controller receives the exact, noiseless,
same-state paired-boundary `R_geo/Z_geo` and same-state `Ip`, together with all
post-1100-ms causal observations and controller-owned action/current history.
The next successor remains unknown before the action is issued.  Invalid or
unpaired boundary data fail closed.

All actions are exact absolute Card15 targets.  Every coil must satisfy
`|delta I| <= 0.3 A` per issue, with equality allowed, and retain at least
95 A of absolute-current headroom.  The stage adds no software queue and may
not rely on the legacy runner's silent clipping.  Issue `k` first affects
state `k+1`.

## Rolling experiment

The exact ID-2Z2 selected Round-B compact supplies states 0--77 and actions
0--76.  State 77, not the state-81 look-ahead endpoint, is the first ID-2Z3
decision state.

There are at most five decisions at states 77, 81, 85, 89 and 93.  At each
decision the stage constructs up to three fresh canonical-source full-prefix
branches:

1. hold the current exact target;
2. apply four exact `p03-forward` increments;
3. apply four exact `p07-minus` increments.

Before any reset, every constructed stream is checked for exact Card15
representation, per-issue slew and the unchanged 95-A headroom.  Hold is
mandatory; an inadmissible non-hold stream is recorded as an offline
exclusion and is never issued.  Every admissible branch then holds its
terminal target for eight more issues, so the
branch exposes four active effects and an eight-ms tail.  Only the first four
issues of the selected branch become part of the logical main path; the next
decision is reconstructed by replaying the complete selected causal prefix
from the canonical 1100-ms source.  Look-ahead hold states are never silently
promoted into executed main-path history.

The complete upper bound is 15 resets, 1,455 plant-advance attempts and 1,470
retained states.  Retry after any attempted advance is forbidden.  Every
sibling prefix in a round must match exactly, and every later selected prefix
must reproduce the prior selected logical path.

## Braking and stabilization gates

The matched hold branch defines the local counterfactual at each decision.
For each non-hold arm the audit computes:

- paired R/Z response over offsets 1--12;
- paired Ip response;
- source R/Z distance through the branch;
- one-ms R/Z step speed;
- terminal maximum speed over the last four effects;
- terminal source distance and Ip offset.

A braking arm is eligible only when all of the following hold:

1. execution, raw, prefix, boundary, Card15, slew and current gates pass;
2. peak paired R/Z response is at least 0.05 mm;
3. maximum paired Ip response is at most 150 A;
4. its terminal source distance is no more than 0.25 mm worse than matched
   hold;
5. its terminal four-state maximum R/Z speed is at least 0.01 m/s lower than
   matched hold.

Eligible arms are selected lexicographically by minimum terminal four-state
maximum speed, minimum terminal source distance, minimum terminal absolute Ip
offset and stable arm identifier.  If no braking arm is eligible, the stage
stops without inventing another macro.

After every completed branch, a coarse stabilization candidate is evaluated
over the final four effects.  All four must have source R/Z radial distance
at most 25 mm, one-ms R/Z speed at most 0.1 m/s and absolute source-relative
Ip at most 5% of source Ip.  This 25-mm corridor is a new, explicitly coarse
braking/stabilization discriminator.  It does not replace the historical
5-mm source short-hold gate and cannot be called a terminal or recoverable
set.  Reaching it stops the search and may authorize only a fresh-repeat and
recourse design.

If five decisions complete without reaching the coarse stabilization gate,
the route is a finite action-grammar failure.  It does not prove global
unreachability or failure of a learned controller.

## Safety, storage and evidence

Every novel successor retains the existing 2 mm R, 2 mm Z and 150 A empirical
post-action caps, 25-mm/5%-Ip inner preissue clearance and 50-mm/10%-Ip outer
hard envelope.  These are simulator exploration controls, not a certified
transition tube.  Any non-whitelisted interface, runtime, raw or safety
failure aborts the campaign and no later action is issued.

Before execution the server must have at least 140 GB free.  The estimated
raw cap is 90 GB and at least 50 GB must remain.  The completed ID-2Z1 and
ID-2Z2 compact evidence, reports and independent audits are tracked and
pushed; only their server `rollouts` subdirectories may be removed to satisfy
this gate.  That deletion is irreversible and must be recorded.

The independent audit must reparse every retained state and all five required
artifacts, reconstruct every outgoing Card15 action, recompute prefix checks,
braking metrics, selection, stabilization verdict, counters, bytes and
inventory digest, and reproduce the primary route exactly.

## Routes and authorization boundary

- input/offline/storage failure: zero TSC;
- execution/interface/raw/prefix failure: stop and preserve evidence;
- no eligible braking arm: finite grammar redesign required;
- budget exhausted without stabilization: finite braking grammar
  insufficient;
- stabilization reached: fresh-repeat and recourse design only.

No route authorizes model fitting, calibration/holdout access, a feedback
controller, MPC, recovery, waypoint/path execution, position atlas, R_mid
crossing, online adaptation, expert data, BC, DAgger or RL.
