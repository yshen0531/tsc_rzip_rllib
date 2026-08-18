# R_geo/Z_geo 1 ms ID-2W2 extended nominal transport design

Date frozen: 2026-08-19

Identity: `rgeo-zgeo-1ms-id2w2-extended-nominal-transport-v1`

## Question

ID-2C1 selected an exact p03-minus stride-one staircase, but real evidence
ended at issue 31. ID-2W1 then held that level and showed renewed source drift;
its paused p04/p07 residual grammar did not recover the transport cost.

ID-2W2 asks one bounded question: if the same exact p03 staircase continues,
does the trajectory enter a materially smaller source-relative R/Z corridor,
and at which state should a later slowdown/braking/hold campaign start?

This is a simulator-only development discriminator. It is not a hold,
controller, recovery, transition-tube, waypoint, model, or global-authority
qualification.

## Frozen action and timing

- canonical fixed 1100 ms source;
- one rollout, 80 issues and 81 retained states (`1100--1180 ms`);
- issue 0 is exact q0;
- issue `k=1..79` is exact `q0 + k * (p03_minus - q0)`;
- issue `k` first affects state `k+1`;
- no software queue, retry, cleanup action, return action, or adaptive change;
- each issued per-coil delta is at most 0.3 A, with equality permitted;
- every target must be exactly representable by Card15 and remain inside the
  absolute current bounds before the runner is called.

Actions 0--31 and states 0--32 must match the tracked ID-2W1 uninterrupted
nominal compact trajectory in R_geo/Z_geo/R_mid/Ip, all 14 coil currents, all
48 wire currents, the action fields, and the semantic artifact hashes under
the already qualified raw-state semantics. Issue 32 is the first novel
continuation.

## Observation and empirical safety envelope

Before every issue, the current same-state paired-boundary R_geo/Z_geo and Ip
are exact/noiseless observables and the complete post-takeover causal history
is available. Future state `k+1` is not known before issue `k`.

The previously observed prefix is not a theorem for the novel continuation.
ID-2W2 explicitly uses the finite TSC-development exploration contract:

- before every novel issue, the current state must remain within 25 mm per
  R/Z axis and 5% Ip of the source;
- each observed successor must remain within the 50 mm per-axis and 10% Ip
  hard outer envelope;
- each successor step must remain within 2 mm R, 2 mm Z and 150 A Ip;
- invalid/missing paired boundary, current, Card15, time, solver or TSC status
  fails closed;
- after any successor failure, no later action is issued;
- these empirical caps and geometric margins are not pre-action plant tubes.

## Prospective scientific gate

The tracked ID-2W1 source-relative R/Z distance at state 32 is
`0.019292294758661708 m`. A complete ID-2W2 trajectory passes the finite
transport-utility gate only if, after state 32:

1. at least three consecutive states have source-relative R/Z distance no
   greater than `0.015 m`; and
2. the minimum post-state-32 distance is no greater than `0.015 m`.

The result must also report the minimum state/time, R and Z components, Ip,
one-ms velocity, the first/last qualifying corridor state, and the trajectory
through state 80. A PASS only authorizes a separate slowdown/braking/hold
branch design around the measured corridor. A clean scientific FAIL stops
blind extension of this exact stride-one nominal and requires a different
nominal allocation. Execution, raw, prefix and scientific failures retain
separate routes.

## Data roles and budget

- maximum reset calls: 1;
- maximum advance attempts/TSC calls/verified advances: 80;
- maximum retained states: 81;
- required complete raw artifacts: 405;
- model fits, training, calibration reads and blind-holdout reads: zero;
- this trajectory is route/design evidence and may not be converted into
  model, expert, BC, DAgger, RL, fixture, calibration or holdout data.

Server storage must have at least 35 GB free before launch and at least 25 GB
after the 8 GB prospective estimate. Raw remains uncompressed and is audited
in place by a separate full-raw implementation.

## Stop and authorization boundary

This design authorizes implementation, server validation, offline preflight,
and, only after those gates pass, one real ID-2W2 rollout. It does not
authorize a second trajectory under the same identity. No outcome directly
authorizes a model, controller, MPC, recovery, waypoint, path, R_mid crossing,
adaptation, expert data or RL.
