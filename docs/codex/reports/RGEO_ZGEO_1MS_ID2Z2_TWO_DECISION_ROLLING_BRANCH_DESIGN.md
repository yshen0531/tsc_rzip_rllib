# ID-2Z2 two-decision rolling branch design

## Purpose

ID-2Z1 established that p03-forward4 and p07-minus4 have finite persistent
transport utility after one exact p03-level64 prefix.  It did not establish a
hold: the selected p03-forward4 path was already moving away again during its
four held effects.  ID-2Z2 therefore replaces another manual ramp-depth stage
with two actual receding decisions.

This is a bounded canonical-source TSC branch search, not a fitted model or a
controller qualification.  Each branch replays its entire causal prefix from
the fixed 1100 ms source; only the selected first four-issue macro is carried
into the next logical decision.  Rejected futures are branch predictions and
do not reveal the future of the selected logical path.

## Decision state and candidate alphabet

The common initial prefix is the independently audited ID-2Z1 selected path:
q0 at issue0, p03-minus stride-one levels1--64 at issues1--64, and p03-forward
levels65--68 at issues65--68.  States0--69 and actions0--68 must match both
ID-2Z1 replays wherever the frozen compact evidence provides a reference.

Round A branches before issue69 from exact state69.  It evaluates seven
eight-issue suffixes through state77:

1. hold the current exact target;
2. p03 forward by four exact one-level increments;
3. p03 unwind by four exact one-level increments;
4. p04-minus by four exact one-level increments;
5. p04-plus by four exact one-level increments;
6. p07-minus by four exact one-level increments;
7. p07-plus by four exact one-level increments.

The chosen Round-A macro occupies issues69--72.  Round B then treats its
state73 as the next exact decision state, replays that selected causal prefix
from the canonical source, and evaluates the same seven relative alternatives
at issues73--76 followed by four holds through issue80/state81.  Existing
virtual-coordinate offsets remain active; a new macro is composed with the
current exact Card15 target rather than silently replacing the previous
allocation.

All 49 possible Round-A/Round-B target combinations are enumerated offline.
A Round-B alternative is admissible only if its exact target stream remains
representable, every per-coil issue delta is at most 0.3 A, and the absolute
current headroom is at least 95 A.  The runner's legacy clipping is never an
action constructor or fallback.  An invalid alternative is recorded and
excluded before plant execution; it cannot be selected.

## Exact observations, execution and empirical stops

Before each issue the same-step paired-boundary R_geo/Z_geo and same-step Ip
are exact/noiseless observations.  The complete post-takeover observation,
issued, serialized, applied/readback and queue history is available.  The
future successor remains unknown before the issue.  An invalid or missing
paired boundary fails closed; magaxis, rc/zc and silent fallbacks remain
forbidden.

Every branch keeps the ID-2Z1 finite simulator-development gates:

- exact Card15 target, issue-to-effect offset one and no added software queue;
- per-coil issued and readback slew at most 0.3 A, equality allowed;
- source-relative preissue clearance of 25 mm per R/Z axis and 5% Ip;
- successor outer envelope of 50 mm per R/Z axis and 10% Ip;
- per-successor empirical caps of 2 mm R, 2 mm Z and 150 A Ip;
- stop before every later issue after boundary, time, runtime, solver,
  current, prefix, raw or empirical-cap failure;
- no retry, cleanup action, return action or continuation after a stopped
  branch.

Only the prospectively listed R/Z/Ip clearance stop may allow the next
independent reset.  These stops are finite TSC exploration rules, not a
controller-grade transition tube or recovery policy.

## Per-round utility and selection

Each round's hold suffix is the matched baseline.  Candidate-minus-hold
responses are evaluated over all eight effect states.  The last four held
effect states are the persistence window.  A non-hold arm is eligible only
when:

1. arm and matched hold complete with exact execution/raw/prefix gates;
2. peak paired R/Z response is at least 0.05 mm;
3. source-distance improvement over hold is at least 0.05 mm in at least
   three of the four persistence states;
4. source-distance improvement at the active-macro terminal state is at least
   0.10 mm;
5. terminal source-distance improvement at the eight-effect horizon is at
   least 0.10 mm; and
6. maximum paired absolute Ip response is at most 150 A.

Eligible arms are ordered lexicographically by smallest absolute terminal
source R/Z distance, smallest active-terminal source R/Z distance, largest
median persistent improvement, smallest absolute terminal source-Ip offset,
then stable arm id.  This keeps geometry as the commanded objective while Ip
remains a hard/soft coupled quantity.  No fitted score, future main-path
measurement or post-result threshold is used.

Both rounds must nominate at least one arm.  Round-B sibling prefixes must be
exactly equal and must reproduce the selected Round-A prefix through state73.
The final report retains the complete decision tree, both matched baselines,
all excluded/ineligible arms, the selected two-macro logical path and its
absolute R/Z/Ip trajectory.

## Budget, evidence role and stop rule

The hard maximum is fourteen canonical resets: seven Round-A streams with
77 issues each and seven Round-B streams with 81 issues each.  Therefore the
maximum is 1,106 attempted/`gotsc`/verified advances, 1,120 retained states
and 5,600 required raw artifacts.  The frozen storage estimate is 68 GB; the
run requires at least 110 GB free before launch and at least 40 GB remaining
after that estimate.  Raw remains uncompressed and receives a structurally
separate full-raw audit on the server.

ID-2Z2 fits or updates zero models and reads zero calibration, blind or
holdout records.  Its raw and compact trajectories are sequence-search and
route evidence only; they are forbidden from model fitting, expert/BC/DAgger/
RL data, calibration, holdout and repository fixtures.

A clean two-round PASS nominates one finite two-macro transport sequence and
authorizes only a separately frozen braking/hold or rolling-controller design.
It does not prove hold, recovery, two-axis authority, arbitrary rolling
optimality, position generalization, waypoint tracking or R_mid crossing.
If Round A or Round B has no eligible arm, this seven-action late grammar is
closed: do not start a third manual macro stage.  The next route must move the
decision earlier, redesign a headroom-preserving action allocation, or use a
separately qualified broader sequence search.  Execution, interface, prefix,
raw and storage failures retain their own classifications and never become a
scientific utility FAIL.
