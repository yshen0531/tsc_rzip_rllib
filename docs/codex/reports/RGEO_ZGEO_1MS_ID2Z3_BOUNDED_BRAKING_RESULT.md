# ID-2Z3 bounded braking rolling-search result

## Outcome

ID-2Z3 completed every admitted branch without a runtime, actuator, boundary,
Ip, prefix, raw, retry, or plant-abnormal failure. The structurally separate
full-raw recomputation passes after one reporting-only lifecycle repair. The
immutable scientific route is
`ONE_MS_ID2Z3_BRAKING_SEARCH_EXHAUSTED_GRAMMAR_INSUFFICIENT`.

This is a finite source-local action-grammar failure. It is not a controller,
recovery, waypoint, global-reachability, or plant failure.

## Evidence identity

- Physical implementation: `68dff0c7733b6ff19dacbbe2917c3c82db8e8a73`.
- Reporting-only audit repair: `54e1601836da796098fda40b2d9eea6e4472742d`.
- Config SHA-256: `434d4629362e154a9d4f26e88b677ab428e75baf26c2d0500a3f113e2baded86`.
- Primary SHA-256: `72ba717fb4b4ad59e35b96e8d4ee5f3689c8df4f886b1497bddfd08dc631106c`.
- Repaired independent SHA-256: `d5bdeb5f88189e0c0617e89408441a4f7c138b0c4a983414dda03695c76f12fe`.
- 14 rollouts, 1,366/1,366 verified one-ms advances, 1,380 states.
- 6,900 required files, 81,272,235,120 bytes, inventory digest
  `7978b9e074b45e233147aa64f3d181cf34eb593723d9701692ae15e4a0e5de9c`.
- Model fits, calibration reads, and holdout reads: zero.

The first independent audit failed only because reconstructed raw
`state-k/inputa` contains outgoing issue `k`, whereas the compact state was
recorded before that rewrite. The auditor already checked every outgoing
Card15 field independently but failed to mark the row with the repository's
existing recovered-raw lifecycle. Revision `54e16018` adds that marker; it
does not alter any action, raw state, primary metric, gate, or route. Server
focused tests passed 8/8 and the complete one-ms suite passed 416/416 before
the repaired zero-TSC audit passed with no failures.

## Scientific result

`r0__p03forward4` was excluded prospectively because its absolute-current
headroom was 94 A, below the frozen 100 A floor. In every one of the five
rolling decisions, `p07minus4` was the sole eligible braking arm and was
selected. The selected sequence is five consecutive four-issue p07-minus
ramps.

The selected p07 arm remained measurable and improved matched-hold terminal
speed in every round, but it did not produce a capturable stationary tail.
The round terminal maximum speeds were `0.3682`, `0.3502`, `0.3194`, `0.3236`,
and `0.3007 m/s`. The corresponding terminal source distances were `24.794`,
`24.963`, `24.976`, `25.469`, and `25.402 mm`.

At the final logically committed state 97, source distance was `24.5653 mm`
and one-step R/Z speed was `0.1904 m/s`. Holding the resulting command for the
eight-ms lookahead allowed speed to grow again; over terminal states 102--105
the maximum distance was `25.4024 mm` and maximum speed was `0.3007 m/s`. Ip
remained inside its frozen five-percent cap. The observed braking action is
transient and the held endpoint is not a stabilization or recovery set.

## Route decision

Do not extend the same p07-only ladder or reinterpret it as feedback. The
next stage must change the candidate grammar and explicitly search for a
capture sequence: additional p07 braking depth plus a separately allocated
second-axis/capture action, with exact Card15 time sharing and matched-hold
comparison. Canonical-source branch replay remains an offline finite search
tool. Any nominated sequence still needs fresh exact replay and bounded-tube
recourse qualification before it may affect a controller.
