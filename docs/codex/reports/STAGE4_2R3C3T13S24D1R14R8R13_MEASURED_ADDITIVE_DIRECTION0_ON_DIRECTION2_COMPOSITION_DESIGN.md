# Stage4.2R3c3T13S24D1R14R8R13 measured additive direction-0-on-direction-2 composition design

Frozen prospectively on 2026-08-08 after final R8R12 v2 primary/independent
agreement and forensic closure, but before R8R13 implementation, additive
composition, formal metric, output, route, or any further TSC execution.

## 1. Question and boundary

R8R11 measured six safe direction-0 transient corrections per R8R7 context:
three issue times `[14,18,22]` times signs `[-1,+1]`. R8R12 then measured one
safe cumulative direction-2-positive staircase per context. Neither fixed
family repaired any of the ten failed R8R7 baselines.

R8R13 asks one bounded zero-new-TSC route question:

```text
Under an explicitly optimistic additive R/Z/Ip composition, does one single
globally fixed measured R8R11 direction-0 transient, added to the measured
R8R12 direction-2 staircase in all sixteen contexts, repair at least one
failed baseline without regressing any of the six baseline-pass contexts?
```

R8R13 is a retrospective measured-trajectory composition diagnostic. It is
not a physical combined-action result, controller, selector, model
qualification, MPC, safety test, robustness test, Gate A, or learning stage.
It runs zero Ray, `gotsc`, TSC, controller, or plant advances and creates no
raw or snapshot. All source trajectories remain forbidden from expert, BC,
DAgger, and RL datasets.

## 2. Immutable authenticated sources

Use the exact accepted R8R7 baseline bank:

```text
run
  stage4_2r3c3t13s24d1r14r8r7_fresh_multipulse_static_observer_interaction_sentinel_20260807_d8d231e_v1
stage
  stage4_2r3c3t13s24d1r14r8r7_fresh_multipulse_static_observer_interaction_sentinel
route
  FRESH_MULTIPULSE_STATIC_OBSERVER_INTERACTION_PASS_MPC_DESIGN_REQUIRED
baseline raw
  16 files / 487298 bytes
  46df626a462dfdbfe7cdf9138a50b6b19c03f0ae5e8bb18cf18c6fcbe05c01a5
final / manifest / state SHA-256
  9ca6afce52442c1b7470cb8ff13a2eac4aab32de1e05a898d206f5fe76e01005
  ae89fb2df01cd6758676baa895880e2005a1f8967c62ea4ae671ab61ea771e24
  04f643e09f414c5d5a305f1a3584450e12e5a39e8d062d454480df3c8d95fe7e
```

Use the exact final R8R11 source:

```text
run
  stage4_2r3c3t13s24d1r14r8r11_sustained_exact_target_refresh_authority_sentinel_20260807_863692b_v1
route
  SUSTAINED_EXACT_TARGET_REFRESH_AUTHORITY_INSUFFICIENT_ASYMMETRIC_SEQUENCE_REDESIGN_REQUIRED
safety raw
  24 files / 759481 bytes
  137fc4024b720b3bd105671051758d8f8ea26014250ce72a9431702af17428da
qualification raw
  72 files / 2288228 bytes
  82958eb8c4e49ff278c4223b8d2d21df9080cfadae02fd65596c727787832a09
primary detailed / summary / independent / final / manifest / state
  aecd3a9e19bc8349398d885b78f6ef6cdbb20974878571036f4062f7f8b71ce1
  8214b9c0340f5562a181a42cb2d4e30ca2f1dd79900f1089fae3422ef3531e9b
  13f4436fff270a5eba1e91790522e3a490df59a879d9bab7636a6c3dc32b7391
  903cdb4f01ff0e124081230f92be2d473e38bde8d0cc0cdb082d71f900e8f3b5
  aaa8062421b9e1a5fa92641bffdf27684229a1db31f8a1a6d98bcde997aa8107
  d805d7de4822678f17b6a814b3cb095ad59b96001db4ae81fd8e047cf8659e24
```

Use the exact final R8R12 v2 source:

```text
run
  stage4_2r3c3t13s24d1r14r8r12_causal_cumulative_direction2_staircase_authority_sentinel_20260808_523c706_v2
route
  CAUSAL_CUMULATIVE_DIRECTION2_STAIRCASE_AUTHORITY_INSUFFICIENT_SEQUENCE_REDESIGN_REQUIRED
safety raw
  4 files / 130839 bytes
  8eb94b448e30272191ebbf6440fdc5a104025d2d407ee914404cf5452fca4beb
qualification raw
  12 files / 395289 bytes
  b51d78d0fa511255d09a941861e54b8b2667dbac499ce354ee94d6bb76c16bb6
primary detailed / summary / independent / final / manifest / state
  123991e8e31d159361785666b483183a3fb31b7db540b3677e12537bc03fd88f
  93df1e3ea60b6655cc0a325aacb5d7d089e349cf42df82968b16f755a545572f
  848867b23b8fc0c9ba5723bf77e03baaf7de532119de1dd2c3d6b53cd1f1f1a4
  2a018bd023ffd4ef1d82611283ead5ac79d00479691d00929c1c95b471e0dea3
  48a0992757f4ee51dcbdf04f6cac0e32116e875d1b1c3626cb93bb9d342bc095
  e5410b24f5b60e682b93c1c411ddae88caec50d17dd23a8be67604b0e4107daf
```

Primary and structurally independent implementations must authenticate every
listed compact artifact and raw inventory before computing a composition.
They must strictly parse all 128 source raw files: 16 R8R7 baselines, 96
R8R11 candidates, and 16 R8R12 candidates. Source bytes may not be modified.

## 3. Exact context and candidate mapping

Match all sources only by the frozen physical `pair_id` and `history_member`.
The context order is the accepted R8R7/R8R12 order of eight pairs times
`minus_first, plus_first`. Pair/history labels are evaluator-only and are not
claimed as controller inputs.

R8R11 contributes the globally fixed candidate family:

```text
candidate index  issue task step  direction  scale  sign
0                14               0          1.5    -1
1                14               0          1.5    +1
2                18               0          1.5    -1
3                18               0          1.5    +1
4                22               0          1.5    -1
5                22               0          1.5    +1
```

The R8R11 issue is held through `issue+1` and exactly returns to its stored
center at `issue+2`, exactly as already executed. R8R12 contributes its one
unchanged direction-2-positive cumulative staircase at `[10,14,18,22]`.
R8R13 may not add another sign, time, scale, direction, context-specific
choice, or continuous coefficient after results are seen.

Each of the six candidates is applied conceptually to all sixteen contexts.
The diagnostic must never form a per-context oracle across the six candidates
for its scientific gate. A single global candidate must satisfy the gate.

## 4. Frozen additive construction

For a context and one R8R11 candidate, require exact common time grid, target,
horizon, and matching baseline identity. For each saved state and each of
`R`, `Z`, and `Ip`, construct:

```text
x_additive(t)
  = x_R8R12(t) + (x_R8R11_candidate(t) - x_R8R7_baseline(t))
```

Independently construct the algebraically equivalent path:

```text
x_additive_check(t)
  = x_R8R7_baseline(t)
  + (x_R8R12(t) - x_R8R7_baseline(t))
  + (x_R8R11_candidate(t) - x_R8R7_baseline(t))
```

The two constructions must agree at absolute tolerance `1e-12` for every
component/state. Velocity is derived only by the unchanged formal evaluator
from the composed R/Z trajectory; it is not independently fitted or copied.

The zero-correction identity `x_R8R12 + (baseline - baseline)` must reproduce
all R8R12 formal outcomes, selected arrival states, and signed margins exactly
within `1e-12`. R8R13 does not compose coil/wire currents, actions, hidden
state, solver flags, or safety telemetry. It therefore makes no combined-
action/current/saturation claim.

This is explicitly an optimistic separable superposition assumption.
Cross-direction plant interaction, state-dependent action representability,
simultaneous exact Card15 targets, combined current utilization, and causal
online selection remain unvalidated.

## 5. Immutable formal evaluation

Use both existing formal metric paths without changing any contract:

```text
slew 1.0/1.1: arrive no later than state 25, hold through state 35
slew 0.9:     arrive no later than state 27, hold through state 37
R/Z <= 0.03 m, speed <= 0.1 m/s, Ip <= 10000 A, arrival streak 3
metric-path absolute tolerance <= 1e-12
```

Before additive results, reproduce exactly:

```text
R8R7 matching baseline formal pass                          6/16
R8R11 candidate formal-pass trajectories                  36/96
R8R12 candidate formal pass                                6/16
R8R12 failed baselines                                       10
```

For each global additive candidate, report all sixteen formal outcomes,
selected arrival, minimum/mean signed margin, matching baseline comparison,
failed-baseline repairs, and baseline-pass regressions. Also report the
minimum/median/maximum failed-baseline signed-margin gain.

## 6. Frozen selection and scientific gate

Rank the six global candidates deterministically by:

1. formal-pass count descending;
2. repaired-failed-baseline count descending;
3. baseline-pass regression count ascending;
4. minimum failed-baseline signed-margin gain descending;
5. frozen candidate index ascending.

The first candidate is the selected diagnostic candidate. R8R13 passes only
if that same globally fixed candidate satisfies every condition:

```text
source/raw/identity/authentication gates                         PASS
zero-correction R8R12 reproduction                              PASS
two additive constructions and two formal metric paths          PASS
formal-pass count                                            >= 7/16
failed baselines repaired                                      >= 1
baseline-pass regressions                                         0
primary/independent selected candidate, numerics, gate, route   exact
new raw / TSC / plant advances                                  0/0/0
```

A pass is only evidence that an optimistic measured additive composition is
worth an exact combined-action preflight. It does not authorize a real TSC
campaign. The next prospective stage would have to construct the selected
combined direction-0/direction-2 Card15 target sequence from causal current
readback and pass every unchanged action/current/saturation/safe-stop gate
before any real sentinel could be designed.

## 7. Routes

```text
source/raw/mapping/reproduction/additive-equivalence failure
  MEASURED_ADDITIVE_DIRECTION0_ON_DIRECTION2_SOURCE_OR_INTEGRITY_FAIL_NO_TSC

all integrity gates pass but no single global additive candidate passes
  MEASURED_ADDITIVE_DIRECTION0_ON_DIRECTION2_AUTHORITY_INSUFFICIENT_NEW_SEQUENCE_IDENTIFICATION_REQUIRED

one globally fixed additive candidate passes every frozen gate
  MEASURED_ADDITIVE_DIRECTION0_ON_DIRECTION2_PASS_COMBINED_ACTION_PREFLIGHT_REQUIRED
```

R8R13 may not be rerun with a changed family or gate under the same identity.
Neither a PASS nor a FAIL is a real combined-action, controller, MPC, safety,
plant-reachability, or Gate A result. Expert data, BC, DAgger, and residual RL
remain blocked.
