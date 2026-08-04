# Stage4.2R3c3T13S24D1R14R1 pooled mixed-basis preflight design

Frozen: 2026-08-04, before R1 implementation or formal execution.

## Purpose and scientific boundary

R1 is a deterministic, zero-new-TSC development preflight. It consumes all 72
immutable D1R14 v2 trajectories to determine whether one fixed amplified
four-direction mixture can repair the observed weak coil-8 direction and
conditioning problem while remaining exactly constructible and safe at each
of the eight authenticated state-10 centers.

R1 executes no controller, plant, Ray, gotsc, TSC, restart, or snapshot
creation. Linear superposition of consumed odd responses is only a prospective
design calculation. A pass authorizes only a separately frozen fresh-TSC R2
safety/geometry sentinel. It does not validate symmetry, cancellation after a
new plant response, transition identification, MPC, expert data, BC, DAgger,
or residual RL.

## Immutable source

The only response source is D1R14 v2 package `d32761c`:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3t13s24d1r14_runs/
stage4_2r3c3t13s24d1r14_zero_baseline_signed_excitation_sentinel_20260804_d32761c_v1
```

R1 must authenticate before reading response values:

```text
raw files / bytes     72 / 2,239,479
raw digest            0433a64ebaea73186bb193d5102686721497219acfcbecbb721e7fad62e8d7a3
final SHA             1a65a37c301ba52325f586e0948b0b94b1266c540e2f2a332e5bc02df60a7da2
independent audit SHA 8e7d3d045477502c1060fe621f2c43235e1d530b59c5d22849337dd20aac3eae
specification SHA     23dec361cb846a9c7a7f762d166deffa6888b32f7264b146bc00e422b435a9d0
stage manifest SHA    5ffeb671df1f15e31fa49bdbe89890b9bfdaa54ff9261931e59d25b0b0f33eb5
stage state SHA       002aa3e16cf2d444cb4481f704750274afb87e6fdf63e88fc32651d19dda82e5
final route           ZERO_BASELINE_EXCITATION_GEOMETRY_FAIL_REDESIGN_REQUIRED
```

The source config SHA is
`d455cd12fca44e5e748d58f23827927e2c25c44b3f0bb2bb401b338f6268f978`.
The accepted D1R14 implementation SHA is
`bd84cd16af8cf3a2a3abf2f0defb76bb352e57900da3b825f3c8529446e47e6c`.
The inherited lattice config SHA is
`5e9425977daebe7f667591f4ad1bdd5f7ebc8ae4e19d78be9624c547e4647e2a`.

All 72 gzip JSON files must parse strictly, match the final inventory by name,
size, and SHA, report completion/success, and reproduce the official D1R14
geometry exactly before the redesign calculation is accepted.

## Frozen response construction

For each of eight contexts and four original directions, normalized visible
outputs are `[R/0.03, Z/0.03, vR/0.1, vZ/0.1, Ip/10000]`, centered at state 10
and observed from state 11 through the unchanged 35/37-state horizon. Let
`A_c` contain the four flattened odd columns `(positive-negative)/2`. Each
column corresponds to the original requested coordinate amplitude `0.25`.

The pooled Gram matrix is the arithmetic mean of `A_c.T @ A_c` over the eight
contexts. Its symmetric eigendecomposition defines the inverse-square-root
whitener `B`. The search is fixed as follows:

```text
NumPy generator             default_rng
seed                        140042
candidate count             60000
candidate k                 B @ Q_k
Q_k                         QR of one 4x4 standard-normal draw
column normalization        divide by maximum absolute coefficient
objective                   max context unit-column condition
                            + 10000 * max(0, 0.005 - minimum odd peak)
tie order                   objective, max condition, -minimum peak, index
expected selected index     35377 (zero based)
```

No alternate seed, restart, optimizer, adaptive refinement, or post-result
manual rotation is allowed. The selected columns are independently amplified
so their minimum predicted odd peak across all eight contexts is exactly
`0.006`. The prospective gate is minimum predicted odd peak at least `0.006`
and maximum unit-column condition at most `4.0`; the real R2 gate remains the
original minimum `0.005`, symmetry ratio at most `0.5`, rank four, and
condition at most `20`.

The frozen requested-coordinate matrix, with candidate directions in columns,
is:

```text
 0.06036182177162116   0.06409209376301149  -0.2910595940286532    0.13657703474397473
-3.921547352685623   -3.280604324442652     3.711134147917624    -3.6727205346962286
 0.49109976246409964   0.13593338869530727  -0.027454015550683088 -0.3079668079336082
-0.18672754749097395  -0.17590787535526847  -0.06766241344875375   0.19464202995789268
```

Its C-order little-endian float64 byte SHA is
`bfe35863262ed12aac303de14341c42c701188481d412c414915a2b4eb6e4bb8`.
Recomputed floating values must agree within `5e-10`; the configured byte
matrix and digest remain the exact R2 design input.

## Exact static Card15 issue preflight

For each context, R1 authenticates the common state-10 current, zero baseline
action, exact state-10 Card15 center, fixed 14-by-4 field basis, payload turns,
current limits, and slew. It constructs all `8 contexts x 4 columns x 2
signs = 64` proposed issue actions using the same dynamic nearest exact Card15
search radius 16 and `exact_stored_center_action` path used by D1R14 v2.

Every construction must pass:

```text
finite and exact Card15 center/target
target reproduction by the quantized actuator
no action saturation or current clipping
incremental normalized action <= 0.25 from the exact zero baseline action
total normalized action abs <= 1.0
predicted current utilization <= 0.55
requested/actual field direction cosine >= 0.98
relative residual outside the fixed four-direction span <= 0.10
```

The maximum online cancellation increment remains `0.24`, but R1 cannot know
the state-11 plant/readback current for a new mixed issue without executing
that issue. Therefore cancellation is explicitly diagnostic only: the
linearized estimate must be reported, not used as proof. R2 must independently
enforce exact stored-center cancellation, the `0.24` online cancellation cap,
zero target-jump net, and all original safety gates before advancing TSC.

## R1 routes

```text
source/authentication failure:
  POOLED_MIXED_BASIS_SOURCE_FAIL_NO_TSC

deterministic search, predicted geometry, or static issue failure:
  POOLED_MIXED_BASIS_PREFLIGHT_FAIL_REDESIGN_REQUIRED

all frozen R1 gates pass:
  POOLED_MIXED_BASIS_PREFLIGHT_PASS_R2_SENTINEL_DESIGN_REQUIRED
```

Regardless of route, new raw count, plant steps, controller calls, Ray calls,
gotsc calls, and TSC calls must all be zero. Formal timing is unchanged:
arrive by state 25/27 and hold through state 35/37. R1 itself does not execute
or evaluate formal tracking.
