# Stage4.2R3c3T13S5 final forensic report

## Result

Stage4.2R3c3T13S5 completed exactly 68 authentic restart TSC trajectories.
Independent server-side raw, snapshot, manifest, package, statistics, and
open-order recomputation certifies the final scientific route:

```text
LATTICE_HOLDOUT_FAIL_REDESIGN
```

This is an identification-design and cross-history local-model failure. It
is not a runtime, deployment, restart, raw-corruption, final reporting, real
MPC, or global plant-reachability result.

## Exact identities

```text
local branch
  codex/stage4_2r3c3t13s1-transition-sentinel

implementation commit
  d048686  Implement T13S5 lattice-native split holdout

strict-JSON reporting hotfix
  8c8d087  Fix T13S5 rank-deficient result reporting

ordered existing-raw finalizer
  70e9429  Preserve T13S5 blind order during raw finalization

campaign
  quantized_lattice_native_split_two_step_blind_holdout_v1

controller
  quantized_lattice_native_split_probe_v42r3c3t13s5_v1

execution package
  r42r3c3t13s5_lattice_native_split_holdout_v1

reporting package
  r42r3c3t13s5_lattice_native_split_holdout_v1h2
```

The two hotfixes changed exactly six frozen reporting/validation paths:

```text
PACKAGE_MANIFEST.json
configs/stage4_2r3c3t13s5_lattice_native_split_holdout_370ms.json
run_stage4_2r3c3t13s5_verify_package.sh
scripts/stage4_2r3c3t13s5_server_postprocess.py
tests/test_stage4_2r3c3t13s5_lattice_native_split_holdout.py
tsc_rzip_rllib/diagnostics/
  stage4_2r3c3t13s5_lattice_native_split_holdout.py
```

The controller, quantized actuator, experiment matrix, action schedule,
thresholds, source snapshots, and formal timing did not change.

## Remote evidence

```text
run
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s5_runs/
  stage4_2r3c3t13s5_real_20260802_d048686

real launch log
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/
  stage4_2r3c3t13s5_lattice_native_split_holdout_20260802_012818.log
  SHA-256
  3da56e5181d2d45985f1e0cf73157570dc870bc44b87ced0d8cb907bb211e4cc

ordered finalization log
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/
  stage4_2r3c3t13s5_ordered_finalize_70e9429.log

independent audit
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s5_audits/
  stage4_2r3c3t13s5_real_20260802_d048686/
  stage4_2r3c3t13s5_server_audit.json
  SHA-256
  dc4d0147ce4fdd8a00105f8fc8ad45466513bac8b012f6843327b1efc271b033

compact final forensic
  stage4_2r3c3t13s5_final_compact_forensic.json
  SHA-256
  674b1e58f100c496608fae8fa695d6ed95ea7740a2f092e3d98ca07ae0122375

timing/route forensic
  stage4_2r3c3t13s5_route_forensic.json
  SHA-256
  97999cd48cb73cb5fd25c14dea3cde1ba2579f7cb496828ac5b8c29deaf300cd
```

Large raw and snapshots remain on the server.

## Validation and deployment

The final reporting package passed:

```text
local focused tests                                  20/20
local complete suite                               680/680
local empty direct-copy suite                      680/680, one expected skip
declared package hashes                              307/307
server staging complete suite                      680/680, one expected skip
server installed complete suite                    680/680, one expected skip

server staging validation log SHA-256
  ec66db10a6994f350de38b7f282634ec76293d62c98ec4ce12e544bd49469785

server installed validation log SHA-256
  d47244c4422917e1206a91767b882adb72de7862c01fc779ff567e5d39808def
```

The finalizer was monitored by exact PID. It created no `gotsc`, TSC, Ray,
controller, plant, raw, or snapshot process/file. No real trajectory was
rerun after the original 68 completed.

## Raw and restart authentication

```text
expected / actual raw                                      68 / 68
raw bytes                                                   3,610,097
raw inventory digest
  09ee846d2fd8c2a516ec01f1b91bcbf8f303885c2377373000ab85dfc45e0f01

successful execution                                      68 / 68
fresh restart and exact initial state                     68 / 68
controller causality failures                                   0
runtime/environment errors                                      0
solver/saturation/clipping errors                               0
forbidden controller/model inputs                              0
actuator interval/Card15 components                 34,272 / 34,272
maximum current utilization                              0.3904 <= 0.55
reported summary exact on independent recomputation              yes
snapshot authentication                                           4/4
```

The four extended baselines reproduced their exact source prefix and frozen
formal result. Formal tracking of probe trajectories is diagnostic only and
was not an identification acceptance gate.

## Reporting defects and safe repair

The first driver completed all raw and then failed while writing a model
containing Python `inf` at a rank-deficient development condition number.
This was a strict-JSON reporting defect; the underlying rank failure was
real. Revision v1h1 serializes the value as JSON `null` with an explicit
`finite=false` and leaves the gate failed.

Before ordinary resume, review found that `_evaluate_control(..., resume=1)`
would call `_result_complete` on all 68 files, pre-opening former holdout raw
before a model hash. That path was not executed. Revision v1h2 added a
reporting-only existing-raw finalizer that bypasses control evaluation.

The actual order was:

```text
development raw opened before model hash                 34
holdout raw opened before model hash                       0
model SHA before first holdout open
  bc710049e4eb6075f0d4675c3fd70ea5cb186b40635b0fa2041483c8c798e862
first holdout open ordinal                                35
total raw opens                                           68
model hash unchanged after holdout                       yes
```

The independent postprocessor then repeated the same order and reproduced
the reported summary exactly. The final result has zero remaining statistics
or reporting errors.

## Frozen scientific gates

```text
target Card15 central symmetry                         32/32
observed current signal                                16/32
observed current symmetry                              16/32
pre-effect causality                                    16/32
development signal                                     16/16
development rank/condition                               2/4
development non-vacuous tube                             3/4
consumed holdout containment                           26/32
consumed holdout relative error <= 0.10                  0/32
consumed holdout pre-effect causality                   16/32
maximum holdout scaled relative error              18.7134597
```

Development cells:

```text
easy transport    rank 4  condition 7.9547833  tube PASS
easy braking      rank 4  condition 7.9547833  tube PASS
hard transport    rank 0  condition non-finite tube PASS
hard braking      rank 1  condition non-finite tube FAIL
```

## Design-defect and real-model conclusions

Source and raw timing forensics show that the lattice wrapper modifies the
final Card15 action after R3c1 has already applied its software delay queue.
The probe therefore changes TSC current at `issue_step + 1`, independent of
the controller's `actual_delay` label. T13S5 incorrectly declared delay-2
effects at `issue_step + delay + 1`.

All 16 hard development probes showed their first nonzero coil-current
difference two states before the declaration. Transport probe current had
returned to baseline at declared states 3/4, producing rank zero. Braking
retained only an even/common component plus one odd direction, producing rank
one. This is an experiment-analysis/design defect, not a solver or plant
failure.

The timing defect is not the only failure. The delay-0/easy cells used the
already-correct immediate states and passed development rank/condition, yet
their consumed independent-history validation passed relative error 0/16.
Thus a single static history-local map also fails genuine cross-history
transfer in this finite test. Changing only the effect indices cannot certify
the T13S5 model.

## Classification and next action

```text
runtime/environment error                         no
packaging/import/deployment error                 no
raw or snapshot corruption                       no
initial strict-JSON reporting error              yes, repaired
ordinary-resume blind-order defect               yes, intercepted and repaired
experiment effect-state design defect            yes
cross-history local-map design failure           yes
plant restart failure                            no
real MPC executed                                no
global plant unreachability shown                no
reliable MPC expert validated                    no
```

The next stage is the preregistered zero-new-TSC T13S6 immediate-effect
audit. It recomputes every response at the actual post-queue states while
preserving the original development/consumed-validation roles and all
thresholds. A corrected development result cannot regain blind status and
cannot authorize a controller; it only determines whether a new independent
history holdout is worth designing or whether the causal multi-hypothesis
model must be redesigned first.

T13S5 probes remain forbidden from expert data. Real MPC, BC, DAgger, and
bounded residual RL remain blocked.
