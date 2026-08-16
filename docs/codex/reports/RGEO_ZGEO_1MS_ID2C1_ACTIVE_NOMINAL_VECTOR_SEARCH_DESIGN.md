# R_geo/Z_geo 1 ms ID-2C1 active-nominal/vector search design

Date: 2026-08-16 Asia/Shanghai

Identity: `rgeo-zgeo-1ms-id2c1-active-nominal-vector-search-v1`

Frozen config SHA-256:
`91763505d58950a4863090776869b9f075fa4b1c6609e4fc2f601fc1dac975eb`.

## Purpose

ID-2C0 passed without TSC or fitting and showed that the current problem is
not responsibly solved by enlarging the ID-2B1 regressor.  ID-2C1 is a small,
finite simulator-development search for two missing ingredients: a
time-varying nominal continuation that materially suppresses q0 drift, and
two-sided local residual response vectors around that continuation.

This is the empirical-identification contract, not the controller-safety
contract.  It prospectively permits bounded novel simulator successors, with
exact current observation and immediate post-successor stopping, but it does
not call those stops pre-action bounds or recourse.

## Phase A: authority scale

Four canonical-source schedules are ordered from q0 through progressively
faster exact Card15 p03-minus staircases.  Every staircase level is exactly
q0 plus an integer multiple of the measured p03-minus field offset.  Each
adjacent per-turn coil change remains at most 0.3 A.  The first incomplete,
interface-invalid, hard-envelope or empirical-step-cap trajectory stops
further escalation.

Among complete nonbaseline candidates, select the smallest terminal
source-relative R/Z norm only if it improves the new matched q0 baseline by
at least 20% and remains within 1000 A of source Ip.  This is a development
selection rule, not a hold or safety gate.  A selected trajectory is an
active nominal candidate, not Nominal-H1.

## Phase B: residual vectors

If Phase A selects a candidate, replay that schedule with a pause at issue 16
as the matched baseline.  Six sibling schedules add exactly one issue of the
actual p04, p07 or p09 Card15 vector, with both signs, then return exactly to
the paused nominal and resume it.  The complete seven-rollout family is
required.  p09 is treated as an event/hybrid diagnostic; it is not pooled as
a smooth gain with p04/p07.

The phase measures development response/tail/Ip geometry only.  It does not
assume superposition, odd symmetry, positive span, repeatability or a valid
local Jacobian.  Selection and probes remain in the same development
identity, so none is a blind validation trajectory.

## Budgets and stopping

Maximum: 11 resets, 352 advance attempts/gotsc calls, 32 issues per complete
rollout and 30 GB estimated raw.  There is no retry after an attempted plant
advance and no cleanup/return plant action.  Each issue is preceded by exact
Card15, slew, absolute-current, paired-boundary, Ip and causal-state checks.
Each successor is checked against the 2 mm/2 mm/100 A empirical cap and the
50 mm/50 mm/10% outer envelope before any later issue.

## Authorization boundary

A complete ID-2C1 result permits only a separately frozen ID-2C2 fresh
validation design.  It does not authorize model fitting, calibration,
holdout, uncertainty contraction, recovery, controller, MPC, transport,
R_mid crossing, online adaptation, expert data or RL.  E1/A4 remain parked.
