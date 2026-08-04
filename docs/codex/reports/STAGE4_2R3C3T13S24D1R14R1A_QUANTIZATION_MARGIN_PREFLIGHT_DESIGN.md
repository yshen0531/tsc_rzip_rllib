# Stage4.2R3c3T13S24D1R14R1A quantization-margin preflight design

Frozen: 2026-08-04, after D1R14R1 was frozen as FAIL and before R1A
implementation or formal execution.

## Purpose and provenance

R1A is a zero-new-TSC exact replay of one fixed repair to D1R14R1. R1 failed
only because mixed direction 2 had Card15 off-basis residual `0.1359745`
against the unchanged `0.10` limit. A disclosed post-failure development grid
scaled only that column from `1.000` to `2.000` in steps of `0.025`; `1.275`
was the first grid value with 64/64 static passes. That grid is selection data,
not validation. R1A freezes `1.275` before implementation and exists to
authenticate and reproduce the exact candidate under a new stage identity.

R1A executes no controller, plant, Ray, gotsc, TSC, or snapshot creation. A
pass authorizes only preregistration of a fresh real-TSC D1R14R2
safety/geometry sentinel.

## Immutable source contracts

R1A first authenticates the final D1R14R1 output:

```text
package checkpoint       36f0d41
implementation checkpoint 7c4002c
output directory          stage4_2r3c3t13s24d1r14r1_pooled_mixed_basis_preflight_20260804_36f0d41_v1
detailed SHA              2342af0c58980b3da62b1bbf8b51d05d269cad0740049e687285ca0beae9e04c
summary SHA               77403c3a650b37c899bb493e8f3528c8ac14e6ad9b3121a91d1f0c5934811ca3
manifest SHA              8d572c09dcd29991c38d7da245511868a2b84e029f44684823de71cf815ea56f
R1 config SHA             e28de194bebc7b5f94257bb173c950b6799eeb80464f62f9d755d1c1aba24869
R1 implementation SHA     1c6249523b47cb65626aab9aa72874edf4100e4e38da3c0168a3db9848f5320f
required route            POOLED_MIXED_BASIS_PREFLIGHT_FAIL_REDESIGN_REQUIRED
required source/search    pass/pass
required static result    48/64; only direction-2 off-basis failures
```

R1A also independently repeats R1's D1R14 v2 raw authentication, official
geometry reproduction, and 72-file inventory check. It may not substitute the
local compact copy for the server raw.

## Frozen repair

Columns 0, 1, and 3 are byte-identical to R1. Column 2 is multiplied by the
exact binary64 result of `1.275`. The fixed requested-coordinate matrix is:

```text
 0.06036182177162116   0.06409209376301149  -0.37110098238653283   0.13657703474397473
-3.921547352685623   -3.280604324442652     4.73169603859497     -3.6727205346962286
 0.49109976246409964   0.13593338869530727  -0.035003869827120934 -0.3079668079336082
-0.18672754749097395  -0.17590787535526847  -0.08626957714716102   0.19464202995789268
```

Its C-order little-endian float64 byte SHA is
`c8cd62c00c1f60b46312927789659657dc8cc35717533193433b0e398c1ec94c`.
R1A must reproduce this exact digest from the authenticated R1 base matrix and
the single frozen multiplier. No alternate column, scale, grid, seed, search,
or adaptive refinement is allowed.

## Frozen gates

The linearized response calculation reuses the authenticated D1R14 odd
responses and original `0.25` coordinate normalization. It must retain:

```text
minimum predicted odd peak >= 0.006
maximum unit-column condition <= 4.0
```

All `8 contexts x 4 directions x 2 signs = 64` exact static Card15 issue
constructions must pass the unchanged R1 gates:

```text
dynamic exact search radius                         16
incremental normalized action                     <= 0.25
total normalized action abs                       <= 1.0
predicted current utilization                     <= 0.55
desired/applied current cosine                    >= 0.98
relative off-basis residual                       <= 0.10
exact center/target and target reproduction        required
no saturation or current clipping                  required
```

The `0.24` online cancellation limit is unchanged but remains diagnostic in
R1A because state-11 plant/readback current is unknown. Only R2 may validate
real exact stored-center cancellation and response symmetry.

## Routes and boundary

```text
R1/D1R14 source authentication failure:
  QUANTIZATION_MARGIN_SOURCE_FAIL_NO_TSC

fixed matrix, predicted geometry, or static issue failure:
  QUANTIZATION_MARGIN_PREFLIGHT_FAIL_REDESIGN_REQUIRED

all frozen gates pass:
  QUANTIZATION_MARGIN_PREFLIGHT_PASS_R2_SENTINEL_DESIGN_REQUIRED
```

Formal arrival/hold timing remains state 25/35 for normal slew and 27/37 for
weak slew; R1A does not execute formal tracking. A pass is not a plant,
transition-model, MPC, expert-policy, robustness, BC, DAgger, or RL result.
