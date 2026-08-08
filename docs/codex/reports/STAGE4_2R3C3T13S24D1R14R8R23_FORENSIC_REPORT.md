# Stage4.2R3c3T13S24D1R14R8R23 forensic report

Date: 2026-08-09 Asia/Shanghai

## Result

Stage4.2R3c3T13S24D1R14R8R23 completed its prospectively frozen zero-new-TSC
causal online-innovation receding-horizon preflight. It authenticated and
strictly processed 432 immutable source trajectories, 1,728 causal decision
origins, and 11,232 forecast points. Source authentication, causal-feature
construction, support, finite-value, forbidden-input, point-prediction, and
primary/independent agreement gates passed.

The conservative model/tube gate and the optional innovation-usefulness gate
failed. The action-tree planner therefore remained fail-closed and was not
opened. The final route is:

```text
CAUSAL_ONLINE_FEEDBACK_MODEL_PREFLIGHT_INSUFFICIENT_REDESIGN_REQUIRED
```

R8R23 ran zero Ray, `gotsc`, TSC, controller, plant advance, raw trajectory,
or snapshot. It is a finite causal model and uncertainty-design failure, not
a runtime, deployment, source, raw, restart, causality, reporting, action-
authority, controller, real-MPC, formal-control, Gate A, or global plant-
reachability result.

## Frozen design, implementation, and package

```text
design checkpoint          0f61d94
implementation checkpoint  c4af11d
package checkpoint         7b2739c
```

The design was frozen before the R8R22 qualification/formal outcome was
opened:

```text
docs/codex/reports/
STAGE4_2R3C3T13S24D1R14R8R23_CAUSAL_ONLINE_INNOVATION_RECEDING_HORIZON_PREFLIGHT_DESIGN.md
SHA-256 fc06e9cfe22a4d4a6740e8822259ff1fdfdadbd2c08d72ceb0685a9d11fd6b6d
```

The package contains 1,106 declared files. Its metadata hashes are:

```text
PACKAGE_MANIFEST.json b6e66550a4fe71c62dd5c96147f9b5abcad370be8fd54f429eb3664e4caba33e
SHA256SUMS           5b4f58257384ba72d9455a5d3944868a689427c8d2385ed5d14109a21d4129f0
```

The project source passed compilation, focused `6/6`, and the Windows-shimmed
full suite `1356/1356`. A fresh empty direct-copy tree passed all 1,106
hashes, 122 JSON parses, compilation of 431 Python files, focused `6/6`, and
full `1356/1356` with one expected isolated-evidence skip. Server staging and
the installed project independently passed the same hashes, JSON,
compilation, focused, and full-suite checks, plus `bash -n` for all 436 shell
files. Only the project virtual environment and the existing server virtual
environment were used. No archive was created or extracted.

## Exact server run and evidence boundary

The server run is:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
stage4_2r3c3t13s24d1r14r8r23_runs/
stage4_2r3c3t13s24d1r14r8r23_causal_online_innovation_receding_horizon_preflight_20260809_7b2739c_v1
```

The authenticated bank contains, for each of 16 contexts, the baseline, 16
complete Boolean U/V schedules, and ten R8R22 continuous constant schedules:

```text
physical pairs                                  8
hidden-history contexts                        16
trajectories per context                       27
total immutable trajectories                  432
decision origins                            1,728
forecast points                            11,232
causal feature dimension                       42
action-expanded feature dimension             133
feature digest 14e1a15c6eb3ba305932b25918ec7127e46cd2a6f7c13ad50701545413fae849
target digest  037be84fcce81dc97c8350d88416fc0ac42534083d1fb5688ab000dee2e81dcc
```

Every outer and nested split excluded both history members of a whole
physical pair. Pair/history/source labels, outcomes, future state, wire or
vessel currents, and simulator internals were forbidden predictors. The
independent audit found zero forbidden inputs and zero non-finite exclusions.
All 1,728 held origins passed the frozen support rule.

This is development evidence, not a fresh controller holdout. Every source
trajectory remains forbidden from expert, BC, DAgger, residual-RL, or other
policy-learning data.

## Model and conservative-tube result

The separate fixed ridge model for each interval passed every held point-
error cap:

```text
quantity       maximum held error       frozen cap
R              0.00115977119136 m       0.015 m
Z              0.00325191242331 m       0.015 m
Ip            75.2220130796 A        3000 A
vR             0.0177881870704 m/s       0.05 m/s
vZ             0.0431037177513 m/s       0.05 m/s
```

The nested maximum-residual tube did not pass:

```text
reserved component containment       54,497 / 56,160
reserved containment rate              0.9703881766381767
required containment rate              1.0

maximum reserved R half-width           0.0126434064439 m  <= 0.025
maximum reserved Z half-width           0.0203448242930 m  <= 0.025
maximum reserved Ip half-width        738.923173319 A      <= 5000
maximum reserved vR half-width          0.106771340225 m/s  > 0.08
maximum reserved vZ half-width          0.183859708965 m/s  > 0.08
```

Whole-pair containment rates were:

```text
p5_q1_a0p750_gap4_settle4  0.9998518518518519
p5_q1_a0p900_gap3_settle4  0.8407407407407408
p5_q2_a0p750_gap3_settle4  0.9998628257887517
p5_q2_a0p900_gap4_settle4  0.9665294924554184
p9_q1_a0p750_gap4_settle4  0.9811851851851852
p9_q1_a0p900_gap3_settle4  0.9693333333333334
p9_q2_a0p750_gap3_settle4  0.9990397805212620
p9_q2_a0p900_gap4_settle4  0.9998628257887517
```

Thus the central point predictor is accurate on this finite leave-pair-out
test, but the frozen uncertainty mechanism is neither fully containing nor
narrow enough in velocity. Point accuracy alone cannot authorize a real
controller.

## Innovation usefulness and fail-closed planning

The already-observed one-step innovation update failed every usefulness
criterion:

```text
cold aggregate squared error             4.251464189166473
adapted aggregate squared error          5.213926114674505
adapted / cold ratio                      1.2263836369504335
required ratio                           <=0.95
strictly improved whole pairs             1/8
required improved whole pairs            >=6/8
innovation clipping rows                  94
allowed clipping rows                      0
```

The frozen rule therefore disabled innovation and selected the cold model.
This is evidence against this fixed bias update, not against every possible
causal feedback estimator.

Because the model/tube gate failed, the 11-level, four-decision planning tree
was not evaluated. The reported zero safe plans, zero predicted repairs, and
baseline-plus-policy oracle `6/16` are fail-closed sentinel values, not
action-authority or controller outcomes. No measured counterfactual states
were stitched.

## Independent reproduction and hashes

The independent implementation did not import the R8R23 primary
implementation. It independently rebuilt features, targets, whole-pair
splits, ridge fits, nested tubes, support, innovation, and fail-closed route.
Agreement was exact:

```text
feature / fit / tube / plan / outcome / route   all true
maximum fitted-value absolute difference        0.0
maximum tube absolute difference                0.0
primary-independent final agreement             true
```

Load-bearing server hashes before the compact derivative audit are:

```text
final report      3d1c88aca308baf67b30010b25df03398dd20e1d4458dfa2413a7c65ceb174cc
independent       af1b419bec6854ec901755c32f1c91131da1a09a0a0d4a1e1cc033ca6f0dd99a
primary detailed  a40a9b895bcfb69069fa5fe6dd7441b7159189d56f7aa50cc893db34a3bcd1a5
primary summary   4d900b3c5b477ff89dc1d62466b3d8e9ce132480f9c85ae26db91d55b1da285a
model evidence    9bc1e2a0e15597812defbf7724d673ae791ae50d7f70eb2aeda005d61f8ddc5f
stage manifest    2f3aef0b48cb5d35846da3e769110fb8e514374ea7cf57c18b364d9879c5e403
stage state       bd55964f69af3a17ce46f503ec629821c05dd54e9cbaf7ee71a9be644a227910
```

Those seven files total 7,613,619 bytes. The 7.22 MB fitted-model evidence
remains on the server. The direct-copied local audit contains only five
compact server JSON files plus its local manifest and sums. The compact audit
is 14,552 bytes with SHA-256
`70d8c861677178ffc153c34358d57fa9ae052c27f69ac39e5b0a91973039d59e`;
the compact manifest and sums hashes are
`a5674baba707e038eef80e96499a118dfc28967dcda6e63c7a67516e603bba59 /
89b9839516de0b584dbae73d78cc1886f31403567603b783e3154baed48f1ebe`.
No raw trajectory was downloaded.

## Downstream decision

R8R23 is immutable and may not be rerun or reinterpreted under changed gates.
Its failure requires a separately frozen new-identity causal model and local
uncertainty redesign before any real controller sentinel. A later
development-stage zero-TSC redesign may use these already consumed rows for
model development, but must not call them a fresh holdout; real controller
authorization requires a prospectively frozen fresh finite envelope.

The next design must preserve the exact causal features and action safety
boundary unless it prospectively justifies a new one, retain whole-pair
separation, independently reproduce point and uncertainty evidence, and
remain fail-closed. It must not weaken the observed R8R23 containment or
velocity-tube gates after the result.

Gate A, expert-data creation, BC, DAgger, and residual RL remain blocked.
