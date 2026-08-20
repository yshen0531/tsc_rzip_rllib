# Post-ID-2Z25 dynamic output-aligned allocation route review

Date: 2026-08-21

## Decision

ID-2Z25 remains final as
`ONE_MS_ID2Z25_CENTERED_D0_SIGNAL_FAIL_CLOSE_CELL`.  Its `0.50F` nominal
starting at issue 16, three original residual axes, two phases and 8+8
signed/return construction are closed.  The ten passing rows are not a
retrospective training set and the failed p00 rows are not deleted to turn
the campaign into a PASS.

The next route is materially different: retain full-F only for the early
transport segment, then enter a prospectively frozen slack allocation at a
causal state/event guard and express the two task-plane residual coordinates
as output-aligned combinations rather than as the original p00/p05/p06 axes.
Before any plant advance, a zero-TSC exact-Card15 preflight must prove the
complete switch, sustained command, inverse/return and tail streams.  This
review authorizes that preflight only.

## What the completed evidence says

The matched ID-2Z25 baselines expose the nominal tradeoff.  Both share the
same prefix through state 16.  Continuing full-F is consistently better than
the `0.50F` center in source distance and one-step speed:

| state | full-F distance / speed | `0.50F` distance / speed |
|---:|---:|---:|
| 24 | 15.792 mm / 0.506 m/s | 16.541 mm / 0.628 m/s |
| 32 | 19.292 mm / 0.386 m/s | 20.725 mm / 0.579 m/s |
| 40 | 21.421 mm / 0.334 m/s | 25.088 mm / 0.516 m/s |
| 48 | 23.207 mm / 0.218 m/s | 28.339 mm / 0.461 m/s |

The common terminal diagnostics are `28.255 mm / 0.416 m/s` for full-F and
`36.487 mm / 0.548 m/s` for the center.  Thus `0.50F` is not a replacement
nominal from issue 16.  Conversely, full-F reaches the 0.3 A issue boundary
on at least one coil and therefore has no unconditional additive residual
bandwidth.  The actual design problem is a causal transition from transport
to a lower-share joint allocation, not selection of one constant share.

ID-2Z25 also separates two response structures.  The p00 order/phase rows
can reverse between h4 and h8 and therefore require a hybrid/event-aware
uncertainty treatment.  The odd components of p05 and p06 are much more
consistent across issue 24 and issue 32.  This does not make the old campaign
PASS, but it is valid consumed design evidence for constructing a new action
coordinate and collecting fresh data.

## New output-aligned seed

Let `r5` and `r6` be the exact residual increments used by ID-2Z25 for the
p05 and scaled-p06 axes.  Define the continuous design seeds

```text
q_R = (r5 - r6) / 2
q_Z = (r5 + r6) / 2
```

Against the ID-2Z25 center, the resulting exact-number input vectors have
rank two and condition `1.05072`.  Their largest components are about
`0.150 A`; the continuous `0.50F +/- q_R/q_Z` candidates have maximum
component no larger than `0.300 A`.  These are arithmetic observations, not
yet Card15 stream qualification.

Using the old paired trajectories only as a descriptive odd-response
construction, the R/Z columns in millimetres are:

| phase / horizon | q_R response | q_Z response | condition |
|---|---:|---:|---:|
| issue24 / h4 | (-0.05928,-0.01927) | (+0.00326,-0.05934) | 1.306 |
| issue24 / h8 | (-0.20244,-0.04883) | (-0.01742,-0.22714) | 1.393 |
| issue32 / h4 | (-0.05938,-0.02028) | (+0.00455,-0.05778) | 1.304 |
| issue32 / h8 | (-0.18013,-0.05594) | (-0.01439,-0.23739) | 1.552 |

This is the first current-route seed that is simultaneously near-axis-
aligned in the task plane and leaves symmetric issue headroom.  It does not
prove superposition, output authority, persistence under a new arrival
history, Card15 representability, capture or recourse.

## Required zero-TSC preflight

The next implementation identity must do no fitting and no TSC.  It must:

1. authenticate the ID-2Z18, ID-2Z23, ID-2Z24R2 and final ID-2Z25 evidence;
2. construct every target with Decimal/Card15 semantics, not float addition;
3. keep the exact full-F prefix until a prospectively frozen causal
   transition guard and then use one common lower-share moving center;
4. construct both signs of `q_R` and `q_Z`, with no p00 branch and no claim
   that ID-2Z25 was repaired;
5. prove the whole stream's slew, absolute current, headroom, exact switch,
   cumulative inverse/return and held-tail properties;
6. freeze one matched transition-center baseline, one zero-fit continuing-
   full-F diagnostic, all signed siblings, one zero-fit replay and complete
   whole-family data roles before real TSC; and
7. fail with zero plant advance if any exact lattice or stream property is
   unavailable.

The p00 removal is part of a new rotated rank-2 task-plane basis and a new
arrival/nominal lineage.  It is not permission to fit the ten passing
ID-2Z25 branches.  All ID-2Z25 rows remain zero-fit.

## Prospective real-campaign boundary

Only a successful exact preflight may authorize one fresh simulator-
development campaign.  It must compare every branch to the matched
post-transition center, retain h1--h8 and a common long tail, and require
both axes and both signs to show finite signal and persistent direction.
Input rank or linear combinations of old responses cannot satisfy the real
gate.  Capture and positive span remain reported separately.

If the new task-plane basis fails real persistence at either predeclared
arrival history, close the entire full-F-to-slack output-aligned grammar.
Do not try neighboring shares, phases, durations or rotations.  The next
route would then require a new takeover/nominal or physical Card15 basis.
If it passes, event/value model development and Authority-L0 design may
proceed in parallel on new identities; neither substitutes for Recourse-L1.

## Final-goal boundary

The final goal remains fixed-1100-ms takeover, exact same-step R_geo/Z_geo/Ip
observation, complete causal history, exact Card15 and at most 0.3 A per coil
per issue, independent safety/recourse, approximate two-axis waypoint/path
tracking, and ultimately bidirectional repeated R_mid crossing without
resetting belief.  This next seed is only a source-local simulator-
development coordinate on the way to that goal.
