# Stage4.2R3c3T13S24D1R14R8R27 forensic report

## Result

R8R27 completed its prospectively frozen zero-new-TSC point-versus-reserve
authority discriminator. The final route is:

```text
POINT_ACTION_TIMING_AUTHORITY_INSUFFICIENT_BROADER_CONTROLLER_REDESIGN_REQUIRED
```

The point-only search found robust-formal plans in `6/16` contexts, but all
six were contexts whose unchanged baselines already passed. It repaired
`0/10` failed baselines, regressed `0/6` baseline passes under fail-closed
fallback, and left the baseline-or-plan oracle at `6/16`. The pair and
combined reserve searches found robust plans in `0/16`. Thus removing all
model reserve does not expose repair authority within the frozen four-slot
U/V action family.

This is a finite action/timing/controller-family authority failure. It is not
a runtime, deployment, source-authentication, raw, restart, causality,
reporting, real-controller, real-MPC, plant-reachability, global-
unreachability, or Gate A result.

## Frozen identity, package, and validation

The design was frozen before any point-only search or outcome:

```text
design checkpoint              61ad6a2
implementation checkpoint      b214b53
initial package checkpoint     682a3a8
dependency-complete package    0832c6b
design SHA-256                  3446d1bd81879f52c4f7b943282a2db5c67e6e2d74a43598c597af7c85a7b9f3
PACKAGE_MANIFEST SHA-256        879f2c12f84e23e4042c3f65a8e5722ddf463c7b50d946de31dcded5984009c7
SHA256SUMS SHA-256              e0960836f607ac5b7c3159e0b2402c23e628a749f6dbc2a1514e7c306097c8aa
```

The final package contains 1,137 declared files plus
`PACKAGE_MANIFEST.json` and `SHA256SUMS`:

```text
strict JSON                       132
Python source                     443
shell source                      440
Markdown                          121
other declared source               1
focused unittest                  8/8
full unittest                     1390/1390
```

Local source validation used only the project virtual environment and loaded
the existing `tests/conftest.py` Windows `resource` shim before unittest
discovery. One initial focused invocation omitted the shim and reproduced the
known Windows `ModuleNotFoundError: resource`; the corrected focused and full
runs passed. This was a test-startup invocation error, not a code regression.

The first empty-copy package exposed that R8R27's source fingerprint test
required the already committed R8R26 compact audit, which had been produced
after the old R8R26 package. Checkpoint `0832c6b` added the complete seven-file
R8R26 compact directory to the manifest without changing R8R27 computation.
A new empty directory then passed all hashes, JSON, compilation, focused
`8/8`, and full `1390/1390` with one expected isolated-evidence skip.

The first server staging directory was copied from that tested empty tree and
therefore also contained test-generated `__pycache__` files. All declared
hashes, JSON, shell, and compilation checks passed, but the exact precompile
physical-file-count gate rejected the extra files. Nothing was installed or
run. A new manifest-only transfer tree containing exactly 1,139 physical
files and no caches was copied directly as v2. Server staging and installed
validation then passed all 1,137 hashes, 132 JSON parses, 443 Python
compilations, 440 `bash -n` checks, focused `8/8`, and full `1390/1390` with
one expected skip. This was transfer-tree contamination caught fail-closed,
not a source-package or scientific failure. No archive or global Python was
used.

## Server run and immutable evidence

The accepted server run is:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
stage4_2r3c3t13s24d1r14r8r27_runs/
stage4_2r3c3t13s24d1r14r8r27_point_versus_reserve_authority_discriminator_20260809_0832c6b_v1
```

Primary, structurally independent, and postprocess commands used the existing
server virtual environment and the same output directory. The seven official
pre-compact files are:

```text
analysis/final_report.json          3bb40d06c1b4791ff57fed3034444147eec49a47e00533a6061bdf3d9db3910d
analysis/independent.json           a2c594c1087a6b549909e061cc844cfd8c7a66ea05d2e4e55877682f371aead6
analysis/primary_detailed.json      f7090ef795a1a20ece8de4de0be266514c8efc1c9f0ddf7849c33a4b71ac40f7
analysis/primary_summary.json       e5c2d23889102ded8662204ea222292e2ea3a2c2eecf194afc33c228d9e6d288
model/discriminator_evidence.json   783e1da566694c5ec21ad4d76303dc2c69b31a15d637709599afb51c24ce08c3
stage_manifest.json                 91b36bda1068a3b715497db28df383b97ddc9fde60c1b4ace6c9f9afe17334d4
stage_state.json                    974bb330771fce56f043ef06488558d59b375da50af5b0d6d0a4c8950b42b099
```

The primary and independent detailed files remain on the server. Only compact
evidence was downloaded:

```text
server_compact_evidence.json  1fca0ad5ecbd077ad3e97994070595f6f120c08044a0ceb88e0a140002c40473
COMPACT_MANIFEST.json         e335fb77278257478942d67fab5406a230103a30e9d200e9fad4a09ef6d2046b
compact SHA256SUMS            aa9675a3aeee45021f326744dfade90426b940fad14d9dca5b6a5bf003129f62
```

The final state records `finished=true`, `real_tsc_executed=false`, zero plant
steps, and zero new raw. No R8 or R8R1 trajectory was rerun.

## Three frozen uncertainty layers

The authenticated bank and model remained exactly:

```text
trajectories                    432
schedules                        27
causal origins                 1728
forecast points               11232
feature digest     14e1a15c6eb3ba305932b25918ec7127e46cd2a6f7c13ad50701545413fae849
target digest      037be84fcce81dc97c8350d88416fc0ac42534083d1fb5688ab000dee2e81dcc
```

Tube digests were:

```text
point-only  8b60d6f5aad9c8f57c951c50a6bd711a3ba51bc46c2b5ccac7884797fd049b64
pair        281c6da6637e22e8baf848e98e33d2c9466e15e9b700f74633a859d3f2af06b8
combined    281c6da6637e22e8baf848e98e33d2c9466e15e9b700f74633a859d3f2af06b8
```

Pair versus combined elementwise tube difference, pair versus combined plan
difference, and combined versus final R8R26 plan difference were all exactly
`0.0`.

The frozen search outcome was:

```text
layer          safe  robust  repairs  regressions  fallback+plan oracle
point-only     16/16    6/16     0/10       0/6             6/16
pair tube      16/16    0/16     0/10       0/6             6/16
combined tube  16/16    0/16     0/10       0/6             6/16
```

All six point-only robust contexts were the same three prefix-9 physical
pairs under both histories. Their baselines already passed, and every selected
plan used `[0,24]` sixteenth-units at all four decision slots. No failed
baseline became formally feasible.

Search totals were:

```text
                               point-only    pair/combined each
evaluated sequences                365793              360296
safe expansions                    162399              158420
state-unsupported nodes                 0                   0
transition-unsupported expansions  201954              200436
hard-action rejections               1440                1440
selected violation range        0--0.922673    0.231507--1.422673
```

The point-only classification required at least one failed-baseline repair
and oracle `>=7/16`; neither was met.

## Independent recomputation

The independent implementation used the R8R26 independent chain and did not
import R8R27 primary computations. It independently rebuilt source
authentication, bank, model, tubes, state support, interval transition hulls,
hard action construction, all three searches, formal evaluation, and route.
Agreement was exact:

```text
maximum model/tube difference       0.0
maximum hull difference             0.0
maximum three-layer plan difference 0.0
maximum R8R26 reproduction diff     0.0
bank / route / outcome agreement    true
```

## Authorization boundary

R8R27 authorizes no fresh controller sentinel and does not satisfy Gate A.
Expert data, BC, DAgger, residual RL, and every other learning step remain
blocked. Every R8-family trajectory remains forbidden from learning data.

Because point-only reserve removal repaired no failed context, the next
prospective identity must change the causal action timing or controller
family rather than rescale uncertainty. A finite front-loaded timing sentinel
may test whether the already authenticated cumulative U/V endpoints gain
physical authority when the same four exact Card15 issues are moved earlier,
but its complete grid, safety partition, gates, and routes must be frozen
before implementation or TSC.
