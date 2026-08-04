# Stage4.2R3c3T13S24D1R14R5 global direction-0 gain preflight design

Frozen prospectively on 2026-08-04 after final D1R14R4 primary and independent
forensics and before R5 implementation or output generation.

## Purpose and boundary

R5 is a zero-new-TSC exact safety preflight for one fixed replacement
excitation candidate. It addresses R4's only two response-signal failures
without changing the `0.005` signal floor, removing a context, or selecting an
action from pair/history/outcome labels.

R5 is not a response validation, amplitude-linearity test, online-cancellation
test, transition-model fit, MPC, controller-performance test, expert-data
stage, BC, DAgger, or RL stage. It creates no raw trajectory and advances no
plant.

## Immutable sources

The exact R4 run is:

```text
/home/yangshen0711/tsc_all/tsc_rzip_rllib/stage4_2r3c3t13s24d1r14r4_runs/
stage4_2r3c3t13s24d1r14r4_time_shifted_sign_split_sentinel_20260804_f5b8348_v1
```

R5 must authenticate before candidate evaluation:

```text
R4 raw count / bytes                       200 / 6,285,765
R4 raw inventory digest
  44a7eb8e677f88f32c57a6be59273501e73f7657527371e1b59578a95c2ae7a9
R4 primary SHA-256
  af9acfb9e524e6ad33799b832981ec7fb2e265ff7c1d3e78796413e83382db71
R4 independent SHA-256
  6a4eec4a660beb6a29e11e184906b8b7a737834280091f1997af74e86fbd761c
R4 package fingerprint
  c9c6fc870618ecbefe1bf9891a6f918927c2062753e2750596d2e73ec7ecf523
R4 spec digest
  080a2df84c86801d76251853a165839e8db59f6614f6b2b446141b0691841059
R4 requested-matrix digest
  c8cd62c00c1f60b46312927789659657dc8cc35717533193433b0e398c1ec94c
```

It must independently reproduce R4's 200/200 safety result, 254/256 signal,
64/64 rank, 64/64 condition, the two exact failed experiment IDs and peaks,
and the official geometry-failure route. Any mismatch stops before candidate
evaluation.

## Fixed candidate

The sole candidate is chosen once and is not searched in R5:

```text
source columns                    R4 pooled mixed columns 0--3
scaled column                     pooled_mixed_0 only
fixed scale                       1.5
unchanged columns                 pooled_mixed_1/2/3
new issue times                   14, 18, 22
context-dependent selection       forbidden
history/pair-label selection      forbidden
sign-dependent magnitude          forbidden
candidate matrix float64-LE-C SHA-256
  69528f0e204b51847c1d2a7df428555a557454e9fa6bc76768d39e7cc5a90da8
```

The exact candidate matrix columns are:

```text
[[ 0.09054273265743173,  0.06409209376301149, -0.37110098238653283,  0.13657703474397473],
 [-5.882321029028434,   -3.280604324442652,    4.73169603859497,    -3.6727205346962286 ],
 [ 0.7366496436961495,   0.13593338869530727, -0.035003869827120934,-0.3079668079336082 ],
 [-0.2800913212364609,  -0.17590787535526847, -0.08626957714716102, 0.19464202995789268]]
```

The factor provides a prospective margin over the two observed R4 weak
responses, but `1.5 * response` is diagnostic only. No predicted response is
an acceptance gate because amplitude linearity has not been validated.

## Zero-TSC replay matrix

Only the eight authenticated R4 zero-baseline trajectories may provide the
visible measured coil-current centers used by the static issue constructor.
Signed-probe outcomes, future trajectory values, source actions, source wire
currents, and hidden wire/vessel currents are forbidden construction inputs.

For each of eight contexts, issue times 14/18/22, and signs +/-1, R5 evaluates
the same fixed scaled direction 0:

```text
8 contexts x 3 issue times x 2 signs = 48 static issue constructions
new raw / controller / plant / Ray / gotsc / TSC = 0
```

The ideal stored-center return is evaluated as a static actuator prediction
only. It does not claim the state reached after a real issued action and cannot
validate causal online cancellation.

## Frozen gates

All 48 constructions must pass:

```text
finite requested/actual quantities                         required
exact fixed candidate and sign                             required
exact Card15 center and target                             required
target reproduction by actuator primitive                 required
no saturation or current clipping                         required
incremental normalized issue action                    <= 0.25
ideal stored-center return increment                    <= 0.24
total normalized action abs                              <= 1.0
predicted current utilization                            <= 0.55
desired/applied current cosine                           >= 0.98
relative off-basis residual                              <= 0.10
positive/negative issued coordinate and field antipodes    24/24
```

The implementation must fail closed on source, design-document, package,
config, candidate-matrix, inventory, or output fingerprint drift. A separate
implementation must recompute the source authentication, matrix construction,
48 actuator cases, and routes without importing the primary audit module.

## Routes

```text
source or R4 reproduction mismatch
  GLOBAL_DIRECTION0_GAIN_PREFLIGHT_SOURCE_FAIL_NO_TSC

any candidate exactness/action/current/quantization gate fails
  GLOBAL_DIRECTION0_GAIN_PREFLIGHT_SAFETY_FAIL_REDESIGN_REQUIRED

all frozen gates pass
  GLOBAL_DIRECTION0_GAIN_PREFLIGHT_PASS_REAL_SENTINEL_DESIGN_REQUIRED
```

A pass authorizes only prospective design of a new-identity authentic TSC
sentinel containing all 8 contexts x 3 issue times x 2 signs for the fixed
scaled direction. That later sentinel must independently validate real online
cancellation and replace direction 0 in the full 64-branch/256-column bank
before any response-model fit can be designed. MPC, expert data, BC, DAgger,
and bounded residual RL remain blocked.
