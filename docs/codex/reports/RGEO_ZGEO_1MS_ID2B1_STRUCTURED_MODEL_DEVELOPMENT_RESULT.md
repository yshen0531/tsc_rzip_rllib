# R_geo/Z_geo 1 ms ID-2B1 structured model development result

Date: 2026-08-15 Asia/Shanghai

Implementation revision: `1e223619e2f6ac9685012665502a924744bd9bcd`

Final route:
`ONE_MS_ID2B1_NO_CONTEXT_ROBUST_ACTION_MODEL_TARGETED_DATA_REQUIRED`

## Execution and evidence integrity

The server installation matched the committed launcher, config, primary,
independent and test hashes.  Focused tests passed 7/7 and the complete 1 ms
regression selection passed 116/116.  ID-2B1 fit twelve deterministic LOCO
ridge models and did not call TSC or advance the plant.  It read no
calibration or holdout records.

The independent audit refit every fold, reproduced the full model artifact
and every metric exactly, and passed with no failure.  Evidence hashes are:

- primary result:
  `20441c50e20bcd4fb25c498904ebc35d5337b5cc067a3f16fac1d6383d9e2984`;
- model artifact:
  `ae79b79e64b13b0db248ffad7f8017a62875b842b32a179c9cba2dc70dca2379`;
- independent audit:
  `ef38f236f2dfa93f5ccb9a9aa6d73d669a7c94e14abcf2a9398a4e170a77be01`;
- execution log:
  `b868dc6bde017920f59d54e7473ed034188b35890b7b5fa9f12e430f03832d8b`.

The server output directory is
`rgeo_zgeo_1ms_id2b1_model_1e223619`.  Free `/home` capacity after the fit was
about 540 GB.  No raw trajectory was created.

## Load-bearing result

No action-conditioned candidate passed all three whole-context folds.
`stable_exp_signed` was the best scientifically useful diagnostic:

| held-out context | action-blind response RMSE | signed stable RMSE | improvement | peak-direction pass |
|---|---:|---:|---:|---:|
| `late_q0` | 0.4198 | 0.2392 | +43.0% | 5/6 |
| `history_p04_plus` | 0.4142 | 0.2307 | +44.3% | 5/6 |
| `anchor_p03_minus` | 0.4985 | 0.6596 | -32.3% | 1/4 |

The model therefore learns a repeatable signed response relation between the
two closely related contexts but does not extrapolate it to the distinct
p03-arrival history.  In the anchor fold its absolute geometry p95/max errors
were `2.741/2.889 mm`, above the frozen `1/2 mm` gates.

The signed/even model and the contextual interaction model performed worse.
The contextual model reduced absolute error in the two familiar contexts but
its response RMSE became `1.423`, `1.634` and `6.899`; this is a direct
development-set warning against adding capacity with only three independent
history families.

The source of the extrapolation gap is visible in the raw response geometry.
For p09-minus, the late-q0 and p04-arrival contexts have about
`0.840--0.848 mm` peaks already at one/two/four issues.  In the p03-arrival
context the one-issue arm is below the 0.05 mm signal threshold and the
two/four-issue peaks are only `0.0596/0.1048 mm`.  Current state-10 R/Z/Ip is
close across these contexts, but the complete causal prefixes are not.  A
two-context training fold cannot identify how gain changes along an unseen
14-dimensional arrival-history direction.

## What this does and does not mean

This is a clean model/support failure, not a TSC, runtime, deployment,
actuator, raw-data, optimizer, controller, recovery or global-authority
failure.  It does not show that stable memory is useless: its gain on two
folds is substantial.  It shows that three context families are insufficient
to qualify a history-scheduled response model under leave-one-context-out
evaluation.

Relaxing LOCO and fitting all three known contexts could make a finite lookup
or local mixture appear successful, but would not support trajectories that
move through new histories.  Increasing GRU/TCN capacity is still less
defensible: the fixed contextual model already exhibits severe extrapolation
overfit.  Calibration and holdout must remain closed.

## Recommended next decision

The next stage should be a prospective zero-new-TSC **context-bridge design
audit**, followed only after review by a fresh fit-eligible TSC campaign.  It
should:

1. inventory exact, already exercised p03/p04 arrival primitives and freeze a
   small set of intermediate strength/timing prefixes that all return to q0
   by the common state-10 prediction origin;
2. measure each context with its own baseline and the problematic p09 signed
   duration-1/2/4 family, plus a small p01 signed control family;
3. retain the full state-11--32 response and tail;
4. preassign whole context families to development, calibration and blind
   holdout before any new response is seen;
5. require critical replay, exact Card15/current/effect timing, R/Z/Ip hard
   envelopes and the simulator-identification data contract;
6. rerun the frozen signed stable-memory baseline first.  Contextual or
   neural residuals may be tested only if the added contexts make that simple
   model's complete-family error measurable and stable.

This context bridge addresses history interpolation at the source-local HFS
anchor.  It still does not identify pure position dependence.  After a
history model passes, a separate multi-anchor matched-time/different-position
and matched-position/different-arrival-history campaign remains necessary.

The alternative of qualifying only the three known histories is faster but
is not recommended as the main control model.  The final two-axis/path/
waypoint, Ip-safe and later HFS/LFS-crossing goal is unchanged.
