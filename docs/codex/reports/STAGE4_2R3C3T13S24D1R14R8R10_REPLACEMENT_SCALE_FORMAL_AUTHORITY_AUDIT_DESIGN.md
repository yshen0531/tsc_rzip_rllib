# Stage4.2R3c3T13S24D1R14R8R10 replacement-scale formal-authority audit design

Frozen prospectively on 2026-08-07 after final R8R9 primary/independent
agreement, but before opening the context-level formal mapping of the matched
canonical and replacement-scale development trajectories described below.

## 1. Frozen question

R8R9 proved that the measured canonical-scale four-pulse alphabet repaired
none of ten failing R8R7 baselines. Earlier, R5/R6 prospectively introduced
one globally fixed and safely executed alternative: direction zero at exactly
`1.5` times canonical amplitude. R8 later repeated both amplitudes on sixteen
additional training contexts.

R8R10 asks:

```text
Across the 24 already consumed development contexts, does the measured 1.5x
direction-zero pulse provide any formal-control repair that its matching
canonical 1.0x pulse does not?
```

This is a read-only authority discriminator. It is not a model fit, controller,
MPC, fresh holdout, robustness qualification, long-hold test, Gate A, or
learning stage.

## 2. Immutable sources

R8R10 authenticates and reads the following accepted server runs in place:

```text
R4 canonical development bank
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s24d1r14r4_runs/
  stage4_2r3c3t13s24d1r14r4_time_shifted_sign_split_sentinel_20260804_f5b8348_v1
  raw: 200 files / 6,285,765 bytes
  digest: 44a7eb8e677f88f32c57a6be59273501e73f7657527371e1b59578a95c2ae7a9
  primary / independent:
    af9acfb9e524e6ad33799b832981ec7fb2e265ff7c1d3e78796413e83382db71
    6a4eec4a660beb6a29e11e184906b8b7a737834280091f1997af74e86fbd761c

R6 replacement-scale development bank
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s24d1r14r6_runs/
  stage4_2r3c3t13s24d1r14r6_direction0_replacement_sentinel_20260804_1e62c2c_v2
  raw: 48 files / 1,509,679 bytes
  digest: c743eff98395325e4da35a28d2e646aacffb00e678753ceb0faf4b86a64aeb83
  primary / independent / manifest / state:
    5c9669818249e8146b6f63d6e50e54f482cb27e64a809fb857bdf64ed617f016
    a705aa669aaafd9b6708d6915655498f3f4f443ab37683eaa5ae5a8902ae9b1f
    24ba49efa425aba83af2344df686b17c5ba37af90f21110275ac898514badf5c
    ef3da5335aa7e8ae8328ae89c4552b961438f5daf92a021562a8f4e6b350de81

R8 training-extension bank
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s24d1r14r8_runs/
  stage4_2r3c3t13s24d1r14r8_partitioned_broad_response_identification_20260804_5e57f60_v2
  raw: 624 files / 19,725,920 bytes
  digest: b5de1cabe0bd47b0d3a3b26aff04714ca0c05653483cd4c92403dc5867eeb762
  primary / independent raw audits:
    8d6e3afc0a631b144538efcfb2542596933e94c1fb8e504b2cffb04733c45ce2
    4f84c476faab515ef0a0f82c14f5547c5de957b7df31fbf3d6c228842edb0262
  manifest / state:
    67d1dc0604aa241161850578fb75c6f04bb140a1f791a5246b9f24c8d8df9f90
    9fff80668023f17d3be273f9cd9694e21b401a5f668c60c1e03508a164c6d5d3
```

The eight R4/R6 pairs and sixteen R8 training-extension contexts are already
consumed development evidence. R8 calibration and holdout remain unopened and
must not be read or created. Large raw stays on the server.

The exact canonical and replacement coordinate-matrix digests are:

```text
canonical 1.0x
  c8cd62c00c1f60b46312927789659657dc8cc35717533193433b0e398c1ec94c
replacement direction-zero 1.5x
  69528f0e204b51847c1d2a7df428555a557454e9fa6bc76768d39e7cc5a90da8
```

## 3. Frozen row matrix

Use exactly twelve whole physical training pairs, both histories per pair,
for 24 physical contexts. For each context select:

```text
one exact zero-action baseline                                      1
canonical direction zero, issue 14/18/22, signs +/-                6
replacement 1.5x direction zero, issue 14/18/22, signs +/-         6
rows per context                                                    13
selected authentic trajectories                         24 x 13 = 312
```

The first eight contexts use R4 baselines/canonical rows and R6 replacement
rows. The other sixteen use only the R8 training-extension bank. Pair and
history labels are permitted solely to establish the already frozen physical
matching; they are not controller or model inputs. No context, outcome, or
margin may select a new amplitude, direction, issue time, or sign.

## 4. Frozen computations

Every selected raw trajectory is strictly parsed and evaluated under the
unchanged formal contract through two equivalent paths:

1. the compact algebraic `FormalEvaluator.evaluate` path; and
2. the existing complete tracking-metric path used by the source campaigns.

For all 312 rows, pass, selected arrival, minimum signed margin, and mean
signed margin must agree at absolute tolerance `1e-12`.

For each context, compute three do-nothing-safe oracles:

```text
baseline                                      baseline only
canonical oracle                             baseline + six 1.0x rows
replacement oracle                           baseline + six 1.5x rows
combined oracle                 baseline + all twelve measured pulse rows
```

Candidate ordering is fixed by minimum signed margin, then mean signed margin,
then issue time, sign `-1` before `+1`, and amplitude `1.0` before `1.5`.
Report without omission:

- baseline pass and signed margins;
- each matched 1.0x/1.5x row's pass, arrival, and signed margins;
- failed-baseline repair sets for each amplitude;
- strict minimum-margin improvement counts and gain distributions;
- contexts repaired by replacement but not canonical;
- baseline, canonical-oracle, replacement-oracle, and combined-oracle counts;
- matched replacement-minus-canonical margin changes for every issue/sign;
- strata by source bank, prefix family, history, issue time, and sign.

The oracles are retrospective authority diagnostics only. They do not prove
that a causal online selector can choose the winning row.

## 5. Integrity gates

All must pass before any scientific route is emitted:

```text
exact R4/R6/R8 hashes, states, manifests, routes, and raw inventories
strict parse and finite complete trajectories                        312/312
exact context/baseline/amplitude/direction/time/sign matrix           24/24
dual formal-metric agreement                                         312/312
known complete-source formal aggregates
  R4 50/200, R6 12/48, R8 training extension 234/624
R8 calibration / holdout raw                                              0/0
new raw / Ray / gotsc / TSC / controller / plant steps              all zero
```

Source runtime, restart, prefix, Card15, current, issue/cancellation, raw,
snapshot, and forbidden-input gates must remain exactly as certified. R8R10
does not reclassify a source execution result.

## 6. Prospective scientific gate and routes

The replacement-scale authority gate requires all of:

```text
at least one failed zero-action baseline                               >= 1
failed baselines repaired by replacement 1.5x                          >= 1
replacement-oracle formal count                       > baseline formal count
replacement-only repair not achieved by matched canonical 1.0x         >= 1
combined oracle formal count                         > canonical-oracle count
```

Routes are frozen as:

```text
source/raw/matrix/formal-equivalence/known-aggregate mismatch
  REPLACEMENT_SCALE_AUTHORITY_SOURCE_OR_AUDIT_FAIL_NO_TSC

integrity passes but replacement supplies no canonical-distinct repair
  REPLACEMENT_SCALE_FORMAL_AUTHORITY_INSUFFICIENT_SUSTAINED_ACTION_REDESIGN_REQUIRED

all scientific gates pass
  REPLACEMENT_SCALE_FORMAL_AUTHORITY_PRESENT_FRESH_SENTINEL_DESIGN_REQUIRED
```

A PASS authorizes only prospective design of a fresh, hard-safe sentinel over
the later R8R7 context family. It does not authorize direct MPC execution or
reuse of the retrospective oracle. A FAIL rules out only this one-step
`1.5x` direction-zero replacement route and requires a genuinely sustained,
asymmetric, or otherwise newly identified action architecture. It does not
prove global plant unreachability.

## 7. Execution and learning boundary

Run primary and structurally independent implementations in the existing
server virtual environment under separate logs. Both independently
authenticate raw and rebuild the full 312-row formal result and route. Keep
large raw and detailed rows on the server; download only compact audits.

No local archive operation, server Git/network/global Python, source raw
mutation, TSC rerun, or probe reuse is allowed. Every R2/R4/R6/R8/R8R1/R8R7/
R8R8/R8R9/R8R10 trajectory or audit source remains forbidden from expert,
BC, DAgger, or RL datasets. Gate A and all learning remain blocked.
