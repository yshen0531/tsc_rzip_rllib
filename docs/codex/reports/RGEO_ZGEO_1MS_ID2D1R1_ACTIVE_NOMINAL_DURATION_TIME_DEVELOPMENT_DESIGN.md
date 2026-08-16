# R_geo/Z_geo 1 ms ID-2D1R1 active-nominal duration/time development design

Date: 2026-08-17 Asia/Shanghai

Identity: `rgeo-zgeo-1ms-id2d1r1-active-nominal-duration-time-development-v1`

## Amendment to ID-2D1 v1

ID-2D1 v1 stopped in a server zero-TSC focused test because a single combined
lag-16 gate incorrectly treated p09 as a smooth 16-age coordinate.  The
physical 24-rollout schedule had full lag-16 support for p04/p07 and full
support for all ten p09 ages actually observable after its issue-22 event,
but the combined 48-column matrix necessarily had six zero directions.

ID-2D1R1 is a new identity.  It does not reinterpret the v1 rank-42 result.
It keeps the physical action matrix, budgets, empirical safety rules, data
roles, exclusions and all signal/Ip gates unchanged.  It replaces only the
incoherent combined support claim with two prospective model-aligned gates:

- smooth p04/p07 block: 16 ages, 32 columns, required rank 32;
- separate p09 event block: 10 ages, 10 columns, required rank 10.

Both condition numbers and minimum singular values must be reported.  P09
may not be silently pooled into the smooth p04/p07 model.

## Frozen campaign and boundaries

The campaign is exactly the 24-rollout matrix defined by the ID-2D1 v1
design: two held active-nominal baselines; p04/p07 plus/minus at issue16 for
duration 2/4 and issue22 for duration 1/2/4; and p09 plus/minus at issue22 for
one issue.  Every rollout has 32 one-ms issues, for ceilings of 24 resets,
768 advances and 792 states.  ID-2C2's issue16/one-issue cells remain absent
and immutable evaluator-only data.

Current same-step paired-boundary R_geo/Z_geo and Ip are exact noiseless
pre-issue observations.  Exact Card15, actual current/readback, absolute
current, `<=0.3 A` adjacent slew, valid boundary, Ip and empirical/hard
envelopes remain fail-closed.  Novel successors remain TSC-only empirical
exposures, not pre-action tubes.

All 24 rollouts, every raw artifact, exact baseline repeatability, both input-
support gates and all unchanged response-signal/Ip gates must pass before the
records become ID-2D1R1 development-fit eligible.  Duration/time differences
are measured, not forced to be nonzero.

## Subsequent model and authorization

A later zero-new-TSC structured model must preserve exact actuator/queue,
separate the active nominal, fit the simplest stable low-order p04/p07 memory,
and represent p09 as an event residual.  ID-2C2 remains immutable evaluator-
only, especially the unseen issue16/one-issue cells.  Neural residuals remain
blocked until the structured model is evaluated.

A complete PASS authorizes only that separately frozen model stage.  It does
not authorize calibration, blind context/history holdout, tube, recovery,
controller/MPC, transport/crossing, online adaptation, expert data or RL.
The final two-axis path/waypoint and HFS/LFS-crossing goal is unchanged.
