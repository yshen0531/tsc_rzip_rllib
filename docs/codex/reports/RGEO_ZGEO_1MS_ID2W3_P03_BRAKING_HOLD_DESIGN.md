# R_geo/Z_geo 1 ms ID-2W3 p03 braking/hold discriminator design

Date frozen: 2026-08-19

Identity: `rgeo-zgeo-1ms-id2w3-p03-braking-hold-discriminator-v1`

## Question

ID-2W2 showed that continuing the p03-minus stride-one staircase through
level 78 did not approach the source after state 32. It did, however, rotate
the velocity and error: near level 52 the Z velocity was near zero, while near
level 64 both R and Z velocities were negative. ID-2W3 asks whether stopping
the ramp at either already observed level produces a finite deceleration/hold
tail.

This is the final p03-only discriminator. A clean failure ends the p03-only
nominal/hold route; no further level ladder is permitted.

## Frozen branches

Both branches start from the canonical 1100 ms source, use a 1 ms issue period,
run at most 96 issues, and retain at most 97 states.

1. `p03_level52_hold`: issue 0 q0; issues 1--52 exact p03 levels 1--52;
   issues 53--95 hold exact level 52.
2. `p03_level64_hold`: issue 0 q0; issues 1--64 exact p03 levels 1--64;
   issues 65--95 hold exact level 64.

Issue `k` first affects state `k+1`. There is no software queue, retry,
adaptive choice, cleanup action, residual action or silent clipping. Each
issued per-coil delta is at most 0.3 A, equality included, and every absolute
target must be exact Card15 and inside current limits before the runner call.

For each branch, every ramp action and arrival state through the first hold
issue must reproduce the independently audited ID-2W2 compact prefix. The
first novel action is the zero-delta hold at issue 53 or 65 respectively.

## Observation and finite empirical envelope

Current paired-boundary R_geo/Z_geo and Ip are exact/noiseless before every
issue, and all post-takeover causal observations/actions remain available.
Future successors remain unknown. The novel hold tails use the same explicit
simulator-development envelope:

- before every novel hold issue, current R/Z offsets must remain within 25 mm
  per axis and Ip within 5% of the source;
- every successor must remain within 50 mm per axis and 10% Ip;
- every successor step must remain within 2 mm R, 2 mm Z and 150 A Ip;
- invalid paired boundary, Card15/current, time, solver or TSC status stops
  before any later issue;
- these are empirical stops, not controller-grade transition tubes.

## Prospective terminal hold gate

The common terminal evaluation window is states 88--96 inclusive. Each branch
is evaluated separately. A branch passes finite nominal hold only if:

1. maximum absolute one-ms R and Z change in the window is no more than
   `0.0001 m` per axis;
2. absolute net R and Z change from state 88 to state 96 is no more than
   `0.001 m` per axis;
3. absolute net Ip change is no more than `100 A`;
4. every terminal state remains within the 25 mm per-axis and 5% Ip source
   envelope; and
5. all execution, exact-prefix, raw and independent-audit gates pass.

The campaign scientific gate passes if at least one branch passes every hold
criterion. The result reports each branch's arrival state, full tail, terminal
step/net metrics, source offsets and best source distance. A PASS nominates a
finite nominal-hold candidate for a new-identity repeatability and bounded-
perturbation stage only; it is not recovery or recursive safety. A clean FAIL
requires a different actuator allocation rather than another p03 level.

## Budget and data role

- maximum rollouts/resets: 2;
- maximum issue attempts/TSC calls/verified advances: 192;
- maximum retained states: 194;
- required artifacts if complete: 970;
- model fit/training, calibration read and blind-holdout read: zero;
- W2 and W3 are route/design evidence only and may not become model, expert,
  BC, DAgger, RL, fixture, calibration or holdout data.

Server storage must have at least 40 GB free before launch and 25 GB after a
15 GB estimate. Raw stays uncompressed and receives an independent in-place
full-raw audit.

## Authorization boundary

This design authorizes implementation, server tests, offline preflight and,
after those pass, one two-branch campaign. It does not authorize a rerun under
changed gates, model fitting, a controller, MPC, recovery, waypoint/path,
R_mid crossing, adaptation, expert data or RL.
