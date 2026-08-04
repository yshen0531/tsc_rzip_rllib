# Stage4.2R3c3T13S24D1R14R6 real-TSC direction-0 replacement sentinel design

Frozen prospectively on 2026-08-04 after final D1R14R5 primary and
independent evidence and before R6 implementation, spec generation, raw, or
TSC execution.

## Purpose

R6 is one fresh authentic TSC safety and response-geometry sentinel for the
single globally fixed direction-0 candidate that passed R5. It tests whether
the candidate has sufficient real response signal at task steps 14, 18, and
22 and whether its causal stored-center cancellation is safe.

R6 is not a search, model fit, MPC, expert controller, expert-data campaign,
BC, DAgger, or RL stage. The 48 probe trajectories are development data and
are forbidden from any expert dataset.

## Immutable source chain

R6 must authenticate, before any TSC rollout:

1. D1R14R5 compact evidence and primary/independent result hashes.
2. All 200 R4 raw files, specs, variants, state, manifest, logs, and primary
   and independent result hashes.
3. All 72 R2 raw files and their frozen source/restart/snapshot closure.
4. The exact R4 source controller and D1R13/D1R11 restart chain used to create
   each causal prefix.

The frozen source facts are:

```text
R5 fixed candidate digest
  69528f0e204b51847c1d2a7df428555a557454e9fa6bc76768d39e7cc5a90da8
R5 compact evidence SHA-256
  930a36087efca7fb1a6ffa7ce31f76835db48ffd56154a38bd282f7316c2d6ad
R5 primary detailed SHA-256
  deb57e9c774ef792ed9f8464987e4528b69f3876a09dcd7ff4ca55ea8d9dedc9
R5 independent SHA-256
  306fd16a65ad44bea1972fb37f4ce316363eeff8a3834ceea8973afe1f42f3cb
R4 raw count / bytes / digest
  200 / 6,285,765 /
  44a7eb8e677f88f32c57a6be59273501e73f7657527371e1b59578a95c2ae7a9
R2 raw count / bytes / digest
  72 / 2,254,876 /
  c210f959e5ce85739dd0b1f70a2513f64f40c6697d01bf7b56db9621759a1649
```

Any mismatch stops before TSC. R4 and R2 raw are read-only and may not be
resumed or relabelled.

## Fixed real-rollout matrix

R6 creates exactly:

```text
8 authenticated contexts
x 3 issue task steps: 14, 18, 22
x 2 signs: +1, -1
= 48 fresh authentic TSC/controller rollouts
```

There is no new baseline rollout. Each R6 response is differenced against the
exact authenticated R4 zero-baseline trajectory for the same context. The R6
probe must reproduce the same source prefix and issue-state current center as
that R4 baseline before applying the new fixed pulse.

The exact four-column coordinate matrix remains:

```text
[[ 0.09054273265743173,  0.06409209376301149, -0.37110098238653283,  0.13657703474397473],
 [-5.882321029028434,   -3.280604324442652,    4.73169603859497,    -3.6727205346962286 ],
 [ 0.7366496436961495,   0.13593338869530727, -0.035003869827120934,-0.3079668079336082 ],
 [-0.2800913212364609,  -0.17590787535526847, -0.08626957714716102, 0.19464202995789268]]
```

Only column 0 is executed in R6. The candidate, amplitude, issue time, and
sign are fixed by the spec. No context/history/pair label, source outcome,
future measurement, source/current wire current, hidden vessel state, or
current-run future value may select or change an action.

## Controller and causal action contract

For each rollout:

1. Reproduce the exact causal source controller/state/action/trace prefix
   through task step 9.
2. From task step 10 until the scheduled issue step, command exactly zero
   incremental normalized action.
3. At the scheduled issue step, construct the exact signed Card15 target from
   the current measured coil-current center and the fixed direction-0 field
   basis.
4. At the next task step, causally return to the stored issue center using
   only current visible coil currents and controller-owned stored state.
5. From two steps after issue through the unchanged 35/37-state horizon,
   command exactly zero incremental normalized action.

The controller may use its fixed schedule, sign, fixed field basis, current
visible observation, current measured coil currents, and controller-owned
past state. It may not use `pair_id`, `history_member`, prefix labels, source
actions/results, raw trajectories, future actions/measurements, hidden wire or
vessel currents, or source/current wire-current files.

## Per-rollout gates

All 48 fresh raw results must strictly parse and pass:

```text
completed and success=true                                  48/48
real gotsc evidence and full expected trajectory            48/48
exact source spec/restart snapshot identity                 48/48
exact visible/source action/trace prefix                    48/48
exact zero pre-issue continuation                           48/48
exact scheduled candidate coordinate and sign               48/48
exact Card15 center and target                              48/48
target reproduction                                         48/48
causal stored-center cancellation                           48/48
exact zero post-cancellation continuation                   48/48
finite R/Z/Ip, coil currents, and wire-current records      48/48
runtime / solver / plant-abnormality errors                      0
saturation / current clipping / forbidden-input reads            0
```

Frozen action/current gates are:

```text
issue incremental normalized action linf                  <= 0.25
causal cancellation incremental action linf               <= 0.24
original cancellation cap                                 <= 0.25
total normalized action abs                               <= 1.0
maximum current utilization                               <= 0.55
desired/applied current cosine                            >= 0.98
relative off-basis residual                               <= 0.10
```

Positive and negative R6 issue coordinates and actual physical field deltas
must be exact antipodes for all 24 context/time pairs.

## Combined response-geometry gate

Only after all R6 safety/raw gates pass, construct one fixed 256-column bank:

```text
issue step 10, directions 0--3, signs +/-       immutable R2:  64 columns
steps 14/18/22, directions 1--3, signs +/-      immutable R4: 144 columns
steps 14/18/22, direction 0, signs +/-                 R6:  48 columns
                                                         total: 256 columns
```

For each of 8 contexts x 4 issue times x 2 signs, the four signed response
directions are kept separate. Each response begins at the first physical
effect state `issue_task_step + 1`, is normalized by its own nonzero L2 norm
for conditioning, and uses the unchanged five-output scaling:

```text
R / 0.03 m
Z / 0.03 m
vR / 0.1 m/s
vZ / 0.1 m/s
Ip / 10000 A
```

Frozen gates are:

```text
finite nonzero response columns                              256/256
peak normalized five-output response >= 0.005               256/256
rank four at relative SVD tolerance 1e-10                     64/64
condition number <= 20                                        64/64
exact issue coordinate/physical-field antipodality           128/128
```

Cross-time, cross-sign, and matched-hidden-history response differences are
reported but are not symmetry acceptance gates. They must remain explicit
inputs to later model architecture decisions.

## Formal timing and scientific boundary

Formal tracking is recomputed from every R6 raw trajectory but remains
diagnostic only. The immutable contract is unchanged:

```text
slew 1.0/1.1: arrive by 250 ms, evaluate through 350 ms
slew 0.9:     arrive by 270 ms, evaluate through 370 ms
R/Z <= 30 mm, speed <= 0.1 m/s, Ip threshold and streak unchanged
```

The 35/37-state horizon does not expand the arrival deadline and is not an
independent long-hold test.

## Routes

```text
source/package/spec/preflight mismatch before rollout
  DIRECTION0_REPLACEMENT_SENTINEL_SOURCE_FAIL_NO_TSC

any runtime/raw/restart/action/cancellation/safety failure
  DIRECTION0_REPLACEMENT_SENTINEL_EXECUTION_OR_SAFETY_FAIL_STOP

all 48 safe, but any combined signal/rank/condition/antipodality gate fails
  DIRECTION0_REPLACEMENT_SENTINEL_GEOMETRY_FAIL_REDESIGN_REQUIRED

all frozen gates pass
  DIRECTION0_REPLACEMENT_SENTINEL_PASS_MODEL_FIT_DESIGN_REQUIRED
```

A pass authorizes only a separately preregistered causal transition-model fit
and held-out validation using the authenticated finite response bank. It does
not authorize MPC execution, expert data, BC, DAgger, or RL.

