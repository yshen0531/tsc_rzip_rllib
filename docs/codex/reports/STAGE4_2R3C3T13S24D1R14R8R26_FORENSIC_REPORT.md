# Stage4.2R3c3T13S24D1R14R8R26 forensic report

## Result

R8R26 completed its prospectively frozen, zero-new-TSC action-transition-
supported multiresolution MPC preflight. The final route is:

```text
ACTION_TRANSITION_SUPPORTED_MULTIRESOLUTION_AUTHORITY_INSUFFICIENT_CONTROLLER_SENTINEL_NOT_AUTHORIZED
```

The whole-schedule model and uncertainty gates passed, and all 16 finite
searches completed safely. No context contained a robust-formal refined plan,
however: repairs were `0/10`, regressions under the fail-closed baseline
fallback were `0/6`, and the baseline-fallback-plus-plan oracle remained
`6/16`. A fresh real-controller sentinel is not authorized and Gate A is not
qualified.

This is a finite action-family/planning-authority failure under the frozen
model, tubes, action-transition support, action boundary, timing, and search.
It is not a runtime, deployment, source-authentication, raw, restart,
causality, reporting, real-controller, real-MPC, plant-reachability, or
global-unreachability result.

## Frozen identity and checkpoints

The design was frozen before any R8R26 metric or route was computed:

```text
design checkpoint          42c1ff3
implementation checkpoint  06ebbf7
package checkpoint         a1f4535
design SHA-256              d79f64712b00c923711b5bac16f6001388edeb3e348c2b71b7c98c942289f853
PACKAGE_MANIFEST SHA-256    3070ee3167b7550f3be3e582ef8d710a6c8c9ff3662a95064c1daeff08b7ea13
SHA256SUMS SHA-256          2ef57f70f1ffcf673b20a67635de9d3e93b7cd1e75215509bd5ee688ee93a777
```

The package contained 1,124 declared files plus `PACKAGE_MANIFEST.json` and
`SHA256SUMS`. It was copied file-by-file into a new local empty directory and
then directly transferred with `scp -r`; no local archive operation was used.

Local source and clean-package validation used only the project virtual
environment and loaded `tests/conftest.py` before unittest discovery:

```text
strict JSON                         125
Python source compilation           440
shell files in package              439
focused unittest                    8/8
full unittest                       1382/1382
clean-copy server-equivalent skip   1 expected
```

Server staging and installed-project validation used only
`$HOME/tsc_all/tsc_simulation/venv_simu/bin/python` and passed all 1,124
hashes, 125 strict JSON files, 440 Python compilations, 439 `bash -n` checks,
focused `8/8`, and full `1382/1382` with one expected skip.

The first staging validation command had a Windows-OpenSSH quote-transport
error: quotes in a Python `-c` expression were stripped and the expression
raised `SyntaxError`. Package hashes had already passed, and no test,
controller, TSC, plant step, or scientific output ran. A directly copied
standalone bash validation script removed the quoting ambiguity and all
staging and installed gates passed. This was a validation-command error, not
a code or package failure.

## Server run and integrity

The final run is:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
stage4_2r3c3t13s24d1r14r8r26_runs/
stage4_2r3c3t13s24d1r14r8r26_action_transition_supported_multiresolution_mpc_preflight_20260809_a1f4535_v1
```

Primary, structurally independent, and postprocess commands ran in that same
directory with separate logs. The final state records `finished=true`, zero
plant steps, zero new raw, and `real_tsc_executed=false`; no raw directory
exists.

The seven official pre-compact files total 1,153,799 bytes:

```text
analysis/final_report.json       78e1bf33e13b56c032356e7fbc57e12737b7620db158b896e82c9979ff4730d2
analysis/independent.json        2e1144940d9f3463c5d7e732e6b85ad0554d0ca24b30521c512460cfe11295ae
analysis/primary_detailed.json   a5f93c0475fd62a9f9f5cfdb542724cfd174c56e2db4e237a8c04858eab111a0
analysis/primary_summary.json    6b4670380f72fb14e48ea47165faab02311ec363c00aff221d06c0a90e12c871
model/preflight_evidence.json    532f4257871e3dd97832416e4a9be8fc447a0a90bc2949b11e1a2bfef1660307
stage_manifest.json              0d61042e9e97c1868231a1eb7b405e7b5928d146d8a69e82b66cdbd9abfae3df
stage_state.json                 a89ab66e075d3e985f4cf0c8e067e1820fefbf301c38cf89afd42e85d61ecce6
```

Only the compact evidence was downloaded. Its principal hashes are:

```text
compact_audit.json     1a5ab3e05f841ff55af75314ec89d2e4a033a574381d1b0047f1b4b3322b0cb4
COMPACT_MANIFEST.json  e5a1cbd518a4611e1a6f1339f31d27c9a2f776c3b585435f5363f0d9b1393e95
compact SHA256SUMS     390d61ac0eb1b790afa95107975ea8470c2e344892f6602e6a1ee142307b488d
```

## Model and tube result

The authenticated bank remained exactly 432 trajectories, 27 schedule
identities, 1,728 causal origins, and 11,232 forecast points, with unchanged
feature and target digests:

```text
feature  14e1a15c6eb3ba305932b25918ec7127e46cd2a6f7c13ad50701545413fae849
target   037be84fcce81dc97c8350d88416fc0ac42534083d1fb5688ab000dee2e81dcc
```

All 27 leave-one-complete-schedule-out folds were retained. Their maximum
held-schedule physical point errors were:

```text
R       0.0009397374730232721 m
Z       0.0016357345376455553 m
Ip     86.31575357630761 A
vR      0.014552584125181067 m/s
vZ      0.0178839983484977 m/s
```

All 56,160 components were contained. The schedule tube maximum was exactly
`[0.015 m, 0.015 m, 3000 A, 0.05 m/s, 0.05 m/s]`. Its componentwise maximum
with the immutable R8R25 pair tube was:

```text
[0.015 m, 0.015 m, 3000 A, 0.05 m/s, 0.05387964718914857 m/s]
```

The combined tube digest equals the R8R25 pair-tube digest
`281c6da6637e22e8baf848e98e33d2c9466e15e9b700f74633a859d3f2af06b8`.
Thus the added schedule reserve passed and did not enlarge the planning tube;
the failure is not caused by a new schedule-jackknife cap violation.

## Action support and finite search

The four interval-specific action-transition hulls had affine ranks
`[2,3,3,3]` and `[13,15,15,15]` unique observed transitions. The frozen
325-level lattice and 33-level coarse union were unchanged. Each context
retained beam counts `[26,90,256,32]` and completed a deterministic search.

Across all 16 contexts:

```text
evaluated token prefixes                 360296
hard-safe expansions                     158420
state-unsupported nodes                       0
transition-unsupported expansions        200436
hard-action rejections                      1440
robust-formal plans                            0
best robust violation range   0.2315070911--1.4226725021
```

Most selected best failing sequences lay on the action triangle boundary and
repeated the same extreme or near-extreme coordinate. That is evidence about
this finite supported action/timing family only; it does not prove global
physical saturation or plant unreachability.

## Independent recomputation

The independent implementation imports the R8R25 independent audit chain,
not the R8R26 primary implementation. It independently rebuilt source
authentication, the bank, 27 schedule fits, residual groups, tubes, SVD
hulls, support decisions, hard action issues, beam/refinement search, formal
metrics, and route. Agreement was exact:

```text
maximum source-reproduction difference  0.0
maximum schedule difference             0.0
maximum hull difference                 0.0
maximum plan difference                 0.0
bank / route / outcome agreement        true
```

## Authorization and next discriminator

R8R26 authorizes no fresh controller sentinel and does not satisfy Gate A.
Expert data, BC, DAgger, residual RL, and all other learning remain blocked;
all R8-family trajectories remain forbidden from learning data.

Before any new calculation or plant work, the next identity should freeze a
zero-new-TSC point-versus-reserve authority discriminator. It should rerun the
same deterministic finite search under prospectively fixed uncertainty
layers (point-only, immutable pair tube, and final combined tube) without
changing model, support, action, timing, ranking, or search. This will decide
whether the next redesign must address uncertainty/excitation or instead
broaden the causal action/timing/controller family. It cannot authorize a
controller, MPC qualification, Gate A, or learning by itself.
