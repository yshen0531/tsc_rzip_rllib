# Stage4.2R3c3T13S24D1R14R8 forensic report

## Result

R8 is final at its fail-closed training boundary as:

```text
PARTITIONED_BROAD_RESPONSE_TRAINING_MODEL_FAIL_STOP
```

The 624 fresh training-extension rollouts are authentic, complete real-TSC
identification evidence.  Combined with the immutable 304-response R2/R4/R6
development bank, they produced 912 training responses over twelve whole
physical pairs.  The frozen action-conditioned full-history kernel passed
pointwise error and response geometry but failed the preregistered whole-pair
relative-error, cosine, peak-ratio, and velocity-tube gates.  Calibration and
holdout therefore remained unopened.

This is a response-center model/design failure.  It is not a runtime,
deployment, plant-restart, causality, raw-corruption, real-MPC, closed-loop
control, or plant-unreachability result.

## Code and package identity

```text
local branch
  codex/stage4_2r3c3t13s24-sequential-transition
prospective design commit
  6063d56
initial implementation / package
  48a4556 / 9b86365
source-phase bookkeeping repair / package
  bcfa1a2 / 5e57f60
raw-report repair / package
  90cb4db / fba8dae
independent raw finite-field repair / package
  a9395f5 / 4d74353
independent model-cardinality repair / package
  71316da / a6febc5
failed-route artifact audit repair / final audit package
  a69abac / 34c3f96
design SHA-256
  c225c6163fbf2146772fdabf100a34b13a3c6d59ee416f605698598acdc2022f
final audit PACKAGE_MANIFEST.json SHA-256
  bdec474b224ac349be6770b1df15bfbc0399cc876ad9b3afd3de0483d1e85e91
final audit SHA256SUMS SHA-256
  893f408a64d3f8796e03a27d203d076fcd3e81ecd72ffcec9addedbe3b97bbc9
```

The real-TSC stage manifest authenticates the execution package with:

```text
declared files                                      910
package fingerprint digest
  7d0a5a5fcbc44291851261b6928420e77a760a81b3d2af18fb67d22dfaf77437
config SHA-256
  3a334ca0360b077e0e875829aff33a408236214f45fca1988cf1675751dd7c39
driver SHA-256
  9d62653c67fb825e41f107e9fc4997222262187b66fe4f2e8960d21990708223
diagnostic/controller source SHA-256
  75ac9e239309a7e528d9644a2871a9ee4224f4692b62c09e1159a2a462aea230
prospective spec digest
  9e85ecaa2f0c8ec010490dab4f001541f18f714980b6cb7070636372edd1d667
```

All later changes were offline reporting or independent-audit changes.  They
did not alter an experiment identity, task, controller, requested/applied
action, TSC trajectory, formal gate, or model result.

## Remote evidence

```text
project
  /home/yangshen0711/tsc_all/tsc_rzip_rllib
run
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s24d1r14r8_runs/
  stage4_2r3c3t13s24d1r14r8_partitioned_broad_response_identification_20260804_5e57f60_v2
stage directory
  <run>/stage4_2r3c3t13s24d1r14r8_partitioned_broad_response_identification
offline log
  logs/nohup/stage4_2r3c3t13s24d1r14r8_offline_20260804_5e57f60_v2.log
real training log
  logs/nohup/stage4_2r3c3t13s24d1r14r8_training_20260804_194749.log
raw-report repair log
  logs/nohup/stage4_2r3c3t13s24d1r14r8_repair_training_raw_audit_20260805_fba8dae.log
accepted independent raw log
  logs/nohup/stage4_2r3c3t13s24d1r14r8_training_raw_independent_20260805_4d74353_v2.log
primary model log
  logs/nohup/stage4_2r3c3t13s24d1r14r8_fit_training_20260805_4d74353.log
```

Large raw, row-level model output, and snapshots remain on the server.  Only
compact evidence is retained in the repository audit directory.

```text
docs/codex/audits/
stage4_2r3c3t13s24d1r14r8_20260805_34c3f96/
```

## Phase inventory and fail-closed boundary

The prospective maximum was 1,248 fresh rollouts.  The actual boundary is:

```text
training extension                                  624 / 624
calibration                                            0 / 312  not run
fresh holdout                                          0 / 312  not run
strictly parsed training raw                         624 / 624
training raw bytes                                  19,725,920
training raw inventory digest
  b5de1cabe0bd47b0d3a3b26aff04714ca0c05653483cd4c92403dc5867eeb762
training model file/hash                                  absent
calibrated tube file/hash                                  absent
heldout_outcomes_opened                                  false
```

The terminal state is 908 bytes with SHA-256
`9fff80668023f17d3be273f9cd9694e21b401a5f668c60c1e03508a164c6d5d3`.
Its `phase_status` is `training_model_failed`, `new_raw_count` is 624,
`real_tsc_executed` is true, and the stop reason is
`training_whole_pair_response_model_or_geometry_gate_failed`.

## Raw, restart, causality, and action audit

Primary repair and independent raw-to-result recomputation agree on:

```text
runtime success / full finite horizon                 624 / 624
exact authentic source prefix state                   624 / 624
exact source controller-trace prefix                  624 / 624
exact causal issue/cancel action semantics            624 / 624
authenticated restart snapshots                         16 / 16
forbidden controller/model inputs                              0
solver errors / saturation or clipping                         0
maximum measured current utilization                       0.392
formal-contract passes, diagnostic only               234 / 624
```

The primary raw audit SHA-256 is
`8d6e3afc0a631b144538efcfb2542596933e94c1fb8e504b2cffb04733c45ce2`;
the accepted independent raw audit SHA-256 is
`4f84c476faab515ef0a0f82c14f5547c5de957b7df31fbf3d6c228842edb0262`.
Probe trajectories are identification data and remain forbidden from every
expert dataset.

## Frozen training-model result

The nested outer validation held out each of twelve complete physical pairs.
The selected candidate was PCA rank 4, RBF bandwidth multiplier 2.0, and
ridge 0.1.  The exact aggregate was:

```text
whole-pair outer responses                            912
all response gates                              719 / 912
relative-L2 gate                                 763 / 912
cosine gate                                      731 / 912
peak-ratio gate                                  829 / 912
finite / point-error gates                       912 / 912 each
maximum relative L2                           1.5279087085521352
minimum cosine                               -0.16994497675301598
peak-ratio range                  0.17852411174023414--2.1303641273377756
maximum scaled point error                    0.05081135014313233
actual / predicted signal                          912 / 912 each
canonical geometry rank/condition                  192 / 192
operational geometry rank/condition                192 / 192
maximum predicted geometry condition            8.151210622342354
maximum actual geometry condition              12.121012187090836
```

The training tube precursor was:

```text
[R, Z, vR, vZ, Ip]
[0.00036284344 m, 0.00019415287 m,
 0.01016237003 m/s, 0.00576029711 m/s, 11.75906737 A]
```

Only the vR cap exceeded its unchanged `0.01 m/s` limit, but that is still a
real frozen-gate failure; the other response-shape gates also failed by large
margins.  Actual and predicted four-direction geometry remained full-rank
and well conditioned, so the result does not support a plant-authority or
local-reachability failure claim.

Failure is not an artifact of only tiny responses.  The 193 failed rows had
actual peak median `0.013348`, versus `0.008044` for the 719 passing rows,
and show pair/issue/direction-dependent amplitude underprediction plus shape
and phase error.  The twelve whole-pair pass counts ranged from 42/76 to
72/76.  Both prefix-5 and prefix-9 context families and both causal history
members remained represented; those orchestration labels were not model
inputs.

Primary detailed and summary SHA-256 values are:

```text
training_model_primary_detailed.json
  797c862666a7bf8f770816bfa83d20f9b2cedea8dfa4be49f061d81680578a50
training_model_primary_summary.json
  2538601ff1086357a96a1f9646a0f9368108fe648b0897da2d987624db111968
```

The final structurally independent recomputation used the repaired audit
package `34c3f96` and reproduced the complete outer prediction rows,
candidate selection, aggregate, and both predicted and actual geometry
families within the frozen tolerances.  Its contract deliberately separates
audit correctness from scientific success:

```text
independent audit passed                              true
scientific_gate_passed                               false
primary_numerical_agreement                           true
primary_outcome_agreement                             true
model_artifact_presence_agreement                     true
training model SHA-256                               empty
route
  PARTITIONED_BROAD_RESPONSE_TRAINING_MODEL_FAIL_STOP
training_model_independent.json SHA-256
  cfb4ad0aebc838045468e6dd9e5937007c06a07458a458f253a0dd411861cba0
```

Thus `passed=true` in this independent file means that the independent
audit agrees with the primary scientific FAIL; it is not a model PASS.

## Reporting and independent-audit defects

Four non-scientific defects were preserved and repaired without rerunning
TSC or changing the frozen model result:

1. The first offline attempt classified the inherited four development
   pairs as `consumed_training` while a source-phase audit expected the name
   `training`.  It stopped before TSC and produced no accepted run.
2. After all 624 real tasks completed, the primary raw audit represented the
   empty issue-10 preissue interval as shape `(0,)`, not `(0,14)`, and
   falsely failed 128 otherwise valid rows.  The explicit reporting repair
   changed zero raw files and ran zero TSC/Ray tasks.
3. The first independent raw audit applied a generic finite check to
   trajectory dictionaries containing valid string metadata and falsely
   marked all 624 rows nonfinite.  The repaired audit checks only physical
   R/Z/Ip and coil/wire numeric fields and agrees with the primary audit.
4. The inherited independent model report hard-coded R7R2 cardinalities and
   one geometry family.  After cardinality repair, its completed numerical
   recomputation attempted to hash a model file that correctly does not
   exist on a scientific FAIL.  The final audit contract requires a model
   artifact if and only if the scientific gate passes.

These are runtime/reporting-tool defects, not evidence against the raw,
restart, action semantics, frozen model metrics, or physical plant.

## Classification

```text
runtime/environment error in real TSC                   no
package/import/deployment error in accepted run         no
raw or snapshot corruption                              no
postprocessing/reporting defects                        yes, repaired only
controller action-semantics failure                     no
authentic plant-restart failure                         no
frozen response-center model/design failure             yes
real closed-loop MPC conclusion                         none; not run
calibration / fresh holdout result                      none; not run
expert data / BC / DAgger / bounded residual RL         not authorized
```

## Formal timing and scientific boundary

The formal timing was never changed: normal slew must arrive by state 25 and
hold through state 35; weak slew must arrive by state 27 and hold through
state 37, with the frozen 30 mm, 0.1 m/s, 10 kA, and streak-three gates.
R8 formal tracking is diagnostic only.  R8 executed no MPC and validates no
unseen target, continuous actuator/plant parameter, noise, disturbance, or
long-hold robustness.

## Next route

R8 is immutable and may not open its old calibration or holdout phases with a
changed model.  The next stage is a separate, prospectively frozen,
zero-new-TSC development discriminator using only the already-opened 912
training responses.  It will test whether the same causal response family
passes unchanged gates on a controller-useful short prediction horizon under
whole-pair nesting.  A pass can authorize only a fresh authentic multipulse
superposition/interaction sentinel; a failure requires causal online
innovation/adaptation or a new identification design, not more capacity in
the failed long-horizon point-center kernel.

Reliable constrained MPC and the full robustness ladder remain mandatory
before expert data, BC, DAgger, or bounded residual RL.

## Validation and commands actually run

All Python commands used the repository-local Windows virtual environment or
`/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python`.  The work
performed local compile, strict JSON parse, focused tests, the complete
1,150-test suite, 910-file manifest/checksum verification, server `bash -n`,
server package/import/self-test verification, and the complete 1,150-test
server suite with one expected server-only skip.  The final local suite was
1,150/1,150; the final server suite was 1,150/1,150 with one skip.

The server workflow then ran the guarded zero-TSC offline phase, exactly 624
fresh authentic training-extension tasks, the zero-TSC raw-report repair,
the independent raw audit, the serial primary `fit-training`, and the serial
independent `training-model-independent` recomputation.  The final
independent recomputation used PID 3235510, ran to natural completion, wrote
the accepted 188,290-byte result, and left no R8 process running.

No global Python, package installation, Git on the server, archive operation,
R8 calibration, R8 holdout, MPC execution, expert-data generation, BC,
DAgger, or RL was run.
