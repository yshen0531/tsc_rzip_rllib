# Stage4.2R3c3T13S24D1R14R8R6 forensic report

## Final classification

Stage4.2R3c3T13S24D1R14R8R6 is final as:

```text
CAUSAL_ONE_STEP_INNOVATION_NO_MEASURABLE_GAIN_STATIC_ROBUST_OBSERVER_SENTINEL_REQUIRED
```

The fixed static causal observer and its prospectively reserved global tube
passed the complete frozen observer qualification.  The one-step innovation
update did not provide measurable benefit and is therefore disabled.  This is
an observer-qualification PASS plus an adaptation-usefulness FAIL, not a
runtime, deployment, restart, causality, raw, controller, formal-control,
real-MPC, plant, reachability, or global-observability conclusion.

R8R6 ran zero Ray, `gotsc`, TSC, controller, or plant advances, created no raw
directory, and modified no source trajectory.  It does not qualify Gate A or
authorize expert data, BC, DAgger, or residual RL.

## Frozen identity and validation

```text
branch
  codex/stage4_2r3c3t13s24-sequential-transition
design checkpoint
  0352207
implementation checkpoint
  df2e8c4
package checkpoint
  6b00e24
declared files / direct-copy total
  980 / 982
PACKAGE_MANIFEST.json SHA-256
  48074662c9f1fbf65a3db61ff2991a436114a3d50ca53c0b57e9e727a16077f5
SHA256SUMS SHA-256
  4be76a31115824b5d54244c3bcd6440975049066e7b4e54def989d0feccd8fdf
```

The package was first reconstructed by direct file copy into a new empty
local directory.  All 980 declared hashes, the stage self-test, and focused
tests passed from that copy.  No local or remote archive operation was used.

Local validation used the project virtual environment and loaded the existing
Windows `resource` shim before unittest collection:

```text
focused tests                                      10 / 10
complete repository tests                       1208 / 1208
local failures / errors / skips                     0 / 0 / 0
```

The direct-copy server staging package passed all GNU hashes, `bash -n`,
compilation, and focused `10/10` in the existing server virtual environment.
After exact authentication of the installed R8R5 package, only the declared
source trees and root launchers were replaced; run trees were untouched.  The
installed R8R6 package then passed the same package verification and:

```text
complete installed repository tests             1208 / 1208
expected server skip                                      1
```

## Exact server output

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
stage4_2r3c3t13s24d1r14r8r6_audits/
stage4_2r3c3t13s24d1r14r8r6_causal_one_step_innovation_observer_20260807_6b00e24_v1
```

The exact package fingerprint embedded in the stage manifest is:

```text
ad49e939d5a3d4950a22d73ccda7ff25c5815b6e37081e0b287fdcdf352a00d4
```

The source bank was reconstructed from all consumed evidence, with no
forbidden or future predictor input:

```text
physical pairs                                             20
history contexts                                           40
causal origin rows                                        600
prescribed issue rows                                     160
feature dimension                                         353
forbidden predictor inputs                                  0
future predictor inputs                                     0
allowed in expert data                                  false
```

## Frozen observer gates

Twenty complete physical-pair outer folds independently fitted the one fixed
linear/PCA32/ridge-1e-6 candidate.  Origin 10 retained the cold startup
observer; origins 11 onward applied the prospectively fixed innovation only
for evaluation.

```text
outer folds                                                20
startup point rows                                    40 / 40
startup finite-exclusion violations                         0
adapted origin point rows                            560 / 560
required adapted point rows                         532 / 560
adapted prescribed issue rows                        120 / 120
required adapted prescribed rows                     114 / 120
adapted tube containment                              560 / 560
required adapted tube rows                            532 / 560
history contexts satisfying all point/tube gates        40 / 40
finite-exclusion violations                                  0
innovation clipping rows                                     0
tube cap gate                                              PASS
```

Maximum adapted point errors in physical units were:

```text
R / Z                         0.0009594395 / 0.0007038558 m
vR / vZ                       0.0113166182 / 0.0098570101 m/s
Ip                                              82.0159328 A
maximum scaled point error                       0.113166182
```

The global tube used the frozen higher-q95/every-context-higher-q90
construction.  Its aggregate row-ratio q95 was `1.6725631775`, the worst
context q90 was `3.4219120289`, and the prospective factor-two reserve gave
scalar `6.8438240577`.  Maximum half-widths were:

```text
R / Z                         0.0032254596 / 0.0033520607 m
vR / vZ                       0.0386971126 / 0.0443856721 m/s
Ip                                             117.0384656 A
```

All are below the frozen `[0.01 m, 0.01 m, 0.05 m/s, 0.05 m/s, 3000 A]`
finite tube caps.

## Adaptation-usefulness result

The uncertainty qualification and measurable-benefit gate were deliberately
separate.  The fixed innovation failed every aggregate usefulness condition
needed to justify online adaptation:

```text
cold mean squared scaled error                 0.000266862153
adapted mean squared scaled error              0.000287714052
adapted / cold ratio                              1.078137340
required ratio                                      <= 0.95
strictly improved contexts                              8 / 40
required improved contexts                            >= 24 / 40
contexts within the <= 1.05 regression limit            12 / 40
worst context adapted / cold ratio                    1.287598795
```

The innovation update made aggregate error about 7.81% worse rather than at
least 5% better.  Retaining it would add state and failure modes without a
measured benefit, so the frozen route correctly selects the static observer.
This does not weaken or reinterpret any row gate.

## Independent agreement and fingerprints

The structurally independent implementation separately reconstructed the
bank, folds, fits, predictions, innovation, kinematic integration, tube,
metrics, artifacts, and route.  It reported:

```text
primary numerical agreement                         true
primary outcome agreement                           true
artifact hash agreement                             true
independent audit passed                            true
```

Load-bearing server SHA-256 values are:

```text
primary detailed
  147c872935846f4aaedeb90953f4f3afe869d879578794f7b221ba228278fabf
primary summary
  cef09d19c8604f3b1b1f737613099db6d174120c7d3b04dbca42582d429694d0
independent audit
  8e2c846f752af773a5decf7545a60d306b8ea83545be40c49f8c785a63598cd2
observer model
  3ba16449086097a42513987df97c95ec6d6d0d35d572e73992fa5eafdfc15519
observer tube
  747a6c24f9abed8a4ec6784e4699c7ebe557a049bb11e10ea9a1d5ca0254b8ea
innovation contract (adaptation disabled)
  272c5979f0b806f228e335bbbb8db1f57df623822d8a8ffe3c797ca96b4203f5
final report
  d9e70003a3267ee01394472f4c2e4efdb03af65656a7dc1f2980a521b74528e3
stage manifest
  2001bece45759d4d8ce8c17cf85e8c063c499ed313493a4e46b53246e52c4beb
final state
  0cb80974ac25d2f5cdfeb6f69e825a5e71ab4caf388b94cd3ac890b35cb140be
```

The first supplemental compact extractor was a read-only reporting-script
failure: it requested `outer_folds` from the intentionally compact summary
instead of the detailed file.  Its preserved output is zero bytes.  The v2
extractor changed only that input location and completed; its local compact
SHA-256 is
`76ae96c596f00d6457975df809129967ed4170a9c489d549c265c029d91ae12e`.
This did not alter any source, model, stage state, manifest, or scientific
result.

Compact evidence and complete validation/phase logs are retained under:

```text
docs/codex/audits/
stage4_2r3c3t13s24d1r14r8r6_20260807_6b00e24/
```

## Handoff boundary

R8R6 certifies a finite causal no-future-action observer center plus a bounded
global uncertainty tube over the consumed 20-pair development envelope.  It
does not yet prove behavior when multiple fresh physical actions interact,
does not validate an action-conditioned transition predictor, and is not a
closed-loop controller or MPC result.

The only authorized next step is a separately frozen fresh authentic
interaction sentinel using the static observer, exact Card15/current/action
limits, fixed startup/fallback, causal information, and prospective
acceptance criteria.  All R8/R8R4/R8R5/R8R6 trajectories remain forbidden
from expert or learning datasets.
