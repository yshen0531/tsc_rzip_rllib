# Stage4.2R3c3T13S24D1R14R4 forensic report

Finalized 2026-08-04 after the authentic 200-task TSC campaign, primary
postprocessing, a structurally separate server-side raw audit, and compact
download hash verification.

## Result

D1R14R4 is a clean safety/restart/causality PASS and a genuine response-signal
geometry FAIL. It is not a runtime, deployment, restart, raw-corruption,
summary/reporting, plant-abnormality, closed-loop-control, or MPC failure.

The sole frozen gate failure is two of the 256 branch-direction signal tests:

```text
context                 p9_q2_a0p750_gap4_settle4 / minus_first
issue task step         18
direction               pooled_mixed_0
positive branch peak    0.004464999999953534
negative branch peak    0.004298000000013680
frozen minimum          0.005
```

All other formal response-geometry gates passed:

```text
direction signal                              254 / 256
rank four                                       64 / 64
condition <= 20                                 64 / 64
maximum condition number              11.570074108693706
issue coordinate/field antipodality            128 / 128
minimum direction peak                0.004298000000013680
```

The route is therefore exactly:

```text
TIME_SHIFTED_SIGN_SPLIT_SENTINEL_GEOMETRY_FAIL_REDESIGN_REQUIRED
```

The `passed=true` field in the independent audit means that the independent
audit itself completed and agrees with the official result. Its
`classification.sentinel_pass` is false and its independently reproduced
route is the geometry-failure route above.

## Code and package identity

```text
local branch
  codex/stage4_2r3c3t13s24-sequential-transition
design commit
  ea49eac
implementation commit
  d27993b
final LF/checksum package commit
  f5b8348
package fingerprint
  c9c6fc870618ecbefe1bf9891a6f918927c2062753e2750596d2e73ec7ecf523
spec digest
  080a2df84c86801d76251853a165839e8db59f6614f6b2b446141b0691841059
requested matrix digest
  c8cd62c00c1f60b46312927789659657dc8cc35717533193433b0e398c1ec94c
```

The first staging directory from package checkpoint `e1437ff` was rejected by
`bash -n` because transferred working-tree shell files had CRLF endings. It
was not installed and created no specs, controller, plant step, raw, Ray,
`gotsc`, or TSC execution. The final `f5b8348` package normalized the declared
R4 shell files to LF, rebuilt checksums, passed installed-server validation,
and is the only package that generated the run below. This was a packaging
error only and did not change experiment semantics.

## Remote evidence

```text
valid staging
  /home/yangshen0711/tsc_software/stage4_2r3c3t13s24d1r14r4_f5b8348_v2
run
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3t13s24d1r14r4_runs/
  stage4_2r3c3t13s24d1r14r4_time_shifted_sign_split_sentinel_20260804_f5b8348_v1
real log
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/
  stage4_2r3c3t13s24d1r14r4_run_20260804_f5b8348_v1.log
postprocess log
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/
  stage4_2r3c3t13s24d1r14r4_postprocess_20260804_f5b8348_v1.log
independent log
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/
  stage4_2r3c3t13s24d1r14r4_independent_20260804_f5b8348_v1.log
```

The 200 raw JSON.GZ files remain server-side. Only compact evidence was copied
directly, without an archive, to:

```text
docs/codex/audits/stage4_2r3c3t13s24d1r14r4_20260804_f5b8348/
```

## Execution, integrity, and safety

```text
expected / actual / strict-parsed raw             200 / 200 / 200
raw bytes                                             6,285,765
official raw inventory digest
  44a7eb8e677f88f32c57a6be59273501e73f7657527371e1b59578a95c2ae7a9
completed / success / nonempty trajectory          200 / 200 / 200
nonempty causal controller trace                          200 / 200
safety / finite / full horizon                      200 / 200 / 200
exact source state prefix / trace                    200 / 200
fresh zero-baseline reproduction                           8 / 8
exact issue / causal stored-center cancel            192 / 192
source R2 strict raw / identity exact                   72 / 72
snapshot authentication / unique                         8 / 8
runtime/environment errors                                   0
plant/solver errors                                           0
saturation or clipping                                        0
forbidden-input trace rows                                     0
maximum current utilization                                  0.3904
```

The real log has SHA-256
`34154d6ee5b88bbc90de0b5c4d4f0e766f9346322e723dd055124646b83fe45f`.
The primary final result has SHA-256
`af9acfb9e524e6ad33799b832981ec7fb2e265ff7c1d3e78796413e83382db71`.
The independent result has SHA-256
`6a4eec4a660beb6a29e11e184906b8b7a737834280091f1997af74e86fbd761c`.
Primary and independent raw inventories, response geometry, route, safety,
restart, source, snapshot, and log conclusions agree exactly. Compact local
SHA-256 values were checked against the server for all nine downloaded files.

## Scientific interpretation

The failed direction is still finite and nonzero, and its containing positive
and negative branches remain rank four with condition numbers below 20. The
failure is specifically insufficient preregistered response magnitude above
the quantization/noise margin in one authentic visible-state/time/history
context. The gate is not weakened after observing the result.

Report-only diagnostics show that time, sign, and hidden-history response
differences can be of response-scale magnitude: maximum relative cross-time,
matched-history, and cross-sign differences are approximately `1.2395`,
`1.2586`, and `1.0521`. These are not failed gates, but they rule out claiming
a time-invariant, hidden-history-invariant, or shared-sign linear response
from R4. A later model must use causal visible measurements and time/state,
not pair/history labels, and must validate holdout prediction explicitly.

Formal tracking passed 50/200 and was diagnostic only. R4 probes are not a
controller-performance test and are permanently forbidden from expert data.
The result does not validate transition-model accuracy, superposition,
amplitude linearity, MPC, new targets, continuous actuator variation, noise,
disturbance recovery, or long hold.

## Next action

R4 is immutable and must not resume. A new zero-TSC identity will authenticate
all R4 evidence and test one globally fixed candidate: multiply only
`pooled_mixed_0` by `1.5` at every new issue time and in both signs, without
context/history-dependent selection. The zero-TSC stage may establish only
exact Card15/action/current/quantization safety on authenticated baseline
states. It cannot prove amplitude scaling, online cancellation, or plant
response. Only a pass may authorize a separately frozen fresh real-TSC
sentinel across every context, time, and sign for the replacement direction.

## Commands and validations actually run

- Local repository boundary, branch, commit, and dirty-state checks.
- Local compileall, all-JSON scan, 16 focused tests, and 1095 complete unit
  tests using `venv/Scripts/python.exe`.
- A 566-file empty-directory direct-copy deployment simulation with package
  hash/import/self-test verification.
- Remote path/virtualenv preflight, 566/566 package hashes, `bash -n`, server
  virtualenv compile/import/JSON checks, focused tests, and installed-package
  verification.
- One zero-plant offline spec/source gate: 200 unique specs, 8 baselines,
  192 probes, issue counts 64 each at steps 14/18/22.
- One authentic Ray campaign with fixed capacity 96 and exactly 200 TSC tasks.
- Server-virtualenv strict gzip/JSON parse of all 200 raw files.
- Primary postprocess and structurally separate independent raw/source/log
  forensics on the server.
- Direct download and local/server SHA-256 comparison for nine compact files.

No R4 task was resumed or rerun. No transition model, MPC, expert dataset, BC,
DAgger, or RL code was executed.
