# Stage4.2R3c3T13S24D1R14R7R2 action-conditioned full-history kernel design

Frozen prospectively after the final R7R1 result and its explicitly labelled
post-result diagnostics, but before R7R2 implementation, fitting, candidate
selection, or route evaluation.

## Purpose and evidence boundary

R7R2 is a new-identity, zero-new-TSC causal response-model development audit.
It addresses three concrete R7/R7R1 defects without changing any response,
tube, geometry, formal-timing, or scientific acceptance threshold:

1. R7's independent lag heads were undefined at lags 26/27 in one nested
   fold.
2. R7R1's linear context tensor underfit held physical pairs.
3. Both models omitted the already revealed request magnitude even though the
   selected direction-zero bank combines exact `1.0x` and `1.5x` requests.

R7R2 authenticates all 320 immutable R2/R4/R6 raw files and uses the complete
304 signed responses:

```text
R2 state-10, four directions, two signs, eight contexts        64
R4 states 14/18/22, four directions, two signs, eight contexts 192
R6 states 14/18/22, direction zero, two signs, eight contexts   48
total                                                           304
```

Every response is still the signed rollout minus its exact matched zero
baseline. R2 supplies state-10 baselines and R4 supplies the later baselines.
The source raw is read in place. No controller, Ray, `gotsc`, TSC, or plant
step runs, and no new raw is created. Probe trajectories remain forbidden
from expert datasets.

## Causal predictor

Pair, history, prefix, target ID, regime ID, delay/slew labels, source
outcomes, source actions, coil/wire-current files, current-run future values,
future actions, and future measurements are forbidden.

For an issue state `t` in `{10,14,18,22}`, the allowed context is fixed before
the requested probe is applied:

1. Normalize visible `[R,Z,vR,vZ,Ip]` by
   `[0.03,0.03,0.1,0.1,10000]`.
2. Take lag-relative offsets `0..22` as
   `visible[max(0,t-offset)]`; this includes the complete current-run visible
   history back to state zero and left-pads only with the already observed
   state zero.
3. Add a 23-element availability mask `offset <= t`.
4. Add numeric target offsets normalized by `[0.03,0.03,10000]` and normalized
   task clock `(t-10)/12`.
5. Authenticate the requested coordinate against its frozen direction,
   sign, and matrix digest and add only its revealed scalar magnitude:
   `1.0` for R2/R4 and `1.5` for R6 direction zero.

The descriptor contains no hidden physical label and no future value.

## Nonlinear per-lag model and fixed tail

There remain eight action heads: two signs by four directions. Within each
outer or inner training fold:

1. Standardize the causal context descriptor using training rows only with
   floor `1e-12`.
2. Fit deterministic training-only PCA.
3. Append the standardized revealed request magnitude.
4. For every observed relative lag, fit an RBF kernel ridge head for signed
   `[vR,vZ,Ip]`. Bandwidth is the positive training median distance times the
   candidate multiplier, with floor `1e-12`.
5. If a requested held horizon exceeds the longest training horizon, first
   predict every available lag head, then fit a fixed degree-two polynomial
   separately to the last eight predicted `[vR,vZ,Ip]` values and evaluate
   only the missing lags 26/27. No held value or copied future tail is used.
6. Reconstruct R/Z by exact 10 ms integration from zero response at the issue
   state.

The complete candidate grid is frozen:

```text
PCA rank                    [4, 8, 12]
RBF median multiplier       [0.5, 1.0, 2.0]
kernel ridge                [1e-6, 1e-3, 1e-1]
total candidates            27
```

Candidate selection remains nested by whole physical pair. The score order is
response-gate failure count, maximum scaled point error, 95th-percentile
relative L2, mean squared scaled error, then PCA rank, bandwidth multiplier,
and ridge order. A final all-data fit is a development artifact, not a
validation result.

## Unchanged response and tube gates

Every one of the 304 nested outer predictions must pass:

```text
relative L2 error                              <= 0.75
response cosine                                >= 0.80
predicted/actual peak ratio              within [0.50, 1.50]
maximum scaled point error                      <= 0.1
```

The residual precursor is the unchanged physical floor plus two times the
maximum componentwise nested out-of-fold residual. It must fit inside:

```text
[0.003 m, 0.003 m, 0.01 m/s, 0.01 m/s, 1000 A]
```

Predicted signal must pass `304/304` at `>=0.0025`. Rank four and condition
at most 20 must pass both fixed branch families:

```text
canonical 1.0x branches
  R2 at state 10 plus all R4 directions at states 14/18/22    64/64

operational replacement branches
  R2 at state 10; R6 1.5x direction zero plus R4 directions
  one through three at states 14/18/22                         64/64
```

The independent implementation must reconstruct source authentication, all
304 response rows, causal descriptors, request scales, nested selections,
tail predictions, metrics, both geometry families, and the route within
`1e-10` relative / `1e-12` absolute tolerance.

## Routes and limitations

```text
source/package/bank/request mismatch
  ACTION_CONDITIONED_FULL_HISTORY_SOURCE_FAIL_NO_TSC

any response/tube/signal/geometry/independent failure
  ACTION_CONDITIONED_FULL_HISTORY_MODEL_FAIL_NEW_IDENTIFICATION_REQUIRED

all gates pass
  ACTION_CONDITIONED_FULL_HISTORY_MODEL_PASS_FRESH_MULTIPULSE_DESIGN_REQUIRED
```

Even a pass authorizes only a separately preregistered fresh authentic
multi-pulse superposition/interaction validation. It does not authorize real
MPC, expert data, BC, DAgger, bounded residual RL, unseen targets, continuous
actuator/plant variation, noise, disturbance recovery, or long-hold claims.
