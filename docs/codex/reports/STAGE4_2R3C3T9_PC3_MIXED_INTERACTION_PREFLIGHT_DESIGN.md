# Stage4.2R3c3T9 PC3 and mixed-interaction preflight design

## Status and purpose

This document freezes the T9 design preflight before any T9 TSC execution.
The preflight is read-only with respect to all source evidence and may write
only a compact JSON result.

T8 established that:

```text
T7 exact bounded feasibility                         16/32
repairs of failed contexts                             0/16
new-direction scale through 4x                       16/32
maximum predicted current utilization                0.3904
global rank-8 / condition-qualified old subsets       1/165
```

The remaining route therefore needs a genuinely new target-relevant temporal
direction and a direct combined-action interaction measurement. T9 must not
repeat amplitude-only extrapolation or a separable-even response model.

T9 is identification work. It is not an R3c4 controller run, formal-control
repair, independent robustness confirmation, long-hold test, or expert-data
campaign.

## Authenticated sources

The preflight must authenticate these exact inputs:

```text
R17 selected expert raw digest
95ef2cdbdbbbecdf0a58b316b44cca4fb788613b1a87c1f9b48e897175b2c112

R3c1 run inventory digest
5bb79906dff14e4128e57f80dcd36576c881b46202e68a63f8dd977777812d2f

T3 eight-basis controller bank
6328ef4116ea5a2ecac66d04583fb92af7830ad5ff6ea484486524cbd2021e86

T6 preflight
94ad5216c147a71cb5dbb907f3451f7c29d83c75394d778e1c11e3fb4112ffa7

T7 feasibility
d4dbcd4a114eec10110432d6bf4337182bcb805b27ab83d689a9e216a052ed30

T8 headroom diagnostic
5fba92cbe0690267d25a7b6f97f53c0d2144e9453420fc7945c05b29d45e18a1
```

The machine-readable contract is:

```text
configs/stage4_2r3c3t9_pc3_mixed_interaction_preflight_v1.json
```

## New temporal direction

For each public task-start actuator case:

```text
delay 0 / slew 1.0 / formal hold state 35
delay 2 / slew 0.9 / formal hold state 37
```

the preflight exactly repeats the frozen T6 construction through PC2, then
takes the third equal-context right-singular direction after removing:

```text
the old T3 eight-schedule action span
+ the R17 target-action residual
+ matched-visible PC1
+ matched-visible PC2
```

The candidate ID is:

```text
matched_visible_target_equal_pc3
```

Only issue step `i` satisfying this causal rule participates:

```text
i + delay + 1 <= formal hold state
```

PC3 is normalized and scaled by the unchanged T6 rule:

```text
min(0.015 formal-schedule L2,
    0.0075 / maximum absolute unit component)
```

Its cancellation has physical effects only at states 39 through 44, after
both immutable formal hold endpoints, and the complete requested three-mode
sum is exactly zero.

## Direct mixed-action factorial

The stress direction uses the exact T7 selected eight schedules:

```text
T3 basis 0, 1, 2, 3, 7
+ R17 target-action residual
+ matched-visible PC1
+ matched-visible PC2
```

For each actuator case, the stress coefficients are the arithmetic mean of
the exact T8 scale-one best coefficients over that actuator case's failed
contexts. This is inspected development evidence and must not be described as
independent selection.

The resulting stress schedule is frozen once per public actuator case. It
does not vary with pair, history, prefix, hidden wire state, or outcome.

The four direct combined actions are:

```text
+stress +pc3
+stress -pc3
-stress +pc3
-stress -pc3
```

One common amplitude is used for all four combinations. It is the largest
amplitude for which every combined formal schedule and every post-contract
cancellation satisfies:

```text
formal L2                         <= 0.015
formal component absolute value  <= 0.0075
cancellation component absolute  <= 0.0075
full requested net               exactly zero within 1e-12
```

These four samples support an exact discrete Walsh decomposition:

```text
intercept
stress main contrast
PC3 main contrast
stress x PC3 mixed contrast
```

The mixed contrast is directly measured. It is not reconstructed from
separable single-column even terms.

## Preflight gates

All gates are conjunctive:

```text
R17 authenticated                                           18/18
R3c1 authenticated                                          32/32
T6, T7, and T8 compact source hashes exact                    yes
T6 source/PC1/PC2 schedules reproduced within 1e-12           yes
PC3 equal-context singular value                       >= 0.5
minimum four-direction residual coverage               >= 0.95
complete action schedule rank                              12/12
selected prospective action schedule rank                    9/9
normalized action-schedule condition                         <= 3
candidate/old-span orthogonality                          <= 1e-12
PC3 mode-2 energy nonzero                                     yes
all new schedules bounded, zero-net, post-contract             yes
four factorial signs exact                                     yes
prospective task count exact                                  224
formal timing unchanged                                        yes
```

A failed preflight vetoes T9 real execution. Passing the preflight authorizes
only implementation and validation of the frozen T9 identification campaign.
It does not authorize R3c4.

## Prospective real identification matrix

If and only if the preflight and full local/server package validation pass,
the new independent real identity contains:

```text
32 contexts x (
  1 extended zero-probe baseline
  + 2 standalone PC3 signs
  + 4 stress-by-PC3 factorial combinations
)
= 224 real TSC tasks
```

The same 32 authenticated restart contexts and exact snapshot/full-wire
integrity checks remain mandatory. Every matched hidden-history pair receives
the same schedule for the same target and public actuator case.

## Frozen response and safety gates

The prospective real campaign must retain:

```text
complete / exact restart / causal                         224/224
extended baseline prefix exact                             32/32
exact standalone PC3 signed schedule                       64/64
exact factorial schedule                                  128/128
runtime / solver / clipping / forbidden-input errors            0
maximum current utilization                                  <= 0.55

standalone central even velocity RMSE                    <= 0.004 m/s
standalone central even position RMSE                   <= 0.0005 m
standalone central even Ip RMSE                              <= 20 A

matched-history PC3 odd velocity RMSE                    <= 0.006 m/s
matched-history PC3 odd position RMSE                     <= 0.001 m
matched-history PC3 odd Ip RMSE                               <= 40 A

matched-history mixed velocity RMSE                      <= 0.006 m/s
matched-history mixed position RMSE                       <= 0.001 m
matched-history mixed Ip RMSE                                 <= 40 A

selected nine-basis response rank                              9/9
selected nine-basis response condition                          <= 25
```

The linear route additionally requires, in every context:

```text
mixed velocity contrast norm / main-effect norm              <= 0.10
PC3 main-effect modulation by the stress background           <= 0.10
```

If either linearity gate fails but the mixed contrast is reproducible across
matched histories, the interaction may be retained only in a separately
specified interaction-aware model and prospective feasibility audit. It may
not be silently discarded. If the interaction is not history invariant, the
model route is vetoed.

Before any R3c4 implementation, an authenticated measured-response
feasibility audit must still achieve:

```text
formal feasibility                                          32/32
failed baseline repairs                                      16/16
baseline-pass regressions                                         0
all physical coefficients inside the frozen bounds               yes
formal timing unchanged                                          yes
```

## Immutable timing and information boundary

The formal contract remains:

```text
slew 1.0: arrive by 250 ms, hold through 350 ms
slew 0.9: arrive by 270 ms, hold through 370 ms
R/Z tolerance 30 mm
speed threshold 0.1 m/s
Ip and arrival-streak rules unchanged
```

The 500 ms identification horizon only records the post-contract
neutralization tail. It is not a long-hold validation.

Runtime may use only current/past visible R/Z/Ip, current/past 14-coil
currents, target, public causal task-start actuator values, the exact R3c1
controller, and the frozen task-clock schedule. It may not use hidden
wire/vessel currents, pair/history/prefix labels, source outcomes/actions,
another member, future values, or post-action current-step telemetry.

Probe trajectories are identification data and are forbidden from expert
datasets. This stage cannot authorize BC, DAgger, or residual RL.
