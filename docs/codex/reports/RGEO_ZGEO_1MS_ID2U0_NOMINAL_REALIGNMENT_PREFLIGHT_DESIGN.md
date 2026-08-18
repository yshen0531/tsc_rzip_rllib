# ID-2U0 nominal realignment and action-allocation preflight design

## Purpose

ID-2U0 is a zero-new-TSC, zero-fit readiness audit.  It corrects the
experimental reference from the held p03 level-15 corridor to ID-2C1's
selected time-varying `p03_minus_stride1` nominal, audits the state-27
return-edge event, and proves that the proposed residual-action grammar is
exactly representable without invoking runner clipping.

The stage may read the authenticated tracked compact evidence and the
canonical 1100 ms source files needed by the existing Card15 constructor.  It
must not reset TSC, call `gotsc`, advance a plant, fit a model, open a holdout,
or modify raw evidence.

## Frozen evidence roles

- ID-2C1 Phase A and its compact result establish the selected moving
  nominal and its finite source-relative R/Z/Ip result.
- ID-2P1 primary compact trajectories provide retrospective event alignment
  and exact p04/p07 action fields.  They are consumed development/design
  evidence, not new U0 fitting data.
- ID-2S1/S2/T1 results provide measured-sequence, exact-replay and matched
  continuation classifications.  Their trajectory records retain zero fit,
  calibration, holdout and controller weight.
- No ID-2N1 or other calibration/holdout record is read.

## Exact action grammar

The moving nominal increments p03-minus by one exact Card15 level per normal
transport issue.  A residual experiment cannot add another dense direction
to the same issue because the nominal already reaches the `0.3 A` per-coil
limit.  The candidate grammar is therefore time-multiplexed:

```text
arrive at exact nominal level L
hold/pause the nominal increment
issue exact translated residual target at level L for two issues
return exactly to level L
resume with exact nominal level L+1 on the next issue
```

The matched baseline uses the same pause duration, return issue and resume
clock but remains at level L instead of applying a residual.  Every adjacent
14-coil target difference must be exactly representable and no larger than
`0.3 A`.  Absolute current limits also remain hard.  Any failure rejects the
campaign before TSC; silent clipping is forbidden.

## Prospective matrix produced by a PASS

U0 audits eight history families formed by:

- probe issue: `24` or `30`;
- contemporaneous nominal level: `18` or `22`;
- arrival history: `frontloaded` or `paced`.

Each family contains a matched baseline and p04/p07 probes of both signs,
for five cells per family.  Every probe lasts two issues, returns to its
contemporaneous level, resumes the nominal, and retains a complete tail.  The
arrival schedules must have the same exact active level at the probe issue
but different earlier increment/settle placement.  Families, not steps or
siblings, are the atomic split unit.

The prospective split is fixed before any response exists:

```text
development: issue24/level18/frontloaded, issue24/level22/frontloaded,
             issue30/level18/frontloaded, issue30/level22/frontloaded
calibration: issue24/level18/paced, issue24/level22/paced
blind:       issue30/level18/paced, issue30/level22/paced
```

This is a data-design split, not advance permission.  A later fresh-campaign
identity must independently freeze storage, execution, raw, boundary, Ip,
current, prefix, signal and independent-audit gates before running.

## Event map and gates

U0 must reproduce these descriptive facts from tracked evidence:

1. the ID-2C1 selected nominal is stride one through issue 31 and improves
   terminal source R/Z norm by about `34.188%` versus q0;
2. P1 has exactly 32 primary probe cells and 16 response samples above
   `0.5 mm`, all at absolute state 27;
3. the issue-24 f03 p04+ direct h1/h2 response is close to the issue-30 T1
   h1/h2 response, while the return-effect h3 differs by roughly
   `0.684--0.691 mm` in R;
4. all proposed baseline/probe/return/resume streams are exact Card15 and
   satisfy the unchanged `0.3 A` slew and absolute-current limits.

The output must contain explicit stream definitions and exact action fields,
not only aggregate booleans.  The only PASS route is
`ONE_MS_ID2U0_NOMINAL_REALIGNMENT_ACTION_GRAMMAR_PASS_U1_DESIGN_ONLY`.

## Claim boundary

A PASS proves only that the evidence lineage and fresh campaign grammar are
internally consistent and exactly executable at the actuator interface.  It
does not prove a transition tube, repeatability, response signal, authority,
hold, recourse, model accuracy, controller safety, MPC, transport, waypoint,
crossing, adaptation, expert data, RL or reachability.  U0 runs zero TSC and
fits zero models.
