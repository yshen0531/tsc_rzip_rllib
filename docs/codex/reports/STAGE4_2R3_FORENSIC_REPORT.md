# Stage4.2R3 final forensic report

Date: 2026-07-30 Asia/Shanghai

## 1. Result

Stage4.2R3 did not validate hidden-history or different-initial-state MPC
robustness. The run completed its entire preregistered state-generation grid,
but no candidate pair met the preregistered hidden-state separation gate.
The control phase was therefore correctly not run.

This is an experimental-design failure, not a runtime failure, packaging
failure, raw-data failure, reporting failure, plant-restart failure, or real
closed-loop MPC failure.

R3 remains failed under its original gate. The gate was not weakened or
reinterpreted after the result.

## 2. Exact identity

```text
local branch       codex/stage4_2r3-hidden-history
design commits     99dcd7b, 9b99fb0
implementation     9d752d2
offline CLI fix    5748f83
controller         authentic_hidden_history_initial_state_mpc_v42r3
package revision   r42r3_authentic_hidden_history_initial_state_v1
PACKAGE_MANIFEST   c56e589c4e233dd7a74da60a1239de21039f92f80c25748f38a9a55c89543bcc
SHA256SUMS          74f837f7b6363e5a44e3366c527f36f5bdab6ff0478be0fab229c8e490ce3404
resolved config    c423c64abd2b57d110a33052e8e8a1420a0336f4de0b878f9c458cb6c62cf2f9
R3 module          993f007f02a633b7f41faed285b9e44664385c23d891d1ded9c9ddb0389f8dd4
```

Remote evidence:

```text
project
  /home/yangshen0711/tsc_all/tsc_rzip_rllib

source R2
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r2_runs/
  stage4_2r2_persistent_controller_checkpoint_replay_20260730_082250

R3 run
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3_runs/
  stage4_2r3_authentic_hidden_history_initial_state_20260730_100915

R3 log
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/
  stage4_2r3_authentic_hidden_history_initial_state_20260730_101040.log

server audit
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3_audits/
  stage4_2r3_authentic_hidden_history_initial_state_20260730_100915
```

## 3. Validation before real TSC

Local validation:

```text
focused R3/R2 tests                         17 passed
complete repository unittest discovery     446 passed
post-offline-CLI focused tests                9 passed
empty-directory deployment simulation      445 passed
package inventory/checksums                 118/118
Python compile/AST and all JSON parse       passed
```

The server staging package and installed package independently passed:

```text
package SHA-256 verification                118/118
Python compile and import closure            passed
bash -n                                      passed
complete server unittest discovery           447 passed
network/Git dependency                       none
server virtualenv modification               none
```

The independent `offline` CLI gate ran before any gotsc process:

```text
required frozen controller cases             4/4
action steps                                 144/144
maximum action absolute difference           0.0
future action reads                          0
future state persisted in controller         0
real TSC executed                            false
state raw files after offline gate           0
snapshots after offline gate                 0
```

The two weak-slew delay-2 paths reproduced 20 main-control plus 17
anticipatory-damping actions. The two normal-slew delay-0 paths reproduced
35 main-control actions.

## 4. Expected versus actual campaign

```text
state-generation rollouts expected           54
state-generation rollouts actual             54
successful real-TSC state rollouts            54
candidate pairs expected                      27
candidate pairs actual                        27
visible-matched pairs                         27
hidden-separated pairs                         0
accepted/selected pairs                        0
conditional control rollouts expected        16-24
control rollouts actual                         0
```

Zero control rollouts is not a missing experiment. The preregistered design
required at least two accepted pairs before control. That condition was false,
so the control phase is `not_run`.

## 5. Raw, snapshot, manifest, and corruption checks

The server-side postprocessor parsed and hashed the full run in place:

```text
run files                                    557
run bytes                                    6,402,205,406
run-inventory digest                         6171fe9eaafcbab2f32d55f18d03855d1a82d1bfd6c4c509098c3e58b79fcc65
source-fingerprint digest                    4ee32cd099b19aa3fd4b0a99be31cf3c4e53edc2f626bd3b578bb63f595fa015
state raw expected/actual                    54/54
raw experiment-ID set exact                 yes
raw parse complete                           yes
snapshot manifests unique                   54/54
snapshot payload inventories valid          54/54
runtime/environment errors                   0
raw/snapshot corruption                      0
```

Only 388,686 bytes of compact evidence were downloaded. Eleven downloaded
run-derived files were checked against the server run inventory and matched
their SHA-256 hashes. Raw JSON.GZ and the 6.4 GB snapshot tree remain on the
server.

The tracked compact audit is
`docs/codex/audits/stage4_2r3_result_20260730_100915/`.

## 6. Pair result recomputation

All 27 reversed-history pairs were valid at the same snapshot clock and met
every visible matching threshold:

```text
maximum visible normalized ratio             0.063074
R difference range                           1.11e-7 to 2.0378e-5 m
Z difference range                           1.175e-7 to 3.1537e-5 m
Ip difference range                          0.0018 to 0.2047 A
coil RMS difference range                    0 to 1.4393e-5 A
```

The hidden difference was orders of magnitude too small:

```text
preregistered wire max minimum               1,000 A
observed wire max range                      0.001 to 0.048 A
preregistered relative RMS minimum           0.05
observed relative RMS range                  4.05e-5 to 0.002411
best pair                                    q2_a0p200_settle4
best wire max difference                     0.048 A
best relative RMS difference                 0.002411
```

The strongest response was monotonic with amplitude for directions 1 and 2
and was largest at the shortest four-step settle. This shows that adjacent
`+a*q, -a*q` actions canceled nearly all passive-current history before the
snapshot.

An exploratory, same-clock all-cross-pair audit considered 459 endpoint
pairs. All 459 remained visibly matched, but the maximum hidden difference
was still exactly 0.048 A and relative RMS 0.002411. Thus the failure is not
caused by the preregistered within-pair matching rule.

## 7. Error and conclusion classification

Runtime/environment error:

```text
none
```

Deployment/package/import error:

```text
none; staging and installed packages passed their complete validation
```

Raw/snapshot corruption:

```text
none; 54/54 raw and 54/54 snapshot inventories passed
```

Summary/statistics/reporting error:

```text
none in the final run; server-side recomputation reproduced the result
```

Experimental-design defects:

1. Adjacent reversed pulses cancel the passive-current excitation too
   effectively to create a hidden-history pair.
2. The absolute 1,000 A hidden threshold is inconsistent with the observed
   wire-current scale. Authenticated R1 endpoints have wire RMS of roughly
   0.4-2.3 A and same-target cross-key differences up to about 5.66 A; R3
   endpoints have wire RMS 6.35-9.20 A. This is a threshold-calibration
   defect, not a code unit-conversion error.
3. Symmetric zero-net histories also leave pair centroids near the frozen
   initial state, so they do not establish different-initial-state coverage.
4. The R3 manifest identifies controller/package revisions but does not embed
   the deployed package source-file digest. External package hashes close the
   audit for this run, but the next stage must make that digest a resume gate.

Real control or plant-restart conclusion:

```text
not tested
```

No selected pair was restarted for closed-loop control. Therefore R3 provides
no evidence for or against MPC hidden-history robustness, observer/history
identification, formal tracking, or plant restart from these new states.

## 8. Frozen conclusions and next action

Still frozen:

- R17 finite static-grid result;
- R1 authentic same-action plant restart, 18/18;
- R2 causal persistent-controller restart, 18/18;
- immutable 250/350 and 270/370 ms formal timing;
- no BC, DAgger, or residual RL.

Not validated:

- matched-visible/different-hidden closed-loop control;
- different initial states;
- unseen targets;
- continuous actuator parameters;
- plant/Jacobian error;
- noise;
- disturbance recovery;
- independent long hold.

The next run must have a new identity. It must not reinterpret R3. The
preregistered R3a design uses a common expert-action prefix to create visibly
different authenticated initial states and separates the nullspace
counter-pulses in time so the passive-current response does not immediately
cancel. Its hidden absolute threshold is calibrated before R3a execution from
the already-authenticated R1/R3 wire-current scale, while retaining the
relative RMS gate and all visible/formal gates.
