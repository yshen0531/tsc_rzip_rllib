# Stage4.2R3c3T13S24D1R14R8R2 forensic report

## Result

R8R2 is final as:

```text
CAUSAL_ONLINE_INNOVATION_BASELINE_FORECAST_FAIL_OBSERVER_IDENTIFICATION_REQUIRED
```

The primary and structurally independent zero-new-TSC audits agree on every
outcome and within the frozen numerical tolerance.  Before any online update
was fitted, the fixed four-state causal affine no-action forecast passed only
17/96 baseline windows.  The prospective all-window baseline gate therefore
stopped the study fail-closed, with no selected update lag and no development
artifact.

This is a causal baseline-forecast/observer-design failure.  It is not a
runtime, package, deployment, source-authentication, raw-corruption, restart,
causality, controller, TSC, MPC, formal-control, or plant-reachability result.

## Code and package identity

```text
branch
  codex/stage4_2r3c3t13s24-sequential-transition
prospective design checkpoint
  431f7e3
implementation checkpoint
  a636583
package checkpoint
  3ce1e04
source-run metadata correction
  c90e299
design SHA-256
  2613cd42b7b3a2e9c985c7ac1a9fd055fc20aa596e16add5a2e4c54cc8514dfe
accepted PACKAGE_MANIFEST.json SHA-256
  b7e698a5805a178131a17b0bf0be3134937f4dd558d21eb44c1099058b2256a3
accepted SHA256SUMS SHA-256
  701447a04054278ae5c86230f97b3c8129a491a813d44e15d6c798ef53427f00
declared package files
  930
```

The metadata correction changed only the descriptive R8R1 source run name
from an incorrect local-audit/checkpoint label to the authenticated server
identity ending in `20260805_c2ed69f_v1`.  It changed no config, source raw,
predictor, gate, result, controller, or action.

## Local validation and direct-copy package

Only the repository virtual environment was used locally:

```text
targeted py_compile                                      PASS
focused unittest                                         8 / 8
full Windows-shim unittest                           1165 / 1165
manifest inventory / hashes                           930 / 930
clean empty direct-copy closure                       932 / 932
clean empty direct-copy focused unittest                 8 / 8
```

The Windows full suite explicitly loaded the existing `tests/conftest.py`
`resource` shim.  No archive was created or extracted.  The accepted clean
package was copied file by file into an empty repository-local directory and
then transferred directly with `scp -r`.

## Deployment recovery and installed validation

The first server staging attempt was rejected before installation because
the locally exercised empty package had acquired 18 undeclared
`__pycache__/*.pyc` files.  This was a package-sanitation failure only.

The second clean staging package passed its exact closure, all 930 hashes,
shell syntax, and Python compilation.  Its installer then passed absolute
source paths to `cp --parents`, creating an unintended package mirror below
the repository's `home/yangshen0711/tsc_software/...` path instead of
updating the declared repository-relative files.  The subsequent installed
hash check correctly reported the nine new R8R2 files unreadable and four
updated documentation hashes mismatched.  No R8R2 result was computed under
that partial install.

The v3 recovery used a fresh clean staging identity and relative
`cp --parents` operands.  It independently authenticated the unintended tree
as exactly the 930 declared package files before deleting only that
task-created tree.  The final installed boundary passed:

```text
staging closure                                         932 / 932
staging hashes                                           930 / 930
staging bash -n                                                PASS
staging Python compile                                         PASS
installed hashes                                         930 / 930
installed bash -n                                              PASS
installed Python compile                                       PASS
focused unittest                                           8 / 8
full unittest                                         1165 / 1165
expected isolated-data skip                                     1
R8R2 self-test                                                 PASS
authenticated bad-tree files                             930 / 930
authenticated bad tree removed                                 PASS
```

The three exact validation-log hashes are:

```text
first sanitation rejection
  4f669cea7e6bd2a774fa60d653caabd790a060af31cbea18a9111d997a6ee47b
second absolute-path install rejection
  4e7def815b9e373b409836007cad1adfba5168fa7e2b81a94e21dee9a7ac01d0
accepted v3 recovery and validation
  285b332504aac8e65102831ba1f1f9c9200363ee1f7e896e27da5fa135ca0f5a
```

The failures were deployment-tool defects detected before scientific
execution.  They changed no R8/R8R1 raw, controller action, plant state,
experiment gate, or R8R2 metric.

## Remote evidence

```text
project
  /home/yangshen0711/tsc_all/tsc_rzip_rllib
R8R2 output
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s24d1r14r8r2_audits/
  stage4_2r3c3t13s24d1r14r8r2_causal_online_innovation_adaptation_20260807_c90e299_v1
primary log
  logs/stage4_2r3c3t13s24d1r14r8r2_primary_20260807_c90e299_v1.log
independent log
  logs/stage4_2r3c3t13s24d1r14r8r2_independent_20260807_c90e299_v1.log
accepted validation log
  logs/stage4_2r3c3t13s24d1r14r8r2_installed_validation_20260807_c90e299_v3.log
```

Large R8 raw remains on the server.  Exact compact evidence and all three
deployment-validation logs are retained at:

```text
docs/codex/audits/
stage4_2r3c3t13s24d1r14r8r2_20260807_c90e299/
```

## Immutable source authentication

Primary and independent audits authenticated the accepted R8R1 boundary:

```text
R8R1 primary detailed SHA-256
  bd0041c3e16b56fce28abb80526bb5f1628ee74f6f5b52a70aaa07019e86a1ee
R8R1 primary summary SHA-256
  5d6c2eb4282dba1ba29e25624b147af8b760c8cfbe5fd085374cf54110de6204
R8R1 independent SHA-256
  3f378dba6eb1304422397b44a347e34d35827624ca6ea61791e85f16e7a5341c
R8R1 state SHA-256
  3f25e7070fd56243b1581b7da17cb433e0876821437bc9e7e098cdf4626d869f
```

The full R2/R4/R6/R8 training bank was also authenticated:

```text
responses / pairs / pair-history contexts              912 / 12 / 24
R8 training raw                                      624 / 624
R8 training bytes                                   19,725,920
R8 training inventory digest
  b5de1cabe0bd47b0d3a3b26aff04714ca0c05653483cd4c92403dc5867eeb762
R8 calibration / holdout raw                              0 / 0
heldout_outcomes_opened                                     false
raw matched-response exact reconstruction               912 / 912
probe descriptors reconstructed from own prefix          912 / 912
forbidden or matched-future predictor inputs                   0
```

R8R2 created no new raw and did not open calibration or holdout.

## Frozen baseline-forecast result

The no-action forecast used only four same-trajectory visible states ending
at the issue state and projected twelve relative lags.  It was required to
keep every future window inside componentwise caps
`[3 mm, 3 mm, 0.01 m/s, 0.01 m/s, 1000 A]`.

```text
baseline windows                                         96
passing windows                                          17
scientific gate                                        FAIL
maximum scaled point error                   25.23346999999822
componentwise maximum physical error
  R       0.016458723999998204 m
  Z       0.010935295653999980 m
  vR      0.2523346999999822 m/s
  vZ      0.1729267443999999 m/s
  Ip      549.1404600000837 A
```

The causal issue-state breakdown was:

| Issue task step | Passed windows | Maximum scaled error |
|---:|---:|---:|
| 10 | 0/24 | 25.2334700 |
| 14 | 0/24 | 17.2926744 |
| 18 | 11/24 | 3.0010950 |
| 22 | 6/24 | 3.3953697 |

Across all 96 rows, cap violations occurred in R/Z/vR/vZ/Ip on
`20/31/61/72/0` rows respectively.  Both history signs failed broadly
(`7/48` and `10/48` passes), and every one of the twelve physical pairs had
at most `3/8` passing windows.  The failure is therefore not an Ip limit, a
single pair, or a single hidden-history sign.  A four-point affine trend is
not a deployable no-action dynamics observer for these causal contexts.

Because the baseline gate failed before adaptation:

```text
outer folds computed                                          0
candidate update lags selected                                0
development artifact                                     absent
online update result                                      unrun
```

The immutable 250/270 ms arrival deadlines and 350/370 ms hold endpoints
were not changed or evaluated by R8R2.

## Independent agreement and hashes

```text
independent audit passed                                  true
scientific_gate_passed                                   false
primary numerical agreement                               true
primary outcome agreement                                 true
development artifact presence agreement                   true
selected update lag                                       none
new raw                                                       0
Ray / gotsc / TSC / controller / plant                0 / 0 / 0 / 0 / 0
```

Primary and independent component maxima differ only at floating-point
roundoff below the frozen tolerance.  The accepted compact hashes are:

```text
primary detailed
  ad04374987ce4de599d71f4673ac110fe763928831e4c9610cdb117efd7977cf
primary summary
  05d761ef64c9e7c2373a6754184ecf42cf0a250d26ee235293e768c0416c0bb2
independent JSON and log
  2ca90fab851c4131f7242bd9a5331286bde15ccaf47d251348b7d80a4597066c
final stage state
  ee06726c8a5170ffd03a9465432ceed6f42053e2db8f710442c80c7809f07670
```

## Classification and authorization boundary

```text
runtime/environment error in accepted run                         no
accepted package/import/deployment error                          no
preserved pre-result deployment-tool defects                     yes
source/raw/snapshot corruption                                    no
primary/independent disagreement                                  no
restart or causality failure                                      no
causal baseline-forecast/observer design failure                 yes
online adaptation scientific result                             unrun
real controller / MPC / formal-control result                   none
plant reachability conclusion                                   none
calibration / holdout result                                    none
```

R8R2 is immutable.  Its fixed four-state affine no-action forecaster may not
be tuned after viewing this result.  The next authorized route is a new,
separately prospectively frozen causal observer/identification design.  A
development observer pass may authorize only a separately frozen combined
online-adaptation validation; it does not authorize a controller, MPC,
expert data, BC, DAgger, bounded residual RL, or Gate A.  Every probe
trajectory remains forbidden from expert datasets.
