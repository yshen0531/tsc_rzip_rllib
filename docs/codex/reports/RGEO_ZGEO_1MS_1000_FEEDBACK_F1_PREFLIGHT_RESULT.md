# Fixed-1000 F1 pre-execution result

## Verdict

F1 is vetoed before offline authorization or any TSC reset. Server focused
tests exposed a control-relevance defect: its unchanged `0.35 mm` deadband
selects q0 no-op for the first path-A/path-B commands because their norms are
only `0.28/0.30 mm`. A PASS could therefore omit the intended first radial
segment while still satisfying the nominal checkpoint gate.

This is a prospective design/gate failure, not a runtime, package, plant,
model or controller result. F1 used zero resets and zero plant advances. Its
frozen identity must not be edited and run.

## Root cause

F0 used 0.35 mm as an endpoint acceptance tolerance while always issuing a
macro. After F0 exposed that an already-close later checkpoint needs an
abstention option, F1 incorrectly reused that acceptance tolerance as the
action-acquisition deadband. Those contracts are not interchangeable.

There is a second structural gap: V0 predicts a candidate's response relative
to a matched continuation. It does not predict the absolute history-
conditioned q0/no-action tail from the current observation to the future
checkpoint. Treating no-op as zero future deviation would therefore be an
unsupported point prediction even if the deadband were changed.

## Required route change

Before another real feedback sentinel, separate three quantities:

1. a non-vacuous acquisition/progress requirement relative to commanded
   displacement;
2. the wider finite endpoint acceptance/safety tolerance;
3. a causal, support-gated prediction/set for the no-action tail and each
   candidate's endpoint value under the complete recent history.

The recommended next work is a zero-new-TSC design/readiness stage for a
direct tail-and-candidate endpoint value model, using only prospectively
eligible fixed-1000 development evidence. It must include q0/no-op as a real
candidate, group whole histories, and set normalized progress/ranking gates
that a do-nothing path cannot pass. Only after a bounded retrospective screen
may a fresh matched-history calibration/blind campaign and a new feedback
identity be frozen.

No nearby deadband, waypoint or duration should be tried under F1.
