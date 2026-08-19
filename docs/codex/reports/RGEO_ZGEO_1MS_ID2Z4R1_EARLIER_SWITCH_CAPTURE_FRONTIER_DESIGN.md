# ID-2Z4R1 earlier-switch capture frontier design

## Decision identity

ID-2Z4 was frozen but never implemented, deployed or run. It is superseded
before execution because a state-97-only matrix would test dose and timing
too late, would give a complete matched-hold baseline undue scientific
priority, and would leave an avoidable low-dose/dwell blind spot. This is a
prospective route correction, not a post-result gate change and not an
ID-2Z4 FAIL.

ID-2Z4R1 is one finite, non-greedy capture discriminator rooted at the exact
ID-2Z3 state-89 causal prefix. It does not fit a model and does not perform a
rolling online search. It evaluates a preregistered frontier of complete
sequences so that switch time, two-axis action allocation and dwell are
tested together once.

## Evidence motivating the correction

The source state is `(R,Z,Ip)=(0.708635102 m, 0.035241343 m,
31286.4059 A)`. Tracked ID-2Z3 checkpoints give:

| state | source distance | R/Z step speed | source-relative Ip |
|---|---:|---:|---:|
| 89 | 24.367235 mm | 0.203647 m/s | about +1390 A |
| 93 | 24.504659 mm | 0.188667 m/s | about +1374 A |
| 97 | 24.565317 mm | 0.190375 m/s | +1354.698 A |

The exact state-96 to state-97 speed is `0.190374573 m/s`. Holding the
state-97 command later reaches a tracked state-105 distance of about
`25.4024 mm` with speed `0.300687 m/s`. Consequently, state 97 is not an
established terminal basin and its remaining radial margin to the 25-mm
capture gate is only `0.434683 mm`.

The p07-minus and p03-unwind Card15 increments are nearly orthogonal in the
14-coil coordinate (about 83.1 degrees). Existing finite paired responses
show p07-minus mainly supplies positive-R braking while p03-unwind supplies
a stronger positive-Z component and tends to release Ip. Those facts justify
a bounded mixed frontier, but they do not prove additivity, monotonicity,
capture, recovery or global authority.

## Frozen action grammar

The exact canonical-source prefix executes issues 0 through 88 and exposes
state 89 before the first candidate issue. Candidate issues are 89 through
100. Every candidate then holds its attained exact Card15 target for issues
101 through 112. The final state is 113 and the terminal gate uses states
108 through 113, so it observes the last six states after seven through
twelve milliseconds of held tail following the final candidate effect.

Tokens are:

- `B`: one exact p07-minus increment;
- `U`: one exact p03-unwind increment;
- `H`: retain the current exact Card15 target.

No token may be clipped, combined with another token in the same issue, or
exceed `0.3 A` on any single-turn coil in one millisecond. The twelve frozen
candidate strings are:

| id | candidate issues 89--100 |
|---|---|
| hold12 | `HHHHHHHHHHHH` |
| b4_h8 | `BBBBHHHHHHHH` |
| b8_h4 | `BBBBBBBBHHHH` |
| b12 | `BBBBBBBBBBBB` |
| u2_h10 | `UUHHHHHHHHHH` |
| b4_u2_h6 | `BBBBUUHHHHHH` |
| b8_u2_h2 | `BBBBBBBBUUHH` |
| b4_u4_h4 | `BBBBUUUUHHHH` |
| b6_u4_h2 | `BBBBBBUUUUHH` |
| b8_u4 | `BBBBBBBBUUUU` |
| b4_u4_b4 | `BBBBUUUUBBBB` |
| b4_u2_b4_u2 | `BBBBUUBBBBUU` |

This is a Pareto-stratified finite design, not a claim that the strings are
optimal. It covers switch points near states 89, 93 and 97, pure-braking and
mixed controls, low U doses, a four-U dose, front-loaded and interleaved
allocation, and explicit dwell.

## Offline and runtime gates

Before any TSC advance, the resolved config, source revision, evidence
hashes, exact state-89 prefix, issue/effect clocks, Card15 targets, absolute
current limits, per-step slew, queue semantics, storage reserve and full
budget must pass. `hold12` and at least one candidate containing both `B`
and `U` must be statically admissible. Failure is `NO_TSC`; thresholds or the
matrix are not edited in place.

Each rollout uses one authentic canonical reset and replays the complete
prefix. Every observed current state uses the same-step valid paired boundary
for exact/noiseless `R_geo,Z_geo` and same-step exact/noiseless `Ip` before
the next issue. The complete post-takeover causal observation and
controller-owned action/current history are retained. Future successors are
not known before their issue.

Any prefix, package, queue, Card15, readback, current-limit, boundary, Ip,
raw or runtime mismatch stops the campaign and is not a scientific grammar
FAIL. A prospectively frozen hard-gate stop after a candidate successor may
classify that candidate as infeasible, but no rejected issue is applied and
no retry or silent gate relaxation is allowed.

`hold12` is an absolute negative control. It may leave the finite runtime
envelope before state 113. A partial hold path is retained and audited but is
not required as a matched baseline for another independently complete and
safe branch. Paired response is descriptive only on overlapping observed
states.

## Scientific metrics and routes

A capture candidate must be complete and must satisfy, for every state
108 through 113:

- source R/Z distance `<=25 mm`;
- one-ms R/Z step speed `<=0.1 m/s`;
- absolute source-relative Ip `<=5%`;
- all unchanged hard Card15/current/queue/boundary/runtime gates.

Complete candidates are also summarized by terminal maximum speed, maximum
source distance, maximum absolute Ip fraction and action count. The report
records the nondominated set. If more than one branch captures, selection is
lexicographic by terminal maximum speed, terminal maximum distance, terminal
maximum Ip fraction, non-hold token count and candidate id. This is an
auditable tie-breaker, not an after-the-fact controller objective.

Routes are separated as follows:

1. input/package/offline/prefix/interface/raw/runtime failure: stop and
   diagnose; no scientific conclusion;
2. finite capture PASS: nominate exactly one frozen sequence for a fresh
   zero-fit exact-prefix replay and then a separate Recourse-L1 design;
3. finite frontier FAIL: close this exact twelve-sequence switch-time/B/U
   frontier and forbid another hand-tuned B-depth ladder; review action basis,
   time allocation and terminal objective.

No route directly authorizes feedback control, hold/recovery claims,
waypoint/path tracking, position generalization, R_mid crossing, online
adaptation, expert data, imitation learning or RL.

## Budget and data role

The hard maximum is twelve resets, 1,356 plant advances, 1,368 retained
states and 6,840 required five-artifact state files. The prospective raw
estimate is at most 90 GB. Deployment must show at least 145 GB free before
launch and preserve at least a 55-GB residual reserve under that estimate.

The compact causal trajectories from this campaign are prospectively
development-only for a later short-horizon, truth-recentered history model.
Replay siblings receive zero extra fitting weight. A selected fresh replay
is qualification evidence and zero fit. Calibration, blind holdout, expert
and controller-safety evidence require new identities.

## Downstream architecture

If fresh replay and Recourse-L1 later pass, the preferred model remains an
exact executor/queue plus a stable low-order history/innovation backbone and
only a small causal GRU/TCN residual when whole-family evidence justifies it.
Each 1-ms decision recenters on exact current `R_geo,Z_geo,Ip`; latent belief
represents unobserved memory and future-response uncertainty, not measurement
noise in those observables. The model should predict short candidate-sequence
outcomes/value and refusal support, then face fresh multi-history and
multi-position calibration/holdout before closed-loop waypoint work.

The final goal remains safe causal approximate tracking of finite relative
R/Z waypoints and paths from the fixed 1100-ms takeover, under exact Card15,
current, slew and Ip gates, ultimately including bidirectional repeated
R_mid crossing without resetting causal belief.
