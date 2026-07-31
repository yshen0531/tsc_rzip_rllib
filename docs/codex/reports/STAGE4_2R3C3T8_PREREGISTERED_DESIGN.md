# Stage4.2R3c3T8 measured-current headroom diagnostic design

Frozen after the final T7 failure and before any T8 optimization or output
creation. T8 is a route discriminator, not a validation stage.

## Question

T7 repaired the selected response matrix condition number on all 32 locked
development contexts, but the unchanged `[-1,1]` envelope repaired none of
the 16 failed baselines. All three new target-direction coefficients
saturated in nearly every failed context.

T8 asks whether allowing only those three newly measured directions a
larger common coefficient envelope could close the optimistic formal
margins while a linear model built from authentic coil-current trajectories
remains below the existing `0.55` current-utilization limit.

The five inherited T3 directions stay in `[-1,1]`. The target-direction
scale grid is frozen as:

```text
1.00, 1.25, 1.50, 2.00, 3.00, 4.00
```

Scale 1.00 must reproduce T7 exactly. It remains a failure even if a later
scale gives a favorable diagnostic.

## Current model

For every selected response and every context, T8 authenticates the exact
plus/minus raw files named by the T7 audit bank and constructs:

```text
delta_current_i = (current_plus_i - current_minus_i) / 2
predicted_current = authentic_T6_baseline_current
                    + sum(c_i * delta_current_i)
```

The calculation uses all 14 coils, all states through the immutable formal
horizon, the actual asymmetric per-coil current limits from the resolved
environment, and the unchanged utilization definition. The maximum allowed
predicted utilization is `0.55`.

The signed-pair current midpoint is compared with the authentic T6 baseline.
The maximum permitted normalized mismatch is `0.0013`; this threshold was
frozen after the pre-design data-shape check exposed at most `0.25 A`
cross-run/current-quantization mismatch.

This current model is an odd linear diagnostic. It does not establish plant
response linearity at coefficients above one.

## Authentication and optimization

T8 binds the exact T7 manifest, audit bank, controller bank, feasibility
result, config and tool hashes; the T6 config, runtime source, raw count and
raw inventory; and the frozen formal evaluator.

For scales above one, each failed context uses the same exhaustive ternary
corner grid and per-endpoint multistart SLSQP structure as T7, with a linear
constraint covering every predicted state/coil current. No pair or hidden
history label may alter bounds, basis choice or scale.

The immutable arrival and hold deadlines, R/Z tolerance, speed threshold,
Ip gates and arrival streak are unchanged.

## Interpretation fixed before result

- If no scale through 4 repairs all 16 failures, measured target directions
  are insufficient even under an optimistic fourfold extrapolation; the
  next real identification must add new target-relevant temporal/actuator
  authority and combined-action nonlinearity measurement.
- If a scale above one repairs all failures within predicted current limits,
  this exposes only a candidate amplitude/combined-action identification
  route. It does not validate that amplitude, authorize R3c4, or establish a
  controller.
- A predicted current pass cannot validate plant linearity. A response
  extrapolation is not a real TSC result.

T8 runs no Ray, `gotsc`, TSC process, plant advance or snapshot. Probe data
remain identification-only and are forbidden from expert datasets. BC,
DAgger and residual RL remain prohibited.
