# R_geo/Z_geo 1 ms ID-2W1 sustained branch campaign design

Date: 2026-08-19

Identity: `rgeo-zgeo-1ms-id2w1-sustained-branch-campaign-v1`

## Purpose

ID-2W1 is one bounded, prospectively frozen TSC-only development campaign.
It follows ID-2V0's decision that the existing two-issue p04/p07 pulse is a
useful excitation but not a demonstrated control grammar. It does not add
arrival histories and it does not fit a model. Instead, it measures whether
a larger but still exact-Card15, rate-limited, time-multiplexed residual
sequence can produce sustained and capturable two-axis progress around the
selected p03 moving nominal.

This stage deliberately distinguishes:

- transport supplied by the p03 nominal;
- the opportunity cost of pausing that nominal to create actuator headroom;
- residual geometry while a cumulative branch is held; and
- the tail after an exact residual return and delayed p03 catch-up.

The campaign is simulator-only empirical exploration. Exact current
R_geo/Z_geo/Ip and the complete takeover-to-current causal history are known
before every issue, but a novel successor remains unknown before its issue.
Runtime state checks can stop before a later issue; they do not turn the
current unknown successor into a pre-action transition tube.

## Common causal prefix and six branches

Every rollout starts from the canonical 1100 ms source and replays the same
p03-minus stride-one prefix:

- issue 0: q0;
- issues 1--18: p03 levels 1--18.

The state before issue 19 is therefore the same exact causal prefix for all
six branches. The horizon is 48 issues, ending at state 48.

The six prospectively frozen branches are:

1. `uninterrupted_nominal`: continue p03 levels 19--31 at issues 19--31,
   then hold level 31;
2. `pause_catchup_baseline`: hold p03 level 18 at issues 19--32, apply
   levels 19--31 at issues 33--45, then hold level 31;
3. `p04_plus_depth6`;
4. `p04_minus_depth6`;
5. `p07_plus_depth6`;
6. `p07_minus_depth6`.

Each residual branch uses the same p03 schedule as
`pause_catchup_baseline`. Relative to p03 level 18 it applies residual
levels 1--6 at issues 19--24, holds residual level 6 at issues 25--26,
returns through levels 5--0 at issues 27--32, catches p03 up through levels
19--31 at issues 33--45, and holds level 31 at issues 46--47.

The residual is constructed in Card15 decimal field space from the already
authenticated p04/p07 signed target. Each adjacent issued target must be
exactly representable, remain within absolute current limits, and change
every coil by at most 0.3 A. The maximum residual offset may reach 1.8 A,
but no single issue may exceed the 0.3 A rule. Legacy runner clipping is
forbidden.

## Timing and event semantics

Issue k first affects state k+1. Residual levels 1--6 first appear at states
20--25. The common maximum-depth plateau is states 25--27. Because prior
evidence identified state 27 as a possible hybrid return/history event,
state 27 is always reported but cannot be the sole reason for a PASS.
States 25 and 26 are the primary non-hybrid plateau decision states.

The residual has returned to zero by state 33. P03 catch-up finishes at
state 46, and states 46--48 form the terminal common-command observation
window. No software queue or future measured current/state is added.

## Execution and safety contract

The finite campaign contains exactly 6 resets, at most 288 attempted plant
advances, 294 retained states, and 1,470 required raw artifacts if complete.
There is no retry after any attempted advance. Any failure preserves the raw
prefix and stops the identity.

Before every issue, the implementation must validate the same-state paired
boundary, exact current R_geo/Z_geo/Ip, current limits, Card15 fields,
issued/readback slew, effect clock, abnormal/runtime status, and outer
R/Z/Ip envelope. Before every residual ramp-up or plateau issue it must also
require the frozen inner exploration clearance. After every successor it
must check a prospectively frozen empirical step cap and stop before the next
issue on any failure.

The empirical step caps and inner/outer margins are finite simulator
exploration thresholds, not physical theorems, transition tubes, recovery
sets, or deployment guarantees. The branch search cannot certify its own
safety, recovery, or controller use.

## Prospective control-utility gates

All paired responses are relative to `pause_catchup_baseline` at the same
state. All gates are frozen before any ID-2W1 plant advance.

Execution/data gates require:

- all six rollouts complete with exact action/current/raw integrity;
- all six state/action prefixes through issue 18 match exactly;
- the two baseline schedules and all four residual schedules match the
  frozen streams;
- maximum absolute paired Ip response no greater than 350 A.

Residual signal and persistence require, for every signed arm:

- peak paired R/Z norm over states 20--32 at least 0.25 mm;
- median paired R/Z norm over states 25 and 26 at least 0.20 mm; and
- the state-25/state-26 response-vector cosine at least 0.5.

Common-state two-axis utility requires at both states 25 and 26:

- the four signed response vectors have maximum angular gap no greater than
  180 degrees; and
- the weakest best projection over a 64-direction grid is at least 0.02 mm.

State 27 is reported independently. It may strengthen uncertainty or hybrid
classification, but it may not repair a state-25 or state-26 gate.

Return/catch-up integrity requires every signed branch at states 46--48 to
remain within 2.0 mm R/Z norm and 350 A Ip of the paused baseline. This is a
bounded-tail gate, not a recovery qualification. Absolute distance to the
source and to `uninterrupted_nominal` is reported at every state but is not
used to disguise a paired-response failure.

## Data roles and route

If and only if every execution, raw, prefix, signal, common-state geometry,
Ip, and bounded-tail gate passes, the six branches become prospective
development action-grammar evidence and may support a separately frozen
surrogate/teacher-data design. They are never calibration, blind holdout,
expert, BC, DAgger, RL, recovery, or controller qualification data.

A scientific FAIL with clean execution stops this cumulative p04/p07 branch
grammar. The next route is then a bounded redesign of the actuator sequence
family or the nominal allocation, not another capacity ladder and not more
histories for the same failed grammar. An execution/interface/raw/safety
failure remains separate and cannot be interpreted as a plant-utility FAIL.

Even a PASS is only a source-local finite action-grammar result. It does not
qualify authority over a region, a transition tube, hold/recovery, rolling
control, a waypoint/path, R_mid crossing, adaptation, or reachability.

