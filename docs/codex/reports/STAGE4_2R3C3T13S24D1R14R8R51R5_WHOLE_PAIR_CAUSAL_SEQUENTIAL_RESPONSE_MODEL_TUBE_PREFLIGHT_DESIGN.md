# Stage4.2R3c3T13S24D1R14R8R51R5 whole-pair causal sequential response model/tube preflight design

Status: conditionally and prospectively frozen on 2026-08-10 after the
R51R4 primary and independent offline constructions both passed, but before
R51R4 real authorization, before any R51R4 TSC/plant step, and before any
R51R4 real response or formal outcome was generated or viewed.

## 1. Conditional question and source boundary

R51R5 may execute only if final R51R4 raw integrity passes independently and
R51R4 repairs at least one of its ten failed source contexts, producing the
exact route:

```text
REDUCED_Q0_TRANSPORT_BRIDGE_R51R4_SUSTAINED_DWELL_AUTHORITY_PRESENT_R51R5_MODEL_PREFLIGHT_REQUIRED
```

If R51R4 instead has zero repair or fewer than 7/16 baseline-plus-measured
oracle passes, R51R5 is not run. That outcome requires a separately frozen
longer sequential action redesign; it may not be converted into a model
failure.

The only prospective R51R5 response source is the complete immutable R51R4
100-trajectory bank plus the exact ten matching R8R7 baselines. R51R1 and
R51R3 may authenticate identities and formal metrics, but their probes are not
additional fitting rows. No R51R4 row, context, candidate, dwell, safe stop,
or adverse outcome may be excluded. All source trajectories remain probes
forbidden from expert, BC, DAgger, residual-RL, or other learning data.

## 2. Frozen rows, strata, inputs, and targets

The five physical-pair strata are fixed by the ten failed R51R3 contexts:

```text
p5_q1_a0p750_gap4_settle4
p5_q1_a0p900_gap3_settle4
p5_q2_a0p750_gap3_settle4
p5_q2_a0p900_gap4_settle4
p9_q2_a0p750_gap3_settle4
```

Each stratum contains both authentic history members and the exact ten action
cells formed by candidate IDs `d0m,d1p,d2m,d3p,u1p50` and return task steps
`16,18`. The unit held out in validation is one complete action cell: both
history members of the same candidate/return combination are held out
together. Therefore the frozen outer audit contains:

```text
5 physical pairs x 10 held-out action cells x 2 history rows = 100 predictions
```

For a row, allowed model inputs are available by task step 12 only:

- visible R/Z/Ip states and their causal first differences through state 12;
- visible 14-coil current and applied-action histories through state 12;
- the exact q0 and candidate Card15 fields already issued;
- the assigned four-coordinate candidate q and requested coordinate;
- the prospectively assigned return step and resulting dwell length;
- fixed target offsets, slew, delay, task clock, and authenticated source
  calibration constants.

Pair/history labels, formal outcome, any state after 12, future measured
current, wire/vessel current, source-result values, another rollout, and a
post-result selected feature are forbidden inputs. The physical-pair stratum
is used only to define the predeclared fitting partition; it is not exposed as
a runtime selector feature.

The output is the full causal response sequence relative to the matching
R8R7 baseline for every state from 13 through the unchanged formal horizon:

```text
delta [R, Z, Ip] at states 13..35 or 13..37
```

No terminal-only surrogate may replace this sequence.

## 3. Fixed model and no model selection

Within each physical-pair stratum and outer held-out action cell, pool the 18
remaining rows. Fit one deterministic affine sequential response map with
these frozen columns:

```text
1
causal visible-prefix vector after fixed centering/scaling
q[0:4]
dwell length
q[0:4] * dwell length
```

Continuous prefix columns are centered and scaled using training rows only.
Zero-variance columns are removed using training rows only and reported.
Action coordinates are never renormalized from held-out responses. Solve the
multi-output map by SVD pseudoinverse with fixed relative cutoff `1e-10` and
no ridge/grid/kernel/model selection. Predictions are made for the two held-
out history rows before their response values enter any statistic.

The implementation must independently reproduce the design matrix, retained
columns, singular values, coefficients, predictions, and outer residuals.
Primary NumPy and independent scalar/direct linear-algebra paths must agree on
all discrete decisions and within `1e-10` absolute numerical tolerance.

## 4. Frozen causal tube

For each outer fold, construct a componentwise time-resolved absolute-error
tube without using either held-out row. Tube calibration uses the 18 training
rows only: repeat leave-one-action-cell-out fits within those nine action
cells, collect their 18 nested out-of-cell residual sequences, and take the
finite-sample maximum at each time/component. No quantile interpolation,
held-out inflation, or post-result cap adjustment is allowed.

For a held-out row define scaled point error and tube width using:

```text
R scale   = 0.03 m
Z scale   = 0.03 m
Ip scale  = 10000 A
```

Containment is inclusive at `1e-12`. A zero-width tube is non-vacuous only if
the associated nested calibration residuals and held-out residual are both
exactly zero at the same component/time.

## 5. Predeclared gates and routes

Source/integrity PASS requires exact R51R4 and R8R7 hashes, 100/100 eligible
rows, all causal-input/forbidden-field gates, all 50 outer folds and their
nested fits, finite arrays, no row exclusion, and exact primary/independent
agreement.

The model/tube PASS gates are frozen as:

```text
retained affine rank equals retained column count             50/50 folds
whitened retained design condition <= 25                     50/50 folds
held-out scaled point error <= 0.35                          100/100 rows
held-out component/time tube containment                    100/100 rows
maximum scaled tube half-width <= 0.35                       100/100 rows
primary/independent discrete agreement                            exact
primary/independent maximum numerical difference <= 1e-10
```

Routes are frozen:

```text
R51R4 did not take its scientific PASS route
  REDUCED_Q0_TRANSPORT_BRIDGE_R51R5_BLOCKED_BY_R51R4_NO_EXECUTION

source, raw, causality, coverage, or independent integrity fails
  REDUCED_Q0_TRANSPORT_BRIDGE_R51R5_EXECUTION_OR_INTEGRITY_FAIL_STOP

integrity passes but any rank/condition/point/tube gate fails
  REDUCED_Q0_TRANSPORT_BRIDGE_R51R5_WHOLE_PAIR_SEQUENTIAL_MODEL_TUBE_INSUFFICIENT_REDESIGN

all frozen gates pass
  REDUCED_Q0_TRANSPORT_BRIDGE_R51R5_WHOLE_PAIR_SEQUENTIAL_MODEL_TUBE_COMPLETE_R51R6_CONTROLLER_PREFLIGHT_REQUIRED
```

R51R5 runs zero TSC, plant steps, controllers, snapshots, optimization, and
model selection. A PASS authorizes only a separately frozen R51R6 causal
model-selected controller preflight, not a real controller campaign.

## 6. Qualification boundary

R51R5 is a development-envelope causal response-model/tube preflight over
development-selected R51R4 actions. It is not an independent holdout, causal
selector, real MPC, formal closed-loop tracking PASS, continuous-parameter,
noise, disturbance, long-hold, or global-reachability result. Gate A remains
blocked, and Gate B is not yet applicable.
