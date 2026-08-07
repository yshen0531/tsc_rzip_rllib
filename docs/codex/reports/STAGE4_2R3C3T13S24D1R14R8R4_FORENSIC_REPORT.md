# Stage4.2R3c3T13S24D1R14R8R4 forensic report

## Final classification

R8R4 is final as:

```text
FRESH_CAUSAL_OBSERVER_DEVELOPMENT_FAIL_STOP_NO_HOLDOUT
```

The eight authentic development baselines completed cleanly, and the causal
observer passed every frozen practical point-prediction aggregate.  The
prospectively fixed empirical tube nevertheless missed the 90% containment
floor in five of 32 development history contexts.  The structurally
independent implementation reproduced the primary decision and numerical
values exactly.  The stage therefore stopped before opening blind holdout.

This is a finite uncertainty-calibration/design failure.  It is not a
runtime, deployment, restart, causality, Card15, raw, snapshot, solver,
controller, formal-control, real-MPC, plant-reachability, or global-
observability failure.

## Identity and execution evidence

The prospectively frozen design SHA-256 was:

```text
942b7698e9d19ee905d75dc7ee9fda370e642e9e986298af32d8f17ed22f8119
```

The implemented campaign checkpoint was `3c12aa3`; its installed execution
package checkpoint was `a1fdee3`.  The exact server run was:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
stage4_2r3c3t13s24d1r14r8r4_runs/
stage4_2r3c3t13s24d1r14r8r4_fresh_causal_observer_identification_20260807_a1fdee3_v1
```

The stage manifest authenticated the exact config, design, fourteen source
files, R8 source, R8R3 source, sixteen frozen specifications, and the package
fingerprint.  Its key hashes were:

```text
config SHA-256
  c9b7007334f603289fdad107e52e642906ab3a60d08c61e1f9515ecc70a6b2b9
spec digest
  7827b8cc39489e20b1fda38978b7b6d98d89102a8f3060aecdbf2896d83dd5f4
scientific package fingerprint
  a449b444ccc7536b802edf235ace73da374636ad0cdb3f12c067ba0a32724813
stage manifest SHA-256
  630d749fc9956e60cf751a8248550c9be5b3d5608a9c012c3c9f05b27a98a9a4
```

Offline preflight authenticated both sources, froze eight development and
eight holdout specifications, observed zero new raw and zero holdout raw,
and ran no TSC.

## Development acquisition

Exactly eight development baselines, both histories of four physical pairs,
ran in fresh workers.  Primary and independent raw audits agreed:

```text
runtime success / full horizon                         8 / 8
exact source physical-state prefix                     8 / 8
exact source causal-trace prefix                       8 / 8
authenticated source restart snapshot                  8 / 8
exact zero future action                               8 / 8
constant future commanded current                      8 / 8
finite trajectory                                      8 / 8
forbidden trace count                                      0
maximum total normalized action abs           0.648149691358026
maximum current utilization                         0.392
raw files / bytes                               8 / 245279
raw inventory digest
  8d0d6c2c8f7e4e8436f9ef958fb30e4276823a8004fbab97b8c50d71b1ed3f66
```

The primary and independent raw-report SHA-256 values were:

```text
8d967ef68ea13e2ae42fc3afe6f566b976f26b633976049e8e7c1a4c0092487c
b720bffd19039c339b57e0a596802991bbe3e17d24d15408b6244733dfa490ee
```

The `route` field in the phase-local primary raw report contains the
configuration's eventual PASS route.  It is a descriptive phase-report
placeholder, not the stage verdict.  The contemporaneous state remained
`development_raw_primary_passed`, and the later model decision set the
authoritative failing route.  No raw or scientific metric depends on that
placeholder field.

## Observer and tube result

Development combined the twelve authenticated R8 training pairs with the
four new R8R4 development pairs.  It reconstructed 480 causal origins across
16 complete pair folds.  The all-development selected candidate was fixed by
the preregistered whole-pair selection rule:

```text
family                    linear
PCA rank                       32
ridge                       1e-6
bandwidth multiplier           0
```

The nested outer point result passed every practical gate:

```text
eligible origin point passes / required / total     480 / 456 / 480
prescribed-issue passes / required / total           128 / 122 / 128
finite-exclusion violations                                        0
maximum scaled point error                         0.12737875204525517
maximum absolute R / Z error         0.000978543 / 0.001129360 m
maximum absolute vR / vZ error       0.011369488 / 0.012737875 m/s
maximum absolute Ip error                         30.516289664 A
```

The fixed higher-quantile-scaled all-development OOF tube stayed far inside
the finite exclusion caps and passed aggregate containment, but failed the
per-history-context floor:

```text
tube-contained origins / required / total            457 / 456 / 480
tube cap                                                PASS
history contexts passing containment                  27 / 32
maximum tube R / Z                  0.000802750 / 0.000786491 m
maximum tube vR / vZ                0.009394006 / 0.012118154 m/s
maximum tube Ip                                  30.322269655 A
```

The five failing contexts, with contained/required/total rows, were:

```text
p5_q1_a0p900_gap4_settle4 | plus_first       12 / 13 / 14
p5_q2_a0p750_gap2_settle4 | minus_first      11 / 15 / 16
p5_q2_a0p750_gap2_settle4 | plus_first       12 / 15 / 16
p5_q2_a0p750_gap4_settle4 | plus_first       10 / 13 / 14
p9_q1_a0p900_gap4_settle4 | minus_first      12 / 13 / 14
```

Every one of these misses is retained.  Aggregate success cannot override a
frozen per-context failure.  Because the scientific gate failed, no observer
model or tube artifact was emitted.

Primary detailed, primary summary, and independent model-audit SHA-256 were:

```text
af8cb6d75a435ecd96948b4c15a2e1929c98527edd5483c8f29c0c6394125dac
bde614d6ac34535d5f22f187925723969921e8333b41d429a32e0719cb8b3bfd
12ee920fb0d49d46285bba31a443a24e09a5b6b9b3b1d0b5ddc61560a20fa86b
```

The independent audit reports `passed=true`,
`primary_numerical_agreement=true`, the same failed scientific gate, the
same empty model/tube hashes, and the same route.

## Independent-audit implementation repairs

The first independent raw attempt used an inventory row schema different
from the primary report.  Checkpoint `c95790a` corrected only that audit
schema.  The second attempt then exposed that the independent digest used a
canonical JSON digest rather than the primary inventory stream digest.
Checkpoint `375b7eb` corrected only that digest implementation.  Neither
repair changed a trajectory, raw byte, controller, feature, model, tube,
threshold, split, or route.  The corresponding package checkpoints were
`9b8ac7e` and `7810525`.

The final installed direct-copy package at `7810525` contained 952 declared
files plus `PACKAGE_MANIFEST.json` and `SHA256SUMS`:

```text
PACKAGE_MANIFEST.json SHA-256
  e30579aafe1039755589d04c53c0dd8c0cf9ae87c21c57cd50816d29ec996dc6
SHA256SUMS SHA-256
  05fc34be5c0303c87bc219540700a0fb5dc9929d6c121c2ce2ced9e71b75070b
```

The package was copied directly through the authorized SSH workflow with no
local archive operation.  Local Windows-shim and installed-server full
suites each passed 1187/1187; the server had one expected isolated-data
skip.  All server commands used the existing
`$HOME/tsc_all/tsc_simulation/venv_simu` environment.

## Final immutable boundary

Final server inspection found:

```text
development raw files             8
blind-holdout raw files            0
model/tube files                   0
holdout outcomes opened        false
new raw count                      8
real TSC executed               true
phase status      development_model_failed
stop reason       development_practical_point_or_tube_gate_failed
final state SHA-256
  617c6ea2e2ae81d5d1ad9f0de2f331a1b0d19caa3031dc76e4714ecc4c417015
```

R8R4 may not resume by changing its tube, thresholds, model, split, or
holdout authorization.  Its eight trajectories remain identification-only
and are forbidden from expert, BC, DAgger, and RL datasets.  The unopened
holdout pair blueprints may be consumed only under a separately frozen new
identity.  MPC, Gate A, expert data, BC, DAgger, and residual RL remain
blocked.
