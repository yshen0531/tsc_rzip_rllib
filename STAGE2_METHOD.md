# Stage2 method

## 1. Why three modes

Stage1.1 established that the first three SVD actuator modes are stable and physically meaningful:

- mode 1: mainly vertical response;
- mode 2: mainly radial response;
- mode 3: mainly Ip/flux and weak coupled correction.

They retain about 99.94% of the weighted response energy, while the fourth mode is poorly conditioned and unstable under response-data resampling. Stage2 therefore fixes the control space to these three modes.

## 2. Time parameterization

The optimization vector contains modal coefficients at control steps:

```text
0, 2, 4, 6, 9
```

for each of three modes. Piecewise-linear interpolation produces modal coefficients for all ten control steps. The mode matrix then maps these coefficients to fourteen TSC-order coil increments.

Per-step coil action is radially scaled if any normalized coil increment exceeds ±1. A second scalar repair preserves the modal direction if an absolute current limit would otherwise be crossed. Under the Stage1.1 operating point the absolute limits are expected to remain inactive; the code nevertheless enforces them.

## 3. Initial seeds

Generation 0 always includes:

- the five-node least-squares approximation of SVD3 ×0.75;
- SVD3 ×0.85;
- SVD3 ×1.00;
- an early-strong / late-soft profile;
- a moderate taper;
- a stronger late-braking search seed;
- zero action.

The Gaussian population is centered at SVD3 ×0.85, with larger initial variance at the late time nodes because the unresolved Stage1.1 problem is primarily terminal braking.

## 4. Linear pre-screen

For each Gaussian sample the Stage1.1 response tensor predicts the R/Z/Ip trajectory. This model ranks only:

- late and terminal R/Z position;
- terminal Ip;
- action magnitude and smoothness;
- action-repair amount.

The model does not use predicted velocity because Stage1.1 showed that millimetre-scale adjacent-state errors can reverse the inferred 10 ms velocity trend.

The default proposal pool is 768. The best model-ranked proposals plus a 25% random subset form the 192 real-TSC population. All named seeds are mandatory. The random fraction prevents the position model from suppressing potentially useful braking trajectories.

## 5. Real-TSC tiers

Every selected candidate is run from the original 1100 ms TSC restart through 1200 ms.

Candidates are ordered by physical tiers:

1. `PASS_PRECISE_HOLD_30MM`
2. `PASS_DAMPED_HOLD_40MM`
3. final 30 mm position streak but speed failure
4. final 40 mm position streak but speed failure
5. at least 50% terminal drift reduction versus zero action
6. all remaining successful candidates

Within a tier, a continuous objective ranks position excess, late/terminal position, terminal and late speed, Ip, action magnitude, action smoothness, and repair amount.

Before a strict 30 mm candidate exists, 25% of the CEM elites are selected by continuous objective across tiers. This prevents the relaxed 40 mm seed population from completely excluding closer but initially underdamped trajectories. After a strict candidate is found, elite selection becomes purely gate ordered.

## 6. CEM update

The 15-dimensional Gaussian uses full covariance so the optimizer can learn:

- correlations between R, Z, and Ip modes;
- correlations between early acceleration and late braking nodes;
- coordinated temporal shaping.

Default update:

```text
population             192
elite count             24
mean update fraction    0.70
covariance update       0.55
diagonal shrinkage      0.10
max generations           8
```

Covariance eigenvalues are clipped to avoid collapse or numerical explosion. Antithetic sampling reduces random directional bias.

## 7. Stop rule

The run stops after eight generations, or after a strict 30 mm hold has been found and two further generations fail to improve the best selection score.

The optimizer does not stop merely because a relaxed 40 mm hold is found; that result was already available before Stage2.

## 8. Confirmation

The top three unique trajectories across all generations are rerun twice each. A confirmed precise pass requires all repeats of at least one trajectory to pass:

```text
final three samples inside |R error| <= 30 mm and |Z error| <= 30 mm
terminal R/Z speed <= 0.10 m/s
late R/Z speed RMS <= 0.10 m/s
terminal |Ip error| <= 10 kA
```

This confirmation is intentionally separate from the CEM generation update.
