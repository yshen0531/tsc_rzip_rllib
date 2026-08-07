# Stage4.2R3c3T13S24D1R14R8R9 forensic report

## Result

R8R9 is final as:

```text
MEASURED_MULTIPULSE_FORMAL_AUTHORITY_INSUFFICIENT_ACTION_REDESIGN_REQUIRED
```

The accepted zero-new-TSC audit is:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
stage4_2r3c3t13s24d1r14r8r9_runs/
stage4_2r3c3t13s24d1r14r8r9_measured_multipulse_authority_audit_20260807_716a0e6_v1/
stage4_2r3c3t13s24d1r14r8r9_measured_multipulse_authority_audit
```

R8R9 ran no Ray, `gotsc`, TSC, controller, or plant step, created no raw
directory, and modified no R8R7 or R8R8 source evidence.

## Provenance and validation

The question and gates were frozen at checkpoint `25b7821`, before the
context-level R8R7 formal mapping was inspected. Implementation and package
checkpoints were `3278729` and `716a0e6`. The design-document SHA-256 is:

```text
3cb4ca9768671aaf575f2cb71c8c33d8643156110dc68c0b1e7b4d714d3d4510
```

Validation used only the local project virtual environment and the existing
server virtual environment:

```text
local project-venv focused / full                   6/6 / 1237/1237
empty direct-copy focused / full                    6/6 / 1237/1237
server staging focused / full                       6/6 / 1237/1237
installed server focused / full                     6/6 / 1237/1237
expected isolated-evidence skip                                  1
declared package hashes                                  1017/1017
```

The package was copied as an ordinary directory tree without local archive
creation or extraction. The server preflight, package hashes, `bash -n`,
compilation, focused tests, and complete suite all passed.

## Source and integrity evidence

The primary and structurally independent audit authenticated the immutable
R8R7 final report, manifest, state, specifications, primary/independent raw
audits, and both raw inventories:

```text
R8R7 baseline raw       16 files / 487298 bytes
  46df626a462dfdbfe7cdf9138a50b6b19c03f0ae5e8bb18cf18c6fcbe05c01a5
R8R7 multipulse raw     32 files / 1068664 bytes
  d8435c8cd61fd082e143d79a3628ad2274780faefc6b676367df917355f49e31
R8R7 final / manifest / state
  9ca6afce52442c1b7470cb8ff13a2eac4aab32de1e05a898d206f5fe76e01005
  ae89fb2df01cd6758676baa895880e2005a1f8967c62ea4ae671ab61ea771e24
  04f643e09f414c5d5a305f1a3584450e12e5a39e8d062d454480df3c8d95fe7e
```

It also authenticated the accepted R8R8 zero-TSC boundary, including the
corrected independent report. All 48 R8R7 raw files strictly parsed. The two
independent formal evaluators agreed on every pass result, arrival result, and
signed margin, with maximum absolute margin difference zero. They reproduced
the already published aggregate exactly:

```text
formal metric equivalence                              48/48
R8R7 baseline formal pass                               6/16
R8R7 multipulse formal pass                            12/32
R8R8 robust zero-selection reproduction                 0/64
```

## Measured authority result

The prospective scientific gate required at least one of the ten failed
baselines to be repaired by either measured schedule and measured-oracle
coverage of at least 7/16. The actual result was:

```text
failed baselines                                           10
strict minimum-margin improvement                         9/10
best-schedule minimum-margin gain, min       -0.00010583333333402667
best-schedule minimum-margin gain, median      0.0001253496476583127
best-schedule minimum-margin gain, max         0.0009268000000006715
failed baselines repaired                                  0/10
measured-oracle formal pass                                6/16
```

Thus the real canonical-scale four-pulse schedules often moved the minimum
margin slightly in the favorable direction, but never crossed the unchanged
formal gate for a failed baseline. The action alphabet has insufficient
measured formal-control authority for the current MPC route.

The R8R8 score-attribution recomputation also agreed exactly: point-only
nonzero candidates were slightly better than zero at 64/64 decisions, while
the frozen candidate-specific robust score preferred zero at 64/64. This
explains the offline selection behavior but does not change either R8R8 or
R8R9's frozen gate.

## Independent agreement and fingerprints

The independent audit rebuilt source authentication, both formal-evaluation
paths, all context comparisons, oracle aggregation, and R8R8 score attribution.
It agrees with the primary numerically, scientifically, and on the final route.
The accepted compact SHA-256 values, rechecked at the original server path,
are:

```text
primary detailed
  4bda8b9dafef7d75dc73aa28b8aebdbfd9df34f98d14c369182c833bd912f4ef
primary summary
  ffb67e2a882605d01af609f57b181657d334297d93e5eee893789873439b23fd
independent
  768a0a408880a19c6d723eccfef98a45018d01fcb63d48ab98e65d61784ce9f0
stage manifest
  96655d1ccc84796b687f05644150909ba6aa64a3da549542eeac92d913cd2e0d
stage state
  e03c09dfd0afffe20bdd641b401dc6e2f3e13b3075c2d3033578b7f5c67355bb
primary log
  1009d47236e2cc8157c58343c460fb9cd477ba3b10f485ad57711fb5d46514aa
independent log
  f69050a18a53d529e4e9bb9109400296766be8448b8ca9535830536862196504
```

## Classification and handoff

R8R9 is a finite measured-action-authority design failure. It is not a
runtime, deployment, restart, causality, raw-corruption, reporting,
formal-evaluator, real-MPC, safety, plant-restart, or global-reachability
failure. R8R7 remains a valid finite interaction-model PASS and R8R8 remains
its clean zero-TSC objective/model/action-design FAIL.

The canonical-scale four-pulse route must not be tuned or rerun under the same
identity. The next work must freeze a genuinely different action architecture
or a zero-new-TSC discriminator using previously authenticated, already
consumed development evidence before computing its outcome. Gate A, expert
data, BC, DAgger, and residual RL remain blocked. Every R8/R8R1/R8R7/R8R8/R8R9
trajectory or audit source remains forbidden from learning datasets.
