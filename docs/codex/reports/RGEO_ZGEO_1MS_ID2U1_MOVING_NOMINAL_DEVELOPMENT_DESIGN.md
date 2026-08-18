# R_geo/Z_geo 1 ms ID-2U1 moving-nominal development design

Date: 2026-08-18

Identity: `rgeo-zgeo-1ms-id2u1-moving-nominal-development-v1`

## Purpose and data roles

ID-2U1 is the development-only first phase of the 8-family/40-stream matrix
frozen by ID-2U0. It executes only the four `development` families
`u00`, `u02`, `u04`, and `u06`: 20 unique whole-trajectory streams, each
with 40 one-ms issues and 41 retained states. The paced calibration families
`u01` and `u03` and paced blind families `u05` and `u07` remain unopened.
They may not be run, inspected, fitted, or substituted during ID-2U1.

The 20 passing trajectories become development-fit data only after all
execution, interface, raw, matched-prefix, signal, and Ip gates pass. They
are never calibration, holdout, expert, Oracle, BC, DAgger, RL, controller,
or safety-qualification data.

## Exact action grammar

Every stream begins at the authentic fixed 1100 ms source and uses the exact
ID-2C1 `p03_minus_stride1` Card15 nominal. A frontloaded history reaches
nominal level 18 or 22 and waits at that exact level until the probe clock.
At issue 24 or 30 it follows one of five matched branches:

- baseline: retain the exact nominal level over the matched probe clocks;
- p04 plus/minus or p07 plus/minus: retain the exact translated target for
  two issues, return exactly to the contemporaneous nominal level, and then
  resume the stride-one nominal.

No p04/p07 target is added to a simultaneous p03 increment. Every adjacent
14-coil target must be exactly Card15 representable, stay within absolute
current limits, and satisfy `max |delta I| <= 0.3 A` before the runner is
called. Legacy clipping is forbidden. Issue `k` affects state `k+1`; no
software queue or alternate effect timing is introduced.

## Observation and empirical simulator contract

Before every issue, current same-step paired-boundary R_geo/Z_geo and
same-step Ip are exact/noiseless observables. The complete post-takeover
causal observation and controller-owned action/current history is available.
The future successor is not known before issue.

This is a prospective TSC-only identification exposure, not a controller
safety qualification. Every action is checked before advance. Every observed
successor is checked against the frozen empirical per-step caps of 2 mm R,
2 mm Z, and 100 A Ip, the 25 mm/25 mm/5% inner issue envelope, and the
50 mm/50 mm/10% outer hard envelope. Any failure stops before the next issue;
post-action stopping is not reinterpreted as a pre-action transition tube.

## Frozen scientific gates

ID-2U1 PASS requires:

1. exactly 20/20 full trajectories, 20 resets, 800 verified plant advances,
   820 states, and all five required artifacts for every state;
2. exact Card15 issue/readback semantics, no silent clipping, no solver,
   runtime, boundary, limiter, current, Ip, inner/outer, or empirical-cap
   failure;
3. within each family, all four probe streams exactly match the baseline
   state/action prefix through the pre-probe state;
4. all 16 paired probe responses reach at least 0.02 mm R/Z norm and no
   paired response exceeds 100 A absolute Ip;
5. an independent server-side raw reconstruction reproduces all counters,
   compact states/actions, prefix checks, response metrics, and artifact
   inventory.

Failure categories remain distinct: storage/offline/input, execution or
interface, raw integrity, prefix mismatch, and signal/Ip design failure.
No failed or partial identity may be resumed after a plant advance. Raw is
preserved for diagnosis, and no failed record is fit eligible.

## Storage and authorization boundary

At least 75 GB must be free before the run. The prospective raw estimate is
50 GB and at least 25 GB must remain after that estimate. Compression is
forbidden. The output directory must not exist.

ID-2U1 PASS authorizes only a separately frozen, bounded comparison of a
support-gated time/phase-scheduled stable local model and one small persistent
causal sequence residual on these development families. Calibration and blind
families remain unopened until a model artifact and evaluator are frozen.
ID-2U1 cannot establish authority, hold, recovery, a transition tube,
controller, MPC, waypoint/path tracking, R_mid crossing, adaptation, expert
data, RL, or reachability.
