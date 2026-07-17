# Stage-1 method and assumptions

## Action semantics

The environment action is a normalized **increment** of single-turn coil current. With the current configuration:

```text
current_slew = 0.3 A/ms
dt = 10 ms
maximum increment per control step = 3 A
```

A perturbation is therefore applied at one control instant and zero increments are used afterward. The resulting current offset persists. This is deliberate: it identifies the derivative with respect to the actual control variable used by the environment, rather than a fictitious one-step current pulse.

## Local time-varying response tensor

For output state `y=(R,Z,Ip)`, injection time `k`, coil `j`, and later state time `t`, the code fits

```text
G[t,:,k,j] = d y[t] / d ΔI[k,j]
```

using perturbations at approximately `{-3,-1.5,+1.5,+3} A`, adjusted by the actual post-clipping current change. The fit is forced through the zero-action baseline. Residuals measure local nonlinearity/asymmetry.

## Spatial actuator modes

Responses from all valid injection/output times are stacked into one weighted matrix with R/Z scaled by 80 mm and Ip weakly scaled by 8000 A. SVD gives 14-dimensional spatial coil modes. These are diagnostic modes, not yet a deployed controller.

## Reachable set

The terminal local model is projected onto R/Z by support-function linear programs. Constraints include:

- per-step current-increment bounds;
- cumulative absolute coil-current bounds at every step;
- terminal Ip within the configured tolerance.

The resulting polygon is a local linear reachable-set estimate, not a global nonlinear proof.

## Constrained sequence optimization

For several spatial-mode counts and target fractions, the code minimizes a weighted quadratic objective over the late part of the 100 ms horizon. It includes terminal/late R/Z/Ip tracking, late R/Z velocity, increment regularization, and cumulative-current regularization. SLSQP enforces exact coil slew and current constraints.

## Nonlinear validation

Predicted sequences are scaled and replayed from the original start state in real TSC. The final Gate-A verdict uses only these nonlinear TSC trajectories.
