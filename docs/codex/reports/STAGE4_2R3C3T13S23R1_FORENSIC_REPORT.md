# Stage4.2R3c3T13S23R1 forensic report

## 1. Result

Stage4.2R3c3T13S23R1 completed its fixed zero-TSC amplitude-coded Hadamard
preflight twice.  The primary and independent detailed, summary, and manifest
files are byte-identical.  Independent server-side forensics then strictly
decompressed and parsed every immutable S21 raw file and recomputed every
S23R1 event and matrix gate without trusting the stored verdict.

```text
authenticated S21 raw JSON.GZ                         360 / 360
strictly parsed successful raw                        360 / 360
raw bytes                                               21083271
raw inventory digest
  8d5a67944e344b06da89c64625d1e94adc60432db230655ec9250c339e3e50f4
contexts / unique event rows                         40 / 3840
finite issue/cancel constructions                  7680 / 7680
issue action/geometry/current gates                3840 / 3840
cancel exact-center/zero-net gates                 3840 / 3840
Decimal-exact central-sign gates                   1280 / 1280
actual global rank-16 contexts                         40 / 40
actual slot rank-4 blocks                            160 / 160
new raw / snapshot / TSC / plant / controller      0 / 0 / 0 / 0 / 0
```

The certified route is:

```text
AMPLITUDE_CODED_HADAMARD_PREFLIGHT_PASS_FREEZE_S24_REQUIRED
```

This is an action-schedule and finite-coordinate PASS.  It authorizes only a
separately frozen S24 sequential identification campaign.  It is not a plant
response, controller, MPC, restart-control, expert-data, BC, DAgger, or RL
result.

## 2. Code and package identity

```text
local branch
  codex/stage4_2r3c3t13s23r1-amplitude-coded-hadamard
implementation/deployment commit
  58d212c834d81ec3f2a3b343c1cfbd7c79789e27
preregistered design commit
  ce9b9c2
config SHA-256
  ad4835a60f129423ca67a0a0a788272fb1eb916296bb10b173baca2a1275f39f
implementation SHA-256
  376cd02e05ad5862399e350ba63fbd200496937fd8881b2ade6b2e6e916860f0
design document SHA-256
  1661c1356c2e31899f8163e6861e97d2d5f8d62dd77263a1b14ef520275ca0f4
PACKAGE_MANIFEST.json SHA-256
  be092936c019bad968f9ea1889a04b1f02119e74a7d05b6d027c047d64c43c35
SHA256SUMS SHA-256
  940a3891741d8c6a4c574dc03e5dc128cd7f5081e99d1a591ecf266afa4d0e4d
declared package files
  467 plus SHA256SUMS
```

The direct, uncompressed, manifest-driven staging path was:

```text
/home/yangshen0711/tsc_software/stage4_2r3c3t13s23r1_58d212c
```

No local or remote archive was created.  Eight local `pyc` files produced by
the empty-directory test were excluded from transfer.  Staging and installed
verification both used only
`/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python`.

```text
staging declared files / pyc                         468 / 0
focused installed tests                                 7 / 7
full staging Linux suite                       901 OK, 1 skipped
full installed Linux suite                     901 OK, 1 skipped
```

## 3. Server outputs and inventory

Primary output:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
stage4_2r3c3t13s23r1_audits/
stage4_2r3c3t13s23r1_amplitude_coded_preflight_20260803_101707
```

Independent output:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/
stage4_2r3c3t13s23r1_audits/
stage4_2r3c3t13s23r1_amplitude_coded_preflight_independent_20260803_101806
```

Each contains exactly three strict JSON files:

```text
detailed bytes / SHA-256
  11848795
  2fe49067ea49551eda1341f6aff74ad6d9c3a5abc2b05e26453aae12bddc0e79
summary bytes / SHA-256
  1773
  305c4003fe5572bd6434541fe983e77422c5e44af46a925bdca6d06b9b4f2177
manifest bytes / SHA-256
  785
  c0e9f5b84f58c4435e14d01e430dec324043bc58a7b7d96d644e2edb55574bbe
```

Only the compact summaries, manifests, and logs were downloaded to
`artifacts/server_audits/stage4_2r3c3t13s23r1_20260803_101707`.  The
11.85 MB detailed file and all S21 raw remained server-side.

## 4. Independent numerical recomputation

The fixed schedule retained issue task steps `10, 13, 15, 17` and cancel
steps `11, 14, 16, 18`.  Every step had 960 independently reconstructed
events.  The 40 contexts remained split into 24 training, 8 calibration, and
8 holdout contexts, with 20 `plus_first` and 20 `minus_first` histories.

The independently recomputed worst cases were:

```text
maximum actual-coordinate error                         0.02378941552 <= 0.07
minimum active coordinate                               0.23214576831 >= 0.18
minimum desired/applied current cosine                  0.99734331973 >= 0.98
maximum relative off-basis residual                     0.06506716542 <= 0.10
maximum incremental normalized action                   0.19499332021 <= 0.25
maximum total normalized action                         0.29333333333 <= 1.00
maximum predicted current utilization                   0.39295000000 <= 0.55
maximum actual normalized global condition              2.87688004981 <= 3.00
maximum actual normalized slot condition                2.03426139188 <= 3.00
minimum actual late-column residual                     0.94280904158 >= 0.50
```

The ideal requested matrix has normalized condition `2.82842712475`; the
slightly larger `2.87688004981` value is the worst actual Card15-reconstructed
matrix.  These are different, correctly reported quantities rather than a
statistics discrepancy.

## 5. Error classification and scientific conclusion

- Runtime/environment errors: none in S23R1.
- Packaging/import/deployment errors: none; both installed verification
  layers passed.
- Raw/snapshot corruption: none; 360/360 source raw parsed and reproduced the
  frozen inventory digest.
- Statistics/reporting errors: none in the stored result.  An external
  forensic command initially searched `run/raw` instead of the nested raw
  directory and therefore saw zero files; the corrected recursive inventory
  recomputation passed.  This command error did not alter any source or
  output.
- Design result: the fixed amplitude-coded sequential action architecture
  passes its complete preflight envelope.
- Real control/plant-restart conclusion: not tested.  S23R1 executed no plant
  step and adds nothing to the already frozen R1c/R2 restart certifications.

R17 remains the 18/18 finite static-grid source.  `R1` still means
Stage4.2R1 and `R17` still means Stage4.1R17.  Formal arrival remains 250/270
ms and hold remains 350/370 ms.

## 6. Next action

Freeze S24 before implementation or response access.  S24 must execute the
exact 1,000-rollout sequential matrix, maintain whole-pair boundaries, fit a
causal state-conditioned recursive transition family from training only,
freeze it before calibration, freeze its uncertainty tube before fresh
holdout, and stop at every failed boundary.  A successful S24 remains only an
identification result; a separate prospective feasibility/MPC stage is still
required before real control.

