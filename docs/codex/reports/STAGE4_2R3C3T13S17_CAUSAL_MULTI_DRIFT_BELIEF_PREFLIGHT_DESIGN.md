# Stage4.2R3c3T13S17 causal multi-drift belief preflight design

## Status and question

This design is frozen after the final S16 result and before S17 audit code or
output.  S17 is a zero-new-TSC, read-only development preflight over the 128
consumed S16 response trajectories and their 16 matched baselines.

S16 showed that the orthogonal physical excitation is valid and that a single
quadratic-drift point estimate is accurate for 120/128 rows, but its one-box
residual tube is neither compact nor containing.  S17 asks whether a fixed,
causal set of plausible natural-drift models gives a compact set-valued
response suitable for a later robust MPC design.  It does not change S16's
failed gates or claim independent validation.

## Immutable source and information boundary

The only source is the exact completed S16 run recorded in its forensic
report.  S17 must authenticate its run manifest, final result, final model
audit, frozen estimator, state, 144 raw files, 16 source snapshots, package
digest, raw inventory digest, and exact 128 experiment identities.

For each signed response trajectory, the predictor may use only:

```text
current-run visible R/Z/Ip states 0 through 10
backward-causal R/Z velocity computed from those states
already-issued current-run actions 0 through 9
the exact fixed orthogonal basis frozen at state zero
the state-10 measured coil current and Card15 uncertainty interval
target, formal task time, and finite actuator setting
```

States 1--8 contain the four signed calibration pairs.  States 9--10 are the
two already-observed zero-deviation settling states.  The response is issued
only after state 10; state 11 and later values are forbidden from every fit,
hypothesis, interval, selection, and controller-side feature.  Pair, history,
prefix, q, regime, source result/action, wire/vessel current, matched-baseline
future, and response sign/direction labels are also forbidden predictor
inputs.  Labels may be opened only after prediction to audit strata.

## Frozen hypotheses

Let `t` be the ten fixed state indices 1--10 mapped linearly to `[-1,1]`.
Let `U` be the fixed ten-by-four issued calibration code:

```text
+e0, -e0, +e1, -e1, +e2, -e2, +e3, -e3, 0, 0
```

For every trajectory and each visible output `(R,Z,vR,vZ,Ip)`, fit all three
of these hypotheses with ordinary float64 least squares:

```text
H1: Legendre drift degrees 0..1 + U             10 x 6
H2: Legendre drift degrees 0..2 + U             10 x 7
H3: Legendre drift degrees 0..3 + U             10 x 8
```

All three hypotheses are always retained.  No AIC, residual, response, label,
or outcome-based model selection is allowed.  Their exact input-only ranks
are `6,7,8`; their exact conditions are approximately
`2.2888783, 2.5392395, 3.1980987`.  Every design must be full rank and have
condition `<= 4.0`.

The native response command is projected into the same exact four-column
orthogonal current basis under the unchanged cosine `>=0.98` and relative
off-basis residual `<=0.15` gates.  For hypothesis `h`, prepend `degree+1`
zeros to the four response coordinates to form its coefficient query `a_h`.
With design `X_h`, fit `theta_h = pinv(X_h) Y` and compute:

```text
prediction_h = a_h @ theta_h
leverage_h   = abs(a_h @ pinv(X_h))
residual_h   = componentwise max(abs(Y - X_h @ theta_h))
```

The per-hypothesis component interval radius is prospectively fixed as:

```text
RESPONSE_FLOOR
+ sum(leverage_h) * residual_h
+ propagated Card15/current-coordinate uncertainty
```

This is a bounded-residual sensitivity propagation, not a fitted scalar tube
multiplier.  The old S16 multiplier and its failed result remain unchanged.
Non-finite values, negative radii, rank loss, or a condition failure stop the
audit fail-closed.

## Belief envelope and gates

The causal response belief is the componentwise hull of all three fixed
hypothesis intervals:

```text
lower = min_h(prediction_h - radius_h)
upper = max_h(prediction_h + radius_h)
center = (lower + upper) / 2
halfwidth = (upper - lower) / 2
```

Only after this artifact has been computed and hashed for all 128 rows may
the authentic state-11 response be opened.  The matched baseline is used only
to form that post-artifact response outcome exactly as in S16.  It may not
change the belief.

Required development gates are:

```text
source/raw/identity authentication                         144 / 144
causal history and forbidden-input audit                   128 / 128
H1/H2/H3 full-rank condition <= 4.0              384 / 384
fixed-basis response projection                            128 / 128
finite nonnegative per-hypothesis intervals                384 / 384
actual response inside belief envelope                     128 / 128
belief halfwidth caps                                      128 / 128
  caps = (0.003 m, 0.003 m, 0.010 m/s, 0.010 m/s, 1000 A)
artifact-before-outcome open order                         128 / 128
forbidden inputs, refit, dropped rows, TSC/plant steps              0
```

Report midpoint scaled error and every result by direction, sign, history,
prefix, q, delay/slew, and target only after prediction.  These are
diagnostics and cannot select a hypothesis or remove a row.

## Routes

```text
CAUSAL_MULTI_DRIFT_BELIEF_PREFLIGHT_PASS_FRESH_WHOLE_PAIR_REQUIRED
  all gates pass; authorize only a separately frozen, new whole-pair
  training/calibration/fresh-context identification campaign using the exact
  causal belief builder.  The fresh holdout may not refit the center or tube.

CAUSAL_MULTI_DRIFT_BELIEF_PREFLIGHT_FAIL_ROBUST_OBSERVER_REDESIGN
  any gate fails; the fixed low-order multi-drift response belief is
  insufficient and must not enter an MPC.  Redesign the causal observer or
  prospective excitation without relaxing caps or formal timing.
```

S17 runs no controller, optimizer, Ray, `gotsc`, TSC, plant step, or snapshot
creation.  Neither route authorizes MPC control, expert data, BC, DAgger, or
bounded residual RL.  The immutable formal timing contract is unchanged.
