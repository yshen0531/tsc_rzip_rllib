# R_geo/Z_geo 1 ms ID-2X1 mixed-allocation hold design

Date frozen: 2026-08-19

Identity: `rgeo-zgeo-1ms-id2x1-mixed-allocation-hold-v1`

## Why this stage

The p03 stride-one path improved the source distance through state32, but
continuing p03 and holding levels52 or64 both drove R below the frozen 25 mm
source-relative clearance. The p03-only route is closed.

Earlier ID-2W1 same-prefix evidence showed that a cumulative p04-minus offset
produces a persistent positive-R response, while p07-plus contributes a
negative-Z response with a negative-R cost. Their depth-six effect was too
weak to repair the pause/catch-up trajectory, but it supplies a measured sign
for a different, sustained allocation. ID-2X1 asks once whether more legal
actuator-time allocation can form a finite hold around the best-known p03
level-32 transport point.

This is bounded canonical-source branch shooting, not model fitting. It does
not infer a linear superposition law from ID-2W1.

## Frozen branches

Every branch starts from the canonical 1100 ms source, issues q0 at issue0 and
p03-minus levels1--32 at issues1--32. The exact p03 level32 target remains the
nominal center thereafter.

1. `p03_level32_hold`: hold that center at issues33--95 (matched baseline).
2. `p04_minus_depth18_hold`: add exact p04-minus residual levels1--18 at
   issues33--50, then hold the combined p03L32+p04m18 target through issue95.
3. `p04m18_p07p6_hold`: perform the same p04-minus ramp, then add p07-plus
   levels1--6 at issues51--56 and hold the combined target through issue95.
4. `p04m24_p07p8_hold`: add p04-minus levels1--24 at issues33--56, then
   p07-plus levels1--8 at issues57--64, and hold through issue95.

The zero-plant design enumeration found maximum per-coil issue slew exactly
0.3 A or less and minimum absolute-current headroom of 98.8 A across these
four streams. The actual implementation must reproduce this with exact
Card15 targets and must reject before calling the legacy runner if any target
is not representable, exceeds current limits or exceeds 0.3 A per coil.

Issue `k` affects state `k+1`; no software queue, clipping, retry, adaptive
choice, cleanup action or future actual current is permitted. Actions0--32
and states0--33 must match the audited p03 prefix.

## Execution and empirical stops

Current paired-boundary R_geo/Z_geo and Ip are exact/noiseless before each
issue; takeover-to-current causal observation/action history is available,
while future successors remain unknown.

The 25 mm R/Z and 5% Ip pre-issue clearance, 50 mm R/Z and 10% Ip outer
envelope, and 2 mm/2 mm/150 A post-successor caps remain unchanged. A branch
that reaches only a pre-issue `PULSE_CLEARANCE_*` stop is preserved as a valid
guarded candidate failure, and the campaign proceeds with the next independent
canonical reset. Any action, Card15, current, boundary, time, runtime, TSC,
solver, outer-envelope, successor-cap or raw failure aborts the campaign.

## Terminal and campaign gate

For each complete branch, states88--96 must satisfy the unchanged hold gate:

- maximum one-ms R and Z change at most 0.1 mm per axis;
- state88-to-state96 net R/Z at most 1 mm per axis and net Ip at most 100 A;
- every terminal state within 25 mm R/Z and 5% Ip of the source.

The campaign passes only if at least one of the three mixed-allocation
branches (not the baseline) completes and passes. A PASS is only a finite
nominal candidate for fresh repeatability and bounded-perturbation
qualification. If all mixed branches stop or fail the terminal gate, this
fixed grammar ends and the next step is a broader, explicitly bounded
action-sequence search rather than deeper p04/p07 ramps or a larger model.

## Budget and data role

- four independent resets/branches;
- at most 384 issue attempts/TSC calls/verified advances;
- at most 388 retained states and 1,940 raw artifacts;
- at least 65 GB free before launch and 35 GB after a 30 GB estimate;
- branch raw is route/action-allocation evidence only;
- zero model fitting/training and zero calibration/blind read;
- controller, expert, BC, DAgger, RL, fixture, calibration and holdout reuse is
  forbidden.

This design authorizes implementation, server tests, offline preflight and,
after they pass, this one four-branch campaign. It authorizes no controller,
MPC, recovery, waypoint/path, R_mid crossing, adaptation or RL stage.
