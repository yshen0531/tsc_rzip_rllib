# R_geo/Z_geo 1 ms ID-2W3R1 level-64 hold completion design

Date frozen: 2026-08-19

Identity: `rgeo-zgeo-1ms-id2w3r1-level64-hold-completion-v1`

## Purpose and identity separation

ID-2W3 safely stopped its first, level-52 branch at state 79 when the current
`R_geo` offset exceeded the preregistered 25 mm pre-issue clearance. Its
independent raw audit passed, but the fail-fast implementation did not start
the second level-64 branch that had already been frozen before ID-2W3 ran.

ID-2W3R1 is a new identity that executes only that unstarted branch. It does
not resume or rerun ID-2W3 and does not alter the schedule, empirical envelope
or terminal hold gate after observing the level-52 result.

## Exact branch

Starting from the canonical 1100 ms source with a 1 ms issue period:

- issue 0 is q0;
- issues 1--64 are exact p03-minus levels 1--64;
- issues 65--95 hold the exact level-64 Card15 target;
- issue `k` first affects state `k+1`;
- state 96 is recorded and no issue 96, cleanup action or recovery action is
  sent.

Actions and arrival states through state 65 must match the independently
audited ID-2W2 compact prefix. The first new transition begins with the
zero-delta hold at issue 65. Every target is checked for exact Card15
representation, absolute current and per-coil slew no greater than 0.3 A
before the runner call; legacy clipping may not be used.

## Empirical stops and terminal gate

The exact ID-2W3 gates remain unchanged:

- before every new hold issue, current source offsets must be within 25 mm R,
  25 mm Z and 5% Ip;
- each successor must remain within 50 mm R, 50 mm Z and 10% Ip;
- each successor step must be within 2 mm R, 2 mm Z and 150 A Ip;
- any invalid paired boundary, time, TSC, solver, Card15, current or raw state
  stops before the next issue.

These are simulator-development empirical stops, not transition tubes.

The branch passes finite nominal hold only if states 88--96 have maximum
one-ms R/Z change at most 0.1 mm per axis, state88-to-state96 net R/Z at most
1 mm per axis and net Ip at most 100 A, while every terminal state remains
within 25 mm R/Z and 5% Ip of the source. Execution, exact-prefix, raw and
independent-audit gates must also pass.

A PASS only nominates a finite source-local nominal-hold candidate for fresh
repeatability and bounded-perturbation qualification. A clean scientific
FAIL, or an empirical-envelope stop, ends the p03-only route and requires a
different actuator allocation.

## Budget and data role

- one rollout/reset;
- at most 96 issue attempts/TSC calls/verified advances;
- at most 97 retained states and 485 required artifacts;
- at least 35 GB free before launch and 25 GB after an 8 GB estimate;
- no retry after an issue attempt and no raw compression;
- zero model fitting/training and zero calibration/holdout read;
- result data is route/nominal-design evidence only and is forbidden from
  controller, expert, BC, DAgger, RL, fixture, calibration or holdout use.

This design authorizes implementation, server tests, offline preflight and,
after they pass, the one branch above. It authorizes no other TSC, model,
controller, MPC, recovery, waypoint/path, crossing, adaptation or RL stage.
