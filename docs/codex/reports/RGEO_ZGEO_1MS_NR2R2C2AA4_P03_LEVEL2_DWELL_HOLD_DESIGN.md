# R_geo/Z_geo 1 ms NR2R2C2aA4 p03 level2 dwell-hold discriminator

Date: 2026-08-14 Asia/Shanghai

Prospective identity:

```text
rgeo-zgeo-1ms-nr2r2c2aa4-p03-level2-dwell-hold-v1
```

Post-C2aA3 review clarification, frozen before implementation or execution:
A3 measured this level2 action only through state16 in the relevant prefix.
A4 states17--32 are a prospective late-state/history extension, not an
already qualified state domain. The `2 mm / 2 mm / 100 A` values below are
empirical stop thresholds and not a proved worst-case theorem for those
unseen successors. The sequence, thresholds and PASS/FAIL routes are
unchanged. A safe scientific FAIL ends further single-p03 static level/dwell
escalation as a prospectively recorded program/value-of-information decision;
it may not be followed by another such ladder stage. This is not a physical
claim that every higher level, longer dwell or switching law is impossible.

## Question and scope

C2aA3 qualified the p03 level2 cell only for a time-varying C2a design inside
levels q0--2. A4 asks the most direct finite-domain question: after the exact
q0 -> level1 -> level2 ramp, can holding the strongest qualified level2 action
through the entire 32 ms horizon materially arrest the source drift under the
already frozen short-hold gates?

This is not an optimizer or model search. Persistent level2 is the maximum
qualified action magnitude in this one-dimensional family. A FAIL rejects
only this sequence; without a plant monotonicity theorem it does not prove
that every q0/level1/level2 switching sequence fails, and it says nothing
about other directions or larger cumulative levels.

## Frozen execution

Two identical fresh canonical resets execute:

```text
step 0       q0
step 1       p03 level1
steps 2..31  p03 level2
```

The targets are byte-identical to A3. Adjacent single-turn changes are at
most `0.3 A`; level2 is at most `0.6 A` from q0. Both replays, their exact
checked-state comparison and a final independent raw audit are mandatory.
The run intentionally ends at level2; it is a finite TSC discriminator, not a
qualified stop, return or recovery action.

## Safety and scientific gates

A3 observed maximum successors of `0.803476 mm R / 0.827237 mm Z / 42.719 A
Ip`. A4 retains the pre-result `2 mm / 2 mm / 100 A` prospectively frozen
empirical finite-sentinel threshold/envelope and the `25/50 mm R,Z`, `5/10% Ip`
inner/outer source envelopes. This threshold is not a strict plant bound;
the frozen config field name `prospective_successor_bound` is retained only
as experiment identity. Every NR0/NR1 paired
boundary, limiter, exact Card15, command/readback slew, absolute-current and
Ip rule remains fail closed. Legacy runner clipping may not be relied on.

For terminal states 24--32, both replays must satisfy the previously frozen
C2a short-hold gates unchanged:

```text
maximum source-axis displacement              <= 5 mm
maximum absolute R/Z step                      <= 0.1 mm
terminal-window absolute R/Z net drift         <= 1 mm
all states remain inside the 25 mm inner envelope
```

## Routes

- PASS:
  `ONE_MS_NR2R2C2AA4_P03_LEVEL2_DWELL_HOLD_CANDIDATE_FOUND_FRESH_VALIDATION_REQUIRED`.
  It freezes this exact sequence for a separate fresh Nominal-H1 validation.
- Scientific FAIL:
  `ONE_MS_NR2R2C2AA4_P03_LEVEL2_DWELL_HOLD_FAIL_REDESIGN`.
- Interface, support or repeatability failures stop under separate fail-closed
  routes.

Even PASS is not Nominal-H1 until fresh validation, and never authorizes C2b,
recovery, atlas, model fitting, MPC, adaptation, RL or global reachability.
