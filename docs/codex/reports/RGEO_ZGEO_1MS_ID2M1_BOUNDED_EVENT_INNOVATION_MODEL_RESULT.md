# R_geo/Z_geo 1 ms ID-2M1 bounded event/innovation model result

Date: 2026-08-18 Asia/Shanghai

## Verdict

ID-2M1 passed as
`ONE_MS_ID2M1_BOUNDED_STRUCTURED_MODEL_PASS_FRESH_CALIBRATION_DESIGN_ONLY`.
The selected candidate is the simpler `separated_event_memory`. The emitted
development model canonical SHA-256 is
`681c26da4829170ce166c86db47362f0365f6cb22a26d419463667777e6fae73`.

This is a source-local development model PASS. It is not calibrated, has not
seen a fresh holdout, and is not an authority, recovery or controller result.

## Evidence identity

- implementation revision: `82fdaee2ff1e1b53c9fc5a8a083bc6129564a524`;
- server output: `artifacts/server_runs/rgeo_zgeo_1ms_id2m1_20260818_82fdaee2`;
- result file SHA-256: `a9791cd29454515aa46f80d3871ea4c2ed2e9714e11f9a660d556d9b409ddbf5`;
- model file SHA-256: `9c177536a3cec7cb7c22ccadfd98dc7791fb45e5c81120b5020f4f59b78fb681`;
- independent audit SHA-256: `119e0001024d30e681ef670ceb7b862026f62f8afbf6085686c63ce5142ad883`;
- focused server tests: `10/10`;
- all matching one-ms server tests: `223/223`;
- TSC calls, resets and plant advances: `0 / 0 / 0`.

The separate process exactly reproduced the result and selected model.

## Selected event-memory model

All four whole-history folds passed every frozen gate. Their R p95 values
were:

| held families | 1 ms (mm) | 2 ms (mm) | 4 ms (mm) | worst unique 1 ms (mm) | response NRMSE |
|---|---:|---:|---:|---:|---:|
| h00/h01 | 0.11799 | 0.12244 | 0.13314 | 0.18812 | 0.06413 |
| h02/h03 | 0.11937 | 0.12106 | 0.13417 | 0.18694 | 0.06475 |
| h04/h05 | 0.22145 | 0.22703 | 0.22703 | 0.45260 | 0.04729 |
| h06/h07 | 0.22306 | 0.22852 | 0.22852 | 0.45241 | 0.04651 |

All `32/32` held probe peak directions were positive. Mean paired-response
NRMSE was `0.055671`. Scaled feature conditions were about
`61,577--69,297`, below the prospectively frozen `1e6` cap but high enough
that fresh calibration and OOD/support checks remain essential.

The improvement comes from the intended separation: exact-causal duplicate
transitions receive one fit weight; action response is fitted after removing
the per-issue mean; the time-indexed nominal is recovered afterwards; and
finite edge lags/dwell features supplement the fixed stable memories. No
history, sign, direction, conditioner or probe label is a feature.

## Rejected innovation candidate

`separated_event_bounded_innovation` passed one-ms R p95 (`0.110--0.248 mm`)
but failed multi-step recursion catastrophically. Its two-ms R p95 was
`9.67--10.34 mm`, four-ms R p95 `44.99--48.52 mm`, and mean paired-response
NRMSE `6.175`. It is permanently ineligible under this identity.

This is important architecture evidence: feeding exact current observations
into an unconstrained fitted correction, even with a fixed decaying rollout
state, is not automatically beneficial. The selected model keeps exact truth
for every real 1 ms replan origin but does not promote this failed correction
into the dynamics.

## Next gate

The next stage must freeze a fresh calibration and unopened whole-history
holdout campaign before running TSC. It should vary conditioner composition,
duration and issue time while staying inside the admitted p04/p07 Card15
action family. Calibration may construct only finite, groupwise horizon
tubes; model coefficients and feature definitions remain frozen. Holdout is
opened only after those tubes are fixed.

No authority shooting, recovery, NMPC, transport, crossing or online
adaptation is authorized until the fresh model/tube holdout passes.
