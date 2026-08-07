# Stage4.2R3c3T13S24D1R14R8R8 forensic report

## Result

R8R8 is final as:

```text
CAUSAL_DISCRETE_PULSE_MPC_SOURCE_OR_OFFLINE_FAIL_NO_TSC
```

The accepted v2 run is:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
stage4_2r3c3t13s24d1r14r8r8_runs/
stage4_2r3c3t13s24d1r14r8r8_causal_discrete_pulse_receding_horizon_mpc_core_20260807_dface45_v2
```

The frozen primary stopped at its zero-TSC acceptance gate. No real controller
trajectory was authorized, no raw directory was created, and no TSC, `gotsc`,
Ray task, controller action, or plant advance was executed.

## Provenance and validation

The design was frozen at `e61ee72` before implementation or result inspection.
The initial implementation was `7e1dc89`. Package `9179c9a` passed local empty-
directory, server staging, and installed validation. Its first offline attempt
stopped before stage creation because the source authenticator expected the
nonexistent R8R7 state value `"finished"` rather than the immutable actual value
`"complete"`. Authentication-only hotfix `2b287cb`, packaged at `dface45`,
changed no candidate, model, objective, action, gate, experiment identity, or
physical semantics.

The accepted hotfix passed:

```text
local project-venv focused / full                 11/11 / 1230/1230
empty direct-copy focused / full                  11/11 / 1230/1230
server staging focused / full                     11/11 / 1230/1230
installed server focused / full                   11/11 / 1230/1230
expected isolated-evidence skip                                 1
declared package hashes                                 1010/1010
```

Every server test used the existing server virtual environment. Transfer was a
direct directory copy; no local archive was created or extracted.

## Frozen primary result

The primary authenticated the exact R8R7 source and model artifacts and
completed all frozen pure computations:

```text
specifications                                                   16
causal decision origins                                          64
candidate forecasts                                             576
exact Card15 issue constructions                                512
exact stored-center cancellations                               512
enumeration side effects                                           0
forbidden or future inputs                                         0
fault-injection safe-zero cases                                  4/4
nonzero selections                                               0/64
```

The primary scientific gate required at least one nonzero selection. It
therefore failed before authorization. The exact compact hashes are:

```text
offline primary detailed
  aad3ee37b1c43672b9718b23b27e5640172dad03158cbaf247578975de05ee11
offline primary summary
  eb7cf6eb2a8abbea020d76f63a59f6f0b4c128255583998c321d6aa979086840
stage manifest
  5b0ad4b85c390e33a38bfb99c03f5163d1ea72c5efb1dd100f0a80477c8d68bf
stage state
  c7914e8f7842ee22892b008e861fba9ead7496fb5f48ae663c0d7fd2da116228
```

The state is `offline_primary_failed`, `finished=true`, `real_tsc_executed=false`,
and `new_raw_count=0`.

## Independent recomputation and reporting repair

The first independent output reproduced all 576 predictions and scores, all 64
selections, all 1024 action constructions, and all five model hashes with zero
numerical or action difference. It nevertheless mapped audit agreement to the
scientific PASS route. That was a reporting bug: audit agreement passed while
the primary scientific gate failed.

Reporting-only fix `98bcb9c`, packaged at `9b12970`, separates these facts and
inherits the authenticated primary route. Its validation passed compilation,
focused `12/12`, and full `1231/1231` locally, in an empty direct-copy package,
in server staging, and after installation, with one expected isolated-evidence
skip in each isolated/server full run.

The original independent JSON is preserved byte-for-byte as
`offline_independent_pre_route_reporting_fix_2144ddad.json`. The corrected
independent audit ran under a new log and reports:

```text
audit agreement passed                              true
primary numerical / outcome agreement          true / true
prediction / score maximum difference             0.0 / 0.0
selected candidate / exact action agreement     true / true
primary scientific gate passed                        false
scientific gate passed                                false
route agreement                                        true
real TSC / new raw                                    no / 0
```

Hashes are:

```text
preserved pre-fix independent
  2144ddad81a59ea2e197d2804b383c05ca4e4703616b51b25a054d08c71e649a
corrected independent
  625a1bb289db927d037a448b6dba88d930246d5360c4c78155b79e2e272b53c1
successful corrected log
  322c6ccbda863f219b7cd8285c740935fbcc92cda3f1644832d1dc36e1ea0fd0
```

A first corrected-launch attempt used the non-executable Windows-copy mode and
stopped at shell launch with `Permission denied`. Its log is preserved with
SHA-256 `f9379790095bd9c96a16dd4a00e9f173095c058f3776a0ae3f8ac9c6617eeb16`.
It entered no Python audit and changed no result. The successful attempt used
an explicit `bash` invocation of the already syntax-validated launcher.

## Retrospective score attribution

Read-only server-venv recomputation over the immutable 576 forecast rows
separated the frozen robust score from two diagnostics. These diagnostics do
not alter the R8R8 gate or authorize a controller:

| Score treatment | Best nonzero/zero ratio, min / median / max | Strictly better | Meets R8R8 `<=0.995` |
|---|---:|---:|---:|
| frozen candidate-specific robust tube | 1.010167968 / 1.017218600 / 1.030202082 | 0/64 | 0/64 |
| point prediction only | 0.995171374 / 0.997048163 / 0.999609468 | 64/64 | 0/64 |
| common static tube diagnostic | 0.994405727 / 0.996805307 / 0.999187393 | 64/64 | 8/64 |

All 64 point predictions moved slightly in the favorable objective direction,
but none achieved the prospectively required 0.5% gain. The additional
response uncertainty made every nonzero robust score worse than zero. This is
a clean frozen objective/model/action-design failure, not a constructor,
solver, runtime, deployment, restart, causality, raw, formal-control, real-MPC,
plant-safety, or global-reachability result.

## Handoff

R8R8 may not be tuned or resumed. The next stage is a separately frozen,
zero-new-TSC measured multipulse authority audit of immutable R8R7 raw. It must
establish whether either real four-pulse schedule repaired any failing baseline
before another MPC objective or real controller is designed. Gate A, expert
data, BC, DAgger, and residual RL remain blocked. All R8/R8R1/R8R7/R8R8
trajectories remain forbidden from learning datasets.
