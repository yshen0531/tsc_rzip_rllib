# R_geo/Z_geo 1 ms ID-2C2 fresh nominal/vector validation result

Date: 2026-08-17 Asia/Shanghai

Implementation revision:
`58f24fc0266259a166288bb60a8f413cc6edd424`.

## Result

The server completed the exact frozen 18-rollout matrix with 18 resets,
576/576 advance attempts, 576/576 `gotsc` calls and 576/576 verified one-ms
plant advances. The complete raw tree contains 594 states and 2,970 required
artifacts totalling 34,982,396,856 bytes. Its line-delimited inventory digest
is `ace05c327380a5945fecad6b9c5e1576543b852a58e85e08b0b687b020389ad5`;
no required artifact is missing.

Primary route:
`ONE_MS_ID2C2_FRESH_NOMINAL_VECTOR_VALIDATION_PASS_STRUCTURED_MODEL_DESIGN_REQUIRED`.
Primary SHA-256 is
`3d665ba7044ae3dca0635987249c241a5d2559764437de802737580ae933a925`.
The independent server-side raw reparse passed with no failures; its SHA-256
is `a4f693915a001d31a64954f30c31d1b3ba345ed6cd8cc4f85d9c0751b3051976`.

## Recomputed scientific evidence

All nine fresh whole-trajectory replay pairs are exact in the checked
R/Z/Rmid geometry, Ip, 14 coil currents, 48 wire currents, issued action
stream and four semantic artifacts. The maximum numerical difference in each
reported physical channel is zero.

Both fixed nominal replays reduce terminal source-relative R/Z norm by
`34.1881573064%` against their matching q0 replay. Maximum source-relative Ip
departure is `722.7429 A`.

Both residual replay sets reproduce the same complete metrics. Every p04,
p07 and p09 signed arm peaks between `34.990` and `51.990 micrometres`; the
largest absolute Ip response is `28.9844 A`, and the largest terminal/peak R/Z
ratio is `0.352771`. The peak-vector matrix has rank two, best two-column
condition `2.70623`, and circular maximum angular gap `136.40943 degrees`.
Each plus/minus pair is nearly opposed; the weakest opposition magnitude is
`0.999607`. Thus all frozen repeatability, nominal, signal/Ip, tail and
two-sided finite positive-span gates pass.

This geometry belongs to the exact one-issue-plus-return primitives and their
causal tails. It is not an instantaneous Jacobian, superposition theorem,
uncertainty tube or recovery policy. P09 remains a separately labelled
hybrid/event primitive.

## Execution identity

Remote run:
`/home/yangshen0711/tsc_all/tsc_rzip_rllib/rgeo_zgeo_1ms_id2c2_runs_20260817_58f24fc0`.

Remote log:
`/home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/rgeo_zgeo_1ms_id2c2_20260817_58f24fc0.log`,
SHA-256 `3fe725d418cfd96951963ec3ddd14fe31befbce45a4e59bc79cb40df8af6fe46`.

Server validation before TSC passed `7/7` focused tests, `133/133` complete
one-ms regressions, `bash -n`, Python compilation and a zero-plant offline
preflight with 18 fixed streams. The run began with 557,672,910,848 free
bytes and ended with 522,126,667,776 free bytes.

## Claim and next boundary

ID-2C2 is immutable evaluator-only data. It may not be fit, calibrated,
turned into a fixture, treated as a blind holdout or used for controller,
expert or RL training. Its exact repeatability does not make a replay lookup
table a useful dynamics model.

The PASS authorizes only a separately frozen structured-model or
model-identifiability design. Any fit must use ID-2C1 only after that design
explicitly grants its postcampaign development role, retain ID-2C2 as fixed
evaluation, and distinguish a time-indexed active nominal from causal action
response. Calibration, blind context/history holdout, uncertainty tube,
recourse and controller work remain blocked.
