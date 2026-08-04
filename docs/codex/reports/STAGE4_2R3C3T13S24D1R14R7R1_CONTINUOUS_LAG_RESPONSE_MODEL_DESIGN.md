# Stage4.2R3c3T13S24D1R14R7R1 continuous-lag response-model design

Frozen prospectively on 2026-08-04 after the D1R14R7 structural failure and
before R7R1 implementation, fitting, or route evaluation.

## Purpose and unchanged evidence boundary

R7R1 is a new-identity, zero-new-TSC causal response-model study. It consumes
the same authenticated 256 isolated responses and eight matched zero
baselines as R7. It changes only the temporal parameterization needed to
make every nested whole-pair fold defined through both the 35-state normal
and 37-state weak-slew horizons.

All R7 source inventories, causal descriptor fields, forbidden inputs,
response definition/scales, four outer whole-pair folds, nested selection
discipline, response gates, tube gates, predicted rank/condition gates,
formal-timing boundary, and scientific limitations remain unchanged.

R7R1 runs no controller, Ray, `gotsc`, TSC, or plant step. The probe raw is
forbidden from expert datasets.

## Continuous-lag model

There remain eight action heads: two signs by four fixed directions. For an
outer or inner training fold:

1. Standardize the causal issue descriptor using training contexts only,
   with floor `1e-12`.
2. Fit deterministic training-only PCA to that descriptor.
3. For every available response point, form normalized relative lag
   `tau = lag / 27`, where lag starts at one.
4. Form a Legendre temporal basis `[1, P1(t), ..., Pd(t)]` using
   `t = 2*tau - 1`.
5. Form the tensor-product feature
   `[1, PCA_context] kron [1, P1, ..., Pd]`.
6. Standardize the nonconstant feature matrix training-only and fit a
   centered multi-output ridge model for signed `[vR, vZ, Ip]` response.
7. Reconstruct R/Z exactly by 10 ms integration from zero response at the
   issue state.

Unlike R7's independent lag heads, one fitted temporal function is therefore
defined at lags 26 and 27 even if an inner training fold contains only
35-state trajectories. No future measurement, copied tail, hidden slew
label, or held outcome is used.

The complete candidate grid is fixed:

```text
PCA rank                   [2, 4, 6]
Legendre temporal degree   [2, 3, 5]
ridge                      [1e-6, 1e-3, 1e-1]
total candidates           27
```

Candidate selection uses exactly the R7 nested order: response-gate failure
count, maximum scaled point error, 95th-percentile relative L2 error, mean
squared scaled error, then PCA rank, temporal degree, and ridge order.

## Unchanged gates

Every one of the 256 nested outer predictions must pass:

```text
relative L2 error                              <= 0.75
response cosine                                >= 0.80
predicted/actual peak ratio              within [0.50, 1.50]
maximum scaled point error                      <= 0.1
```

The componentwise residual precursor remains response floor plus two times
the maximum nested out-of-fold residual and must fit inside physical caps:

```text
[0.003 m, 0.003 m, 0.01 m/s, 0.01 m/s, 1000 A]
```

All predicted branches must also pass signal 256/256 at `>=0.0025`, rank
four 64/64, and condition at most 20 for 64/64. A structurally separate
implementation must reconstruct the raw bank, nested selections, predictions,
metrics, geometry, and route within `1e-10` relative / `1e-12` absolute
numerical tolerance.

## Routes

```text
source/package/bank mismatch
  CONTINUOUS_LAG_RESPONSE_MODEL_SOURCE_FAIL_NO_TSC

undefined fold or any response/tube/geometry/independent gate failure
  CONTINUOUS_LAG_RESPONSE_MODEL_DEVELOPMENT_FAIL_BROADER_DECONFOUNDED_IDENTIFICATION_REQUIRED

all gates pass
  CONTINUOUS_LAG_RESPONSE_MODEL_DEVELOPMENT_PASS_FRESH_MULTIPULSE_VALIDATION_DESIGN_REQUIRED
```

Even a pass only authorizes prospective fresh authentic multi-pulse
superposition validation. It does not authorize MPC execution, expert data,
BC, DAgger, bounded residual RL, continuous actuator/plant variation, noise,
disturbance recovery, or long-hold claims.
