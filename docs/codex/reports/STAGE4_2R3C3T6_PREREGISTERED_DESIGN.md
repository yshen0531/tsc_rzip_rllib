# Stage4.2R3c3T6 preregistered target-residual identification design

## Status and purpose

This document freezes Stage4.2R3c3T6 before any T6 TSC execution.

T6 is a signed local-response identification campaign. It is not an R3c4
controller run, formal-control repair, independent confirmation, long-hold
test, or expert-data campaign.

The purpose is to measure three genuinely new target-relevant action
directions that are outside the authenticated Stage4.2R3c3T3 eight-schedule
span. T6 may authorize only a later server-side response-bank feasibility
audit.

## Evidence used to freeze the directions

The compact authenticated preflight is:

```text
docs/codex/audits/
stage4_2r3c3t6_new_direction_preflight_20260731_428a0bd/
stage4_2r3c3t6_new_direction_preflight_v1.json

SHA-256
94ad5216c147a71cb5dbb907f3451f7c29d83c75394d778e1c11e3fb4112ffa7
```

It authenticated:

```text
Stage4.1R17 selected expert raw                       18/18
Stage4.2R3c1 final control raw                        32/32
Stage4.2R3c3T3 controller-bank samples                32/32
T3 controller bank SHA-256
6328ef4116ea5a2ecac66d04583fb92af7830ad5ff6ea484486524cbd2021e86
```

No TSC was executed by the preflight. The first preflight implementation
stopped before output because it treated R3c1's phase-reference-conditioned
`measurement_physical` as a pure target-error field. Hotfix `428a0bd`
instead recomputed the target offset from the exact raw initial state and
frozen target specs. It changed no source data, schedule algorithm, bound,
or experiment semantics.

## Frozen candidate construction

The action coordinate is:

```text
issued_desired_physical_mode_coefficients
```

For each of the two public task-start actuator cases:

```text
delay 0 / slew 1.0 / formal hold state 35
delay 2 / slew 0.9 / formal hold state 37
```

the construction is:

1. Form the authenticated R17 `RZ_p10_m10 - nominal` expert-action
   difference.
2. Retain issue `i` only if:
   ```text
   i + delay + 1 <= formal hold state
   ```
   The last two weak-actuator issue rows therefore remain exactly zero.
3. Project outside the eight frozen T3 action schedules.
4. Normalize the resulting R17 residual as the first direction.
5. Pair R3c1 tasks that have the exact same restart snapshot, raw initial
   R/Z/Ip, and 14-coil currents, differing only in target.
6. Project each paired target-action difference outside the old eight
   schedules and the R17 residual.
7. Give all eight restart contexts equal norm, then freeze the first two
   right-singular directions. Reorthogonalize them against the old span,
   the R17 direction, and one another.

The three probe IDs are:

```text
r17_target_action_residual
matched_visible_target_equal_pc1
matched_visible_target_equal_pc2
```

Direction sign is only a deterministic storage convention because both
physical signs are executed.

## Preflight novelty result

```text
actuator                  R17 residual   matched median residual
delay 0 / slew 1.0           0.864443                  0.961088
delay 2 / slew 0.9           0.820404                  0.953291
```

For both actuator cases:

```text
old plus new schedule rank                         11/11
normalized schedule condition                    2.5511
candidate/old maximum orthogonality error        <= 1e-12
candidate count                                        3
third physical-mode energy                         nonzero
```

This proves action-schedule novelty and target relevance. It does not prove
plant-response novelty or useful controller authority; those are T6's real
identification questions.

## Frozen amplitude and timing

Each unit direction is scaled by:

```text
min(0.015 formal schedule L2,
    0.0075 / maximum absolute unit component)
```

Observed frozen bounds are:

```text
formal L2                         <= 0.015
formal component absolute value  <= 0.0075
cancellation component absolute  <= 0.002831
```

The formal schedule spans every causally effective issue row through the
unchanged hold endpoint. It is followed by an exact component-wise
neutralization at physical effect states:

```text
39, 40, 41, 42, 43, 44
```

Every signed schedule therefore has exactly 41 nonzero issue rows and
requested three-mode net zero within `1e-12`. Physical state 39 remains
strictly after both formal hold endpoints. Observation continues to state
50 only to measure neutralization; it cannot relax the arrival or hold gate.

## Frozen task matrix

The 32 existing development contexts remain unchanged:

```text
4 selected hidden-history pairs
x 2 members
x 2 targets
x 2 actuator cases
= 32 contexts
```

Each context executes:

```text
1 extended zero-probe baseline
+ 3 directions x 2 signs
= 7 tasks
```

Total:

```text
32 extended baselines
192 signed probes
224 fresh-controller, fresh-TSC tasks
```

Experiment IDs include the full signed schedule, source fingerprints,
controller revision, formal horizon, and observation horizon. A schedule,
amplitude, matrix, gate, or controller change requires a new identity.

## Controller information boundary

The online controller may use only:

- current/past visible R/Z/Ip;
- current/past 14-coil currents;
- target;
- causal task-start delay/slew/gain;
- the unchanged R3c1 controller;
- the frozen T6 schedule selected only by public delay/slew and probe ID.

It may not use:

- pair or history labels;
- hidden wire/vessel currents;
- R17 or R3c1 source actions/results;
- source coil currents;
- future actions or measurements;
- post-action current-step telemetry.

All direction derivation is offline and frozen in the hashed preflight. Probe
trajectories are identification data and are forbidden from expert datasets.

## Frozen real-identification gates

Execution and integrity:

```text
complete authenticated raw                            224/224
fresh controller and fresh TSC                        224/224
initial plant restart exact                           224/224
causal trace and exact frozen schedule                224/224
extended baseline formal prefix exact                   32/32
runtime / solver / clipping / forbidden-input errors        0
maximum current utilization                              <= 0.55
```

Central signed symmetry, for 96 context-direction groups:

```text
even velocity RMSE     <= 0.004 m/s
even position RMSE     <= 0.0005 m
even Ip RMSE           <= 20 A
```

Matched hidden history, for 48 pair-target-actuator-direction groups:

```text
odd velocity RMSE      <= 0.006 m/s
odd position RMSE      <= 0.001 m
odd Ip RMSE            <= 40 A
```

Formal-prefix response geometry, separately for all 32 contexts:

```text
new response rank / condition       3/3, <= 25
combined response rank / condition  11/11, <= 25
```

The combined matrix is the exact authenticated T3 eight-response bank plus
the three measured T6 odd responses, evaluated only at response states 3
through 35/37 inclusive. The first two response states are excluded exactly
as in the frozen T3 condition gate; post-contract neutralization cannot
improve the condition gate.

Formal tracking of baseline and signed probes is diagnostic-only. Signed
probe failure is not a closed-loop controller conclusion.

## Decision rules

- Runtime, deployment, corruption, restart, causality, reporting, response
  design, and real control conclusions must remain separately classified.
- If the 224-task campaign passes, build an authenticated eleven-basis bank
  and run a new unchanged-contract optimistic feasibility audit. Do not
  execute R3c4 directly.
- If any identification gate fails, preserve all raw and redesign without
  weakening formal timing, current, symmetry, history, or condition gates.
- A reporting-only defect may be repaired and safely resumed only when raw,
  controller semantics, schedules, experiment IDs, and source fingerprints
  remain unchanged.

BC, DAgger, and bounded residual RL remain prohibited.
