# ID-2Z20 Authority-L0 result

Date: 2026-08-20
Final route: `ONE_MS_ID2Z20_PHASE_A_SIGNED_AUTHORITY_FAIL_CLOSE_GRAMMAR`

## Outcome

ID-2Z20 completed the entire preregistered Phase A and stopped at its intended
gate. All `17/17` rollouts completed: one matched hold plus sixteen signed
rank-four pulse/return trajectories at issues 32 and 40. Execution, exact
Card15 targets, `<=0.3 A` issue/return slew, paired-boundary observation,
current/Ip/outer gates, raw inventory and independent raw recomputation passed.
The independent audit reproduced the failing route exactly.

The evidence totals are `17` resets, `1,105/1,105` attempted and verified
plant advances, `1,122` states and `5,610` required artifacts totaling
`66,077,860,728` bytes. There were zero safe stops, zero model fits and zero
calibration/holdout reads. Phase B feedback candidates and all Phase C replay,
different-history and finite-return paths were correctly left unrun.

## Why Phase A failed

The four exact Card15 input coordinates had current-space rank four and
condition `4.447`, but input rank did not become useful two-axis plant
authority. At both phases only the `b0` pair passed the individual response
gate. The `b1` and `b2` peaks were only about `14--18 um`; `b3` was about
`4 um`. The best 64-direction weakest projection was only `9.88 um` at phase
32 and `10.32 um` at phase 40, below the frozen `20 um` gate. Consequently
neither phase had even one passing common geometry state, let alone the
required two consecutive states.

The phase-32 `b0+` trajectory also contained a discrete state-35 response of
`637.33 um` (`dR=-624.98 um`, `dZ=+124.85 um`). Its surrounding response was
only tens of micrometres. It is therefore a phase-specific hybrid transient,
not evidence that the full rank-four grammar has persistent two-dimensional
authority. The gate correctly did not allow this single-frame excursion to
carry Phase A.

## Reporting recovery

The first `dev_hold` physically completed before the original implementation
failed while JSON-serializing a live `Card15Target`. The initial result
incorrectly reported zero advances because no compact row had yet been
written. No rerun was performed. A separately tested reporting-only recovery
reparsed `66` raw states and `330` artifacts, reconstructed all `65` outgoing
Card15 actions, and found exact zero differences in R/Z/Ip, 14 coil and 48
wire values through state 32. The recovered hold was injected as the first
row and explicitly skipped during continuation. The final totals and
independent audit correctly include its `65` physical advances.

The preissue `inputa` byte hash cannot be recreated after the runner writes
the outgoing issue into the same state directory. That limitation is stated
explicitly; no byte identity was invented. Physical prefix equality,
outgoing action equality and raw inventory were independently verified.

## Scientific interpretation

This is a clean failure of this exact source-local, two-phase, one-issue
pulse then exact-return action grammar. It is not evidence of runtime error,
randomness, raw corruption, actuator failure, global plant unreachability,
absence of all control authority, controller failure or Recourse-L1 failure.

It does close the intended shortcut: numerical rank in 14-coil input space
cannot be used as a substitute for sustained R/Z/velocity authority. The
current grammar does not justify a feedback selector, a candidate-value
model or a controller, and no third model may be trained on the premise that
Phase A supplied a useful action set.

## Route decision

The next work must return to action allocation and terminal dynamics rather
than model capacity. The most defensible next design is a bounded zero-TSC
review that uses all existing Z1--Z20 evidence to define a *sustained* action
grammar around the full-F moving nominal: longer but still exact-return
segments, explicit braking/capture value, actual terminal one-step velocity,
and matched histories. It must distinguish smooth persistent effects from
scheduled hybrid events and must not reuse the failed one-pulse rank-four
claim.

Only if that review can prospectively identify a materially different,
statically admissible finite sequence family with a direct capture/authority
test should another TSC campaign be designed. Otherwise the source-local
Card15 basis/nominal/terminal set itself requires a higher-level redesign.
No further TSC or model training is authorized by ID-2Z20.

Compact evidence:
`docs/codex/audits/rgeo_zgeo_1ms_id2z20_20260820_2cc758de_v1/compact_evidence.json`.
