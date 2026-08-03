# Stage4.2R3c3T13S20 forensic report

## Final classification

Stage4.2R3c3T13S20 is frozen as an excitation-sequence design failure.  It
is not safe to resume under the S20 controller identity.

```text
saved fail-closed route
  DYNAMIC_EXACT_CARD15_RUNTIME_OR_EXECUTION_FAIL_STOP

forensic classification
  DYNAMIC_EXACT_CARD15_CALIBRATION_SEQUENCE_DESIGN_FAIL_NEW_IDENTITY_REQUIRED

runtime or environment error                              no
deployment or import error                                no
raw or snapshot corruption                                no
statistics/reporting error                                yes, stale terminal phase_status only
excitation/controller sequence-design defect              yes
plant-restart failure                                      no
real closed-loop control failure established               no
safe same-source resume                                    no
```

The saved generic execution route remains authentic: the controller's frozen
zero-net guard stopped one baseline before its eighth plant advance.  The
more specific classification above comes from post-run raw and zero-plant
forensics; it does not weaken or reinterpret any gate.

## Identity and exact evidence

```text
local branch
  codex/stage4_2r3c3t13s21-cumulative-closure

execution package commit
  9113198  Fix S20 canonical S19 inventory authentication

forensic working-tree parent
  216c386  Record S20 network pause forensic handoff

package revision
  r42r3c3t13s20_dynamic_exact_card15_pooled_observer_campaign_v2

controller revision
  dynamic_exact_card15_calibration_probe_v42r3c3t13s20_v1

remote run
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s20_runs/
  stage4_2r3c3t13s20_dynamic_exact_card15_pooled_observer_campaign_20260803_9113198
```

Installed source fingerprints:

```text
PACKAGE_MANIFEST.json
  78a99f79ad08b64404023ba08a391828cc6f3f4025a2ece878d3b41c8ca92743
SHA256SUMS
  090817d842879f91f25655398119860e16a958f0f018f17d4689fff8348c7dc7
config
  400011233b68be3db2246b2f559db4b349369aaac53348a907b3d6d2c4d77c4b
controller source
  c3f05417f90ac0d65514e98a74567ab16dcca6aae05342c746a33dc63c7fddd1
CLI wrapper
  a49c0d8d6e581d427939ab8cf814ac0719698e72f29de01007738f6b66746255
focused tests
  6ea0984b4c84cb05a7e7e1c865eea143f1b17df3c1d160fbc132931664c059f5
```

Run artifact fingerprints:

```text
manifest
  496f5cb5e813023faccbfb0b2ed7d299e497c1358ed9f958e2c6e06f0247dee7
state
  940363eec1ac4b30691733571210b723146b245e8c3114543e619cc921f5ff59
offline preflight
  e6d5c5227f2c0d2e8d1a8d13902ca1bc704a3c6ed904eeec9873226ae65a2b3d
training-baseline gate
  a04b4c820c6051df63d6d92848c27fa9bdef2d1a9fce15fb116002c24bc73100
enhanced final-net forensic
  64c018a839492bc80e92ffecd3db41eba4375f2f937e92dee0694362f1cce364
independent full forensic v2
  8a94fa842ab49a466ef3bbce07e248adb582f5abd461dca56a7bc81a1d39f890
```

Compact evidence is tracked under:

```text
docs/codex/audits/stage4_2r3c3t13s20_result_20260803_9113198/
```

Large raw and snapshots remain immutable on the server.

## Offline and execution inventory

The valid package-v2 offline preflight passed before any plant step:

```text
S19 development authentication                              PASS
prior T13 raw parsed                                    900
candidate-pair prior hits                                 0
context/spec identities                              40 / 360
snapshot inventories                                  40 / 40
preaction fixed-basis checks                          40 / 40
new raw / TSC / plant advances                         0 / 0 / 0
```

The first commit-`1861dbd` offline attempt is separate.  It expected a legacy
S19 inventory token, failed with zero raw/TSC, and was replaced by package v2
after canonical recomputation of the unchanged S19 raw.  That was an
authentication/statistics-reference bug only and is not an S20 plant result.

The v2 training-baseline phase then produced:

```text
full campaign expected rollouts                            360
training baseline expected / actual raw                24 / 24
strict JSON.GZ parse                                    24 / 24
complete successes                                     23 / 24
structured partial failures                             1 / 24
raw bytes                                             1,342,538
raw inventory digest
  d78ba9a01e54611c7489bc13ae70883b2020a5647473976e6ca29c9c2f22de52
training probes / calibration / holdout raw               0 / 0 / 0
```

Independent server-side recomputation over the 23 complete baselines found:

```text
runtime / exact restart / causality                     23 / 23
actuator and calibration trace                          23 / 23
exact eight-event calibration net zero                  23 / 23
maximum dynamic design condition                    3.1980986512
maximum current utilization                           0.392
formal tracking PASS, diagnostic only                   10 / 23
```

The 23 successful contexts also supported 184/184 zero-plant full-path probe
replays.  This does not create probe raw or make a model/observer claim.

## Exact failed path

```text
experiment
  s42r3c3_a40f88ad021de4a85a93
pair / member / regime
  p9_q1_a0p900_gap2_settle4 / minus_first / D
raw SHA-256
  2d46a693b965e6c403aacdfa5f8f136cf197cf6114bab972b65155fbc212db06
trajectory / trace lengths
  8 / 7
last completed trace event
  task step 6, calibration_issue
failure
  ValueError('T13S20 dynamic calibration sequence is not exact zero net')
```

Seven plant advances completed.  The controller failed while constructing
the eighth action, before `env.step()` could apply it.  The partial raw was
preserved correctly and contains no evidence of a TSC, restart, solver,
saturation, or plant-control failure.

With only the terminal zero-net guard disabled for inspection, source-exact
controller replay proposed an eighth action whose final aggregate field net
was zero on 13 coils and `+0.0004 kA-turn` on coil index 8.  This is caused by
independently nearest quantization of each event; independent local choices
do not guarantee a globally exact eight-event sum.

## Cumulative exact closure forensic

At the same causal step-7 center, the exact negative of the seven-event
running net is representable on all 14 coils.  It passes every unchanged S20
action and geometry limit:

```text
Card15 target components exactly representable           14 / 14
signed primary coordinate                         1.0000000000
maximum absolute cross-coordinate                  0.0250000000
desired/actual current cosine                      0.9999973274
relative off-basis residual                        3.74e-16
incremental normalized action L-inf                0.2148095267
total normalized action absolute maximum           0.2160478395
current bounds                                            PASS
predicted maximum current utilization               0.3761
plant advances in forensic                                0
```

This proves a bounded causal cumulative-closure action exists for the failed
path.  It does not prove the same action for all future contexts and does not
turn S20 into a completed observer experiment.

## Reporting defect

The saved state correctly records `finished=true`, `primary_pass=false`, and
`stop_reason=training_baseline_or_lattice_gate_failed`, but leaves
`phase_status=offline_ready`.  This is a stale terminal state/reporting field.
It did not alter task execution, raw preservation, action selection, or any
scientific gate.  The saved baseline gate also correctly fails closed when
one result is incomplete; the independent forensic supplies the missing
per-success audit without changing that saved gate.

## Why S20 cannot resume

Replacing the eighth action with cumulative closure would change the
controller source fingerprint and the physical action on the failed path.
The failed path has no completed eighth plant advance, but repository rules
still prohibit a same-identity resume when controller/action semantics change.
The 23 successful raw files remain valid S20 evidence and are not overwritten;
they cannot be relabeled as results from the corrected controller.

The correct continuation is a separately preregistered S21 identity that
reruns the complete 360-rollout matrix.  It may use S20 only as development
evidence for the prospective action rule.  It must not reuse S20 raw as S21
campaign outcomes.

## What is and is not concluded

Frozen conclusions:

- authentic restart, causal execution, exact action accounting, and exact
  zero net passed for the 23 completed finite training baselines;
- the one stopped path is a real excitation-sequence design defect;
- cumulative exact closure is feasible for that exact causal state;
- S20 did not reach an observer training, calibration, holdout, MPC, or
  expert-data gate.

Not validated:

- the S20 pooled observer;
- robust finite-horizon restart MPC;
- new targets, continuous actuator/plant parameters, noise, disturbances,
  recovery, or independent long hold;
- expert data, BC, DAgger, or bounded residual RL.

## Commands and outcomes

The forensic work reread the repository instructions, project context,
server workflow, current task, frozen S20 config/design, launchers, exact
controller source, and tests.  The fixed authorized SSH endpoint was used
only after `tsc-airgap` name resolution failed.  Server-side Python parsed
all 24 raw files and complete logs, verified all 40 snapshot inventories,
recomputed 23 complete baseline audits, replayed 184 probe paths without a
plant advance, and evaluated the cumulative inverse action.  Compact JSON
was copied directly without an archive.  No package deployment, campaign
resume, new S20 raw, training probe, calibration, holdout, MPC, expert-data,
BC, DAgger, or RL execution occurred during this forensic stage.
