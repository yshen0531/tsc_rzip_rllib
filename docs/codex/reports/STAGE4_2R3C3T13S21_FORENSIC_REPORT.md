# Stage4.2R3c3T13S21 forensic report

## 1. Result

Stage4.2R3c3T13S21 completed its prospectively phased 360-rollout real-TSC
campaign. All raw, restart, causal-execution, actuator, Card15, exact-net,
model-freeze, tube-freeze, and independent server-recomputation gates passed.

```text
training / calibration / holdout real rollouts       216 / 72 / 72
expected / actual raw                                     360 / 360
complete successful raw                                   360 / 360
training whole-pair OOF rows                              192 / 192
calibration point / containment / cap / joint              64 / 64
fresh holdout point / containment / cap / joint            64 / 64
forbidden predictor inputs                                          0
runtime or environment errors                                       0
raw or restart errors                                                0
statistics or reporting errors                                      0
```

The exact route is:

```text
CUMULATIVE_EXACT_CARD15_POOLED_OBSERVER_HOLDOUT_PASS_LOCAL_SET_MODEL_ONLY
```

This certifies a finite clean local response-set model after the frozen
active-calibration sequence. It is not a real MPC, a robust restart-control
pass, or evidence that the model may be recursively rolled through the full
formal horizon.

## 2. Code and package identity

```text
local branch
  codex/stage4_2r3c3t13s21-cumulative-closure
design checkpoint
  8393f55
implementation checkpoint
  b83e406
deployed package checkpoint
  98dc353
```

Load-bearing deployed hashes were:

```text
config
  d9ebb6df8a20a0b948d8a03d071454a7cf513337be4338e5d873c44aea0342d8
campaign implementation
  bcca9f32743020d9e96dd0e9860505151a1f1d1d0c9b0a0822d6dc315960cf92
frozen design
  61504e4d014c4f2e357b312a74a90195164c7811683dca8dbc19eeb80096793a
PACKAGE_MANIFEST.json
  9cdc69f9d3b8987fa21059615ea9c5346cb5ece720fe7d73c87996a88075a08b
SHA256SUMS
  6371278c7ba9d8b9f55ac88f6a9abc26634ea526cdad37c8918abf7f933ea4ee
```

The package declared 425 files. Staging and installed verification,
`bash -n`, compile/import, focused tests, and the complete 872-test Linux
suite all passed under the existing server virtual environment.

## 3. Server paths

```text
validated staging package
  /home/yangshen0711/tsc_software/stage4_2r3c3t13s21_98dc353
canonical project
  /home/yangshen0711/tsc_all/tsc_rzip_rllib
run
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s21_runs/
  stage4_2r3c3t13s21_cumulative_exact_card15_pooled_observer_campaign_20260803_024821_98dc353
logs
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/
  stage4_2r3c3t13s21_*.log
```

All Python phases used
`/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python`. No server
Git, package installation, global Python, archive transfer, or large-result
download was used.

## 4. Phase evidence

The offline gate authenticated the historical source chain, all 40 restart
contexts and snapshots, and zero prior response outcomes for the selected
20 whole pairs. Its zero-plant S20-to-S21 replay proved:

```text
first seven actions unchanged                               24 / 24
successful S20 eighth actions unchanged                     23 / 23
failed S20 eighth action repaired                            1 / 1
cumulative Decimal closure exact                            24 / 24
new raw / TSC / plant advances during offline phase          0 / 0 / 0
```

The training model was hashed before calibration opened:

```text
selected ridge                                                    0.0
maximum absolute scaled whole-pair OOF error            0.01329607898
training model SHA-256
  a685d428eebcef10d7f6a36e3e6c8ada1b4c7177b6a94d52a516b390a2c997fd
```

The calibrated tube was hashed before holdout opened:

```text
maximum scaled calibration point error                 0.02172025886
calibrated tube SHA-256
  eff9d987f46b824714456f75a2d4a602ca3f144a3009e2904c9023a33a0ade20
heldout outcomes opened before tube hash                              0
```

Fresh holdout results were:

```text
point / containment / cap / joint                         64 / 64 / 64 / 64
maximum absolute scaled point error                      0.0108949379021
maximum halfwidth R/Z/vR/vZ/Ip
  8.68831e-5 m / 4.39127e-5 m /
  0.00868831 m/s / 0.00439127 m/s / 38.36884 A
```

Probe trajectories remain forbidden from expert datasets.

## 5. Raw inventory and independent recomputation

```text
files                                                          360
bytes                                                   21,083,271
digest
  8d5a67944e344b06da89c64625d1e94adc60432db230655ec9250c339e3e50f4
training baseline / probe                                  24 / 192
calibration baseline / probe                                 8 / 64
holdout baseline / probe                                     8 / 64
```

Independent raw iteration found 360/360 matching stage, campaign,
controller, trajectory length, trace length, online solver, event schedule,
cumulative closure method, and exact-zero fields. It found zero parse
failure, abnormal trajectory, forbidden trace, or failure reason.

The independent server postprocessor exactly reproduced the frozen training
artifact, calibrated tube, and final summary:

```text
server_independent_postprocess.json
  d6bc5c3690cda4610586db6f03cf21c22d35b37d7cd82f3709572c45e5b7172e
final_result.json
  e72e66318836c11dac025b66a74682e8459d0c336dac5d0d27e54d5353c5e233
server_final_audit.json
  edaa88cc4963acf3552663959b016fc5234dee771e155fa16b26a069f66973e0
run manifest
  337b4eef13be53ed98751fbd32544f08d40611498756d944b757d7e862cd09af
final state
  01ebdfab81d8d24f96d222846a71ee23c49daafbe93c7fabe2c49cb0a2e60fd1
```

## 6. Formal-control diagnostic and route implication

Formal tracking was deliberately diagnostic for identification. A
post-campaign raw/spec-matched route forensic, explicitly retrospective and
not an S21 acceptance gate, found:

```text
baseline formal pass / fail                                16 / 24
signed probes formal pass / total                          99 / 320
failed contexts repaired by any measured probe              0 / 24
individual repairing probes                                       0
passing contexts with at least one probe regression           6 / 16
individual regressing probes                                      29
```

Thus the S21 local response observer is statistically valid over its frozen
finite envelope, but none of the eight measured state-10 signed directions
repairs any failing baseline. This is not an observer failure and does not
prove that a multi-step, relinearizing MPC is impossible. It does prove that
S21 PASS cannot itself be promoted to a control PASS or direct real-MPC
authorization.

## 7. Error classification

```text
runtime or environment error                         none
packaging, import, or deployment error               none in final package
raw or snapshot corruption                           none
statistics or reporting error                        none in final result
test not run                                          none required
identification/model result                           finite-envelope PASS
real closed-loop control result                       not an acceptance gate
plant restart conclusion                              exact in all 360 raw
global plant reachability conclusion                  not tested
```

One PowerShell-to-SSH wrapper occasionally returned a trailing-CR shell
diagnostic after the intended remote command had already completed. Direct
PID, log, state, raw, and hash checks separated that transport-wrapper issue
from the real server phases; it did not alter any run.

## 8. Frozen and unvalidated scope

Frozen:

- R17 remains the 18/18 finite static-grid source.
- R1 means Stage4.2R1 authentic plant restart; R17 means Stage4.1R17.
- R1c/R2 finite restart certifications remain unchanged.
- R3c1 remains a genuine 16/32 closed-loop controller result.
- S21 is a clean 360/360 local response-set identification PASS.
- Formal arrival remains 250/270 ms and hold remains 350/370 ms.

Not validated:

- recursive or full-horizon prediction from the S21 one-step model;
- a new restart MPC or any new real control campaign;
- independent hidden histories or unseen initial states;
- unseen targets and continuous delay/gain/slew or plant mismatch;
- measurement noise, disturbance recovery, or independent long hold;
- expert-data, BC, DAgger, or bounded residual RL readiness.

The next action is the prospectively frozen zero-new-TSC S22 full-horizon
affine authority discriminator. It asks whether the four measured state-10
signed directions have even optimistic bounded-combination authority under
the unchanged formal gate. It cannot itself authorize real MPC.

