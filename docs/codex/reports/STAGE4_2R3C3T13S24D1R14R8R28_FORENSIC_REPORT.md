# Stage4.2R3c3T13S24D1R14R8R28 forensic report

## Result

R8R28 completed its prospectively frozen front-loaded cumulative endpoint
timing-authority sentinel. The final route is:

```text
FRONT_LOADED_ENDPOINT_TIMING_AUTHORITY_INSUFFICIENT_BROADER_CAUSAL_CONTROLLER_REDESIGN_REQUIRED
```

All `64/64` authentic trajectories completed and passed the frozen runtime,
restart, causality, exact Card15 target-chain, current, finite-state, raw, and
independent-audit gates. Formal evaluation nevertheless found no repair among
the ten failed R8R7 baselines. The baseline-or-four-candidate held oracle
remained `6/16`, exactly the baseline pass count. Moving the unchanged four U
or V cumulative endpoint issues from `[10,14,18,22]` to either
`[10,13,16,19]` or `[10,12,14,16]` therefore did not establish finite formal
authority.

This is a genuine finite action-timing/controller-family design failure. It
is not a runtime, deployment, source-authentication, restart, causality,
Card15, current, raw, snapshot, solver, saturation, formal-evaluator,
reporting, real-MPC, Gate A, plant-reachability, or global-unreachability
result.

## Frozen identity, package, and validation

The design was frozen before implementation, offline construction, candidate
execution, formal metrics, or TSC outcome:

```text
design checkpoint               e4264d1
implementation checkpoint       7d8c40d
package checkpoint              a31262d
design SHA-256                   03c714797389872a9388b4ae8acd4711f6d2ad6db074ef25c22075ecbc8af099
PACKAGE_MANIFEST SHA-256         ee7b87742173707894152801ac475203144e6fa5224bdba0b641c09d50864597
SHA256SUMS SHA-256               c40e78e3f8d7fc37761bd1620fea685921eb31065708e5a63c01186b5344cdd9
```

The package contains 1,143 declared files plus `PACKAGE_MANIFEST.json` and
`SHA256SUMS`:

```text
strict JSON                        133
Python source                      446
shell source                       441
Markdown                           122
other declared source                1
focused unittest                 10/10
full unittest                 1400/1400
```

Local validation used only the project virtual environment and loaded the
existing `tests/conftest.py` Windows `resource` shim before unittest
discovery. Compilation, focused `10/10`, and full `1400/1400` passed. The
first invocation from inside the fresh empty-copy tree accidentally supplied
a nested copy path and failed before tests started; the corrected invocation
against the exact same copy passed all hashes, JSON, compilation, focused,
and full tests with one expected isolated-evidence skip. This was a local
command-path error, not a source or test failure. The Windows `bash`
executable was only a WSL launcher, so authoritative `bash -n` validation was
performed with the real server shell.

A fresh manifest-only transfer tree contained exactly 1,145 physical files
and no cache files. It was copied directly through the authorized SSH
workflow without local compression or extraction. Server staging and the
installed project both passed all 1,143 declared hashes, 133 JSON parses, 446
Python compilations, 441 `bash -n` checks, focused `10/10`, and full
`1400/1400` with one expected skip, using only the existing server virtual
environment.

## Server run and source authentication

The accepted server run is:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
stage4_2r3c3t13s24d1r14r8r28_runs/
stage4_2r3c3t13s24d1r14r8r28_front_loaded_cumulative_endpoint_timing_authority_sentinel_20260809_a31262d_v1
```

Every remote command used the existing server virtual environment and the
same output directory. Primary and structurally independent offline paths
authenticated the final R8R7 baseline, R8R14 cumulative atlas, and R8R27
route evidence. They agreed exactly before any worker or plant advance on:

```text
specifications                         64/64
major exact-Card15 issues            256/256
stored-target refreshes            1408/1408
maximum offline issue increment      0.1409259259259261
maximum predicted current use        0.3905
maximum refresh increment            3.7037037048793097e-06
new raw before authorization          0
real TSC before authorization         false
```

No R8, R8R1, or earlier R8-family trajectory was rerun.

## Prospective two-phase real-TSC execution

The safety phase completed first and remained formally blinded:

```text
safety trajectories                     16/16
full horizon / calibration / event       16/16
target chain / state prefix / trace      16/16
major issues                                64
refreshes                                  352
forbidden trace fields                       0
maximum current utilization              0.392
maximum issue increment       0.1407407407407407
safety raw inventory       16 files / 522050 bytes
safety raw digest
  6c0bee541d4d72cf5b1e1da77190d821144d7e19a5c70e780f52d4e41c0fdf13
```

Only after exact primary/independent safety agreement was qualification
authorized. Qualification then completed:

```text
qualification trajectories                48/48
full horizon / calibration / event         48/48
target chain / state prefix / trace        48/48
major issues                                  192
refreshes                                   1056
forbidden trace fields                         0
maximum current utilization               0.3924
maximum issue increment        0.1409259259259261
qualification raw inventory  48 files / 1576438 bytes
qualification raw digest
  f95e7cfbc125bd076829ce1d621725f0e4c2078542ade5041f61460d4abb488b
```

The combined immutable raw inventory is 64 files with digest:

```text
6ee50ed33eaee165f1543d67e669155e53acafd8cb5c67b879fcee45238a7b7f
```

Raw-phase reports use the frozen provisional success route because they
audit execution integrity before formal outcomes are opened. They do not
claim scientific authority. The final formal route above supersedes that
phase-local route.

## Formal authority result

The unchanged formal evaluator reproduced all 16 R8R7 baseline outcomes and
all 80 saved baseline/candidate metric rows exactly. Primary and independent
formal paths agreed with maximum absolute margin difference `0.0`.

```text
candidate       formal passes   failed repairs   baseline-pass regressions
g2 UUUU              5/16            0/10                   1/6
g2 VVVV              6/16            0/10                   0/6
g3 UUUU              6/16            0/10                   0/6
g3 VVVV              6/16            0/10                   0/6
```

Across the 64 new candidates there were 23 formal passes, all confined to
already-passing baseline contexts. The one regression was the minus-history
member of `p9_q2_a0p900_gap4_settle4` under g2 UUUU, whose minimum signed
margin became `-0.0006570666666658731`. Fail-closed baseline fallback retained
all six baseline passes, but no candidate repaired any failed baseline:

```text
baseline formal pass                         6/16
failed baselines                               10
failed-baseline repairs                      0/10
baseline-or-four-candidate held oracle       6/16
scientific authority gate                    FAIL
```

The best candidate improved the minimum signed margin in every failed
context, but the gains were insufficient to cross the formal boundary:

```text
minimum gain                  0.02813746666666672
median gain                   0.09123908539038728
maximum gain                  0.136557298392177
```

This positive but insufficient margin movement is evidence that U/V timing
changes affect the plant. It is not evidence that a causal selector or
feedback controller would pass, because even the post-result per-context
oracle repaired `0/10`.

## Independent recomputation and official hashes

The independent implementation rebuilt source authentication, all 64 specs,
offline action/target chains, safety and qualification raw audits, the
unchanged formal evaluation, candidate summaries, held oracle, gate, and
route without importing R8R28 primary computations. Agreement was exact:

```text
offline specifications/actions/targets       exact
safety raw primary/independent                exact
qualification raw primary/independent         exact
formal outcomes and numerics                  exact
route and scientific gate                     exact
```

Official final hashes are:

```text
analysis/final_report.json       b32aaa273c17952b0f6ffc32ba907f5f78cff93e7bfa67038e042d95d3d45bc4
analysis/final_independent.json  ed4c8b1d997cd670aa28447ba4c012e585c92f5bd2c9420acb57e424e35405d1
analysis/primary_detailed.json   0c33fc51fc46730b85d760022a77d70d91272a9ed22c09b0900e42e693d6253a
analysis/primary_summary.json    ebadba93595bc77257262f223cc27740ebd3c80434ab56df6d088dfaf57b2c18
all_specs.json                   e635a57519c34b28291efa56c1ae39b92c8bfc07c4cdfb3a927221c5d2facb5c
stage_manifest.json              b687a127185a21127f4923303b93ec734b0b3381aaf3cad282bc2b1cb6dfbc04
stage_state.json                 8b246c5617a0bf27a40ac02004c4c9350863ad427181cf878283529c23fa74b8
```

The final state records `finished=true`, `phase_status=complete`,
`real_tsc_executed=true`, `new_raw_count=64`, and
`stop_reason=formal_authority_gate_failed`.

## Compact evidence and reporting incidents

Large raw files remain on the server. The compact direct-copy audit contains
18 declared evidence files plus its manifest and sums, 20 physical files in
total, and no raw JSON.GZ:

```text
compact_audit.json SHA-256       af770eb49fac235d6d6c7bdbb8cc0d6111d5c0d525a12575f6762cb069a6709e
COMPACT_MANIFEST.json SHA-256     dfe3ba396c9429a3343bab924c06f1a17d0e36712333ee5d09acece768f6aa2e
compact SHA256SUMS SHA-256        8595f333bd3c15dd85d6b7a716d84f82f4b3f264a55546537c6abf488fdd4af8
```

The first compact-export script stopped before writing because it incorrectly
treated the stage manifest's source-subset `package_fingerprint` digest as
the current full deployment-manifest hash. The exact empty export directory
was verified and removed with `rmdir`; a corrected read-only export then
authenticated the installed deployment hashes explicitly and produced the
accepted compact evidence. A follow-up read-only diagnostic also terminated
on a here-document/variable error without mutation. These were compact-
reporting script errors after the immutable scientific result, not package,
raw, or result changes. The stage manifest's
`d1d8aa2acde5b7013b2e87a0cdee1a05bde209e3f6435d2970aba377170b46ae`
fingerprint is intentionally the authenticated R8R7 source subset; the
accepted compact audit separately records the installed full-manifest hashes.

## Authorization boundary

R8R28 is immutable and may not resume or be outcome-tuned under the same
identity. It authorizes no direct controller deployment, MPC qualification,
expert data, BC, DAgger, residual RL, or Gate A claim. Every source and R8R28
trajectory remains forbidden from learning data.

Because neither fixed endpoint timing nor a post-result per-context oracle
repaired a failed context, another fixed U/V schedule scan is not justified.
Before any new calculation, controller implementation, or TSC execution, the
next identity must prospectively freeze a genuinely causal visible-state
feedback architecture, its finite candidate family or deterministic law,
hard safety/fallback behavior, independent audit, and pass/fail routes. A
controller-design result remains only one step toward the complete Gate A
qualification envelope.
