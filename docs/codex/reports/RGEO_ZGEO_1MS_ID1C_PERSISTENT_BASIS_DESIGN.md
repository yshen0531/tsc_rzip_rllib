# ID-1C exact-centred persistent basis validation design

Date: 2026-08-14 (Asia/Shanghai)

## Decision being tested

ID-1B showed that the old full-amplitude p03/p04/p07 absolute response rays
all had positive R components. ID-1C0 then screened all ten consumed NR2R1
development pairs at their causally pure first-event windows and selected
p01+p09 as the strongest finite two-direction candidate. ID-1C asks whether
an exact q0-centred, half-amplitude version of those directions remains
repeatable, two-sided and positively spanning when held for four consecutive
effects at late q0.

This is a fresh TSC-only empirical discriminator. It is not a model,
controller, tube, hold, recovery or reachability experiment.

## Frozen finite matrix

- canonical 1100 ms source and 1 ms issue period;
- 10 rollouts, 18 advances each, at most 180 attempts and `gotsc` calls;
- two all-q0 baselines;
- p01 and an exact-centred half-amplitude p09 reconstruction;
- both Card15 signs, two complete replays per signed arm;
- q0 through issue 9, unchanged selected target at issues 10--13, exact q0
  return at issue 14, then q0 through issue 17;
- pure response states 11--14; state 15 and later are reported tail only.

Every target is specified by its actual 14 Card15 fields. Both signed pairs
must be exactly centred on q0 in actual current coordinates. The largest
designed component is 0.15 A; the user's 0.3 A per-step allowance remains
unchanged and is not reinterpreted as a prohibition on using the full limit.

## Gates and route boundary

Execution, Card15, current, limiter, paired-boundary R_geo/Z_geo, Ip, timing,
raw inventory and exact replay remain fail closed. Each signed arm must have
at least 0.01 mm peak R/Z signal; each pair's odd half-difference must have at
least 0.01 mm norm; its even midpoint response must not exceed 0.005 mm. The
four actual response rays must have rank two, best pair condition at most 20,
maximum angular gap at most 175 degrees and minimum directional support at
least 0.005 mm. Absolute Ip response must not exceed 100 A.

A PASS selects only this persistent temporal/action basis. It then permits a
new, separately frozen fit-eligible context/history/anchor development stage,
followed by fresh grouped calibration and an unopened whole-family holdout.
ID-1C itself remains forbidden for fitting. Any scientific FAIL returns to
direction/action-centre design; it cannot be interpreted as a global plant or
closed-loop failure.
