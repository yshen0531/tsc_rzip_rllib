# R_geo/Z_geo 1 ms ID-2B0 model-readiness audit design

Date: 2026-08-15 Asia/Shanghai

Identity: `rgeo-zgeo-1ms-id2b0-model-readiness-audit-v1`

## Decision being made

ID-2A completed as the first development-fit-eligible dataset in the new
round.  Its exact p09-minus four-issue primitive has a peak R/Z response of
`0.848202 mm`, `0.845307 mm` and `0.104847 mm` in the three complete causal
prefix families.  This deterministic factor-of-8.09 context difference is
strong evidence against an instantaneous fixed response map, but it does not
by itself specify a fair predictive model or prove position dependence.

The already tracked `ID2B v1` config is therefore retained as an unexecuted
design checkpoint and superseded before fit.  It starts prediction at state
10 with ten real action-history steps while including an ARX lag-16 candidate;
it contains no explicitly stable low-order state-space candidate; it does not
define causal propagation of future actual current; and its 4 mm absolute
geometry gates can be much larger than the measured action-conditioned
response.  No gate is weakened after model results because no ID-2B model has
been fit or trained.

ID-2B0 is the intervening zero-new-TSC, zero-fit readiness audit.  It decides
whether ID-2A supports a limited structured model comparison and freezes the
semantics needed by that comparison.  It does not select or fit a predictive
model.

## Evidence and execution boundary

The audit runs read-only in the server repository against the immutable
`rgeo_zgeo_1ms_id2a_runs_20260815_d25ee2a9` tree.  It authenticates the ID-2A
config, primary result, independent audit, raw inventory and every one of the
42 compact trajectories.  A structurally separate audit reparses all 1,386
raw states and independently recomputes the load-bearing readiness metrics.
Outputs are written only to a new ID-2B0 result directory.

Counters are frozen at zero plant advances, zero TSC, zero model fit/training
and zero holdout reads.  ID-2A remains development data.  Wire currents and
sprsina may be checked for raw integrity but may not become model features.

## Required analyses

1. Reconstruct each action trajectory minus its own matched context baseline
   over states 11--32.  Absolute natural evolution and action-conditioned
   response are reported separately.
2. Report response peak, peak state, terminal response, turning points,
   duration separation, signed even/odd components and Ip response for every
   context/direction/sign/duration cell.
3. At state 10, compare instantaneous allowed observations and the complete
   causal state/current/action prefix.  Exact same-prefix/same-action response
   collisions are a support failure; merely distant contexts are reported as
   extrapolation geometry, not relabelled as collisions.
4. State 0 through 10 and issues 0 through 9 are the only real takeover
   history available at the first prediction origin.  Padding, repeating the
   first frame or reading future states is forbidden.
5. Build a scaled output-response block Hankel from matched-baseline
   deviations and report singular values and energy ranks.  These values are
   descriptive candidate-order evidence, not a claim of true plant order.
6. Distinguish one-ms rolling prediction, which is re-centred on newly
   observed exact R_geo/Z_geo/Ip and actual current, from an open recursive
   state-10 rollout.  Inside a future planning rollout, only candidate issued
   actions are known; future actual current must be propagated by the exact
   actuator/queue/readback contract and must never be read from future labels.
7. Demonstrate why any ID-2B1 verdict must include both absolute-state and
   paired action-response metrics.  The matched future baseline is evaluator
   truth only and cannot be fed to a predictor.

## Routes

An evidence/raw mismatch stops as
`ONE_MS_ID2B0_INPUT_OR_RAW_INTEGRITY_FAIL_STOP`.

An exact collision of the complete allowed causal prefix and future action
with a materially different deterministic response stops as
`ONE_MS_ID2B0_CAUSAL_SUPPORT_FAIL_TARGETED_TSC_REQUIRED`.  The next data stage
would then be a separately frozen matched position/history discriminator, not
a larger network.

Otherwise the audit completes as
`ONE_MS_ID2B0_READINESS_COMPLETE_ID2B1_REDESIGN_REQUIRED`.  This route permits
only a new prospective ID-2B1 contract containing genuine-history baselines,
an explicitly stable low-order innovation/state-space candidate, fixed
sign/context interactions, leak-free actuator propagation, whole-context
LOCO evaluation and an optional small residual model.  It does not authorize
calibration, holdout, controller, MPC, recovery, online adaptation or new TSC.
