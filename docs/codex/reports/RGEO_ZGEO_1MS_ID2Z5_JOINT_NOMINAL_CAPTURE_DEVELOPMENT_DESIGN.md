# ID-2Z5 joint nominal/capture development design

Date: 2026-08-19

## Purpose

ID-2Z5 corrects the control-relevance error exposed by ID-2Z4R1.  The next
experiment does not finish a distance-only transport and then try to capture
from a thin late corridor.  It starts from the independently audited p03
stride-one state-61 prefix and varies transport and braking jointly while the
limiting-coil engineering reserve is still exactly 100 A.

This is one prospectively fit-eligible TSC development campaign.  It is not a
controller, safety model, hold, recovery policy, terminal set, waypoint result
or reachability result.  Its compact trajectories may be used only to develop
and compare a small truth-recentered short-horizon sequence nominator.  Fresh
whole-history calibration, blind holdout, repeatability and Recourse-L1 remain
separate identities.

## Evidence corrections retained without changing old verdicts

The completed ID-2Z4R1 route remains final.  Two reporting distinctions are
made explicit here:

- at state 93 the actual R-axis distance to the 25 mm exploration boundary is
  about 2.0145 mm; 0.0145 mm is the deliberately conservative remainder after
  additionally subtracting the 2 mm empirical post-successor trip value;
- 100 A was introduced as a Z4/Z4R1 engineering action-selection reserve.  Z1,
  Z2 and Z3 used 95 A.  It is not a physical current limit, an already
  qualified recovery reserve, or an invariant of the accepted historical
  prefix.

ID-2Z5 nevertheless keeps 100 A prospectively over every newly constructed
target from issue 61 onward.  This is a new-stage design choice, not a
retroactive reinterpretation or weakening of ID-2Z4R1.

## Fixed prefix, observability and timing

- takeover is fixed at 1100 ms;
- issue `k` produces its first physical effect at state `k+1`;
- before every issue, same-step paired-boundary `R_geo`, `Z_geo` and `Ip` are
  exact/noiseless observables;
- the complete causal observation and controller-owned action history since
  takeover is available;
- state `k+1` and future actual current remain unknown before issue `k`;
- issues 0--60 exactly replay the audited ID-2W2 p03 stride-one prefix;
- state 61 and prefix checkpoints 0/32/49/53/57/61 must reproduce the tracked
  compact reference before any later action is issued.

The novel allocation occupies issues 61--84.  Issues 85--116 hold the attained
exact Card15 target.  The horizon is therefore 117 issues / 118 states, and the
descriptive terminal window is states 112--117.  The long tail is intentional:
it distinguishes a transient low-speed crossing from finite capturability.

## Exact action grammar

The token alphabet is deliberately small and fully executable:

- `H`: hold the current exact target;
- `B`: add one exact p07-minus increment;
- `F`: add one exact p03-forward increment.

Each token consumes one 1 ms issue.  No two tokens are summed in one issue,
no clipping is allowed, and every target is reconstructed in Card15 decimal
space.  `B` and `F` act oppositely on the limiting PF4L reserve.  Every frozen
non-hold stream starts with `B`, and every prefix of every stream keeps the
newly constructed target headroom at or above 100 A.

The twelve development families are:

```text
hold24            HHHHHHHHHHHHHHHHHHHHHHHH
b4_h20            BBBBHHHHHHHHHHHHHHHHHHHH
b8_h16            BBBBBBBBHHHHHHHHHHHHHHHH
b12_h12           BBBBBBBBBBBBHHHHHHHHHHHH
bf_alt            BFBFBFBFBFBFBFBFBFBFBFBF
bbff_repeat       BBFFBBFFBBFFBBFFBBFFBBFF
bbbfff_repeat     BBBFFFBBBFFFBBBFFFBBBFFF
bbbbffff_repeat   BBBBFFFFBBBBFFFFBBBBFFFF
b4_f4_h16         BBBBFFFFHHHHHHHHHHHHHHHH
b8_f8_h8          BBBBBBBBFFFFFFFFHHHHHHHH
b12_f12           BBBBBBBBBBBBFFFFFFFFFFFF
b4_h4_f4_h12      BBBBHHHHFFFFHHHHHHHHHHHH
```

One thirteenth rollout, `bf_alt_replay`, is a byte-independent replay of the
`bf_alt` action schedule.  It has fit weight zero and is used only for finite
repeatability/integrity.  Siblings remain in the same future split.

This matrix is not a claim that B/F spans all useful 14-D actions.  It is the
smallest bounded dataset that tests the earlier joint-allocation hypothesis
with meaningful timing, dwell, duty-cycle and return-age variation while
remaining in an exact supported action coordinate.

## Four separate constraint meanings

The stage must keep these concepts separate:

1. physical hard envelope: valid paired boundary, finite state, absolute coil
   current, Card15, slew, Ip and the existing 50 mm / 10% outer envelope;
2. simulator-development corridor: the existing 25 mm per-axis / 5% Ip
   pre-issue empirical corridor and 2 mm / 2 mm / 150 A post-successor trip;
3. descriptive capture set: six terminal states within 25 mm Euclidean source
   distance, 0.1 m/s one-step R/Z speed and 5% source-relative Ip;
4. Recourse/terminal set: not supplied by this campaign and not implied by a
   descriptive capture.

The 100 A target headroom is an additional finite-stage engineering reserve,
not any of the four physical/recourse meanings above.

## Pre-TSC gates and budget

Before a reset, the implementation must prove:

- every evidence hash and the exact state-61 reference identity;
- exactly 13 streams in the declared order and exactly one zero-weight replay;
- 117 issues per stream, issue-to-effect offset one, and no issue after 116;
- every requested increment is at most 0.3 A per coil, with equality allowed;
- every newly constructed target is within physical current limits and has at
  least 100 A target headroom;
- all non-hold streams start with B and the prefix B-minus-F balance never goes
  negative;
- free-space and output-nonexistence gates pass.

The maximum budget is 13 resets, 1,521 advance attempts/gotsc calls/verified
advances, 1,534 retained states and 7,670 required artifacts if complete.
There is no retry after any attempted plant advance.

## Runtime and evidence gates

Every live checkpoint is checked before the next issue.  Any non-whitelisted
runtime, interface, prefix, raw or inventory failure aborts the campaign.
The existing simulator-only empirical exploration contract permits a branch
to stop after a prospectively named clearance or post-successor trip, but the
failed action is never retried and no later issue is sent on that reset.

Development-data readiness requires all integrity gates plus:

- at least eight complete non-replay families;
- at least ten classified non-replay families with at least sixteen observed
  novel successors each;
- at least six distinct complete non-replay token schedules;
- the `bf_alt` / `bf_alt_replay` pair to agree exactly on checked R/Z/Rmid/Ip,
  14 coil currents, 48 wire currents and issued actions over their common
  complete trajectory.

The capture metric is reported but is not required for development-data PASS.
A captured stream is only a candidate for a separately frozen fresh replay.

## Route and stop rules

- any offline/input/storage failure: zero TSC;
- any unapproved runtime/interface/prefix failure: stop and preserve raw;
- insufficient complete/support/replay evidence: finite development FAIL;
- readiness PASS: authorize only a small truth-recentered short-horizon model
  comparison on this development identity;
- no same-identity rerun, adaptive candidate insertion or threshold change;
- if one bounded model comparison and one fixed canonical-source shortlist do
  not produce a repeatable capture candidate, close this B/F basis and perform
  an authority/reachability review rather than another depth or network ladder.

The final goal remains safe approximate two-axis waypoint/path tracking from
the fixed 1100 ms takeover and, after staged expansion, repeated bidirectional
R_mid crossing with continuous belief.  ID-2Z5 is only a source-local bootstrap
toward that goal.
