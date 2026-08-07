# Stage4.2R3c3T13S24D1R14R8R5 forensic report

## Final classification

R8R5 is final as:

```text
CONTEXT_ROBUST_CAUSAL_OBSERVER_HOLDOUT_FAIL_REDESIGN_REQUIRED
```

The run is a clean finite observer uncertainty-qualification design failure.
It is not a runtime, deployment, restart, causality, Card15, current, raw,
snapshot-authentication, primary/independent disagreement, reporting-route,
controller, formal-control, real-MPC, plant-reachability, or global-
observability failure.

The fixed causal point observer passed every blind point row.  The only
scientific miss was the prospectively fixed per-context tube-containment
gate: one of eight blind history contexts contained 14/16 rows when 15/16
were required.  The frozen R8R5 gate is not relaxed or relabeled.

## Code, package, and validation boundary

```text
branch
  codex/stage4_2r3c3t13s24-sequential-transition
design checkpoint
  546c6f7
implementation checkpoint
  4f0bf06
package checkpoint
  26b96e8
declared package files / empty-copy total files
  966 / 968
installed PACKAGE_MANIFEST.json SHA-256
  be7aa2283255879c619c878f91f9d8de12caf384ef0fc64656d8543981ef81f6
installed SHA256SUMS SHA-256
  82d5e4fd72fe60fa5d8b619fdc09db1975d2761d53fed4c8f6addd2834d1a960
```

Local validation used only `venv/Scripts/python.exe` and loaded the existing
Windows `resource` compatibility shim before discovery:

```text
R8R5 focused tests                                      11 / 11
full unittest suite                                  1198 / 1198
```

The empty local package was built by direct file-tree copy; no archive was
created or extracted.  The first server staging checksum attempt exposed a
Windows-to-Linux line-ending deployment defect: the copied `SHA256SUMS` used
CRLF, so GNU `sha256sum` treated the carriage return as part of every path.
No package source hash, Python source, scientific input, or server result was
changed.  The checksum file was normalized to LF, directly recopied, and the
same staging directory then passed all 966 hashes, `bash -n`, 370-source
compilation, self-test, and focused 11/11 tests.

Installed validation used only
`$HOME/tsc_all/tsc_simulation/venv_simu/bin/python`:

```text
installed hash closure                                966 / 966
R8R5 focused tests                                      11 / 11
full unittest suite                                  1198 / 1198
expected Linux skip                                      1
```

## Exact server identity

```text
run directory
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s24d1r14r8r5_runs/
  stage4_2r3c3t13s24d1r14r8r5_context_robust_observer_holdout_20260807_26b96e8_v1

stage directory
  stage4_2r3c3t13s24d1r14r8r5_context_robust_observer_holdout

campaign identity
  context_robust_causal_observer_holdout_v1
```

R8R5 ran zero development TSC.  It first authenticated and reused the
consumed R8R4/prior development bank.  Only after primary and structurally
independent development agreement did it authorize exactly eight new blind
baseline rollouts.

R8/R8R1 trajectories were not rerun.  R8R5 issued no probe trajectory; all
eight R8R5 baselines are nevertheless explicitly forbidden from expert,
BC, DAgger, or RL data by the frozen stage contract.

## Development freeze before blind holdout

The single fixed candidate was unchanged:

```text
family / PCA rank / ridge
  linear / 32 / 1e-6
development pairs / contexts / origin rows
  16 / 32 / 480
whole-pair outer folds
  16
```

Primary development results were:

```text
origin point rows                                       480 / 480
prescribed issue point rows                             128 / 128
finite-exclusion violations                                      0
maximum absolute scaled point error               0.10815621222166566
aggregate tube containment                              480 / 480
tube-cap gate                                                  PASS
aggregate higher-q95 row ratio                    1.6587932435314114
maximum context higher-q90 row ratio               2.1670444001315077
fixed reserve multiplier                                      1.25
final tube scalar                                  2.7088055001643845
maximum tube [R,Z,vR,vZ,Ip]
  [0.0013108881956189176,
   0.0012843384434839996,
   0.015340389105831992,
   0.01978891704103777,
   49.516195667296266]
```

The development model/tube were serialized and frozen before holdout:

```text
observer model SHA-256
  d3d7ecebbe51ca20e83cdb126682d2bebad749b8fd5cb67dd57b3baf416e77e4
observer tube SHA-256
  3a436307a507b9aacda85321dd4d55e6bbcc996efe2e25c2b5026571c7108786
primary detailed SHA-256
  90c28e3a8f9f944b95ace4d5288dd04e53171f02cf4b5f925f1caceb0eaf9b40
primary summary SHA-256
  61c47645a0b6aa8d04b9a0a5d8f0529a3f1e89aa1046570f6449c9b646e27ac0
independent SHA-256
  19b3a0427d30d683b7c3cd23ef246ff3269f4dd2f94251febf61e56b153fa1eb
```

The independent development implementation reconstructed the model, tube,
all metrics, and route exactly.  Holdout raw remained zero until the
authorization phase committed these hashes.

## Authentic blind holdout execution

Exactly eight fresh-controller, fresh-TSC-process baseline rollouts completed:

```text
expected / successful / full horizon                         8 / 8 / 8
runtime success                                                8 / 8
source restart snapshot authenticated                          8 / 8
source physical-state prefix exact                             8 / 8
source action/trace prefix exact                               8 / 8
zero future action exact                                       8 / 8
constant future commanded current exact                        8 / 8
finite raw                                                     8 / 8
forbidden trace count                                              0
maximum total normalized action abs              0.648149691358026
maximum current utilization                               0.3924
```

The rejected scientific route did not arise from execution:

```text
raw files                                                       8
raw bytes                                                  245493
raw inventory digest
  55cae64bf5b907b4cd6013615388dbb637dd2f1f14e49bda7fb49d11cf5b3d14
primary raw audit SHA-256
  b7de85b3041f753b43a2a62cf51467a3981f558424f65c0b959bf5ba434e6193
independent raw audit SHA-256
  f9b2f69fb24e616438276c555cfd7735985ba658f67259c68be80bbd371b3379
```

The independent raw audit strictly parsed all eight gzip JSON files and
reproduced every file name, byte count, SHA-256, aggregate inventory digest,
and raw gate.

## Blind fixed-model result

The frozen model and tube were not refit, rescaled, or reselected after
holdout opened.

```text
blind physical pairs / history contexts                       4 / 8
origin rows                                                     120
prescribed issue rows                                            32
origin point passes                                          120 / 120
required origin point passes                                 114 / 120
prescribed issue point passes                                  32 / 32
required prescribed issue passes                               31 / 32
finite-exclusion violations                                           0
tube containment                                             117 / 120
required aggregate containment                               114 / 120
contexts passing every gate                                      7 / 8
maximum absolute scaled point error               0.10499799349051298
```

The sole failed context was:

```text
p5_q2_a0p900_gap4_settle4 | plus_first
tube contained / required                                  14 / 16 / 15
```

All eight contexts passed their point and prescribed-issue point gates.
Read-only row forensics found only three tube-uncontained rows in the entire
blind set, and all four violating component/lag cells were Ip at future lags
11--12:

```text
context/history                              origin  lag  abs Ip error  ratio
p5_q2_a0p900_gap4 | minus_first                  25   12   50.4224597 A  1.0183024
p5_q2_a0p900_gap4 | plus_first                   24   12   56.9548931 A  1.1502276
p5_q2_a0p900_gap4 | plus_first                   25   11   61.6116792 A  1.2621076
p5_q2_a0p900_gap4 | plus_first                   25   12   80.4845370 A  1.6254184
```

All three rows still passed the point caps.  The failed context would have
needed a multiplicative factor `1.1502275638242219` to satisfy its unchanged
15/16 gate; this is retrospective descriptive evidence only and is not
applied to R8R5.

Primary and independent blind model audits agree exactly:

```text
primary detailed SHA-256
  ff9b5bc6f9fde008b6e43ebe200c27d58a86fa82140d5d45d689777681d0f67d
primary summary SHA-256
  61a4cce213f74a88843f1df982037b09d0939057154ed9cc9c2491c40d3d1614
independent SHA-256
  c5089f9a69987d4c469f765369edd39d75418aa0cbcf99a0de07ecc47eb0700b
final report SHA-256
  c2f7307dd3ea5265c6099443b9dac85365dfe70db6d7c5e0ac08c3fe4b34df65
stage manifest SHA-256
  d737bb77a9547fac8c1378dab3fdbd63aeca60cc30fefc38ecf5dab181d441cc
final stage state SHA-256
  dc564ddfb9edae9b044dfa358ddb98306b56f328a8fc06c60b8c43ade772e48c
```

`final_report.passed=true` records successful completion of the dual-audit
postprocess.  The scientific fields remain
`scientific_gate_passed=false` and `state.verdict.passed=false`; the route is
the FAIL route quoted above.

## Supplemental audit provenance

The first read-only row-forensics attempt stopped before emitting an audit
JSON because it compared the detailed evaluation, which contains `rows`,
directly with the compact summary evaluation, which intentionally omits
`rows`.  Its preserved 353-byte server log has SHA-256
`0070dba9747c7ab72da366cc0d0372ee6bed03f323a555d2360fe40b0456a10a`.
This was a supplemental audit/reporting-schema error, not an R8R5 result or
raw error.

The v2 read-only audit removed `rows` before the compact comparison, then
independently reauthenticated every raw file and reproduced the primary and
independent result objects.  Its JSON and log are byte-identical, 10,807
bytes, SHA-256
`87e1ebc466ac8375ea76226787b22fe013f9de0c95b27a19d9d68499c77896ab`.
Compact evidence is retained at:

```text
docs/codex/audits/
  stage4_2r3c3t13s24d1r14r8r5_20260807_26b96e8/
```

Large raw and full server outputs remain on the server.

## Handoff

Before any R8R6 adapted prediction or metric was computed, the new causal
one-step innovation observer was frozen at checkpoint `0352207`:

```text
docs/codex/reports/
  STAGE4_2R3C3T13S24D1R14R8R6_CAUSAL_ONE_STEP_INNOVATION_OBSERVER_DESIGN.md
SHA-256
  6f8886f42321a2e99a97332ecf03c1827b5385ebfc50f6ee07fefefcafa182f1
```

R8R6 is zero-new-TSC and keeps adaptation only if it has prospectively
measurable benefit.  A successful development result may authorize only a
separately frozen fresh interaction sentinel.  MPC, Gate A, expert data,
BC, DAgger, and bounded residual RL remain blocked.
