# R_geo/Z_geo 1 ms ID-2V0 control-utility and support audit design

Date: 2026-08-19

Identity: `rgeo-zgeo-1ms-id2v0-control-utility-support-audit-v1`

## Purpose

ID-2V0 is one bounded, server-tested, zero-new-TSC and zero-fit decision
audit. It prevents two different questions from being conflated after
ID-2U2:

1. whether the four-family development set covers causal history and
   level/time corners well enough for a model; and
2. whether the currently measured p04/p07 two-issue exact-return grammar has
   enough persistent, distinguishable control utility to justify collecting
   more histories for that same grammar.

ID-2V0 reads only the twenty tracked ID-2U1 development trajectories and
the frozen ID-2U2 evidence. The unopened `u01/u03/u05/u07` families do not
exist as result records and may not be inferred, generated, opened, or used.
No model is fitted, selected, or emitted.

## Evidence integrity

The stage binds by SHA-256 to the post-U2 route review, U1 config/result/raw
audit, and U2 config/result/independent audit/result report. It requires the
U1 PASS and U2 FAIL route tokens exactly, twenty development trajectories,
four independent history families, sixteen probe cells, and zero
calibration/blind reads. Any mismatch stops before analysis.

## Support decomposition

For every leave-one-family-out fold, the audit reconstructs the exact
30-dimensional U2 causal-prefix feature and the frozen fold-local scaler. It
reports:

- held distance and support threshold;
- nearest training family;
- centered feature rank and condition;
- squared-distance contribution from `time_level_age`, current R/Z/Ip,
  1/2/4-step R/Z/Ip finite differences, actual-current coordinates, and the
  four fixed-pole action-memory blocks;
- the largest individual normalized feature contributions.

This is a descriptive decomposition of the already frozen U2 support rule.
It may not change U2's support threshold or verdict. In particular, it must
not relabel the `u02` corner failure as pure arrival-pace causality unless the
measured feature blocks support that narrower statement.

## Control-utility recomputation

For each development family and each of the four signed p04/p07 cells, the
paired response is recomputed against its exact matched baseline over
horizons 1--8 and at state 40. The audit reports:

- absolute moving-baseline R/Z motion from each probe origin;
- maximum residual R/Z response by horizon and its fraction of baseline
  motion;
- state-40 residual magnitude;
- maximum paired `|delta Ip|` and exact issued-current/slew headroom;
- sixty-four-direction time-resolved and horizon-8 directional progress,
  maximum angular gap, and minimum best progress;
- best-versus-second-best action utility gaps and a `20 micrometre`
  equivalence class diagnostic;
- odd/even closure, signed-direction cosine, and isolated hybrid-excursion
  ratios;
- the one-ms observation/replanning boundary versus the longer fixed macro
  schedule used only for evaluation.

The audit distinguishes a measurable excitation from persistent control
utility. A transient peak alone cannot satisfy the route criterion.

## Retrospective program criteria

These criteria are frozen before implementing the audit, but the underlying
U1 data have already been observed. They are therefore program-design
criteria only, not prospective plant, safety, authority, or statistical
qualification gates.

The current pulse grammar may route to a history-support expansion only if
every development family satisfies all of:

1. maximum horizon-8 residual R/Z magnitude is at least `5%` of the matched
   moving-baseline horizon-8 R/Z motion;
2. maximum state-40 residual R/Z magnitude is at least `0.05 mm`;
3. minimum sixty-four-direction horizon-8 best progress is at least
   `0.02 mm`;
4. all exact Card15/current/slew/Ip integrity checks remain valid.

These values do not claim that 5%, 0.05 mm, or 0.02 mm are sufficient for
the final controller. They are only a low bar for deciding whether another
approximately 50 GB of the same pulse grammar has plausible control value.

## Frozen routes

If evidence or metric reproduction fails, stop as input/audit failure.

If every family meets the retrospective utility criteria, route to a
separately designed minimal `2 x 2 x 2` history-support extension. That
later design must preserve `u01/u03/u05/u07` unopened, introduce a common
arrival-history factor rather than four arbitrary schedules, and use both
held-history and leave-one-corner-out evaluation.

If any family fails, route to a separately designed, fixed-budget,
same-prefix multi-arm branch campaign. It must compare exact-Card15
transport continuation, pause/deceleration, signed residual dwell/return/
resume, and a finite recovery continuation under an absolute terminal and
sustained R/Z, velocity/hold, Ip, current, and hard-envelope objective. It
must not use a single transient response peak as authority.

## Authorization boundary

ID-2V0 executes no TSC, reset, plant advance, model fit, calibration,
holdout, controller, optimizer, MPC, waypoint, crossing, adaptation, expert
data, or RL. A completed route authorizes only the design of the selected
separate successor. Existing U1 raw remains immutable on the server.

