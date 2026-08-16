# R_geo/Z_geo 1 ms ID-2C0 control-relevance and method audit design

Date: 2026-08-16 Asia/Shanghai

Identity: `rgeo-zgeo-1ms-id2c0-control-relevance-audit-v1`

Frozen config SHA-256:
`e4cc745ccc8b013f5021d43b90ef2af1540cb11bcb7161113f92c34a7ec23123`.

The bound evidence set includes the compact q0 and A3 level-two trajectories
used to recompute the approximately five-percent state-16 response ratio; it
does not rely on that number as an unbound narrative constant.

## Decision

ID-2B1 remains final as a clean failure of its frozen candidate set.  Its
result does not, however, isolate a single cause.  Only three complete ID-2A
contexts exist; the signed/even paired-response features are structurally
context invariant; the sole contextual candidate uses a narrow interaction;
and the distinct p03 arrival changes current R/Z/Ip together with causal
history.  The former recommendation to proceed directly to an ordinary
six-to-eight-context bridge is therefore superseded before any new TSC.

ID-2C0 is a server-side, read-only audit of the already tracked compact
evidence plus the immutable server-side ID-2A compact trajectories.  It runs
zero TSC, advances the plant zero times, fits or trains no model, and reads no
calibration or holdout record.  A PASS authorizes only a separately frozen
ID-2C1 development design.

## Evidence corrections to be made explicit

1. The factor-of-eight p09 response contrast is a strong context effect, not
   a pure hidden-history result.  At state 10 the p03-arrival context also
   differs in R, Z and Ip.  No exact complete-prefix/action collision exists.
2. In matched-baseline response evaluation, the history base of
   `stable_exp_signed` and `stable_exp_signed_even` cancels.  Their remaining
   future-action feature difference must be recomputed across all contexts;
   if it is identical, these candidates cannot be described as learned
   context schedulers.
3. `stable_exp_contextual` may vary the response but has 387 features and only
   two independent training contexts in each LOCO fold.  Its failure is not a
   theorem against a compact LPV, hybrid or local-mixture model.
4. Natural nominal evolution and action response must be separated.  ID-2B0
   required a time-indexed nominal and a simple action response baseline;
   ID-2B1 instead fit total state delta in one ridge regression.
5. A 22-step curve RMSE or an aggregate arm-direction fraction cannot hide a
   critical one-ms event.  The audit must report horizon-one error, every
   signal arm's peak direction and peak-point error, and maximum pointwise
   error.

## Control-relevance question

The next data must be useful for the final control objective, not merely make
a probe easier to predict.  Existing finite evidence says:

- q0 is not a source hold;
- the tested constant p04/p07 schedules did not materially depart from q0;
- the p03 cumulative level-two response opposed the drift but was only about
  five percent of the source-to-state-16 displacement norm;
- q0-centred persistent p03/p04/p07 rays did not positively span R/Z;
- p09 has a large, short and context-dependent event, while p01 is smooth but
  weak.

ID-2C0 therefore audits readiness for a small, finite, canonical-source
time-varying sequence search.  ID-2C1 may use the full allowed `0.3 A` per
single-turn coil step, but every target is the actual fourteen-dimensional
Card15 vector and every action remains subject to exact slew, absolute-current,
boundary and Ip gates.  It must not become an unstructured fourteen-dimensional
random campaign.

The future search objective is an **active nominal corridor**: a finite
time-varying continuation that materially suppresses the matched q0 R/Z drift
while retaining two-axis residual-action and Ip/current headroom.  It is not
required to be an exact static equilibrium and it does not restore the retired
250/270 ms deadlines.  Discovery trajectories are development-search data
only.  A selected continuation still needs a fresh identity and fresh replay
before any model-development campaign is defined.

## Position/history factorization and data roles

ID-2C1 should retain prefix endpoints that can later support both contrasts:

- nearly matched current R/Z/Ip at one time with different arrival history;
- comparable arrival structure with different current position.

The first such batch is development/factorization only.  It must not be split
into undersized development, calibration and holdout subsets.  Once an active
nominal and a model class are frozen, calibration and whole-context blind
holdout require separate fresh identities.

## Routes

- Source, hash, raw or contract mismatch:
  `ONE_MS_ID2C0_INPUT_OR_EVIDENCE_INTEGRITY_FAIL_STOP`.
- Required attribution or control-relevance audit incomplete:
  `ONE_MS_ID2C0_METHOD_OR_CONTROL_RELEVANCE_AUDIT_INCOMPLETE_STOP`.
- Complete audit:
  `ONE_MS_ID2C0_CONTROL_RELEVANCE_AUDIT_COMPLETE_ID2C1_DESIGN_REQUIRED`.

The PASS route authorizes design only.  It does not authorize ID-2C1 TSC
under the ID-2C0 identity, a predictive model, calibration, holdout,
uncertainty tube, recovery, controller, MPC, transport, crossing, online
adaptation, expert data or RL.
