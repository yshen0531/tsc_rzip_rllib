# Stage4.2R3c3T13S24D1R14R8R3 forensic report

## Verdict

R8R3 is final as:

```text
CAUSAL_HISTORY_NO_ACTION_OBSERVER_FAIL_FRESH_IDENTIFICATION_REQUIRED
```

Primary and structurally independent server recomputations agree numerically
and on the route.  The causal history observer passed 346/360 complete outer
origin rows and 89/96 prescribed issue rows inside the frozen component caps.
All 14 failed rows exceeded only the vR and/or vZ cap; maximum physical errors
were 1.024 mm R, 0.828 mm Z, 0.0138785 m/s vR, 0.0107686 m/s vZ, and 36.83 A
Ip.  All 12 fold-local inner residual tubes exceeded the unchanged velocity
caps, so the all-row tube gate also failed exactly as preregistered.

This is a finite causal observer/model/data-coverage design failure.  It is
not a runtime, deployment, restart, causality, raw, reporting-route,
controller, formal-control, real-MPC, plant, or reachability failure.

## Checkpoints and package

```text
branch
  codex/stage4_2r3c3t13s24-sequential-transition

prospective design checkpoint        a0fa6bf
implementation checkpoint            a3148a3
package checkpoint                   e8cea14

design SHA-256
  c55130a41f6522259d6fe9073686f0c86226c7dc11be7e93607b63f0abd0dfcb
PACKAGE_MANIFEST.json SHA-256
  3201db6b1f1db3380d1a7d40ce873ddd49dd27f8e2a7d9a1273b95c4f56bef0f
SHA256SUMS SHA-256
  694502bb2c6b0b0c3d4a84b22f181e7d01c95e33ed9a75ad68c49e631186dada
declared files / clean direct-copy closure       939 / 941
```

The clean package was created by direct file-tree copy inside the repository.
No local or server archive was created or extracted.  The empty-directory
closure contained exactly the 939 declared files plus `PACKAGE_MANIFEST.json`
and `SHA256SUMS`; all 939 hashes, all JSON files, source compilation, and the
focused suite passed before transfer.

## Validation

Local validation used only `venv/Scripts/python.exe`:

```text
py_compile selected R8R3 sources                         PASS
R8R3 focused unittest                              11 / 11
full unittest with tests/conftest.py Windows shim 1176 / 1176
empty-directory package closure                         941
empty-directory package hashes                    939 / 939
empty-directory JSON / source compile                    PASS
empty-directory focused unittest                    11 / 11
```

The package was transferred as a directory tree with `scp -r` to:

```text
/home/yangshen0711/tsc_software/r8r3_package_e8cea14
```

Server validation used only the existing virtual environment:

```text
/home/yangshen0711/tsc_all/tsc_simulation/venv_simu
```

Staging and installed validation both passed 939/939 package hashes,
`bash -n`, compileall, contract self-test, focused 11/11, and full 1176/1176
with one expected isolated-data skip.  Exact compact logs are under:

```text
docs/codex/audits/
  stage4_2r3c3t13s24d1r14r8r3_20260807_e8cea14/server_logs/
```

The staging launcher self-test was initially invoked with a staging project
root and correctly stopped at its canonical-project path guard.  The same
log records recovery through the direct contract self-test entry followed by
focused and full tests.  The guard was not weakened.  Before transfer, two
read-only SSH base-check commands were also rejected by Windows/SSH quote
handling before making any remote change; a `bash -s` stdin script then
authenticated the complete installed R8R2 930-file base.  These are preserved
validation-procedure incidents, not source or scientific failures.

## Server sources and output

R8R3 reauthenticated the immutable R8/R8R1/R8R2 evidence.  The R8 source raw
inventory remained 624 files, 19,725,920 bytes, digest:

```text
b5de1cabe0bd47b0d3a3b26aff04714ca0c05653483cd4c92403dc5867eeb762
```

R8 calibration and holdout raw remained zero.  R8R3 source reconstruction
proved:

```text
physical pairs                                      12
history contexts                                    24
causal origin rows                                 360
prescribed issue rows                               96
selected baseline raw                               32
zero-future-action baselines                        32 / 32
constant-future-current baselines                   32 / 32
probe features reconstructed from own prefix       912 / 912
probe feature equality to matched baseline          912 / 912
forbidden predictor inputs                            0
matched-future predictor inputs                       0
future-probe predictor inputs                         0
```

Canonical output and logs:

```text
output
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s24d1r14r8r3_audits/
  stage4_2r3c3t13s24d1r14r8r3_causal_history_no_action_observer_20260807_e8cea14_v1

primary log
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/
  stage4_2r3c3t13s24d1r14r8r3_primary_20260807_e8cea14_v1.log

independent log
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/
  stage4_2r3c3t13s24d1r14r8r3_independent_20260807_e8cea14_v1.log
```

Accepted server artifact sizes and SHA-256 values:

```text
primary_detailed.json  2714286
  a0db5c6db2687747ffd5de8a4a773635bfce15973e8e817eebe74a3356470a00
primary_summary.json      11207
  b8992e53a07e339015dc714377fcca57860dac3cb7b4b169d67e3623b520e364
independent.json           8077
  4cb71b25ad69848349a2034fff335b9d869a56f709465be9baed6b209637f8ba
stage_state.json            485
  e016c0ab9ee2c7a2f4701e553733c4392f48026f648450408cca4e19df9a9bcb
```

The 2.7 MB detailed row output remains on the server.  Only the compact
summary, independent result, final state, and logs were downloaded.

## Frozen scientific result

```text
outer folds                                         12
origin rows / component-cap passes             360 / 346
prescribed issue rows / passes                   96 / 89
tube-cap folds                                     0 / 12
held rows contained by their fold-local tube    360 / 360

component-by-future-state cap violations
  R / Z / vR / vZ / Ip                       0 / 0 / 22 / 8 / 0

maximum absolute physical error
  R                                              0.0010241108 m
  Z                                              0.0008283664 m
  vR                                             0.0138784810 m/s
  vZ                                             0.0107685532 m/s
  Ip                                            36.8332756 A
maximum absolute scaled point error                 0.1387848103
```

Pass counts at the four prescribed origins were:

```text
origin 10                                          18 / 24
origin 14                                          24 / 24
origin 18                                          23 / 24
origin 22                                          24 / 24
```

All observed component violations occurred at future lags 9--12:

```text
lag 9   vR 2, vZ 3
lag 10  vR 4, vZ 4
lag 11  vR 8, vZ 1
lag 12  vR 8
```

The worst fold-local tube half-widths and ratios to the unchanged caps were:

```text
component     maximum physical half-width       maximum cap ratio
R                    0.0034716521 m                    1.1572
Z                    0.0016377286 m                    0.5459
vR                   0.0431454369 m/s                  4.3145
vZ                   0.0219044087 m/s                  2.1904
Ip                  90.8823284 A                       0.0909
```

R exceeded the tube cap in 2/12 folds; vR and vZ exceeded it in 12/12;
Z and Ip never did.  The tube remained finite and contained every held row,
but the preregistered cap prohibited treating a wide tube as useful.

All twelve selected candidates used the largest frozen PCA rank 32.  Eleven
folds selected a linear kernel and one selected RBF; ridge selection was
distributed across all three frozen values.  The weakest pair passed 21/28
origin rows.  These facts support a finite feature/model/data-coverage gap,
not a numerical solver or source-authentication error.

## Independent agreement

The independent implementation separately rebuilt raw sources, causal
features, every nested candidate score, fold selection, prediction, tube,
metric, and route.  It reports:

```text
primary_numerical_agreement                       true
primary_outcome_agreement                         true
development_artifact_presence_agreement           true
development_artifact_hash_agreement               true
independent passed                                true
```

Because the scientific gate failed, no observer artifact was emitted.  This
absence is the frozen result, not a missing-file deployment error.

## Execution and conclusion boundary

R8R3 created zero raw and executed zero Ray, `gotsc`, TSC, controller, or
plant advances.  It did not evaluate formal tracking or any closed loop.  The
120 ms prediction window does not change the formal arrival or hold timing.

A read-only post-result stratification initially failed only while serializing
a NumPy integer and was immediately rerun with explicit scalar conversion.
The rerun printed the statistics above; a stdin here-document terminator
warning occurred after the complete JSON had printed.  Neither incident
changed a source, result, metric, route, or state file.

R8R3 is immutable and may not be retuned.  The active route is to
prospectively freeze a new-identity fresh causal observer-identification
campaign.  The already small point errors do not justify post-result gate
weakening; the new application policy may instead preregister a practical
finite qualification on genuinely fresh development/holdout data while
retaining zero hard-safety violations and the immutable formal contract.

R8R3 does not authorize a controller, MPC, Gate A, expert data, BC, DAgger,
or bounded residual RL.  Probe trajectories remain forbidden from expert
datasets.
