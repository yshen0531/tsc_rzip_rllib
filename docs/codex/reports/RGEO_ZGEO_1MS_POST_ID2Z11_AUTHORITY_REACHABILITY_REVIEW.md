# R_geo/Z_geo 1 ms post-ID-2Z11 authority/reachability review

Date: 2026-08-20 Asia/Shanghai

## Scope

This is a zero-new-TSC, zero-fit review of tracked ID-2Z11 compact evidence.
It records the one bounded successor selected after the frozen macro teacher
failed capture. It does not change ID-2Z11's verdict.

## What ID-2Z11 actually localized

The exact selected replay `b8 -> b4f4` has no captured state. Its closest
instantaneous normalized capture score occurs at state 61:

```text
source R/Z distance                         25.880440 mm
one-step R/Z speed                           0.141940 m/s
absolute source-relative Ip fraction         0.035779
worst normalized score                       1.419404
```

State 60 is `25.757234 mm / 0.168088 m/s`; state 62 is
`26.027176 mm / 0.178525 m/s`. Thus the path passes near, but not through,
the capture set and then accelerates. Among states that remain within 25 mm,
the lowest measured speed is still `0.218018 m/s` at state 48. This is a
position/velocity timing failure, not merely a terminal-reporting artifact.

## Exact B/F action-allocation geometry

At the exact Card15 boundary, the per-step B and F actual-current increments
are rank two and have condition about `1.24348`. Their maximum component is
`0.3 A`. On a coefficient grid
`{-1,-0.75,-0.5,-0.25,0,0.25,0.5,0.75,1}^2`, exactly 41 combinations satisfy
the unchanged `<=0.3 A` per-coil slew. The feasible coefficient hull is the
diamond `|alpha_B| + |alpha_F| <= 1`.

Consequences:

- simultaneous allocation cannot create more total one-step authority than
  the signed B/F vertices;
- it can create intermediate directions and remove the old requirement to
  spend an entire millisecond on one vertex;
- U and P are exactly the negative F and negative B vertices already tested
  in ID-2Z11; their failure does not test the four diagonal allocations;
- if an exact receding search over the boundary directions still cannot
  capture, further B/F macro depth has little scientific value.

## Frozen successor decision

The next identity is one last source-local signed-B/F convex-allocation
discriminator, not another learned model or hand-selected macro ladder.

At state 61 and then at the selected state 65 history, it evaluates the same
nine four-issue candidates:

```text
hold
(+1, 0), (+0.5,+0.5), (0,+1), (-0.5,+0.5),
(-1, 0), (-0.5,-0.5), (0,-1), (+0.5,-0.5)
```

The ordered pair is `(alpha_B, alpha_F)`. Every non-hold candidate repeats
its exact simultaneous allocation for four issues. Selection is capture
first and otherwise the unchanged distance/speed/Ip score. The first round
commits four issues, observes exact state 65, and replans once. All branches
share terminal states 72--77. A fresh exact replay is mandatory.

This is an algorithmically generated boundary of the exact feasible
allocation polygon. No direction may be added or removed after outcomes.
The campaign budget is 9 + 9 branches plus one replay. No data is fit-eligible.

## Stop rule

PASS requires selected-path six-state capture and exact replay, together with
all interface/raw/independent gates. Relative score improvement is not PASS.

FAIL closes the entire frozen signed B/F convex-allocation basis at this
state61 causal history. It routes to an earlier takeover/nominal and new
physical-action-basis review. It forbids another adjacent root, deeper beam,
larger model, relaxed capture gate or retrospective use of the trajectories
for fitting.

This finite FAIL would still not prove global plant unreachability, but it
would end the current source-local B/F search line.

## Final-goal boundary

The final goal remains fixed-1100-ms, 1-ms exact-RZI, full-causal-history,
exact-Card15 two-axis waypoint/path control under independent hard safety and
recovery, eventually including bidirectional repeated `R_mid` crossing with
continuous belief. The successor is only a finite capture/authority
discriminator.
