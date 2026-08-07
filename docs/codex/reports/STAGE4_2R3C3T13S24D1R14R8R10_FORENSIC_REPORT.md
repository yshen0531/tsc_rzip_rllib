# Stage4.2R3c3T13S24D1R14R8R10 forensic report

## Result

R8R10 is final as:

```text
REPLACEMENT_SCALE_FORMAL_AUTHORITY_INSUFFICIENT_SUSTAINED_ACTION_REDESIGN_REQUIRED
```

The accepted zero-new-TSC audit is:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
stage4_2r3c3t13s24d1r14r8r10_runs/
stage4_2r3c3t13s24d1r14r8r10_replacement_scale_formal_authority_audit_20260807_9afcea6_v1/
stage4_2r3c3t13s24d1r14r8r10_replacement_scale_formal_authority_audit
```

R8R10 ran no Ray, `gotsc`, TSC, controller, or plant step, created no raw
directory, and modified none of the authenticated R4, R6, or R8 source
evidence.

## Provenance and validation

The replacement-scale question and gates were frozen at checkpoint
`b515fff`, before the matched context-level formal outcomes were computed.
Implementation and package checkpoints were `91aff81` and `9afcea6`. The
design-document SHA-256 is:

```text
d10bcbf73c64222df2eac5ee81acfcade7d069f6d4d89ae500d2e760ba2e8a06
```

Validation used only the local project virtual environment and the existing
server virtual environment:

```text
local project-venv focused / full                   6/6 / 1243/1243
empty direct-copy focused / full                    6/6 / 1243/1243
server staging focused / full                       6/6 / 1243/1243
installed server focused / full                     6/6 / 1243/1243
expected isolated-evidence skip                                  1
declared package hashes                                  1024/1024
```

The package was copied as an ordinary directory tree without local archive
creation or extraction. The initial Linux `sha256sum -c` invocation treated
the Windows CRLF on each checksum line as part of the path and stopped before
compilation. A read-only `sed 's/\r$//'` input stream then verified all actual
file hashes without modifying the package. Staging and installed `bash -n`,
compilation, focused tests, and complete suites passed.

## Source and integrity evidence

The primary and structurally independent implementations authenticated and
strictly parsed all three immutable development banks:

```text
R4 raw        200 files / 6285765 bytes
  44a7eb8e677f88f32c57a6be59273501e73f7657527371e1b59578a95c2ae7a9
R6 raw         48 files / 1509679 bytes
  c743eff98395325e4da35a28d2e646aacffb00e678753ceb0faf4b86a64aeb83
R8 training   624 files / 19725920 bytes
  b5de1cabe0bd47b0d3a3b26aff04714ca0c05653483cd4c92403dc5867eeb762
```

They reproduced the complete published formal aggregates exactly:

```text
R4 formal pass                                           50/200
R6 formal pass                                            12/48
R8 training formal pass                                 234/624
selected formal metric equivalence                      312/312
maximum selected signed-margin difference                     0
```

All pass results and selected arrivals also agreed. R8 calibration and
holdout remained unopened. The run contains exactly five compact JSON files
and no raw directory.

## Replacement-scale authority result

The frozen matrix contained 24 consumed development contexts. Each context
used one zero baseline, six canonical direction-zero 1.0x rows, and six
replacement direction-zero 1.5x rows. The prospective gate required at least
one failed baseline repaired specifically by replacement authority, plus
strict oracle improvements over both baseline and canonical coverage.

The result was:

```text
baseline formal pass                                      8/24
failed baselines                                             16
canonical formal-pass trajectories                       48/144
replacement formal-pass trajectories                     48/144
canonical strict margin improvement on failed baselines    15/16
replacement strict margin improvement on failed baselines  16/16
replacement gain, minimum                    0.000050072836658
replacement gain, median                     0.000210307502231
replacement gain, maximum                    0.015329058949230
canonical oracle formal pass                               8/24
replacement oracle formal pass                             8/24
combined oracle formal pass                                8/24
canonical / replacement repairs                          0/16 / 0/16
replacement-only repairs                                    0/16
```

The larger pulse therefore moved every failing baseline's minimum margin in
the favorable direction, sometimes materially, but never crossed the
unchanged formal gate. Neither amplitude enlarged measured-oracle coverage
beyond the eight baselines that already passed. This rejects the fixed
single-pulse amplitude substitution as sufficient formal-control authority;
it does not show that a sustained, asymmetric, sequential, or otherwise new
action architecture is unreachable.

## Independent agreement and fingerprints

The independent audit separately rebuilt source authentication, raw parsing,
both formal-evaluation paths, row matching, oracle aggregation, and the final
route. It agreed with the primary on every numerical field and outcome, with
maximum absolute numerical difference zero. The accepted compact SHA-256
values are:

```text
primary detailed
  dea560af0e491fc2ee6022b50174bdc3902fc5a615800edb335d050e17850821
primary summary
  e359a5ae19d59de7e8cb60e00e13932706ccadd1ea643bf8955f34b86a6aef33
independent
  161180d549878874c28cf24d83f0aae86bb174fe1e02cd328dff0b71f214962f
stage manifest
  60dfa552ec580e57f3b5284b56509d00feb273fc1c92e78ccf4765cff853c56c
stage state
  8ab651f135a9b460ee54a89172bcc3f42b6bc60e535d39702ae7a7606414989e
primary log
  6871927da94c8272c91d9a4798c271624b791a947834459e800039cc40722a5c
independent log
  ee3797ec5ab324cadd9c1e6a6bbd6e5c738d2214ca32ac4720af52ff211a9a26
```

## Classification and handoff

R8R10 is a finite measured-action-authority design failure. It is not a
runtime, deployment, restart, causality, raw-corruption, reporting,
formal-evaluator, real-MPC, safety, plant-restart, or global-reachability
failure. R8R7 remains a valid finite interaction-model PASS; R8R8 and R8R9
remain clean controller/objective and measured canonical-authority failures.

The fixed direction-zero 1.0x/1.5x isolated-pulse route must not be tuned or
rerun under the same identity. Before any new outcome is computed, the next
stage must prospectively freeze a genuinely sustained or asymmetric causal
action architecture with unchanged hard Card15/current/safety, restart,
causality, integrity, and formal timing contracts. Gate A, expert data, BC,
DAgger, and residual RL remain blocked. All R8-family probe, audit, and
qualification trajectories remain forbidden from learning datasets.
