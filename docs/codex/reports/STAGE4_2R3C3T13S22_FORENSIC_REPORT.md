# Stage4.2R3c3T13S22 forensic report

## 1. Result

Stage4.2R3c3T13S22 completed the prospectively frozen zero-new-TSC
full-horizon affine-authority audit. It authenticated every S21 source raw,
reproduced every baseline and signed-probe formal diagnostic, completed all
40 bounded optimizations, and independently reconstructed every saved
coefficient trajectory. The optimistic affine family remained feasible in
only the same 16 contexts whose unmodified baselines already passed.

```text
S21 source raw authenticated                              360 / 360
baseline formal reproduction                               40 / 40
measured-probe formal reproduction                        320 / 320
finite four-direction constructions                         40 / 40
optimizer normal return / reported success                  40 / 40
independent coefficient and forward checks                  40 / 40
optimistic affine formal feasibility                        16 / 40
failed baselines repaired                                    0 / 24
passing baselines regressed                                   0 / 16
new raw / snapshots / TSC / plant advances               0 / 0 / 0 / 0
```

The exact route is:

```text
AFFINE_STATE10_AUTHORITY_FAIL_SEQUENTIAL_MODEL_REQUIRED
```

This vetoes the frozen single-state-10, four-direction affine response
family. It does not prove global plant unreachability and is not a real MPC
or closed-loop result.

## 2. Code and package identity

```text
local branch
  codex/stage4_2r3c3t13s22-affine-authority
implementation/deployment checkpoint
  dc4b559
S21 immutable execution source
  98dc353
```

Load-bearing deployed hashes were:

```text
S22 config
  d86478f9452ea3b4ecb285fc839195175b690825f0adfc9c225797b8e23d2f7d
S22 implementation
  9e973358e77bb377f8068ce5114063cde6ab221df77b924a86f8551a743389c6
frozen S22 design
  e05f9d6be056264b1f57c9ee77150c6b08e49bb21c5e170c91387c42327d6529
PACKAGE_MANIFEST.json
  9ac90efb1f4c45f26b4b10b5f83d240ff3bec3374087ef38a29228504657146c
SHA256SUMS
  4e992c255dfdcf8c3e72e1824ab6bcd6b572cf89ef500da68b3a15abf46411ad
```

The package declared 437 manifest files plus `SHA256SUMS`. The local clean
empty-directory deployment simulation verified 437/437 hashes and the
focused suite passed 7/7. Windows collection found 512 platform-compatible
tests; 27 pre-existing Unix-only modules could not import `resource` on
Windows. The authoritative Linux staging and installed validations closed
that platform gap: package verification, shell syntax, compile/import,
focused tests, and the complete suite all passed, with 879 passed and one
expected skip.

Installed validation log hashes:

```text
stage4_2r3c3t13s22_installed_validation_dc4b559.log
  da5b54dc29fdcc9c444029e02ac2144e0e7bc0cd4fd83568862ba340b2018bac
complete installed test log
  14c036f007cbde82712ab4492d21761954ce5bded5a81bbb0b61dd263bbb52eb
```

## 3. Server paths and execution

```text
validated staging package
  /home/yangshen0711/tsc_software/stage4_2r3c3t13s22_dc4b559
canonical project
  /home/yangshen0711/tsc_all/tsc_rzip_rllib
S21 immutable source run
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s21_runs/
  stage4_2r3c3t13s21_cumulative_exact_card15_pooled_observer_campaign_20260803_024821_98dc353
S22 audit output
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s22_audits/
  stage4_2r3c3t13s22_full_horizon_affine_authority_20260803_080437
S22 log
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/logs/nohup/
  stage4_2r3c3t13s22_full_horizon_affine_authority_20260803_080437.log
```

The audit process, PID 2552724, exited naturally after completing all 40
optimizations and was never restarted. The log hash is:

```text
6f40577282db49d8d453b9a4eab93d2c6c58e713eccdf756b615b2c10f4a4cff
```

All server Python used
`/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python`. No global
Python, server Git, package installation, network dependency, archive, or
source-raw download was used.

## 4. Source authentication and output integrity

The immutable S21 source inventory remained:

```text
raw files / bytes                                      360 / 21,083,271
raw digest
  8d5a67944e344b06da89c64625d1e94adc60432db230655ec9250c339e3e50f4
run manifest
  337b4eef13be53ed98751fbd32544f08d40611498756d944b757d7e862cd09af
final state
  01ebdfab81d8d24f96d222846a71ee23c49daafbe93c7fabe2c49cb0a2e60fd1
training model
  a685d428eebcef10d7f6a36e3e6c8ada1b4c7177b6a94d52a516b390a2c997fd
calibrated tube
  eff9d987f46b824714456f75a2d4a602ca3f144a3009e2904c9023a33a0ade20
final result
  e72e66318836c11dac025b66a74682e8459d0c336dac5d0d27e54d5353c5e233
independent S21 postprocess
  d6bc5c3690cda4610586db6f03cf21c22d35b37d7cd82f3709572c45e5b7172e
final S21 audit
  edaa88cc4963acf3552663959b016fc5234dee771e155fa16b26a069f66973e0
```

S22 compact output hashes are:

```text
detailed affine audit
  ed2a2f4c714670428c8d89026ee0a00420b59d20bfb7f82e048853dc934fd67d
summary
  3559187879dc5630f2688d0adb64b83391fc286eca14f6a531fae1c90fa4f01e
manifest
  cf09a6c520886aee46495c7885d1ad6ab8ebf18caac771cf5b401e9803a88f95
provenance digest
  a94db7429ab0b123dd4f4bd690d208b373e943b683872716dee94d9f44d3ea66
independent server raw/forward postprocess
  82f18ad41f6f03b073ced10cbd5a52154918889ab67f677856f18f3a26bea3a1
```

The independent postprocessor reopened all 360 gzip raw files in place,
recomputed their exact inventory, reconstructed every stored coefficient
trajectory from raw, and matched all 40 formal evaluations. Its first
invocation stopped before writing output because a staging-directory
`sys.path[0]` did not contain the project package; the corrected invocation
used the canonical project path and changed no scientific code, input,
optimizer, or result. The corrected temporary script hash was
`06139e2a39063b39c5d2a0a075e654028347c43ce4ffd06021fd0b02b8758564`.

## 5. Formal and physical forensics

The baseline-to-affine cross-classification is exact:

```text
baseline FAIL -> affine FAIL                              24
baseline FAIL -> affine PASS                               0
baseline PASS -> affine FAIL                               0
baseline PASS -> affine PASS                              16
minimum / maximum optimized signed margin       -0.5924995 / +0.2258494
solutions with at least one coefficient within 1e-6 of a bound       40/40
```

The independent physical-metric audit found that all 24 failed contexts are
limited by sustained R/Z position error. Four also fail the post-arrival
speed term; Ip is not limiting:

```text
failed sustained box maximum error              0.030337--0.047775 m
failed post-arrival speed margin negative                         4/24
failed post-arrival speed metric                 0.0232--0.11078 m/s
failed sustained Ip maximum error                  185.7--290.5 A
```

Only 14/40 contexts kept every measured even/non-affine residual within the
unchanged S21 component caps. Global maximum absolute even residuals were:

```text
R / Z                              0.0010937445 / 0.003682652 m
vR / vZ                            0.0250467 / 0.0307917 m/s
Ip                                               70.13325 A
```

This non-affine residual confirms that T9's interaction warning remains
relevant. It is a model-validity diagnostic, not the cause of the formal
classification: the deliberately optimistic odd-only construction already
failed 24/40.

## 6. Error classification

```text
runtime or environment error                              none
packaging, import, or deployment error                    none in final package
source raw or snapshot corruption                         none
statistics or reporting error                             none in final result
test not run                                               none required on Linux
identification model-class result                         finite optimistic FAIL
real controller or MPC executed by S22                    no
real TSC or plant advance executed by S22                 no
new plant-restart conclusion                              none
global plant-reachability conclusion                      not tested
```

The result is therefore a genuine frozen model-class/authority failure, not
a run failure and not a report bug.

## 7. Frozen and unvalidated scope

Frozen:

- R17 remains the Stage4.1R17 18/18 finite static-grid source.
- R1 remains Stage4.2R1 authentic plant-state restart.
- S21 remains a 360/360 finite local one-response-set observer PASS.
- S22 vetoes only the bounded four-direction, single-state-10 affine family.
- Formal arrival remains 250/270 ms and hold remains 350/370 ms.

Not validated:

- a sequential state-conditioned transition model;
- a new restart MPC or any new real closed-loop controller;
- independent hidden histories or unseen restart states;
- new targets, continuous delay/gain/slew, or plant/Jacobian error;
- measurement noise, disturbance recovery, or independent long hold;
- MPC expert data, BC, DAgger, or bounded residual RL readiness.

The next stage must prospectively establish safe, independently conditioned
multi-time action excitation before collecting a sequential transition
campaign. Enlarging S22 coefficients, relaxing the formal gate, or treating
the 16 unchanged baseline passes as repairs is forbidden.
