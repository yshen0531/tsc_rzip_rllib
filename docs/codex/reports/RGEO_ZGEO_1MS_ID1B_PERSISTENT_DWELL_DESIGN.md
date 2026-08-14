# ID-1B persistent-dwell signed geometry discriminator

Date: 2026-08-14 (Asia/Shanghai)

Frozen config SHA-256:
`3ceef849a801a5a027cc39144a4e3210a325a2e2d45e611fadd2f20369c3d1ae`.

## Purpose

ID-1A is frozen as a clean design FAIL and its trajectories are not fit
eligible. Its one-issue pulse was returned to q0 one issue later, so the
effect-age 1--4 mean crossed a second action edge. ID-1B asks a narrower and
causally clean question: while one exact signed Card15 target remains active
for four consecutive effects at late q0, do the measured p03/p04/p07 response
rays provide a reproducible, positively spanning R/Z temporal primitive with
bounded Ip cost?

This is not a model, controller, transition tube, hold, recovery or
reachability experiment.

## Frozen matrix and timing

- canonical 1100 ms source, 1 ms issue period;
- 14 rollouts, 24 advances each, at most 336 plant advances;
- two all-q0 baselines;
- p03, p04 and p07, both exact Card15 signs, two complete replays each;
- q0 through issue 9;
- the selected target at issues 10, 11, 12 and 13;
- exact q0 return at issue 14 and q0 thereafter;
- measurement states 11--14, all generated while the same selected target is
  active under the frozen `issue+1` effect rule;
- state 15 is the first q0-return effect and is excluded from the action
  vector. States 15--24 are a separately reported tail.

The action value may use the full 0.3 A per-coil per-step allowance. All
issued, serialized, applied/readback, absolute-current, limiter, boundary and
Ip gates remain fail closed. Current same-step paired-boundary R_geo/Z_geo and
same-step Ip are exact/noiseless observations before each issue. The future
successor remains unknown before the action.

## Scientific gates

After matched-q0 subtraction, each signed arm must have at least 0.01 mm peak
R/Z response and at most 150 A absolute Ip response. The six four-state mean
R/Z columns must have numerical rank two and a best two-column condition no
greater than 20.

Rank is not sufficient. Sort the six nonzero response angles on the circle;
their maximum cyclic gap must be at most 175 degrees. In addition, over 360
uniform unit directions, the minimum of the maximum dot product with any
measured response ray must be at least 0.005 mm. These are finite empirical
positive-span/support gates, not proofs of controllability outside this
source/time/action/history cell.

Every baseline and signed arm has two exact replays. Tail extinction is
reported but not gated.

## Data role and routing

Even a complete PASS opens ID-1B only for selecting a persistent temporal
primitive and low-dimensional action basis. ID-1B is forbidden for predictive
model fitting, calibration, holdout, expert/Oracle/fixture/BC/DAgger/RL data,
controller safety or recourse qualification.

A PASS requires a new fresh context/history/anchor development campaign using
the selected primitive, followed by grouped fresh calibration and unopened
whole-family holdout. A positive-span FAIL triggers direction/temporal
primitive redesign; it is not a model or global plant-authority conclusion.
