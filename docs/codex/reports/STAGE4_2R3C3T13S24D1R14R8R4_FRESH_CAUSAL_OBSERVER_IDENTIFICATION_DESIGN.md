# Stage4.2R3c3T13S24D1R14R8R4 fresh causal observer identification design

Frozen prospectively after the final R8R3 primary/independent agreement, but
before any R8R4 implementation, feature matrix, fit, prediction metric, new
TSC trajectory, model/tube artifact, or route is produced.

## Purpose and scientific boundary

R8R3 learned a causal no-action observer from twelve already opened physical
pairs.  It missed the old deterministic point cap in only 14/360 origin rows,
all at future lags 9--12, but its leave-one-pair-out maximum-residual tubes
were too wide.  Every selected fold used the largest available PCA rank 32.
That is a finite model/data-coverage failure, not permission to retune R8R3 or
to weaken its frozen gates.

R8R4 is a new-identity, prospective baseline-only identification campaign.
It adds genuinely fresh no-action development histories, freezes a higher-
capacity causal observer and finite qualification tube, and only then opens
genuinely fresh whole-pair holdout histories.  The practical gates below are
new prospective gates for the stated finite application goal; they do not
relabel R8R3 and do not alter the deterministic formal-control contract.

R8R4 is not an action-response experiment, controller, MPC, formal tracking
PASS, Gate A result, expert-data campaign, BC, DAgger, or residual RL result.

## Immutable source evidence

Before offline acceptance R8R4 must authenticate the exact R8 and R8R3
sources, including:

```text
R8 source run
  /home/yangshen0711/tsc_all/tsc_rzip_rllib/
  stage4_2r3c3t13s24d1r14r8_runs/
  stage4_2r3c3t13s24d1r14r8_partitioned_broad_response_identification_20260804_5e57f60_v2
R8 stage state SHA-256
  9fff80668023f17d3be273f9cd9694e21b401a5f668c60c1e03508a164c6d5d3
R8 stage manifest SHA-256
  67d1dc0604aa241161850578fb75c6f04bb140a1f791a5246b9f24c8d8df9f90
R8 training raw count / bytes / digest
  624 / 19725920
  b5de1cabe0bd47b0d3a3b26aff04714ca0c05653483cd4c92403dc5867eeb762
R8 original calibration raw count                         0
R8 original holdout raw count                             0

R8R3 primary detailed / summary / independent / final state SHA-256
  a0db5c6db2687747ffd5de8a4a773635bfce15973e8e817eebe74a3356470a00
  b8992e53a07e339015dc714377fcca57860dac3cb7b4b169d67e3623b520e364
  4cb71b25ad69848349a2034fff335b9d869a56f709465be9baed6b209637f8ba
  e016c0ab9ee2c7a2f4701e553733c4392f48026f648450408cca4e19df9a9bcb
R8R3 required route
  CAUSAL_HISTORY_NO_ACTION_OBSERVER_FAIL_FRESH_IDENTIFICATION_REQUIRED
```

The R2/R4/R6 and S21/D1R11 evidence transitively authenticated by R8 must
retain its exact hashes, raw inventories, snapshot integrity, and routes.  No
source raw, snapshot, manifest, state, or result is modified.  R8's original
calibration and holdout directories remain empty; R8R4 consumes their pair
blueprints under a distinct stage identity and distinct raw directories.

## Prospectively fixed fresh partitions

R8R4 uses only the baseline role, both history members, for the following
whole physical pairs:

```text
development (four pairs, eight fresh trajectories)
  p5_q1_a0p900_gap3_settle4
  p5_q2_a0p750_gap3_settle4
  p9_q1_a0p900_gap3_settle4
  p9_q2_a0p750_gap3_settle4

blind holdout (four pairs, eight fresh trajectories)
  p5_q1_a0p750_gap4_settle4
  p5_q2_a0p900_gap4_settle4
  p9_q1_a0p750_gap4_settle4
  p9_q2_a0p900_gap4_settle4
```

All sixteen specifications and their ordered digest are frozen during the
offline phase before the first plant advance.  A specification delegates the
unchanged authenticated controller only through task step 9 and commands
exact zero normalized incremental action thereafter.  It inherits the exact
R8 restart state, target, Card15 boundary, current gates, formal horizon, and
fresh-process requirements.  No probe, cancellation pulse, or nonzero action
is added.

All R8R4 trajectories, including the no-probe baselines, are identification
and qualification evidence and are forbidden from every expert, BC, DAgger,
or RL dataset.

## Strict execution order

The only allowed phase order is:

1. authenticate sources and freeze all sixteen specs without TSC;
2. run exactly the eight development baselines;
3. independently audit development raw and snapshots;
4. construct nested whole-pair predictions using the twelve prior training
   pairs plus four fresh development pairs;
5. if and only if every development gate passes, fit the all-development
   observer, derive its tube, serialize both, and freeze their SHA-256 values;
6. independently reproduce the development decision and artifact hashes;
7. authorize and run exactly the eight blind holdout baselines;
8. evaluate the already frozen observer/tube without refitting, recalibration,
   tube expansion, threshold change, or candidate reselection; and
9. independently recompute the final holdout result.

Before step 7 the R8R4 holdout raw inventory must be exactly zero.  A failed
development acquisition, audit, model, coverage, tube, or independent gate
stops the stage without opening holdout.  A failed holdout is final and may
not resume under changed semantics.

## Hard acquisition, safety, and causality gates

Every attempted trajectory is individually recorded.  The following are
all-or-nothing in development and holdout:

```text
fresh authentic restart and exact source physical prefix
causal trace and action prefix
exact zero incremental action from task step 10 onward
constant commanded applied-current target from state 10 onward
Card15 representability and exact actuator boundary
finite trajectory and successful solver/plant execution
no saturation, abnormal plant state, or forbidden input
maximum total normalized action <= 1.0
maximum current utilization <= 0.55
strict raw parse and complete manifest/snapshot authentication
no later plant advance after any structured stop
```

These gates are not statistical and cannot be offset by aggregate observer
accuracy.  Any violation routes to execution/audit failure, not observer
failure.  Baseline formal tracking is diagnostic only.

## Causal rows and deployable feature

Visible state, scales, time step, origin eligibility, source selection for
the twelve prior pairs, and the 353-dimensional feature are exactly R8R3:

```text
visible state [R, Z, causal vR, causal vZ, Ip]
scales [0.03 m, 0.03 m, 0.1 m/s, 0.1 m/s, 10000 A]
dt 0.01 s
origin t = 10 ... (last state - 12)

visible states t-10 ... t                         11 * 5 = 55
issued normalized actions t-10 ... t-1           10 * 14 = 140
measured applied currents through state t         11 * 14 = 154
numeric user target R/Z/Ip offsets                             3
relative task clock (t - 10) / 15                              1
total                                                        353
```

No padding is used.  Categorical pair/history/source/regime/delay/slew IDs,
experiment ID, source result, formal outcome, hidden or wire current, matched
future, future measurement, future applied current/action, and heldout outcome
are forbidden predictor inputs.  Pair/history identifiers are evaluator-only
for split enforcement and reporting.  The blind holdout target cannot affect
any preprocessing, model, tube, or threshold.

The target and output reconstruction also remain R8R3: directly predict the
next twelve origin-relative vR/vZ/Ip changes, add the observed origin values,
and reconstruct R/Z only by exact 10 ms kinematic integration.  There is no
learned independent position head, outcome reset, smoothing, clipping, or
recursive future input.

## Frozen expanded candidate family

Every candidate uses training-fold-only feature mean/standard deviation,
`1e-12` scale floors, canonical-sign PCA, a training-target mean, and kernel
ridge solved by least squares.  Candidate PCA ranks are:

```text
[32, 48, 64, 96]
```

At every rank:

```text
linear kernel
  K(x,y) = dot(x,y) / rank
  ridge in [1e-6, 1e-4, 1e-2]

RBF kernel
  bandwidth = multiplier * median positive training-pair distance
  multiplier in [0.5, 1.0, 2.0]
  ridge in [1e-6, 1e-4, 1e-2]
```

There are exactly 48 candidates.  If a requested PCA rank exceeds the
available numerical rank in a fold, that candidate is ineligible rather than
silently truncated.  No architecture, feature, rank, ridge, bandwidth,
ensemble, neighbor, output transform, threshold, or loss may be added after
any R8R4 metric or raw trajectory is viewed.

## Development whole-pair validation and selection

Development evaluation combines exactly sixteen physical pairs: twelve
already opened R8 training pairs and four new R8R4 development pairs.  Each
outer fold holds both histories and all eligible origins from one complete
pair.  Inner leave-one-training-pair-out selection uses only the remaining
fifteen pairs.

Candidate scoring is lexicographic:

1. rows outside the practical point caps below;
2. component-by-future-state practical-cap violations;
3. rows outside the finite exclusion caps below;
4. maximum scaled point error;
5. 95th-percentile row maximum scaled point error;
6. mean squared scaled error;
7. family order linear then RBF;
8. increasing PCA rank;
9. increasing bandwidth multiplier, linear treated as zero; and
10. increasing ridge.

After a development PASS the final candidate is selected by the identical
leave-one-pair-out rule over all sixteen development pairs, then fit once on
all sixteen.  This final all-development fit is not validation.

## Prospectively fixed practical finite qualification

The practical point caps are:

```text
[R, Z, vR, vZ, Ip]
[0.003 m, 0.003 m, 0.02 m/s, 0.02 m/s, 1000 A]
```

They reserve 90% of the unchanged 30 mm position tolerance, 80% of the
unchanged 0.1 m/s speed tolerance, and 90% of the unchanged 10 kA Ip
tolerance for later controller/model/action effects.  They qualify an
observer prediction; they do not change formal trajectory acceptance.

Every predicted future state must also remain inside the finite exclusion
caps:

```text
[0.01 m, 0.01 m, 0.05 m/s, 0.05 m/s, 3000 A]
```

No exclusion-cap miss is permitted.  For both development outer predictions
and blind holdout predictions, the practical point gate is:

```text
at least 95% of all eligible origin rows pass every point cap
at least 95% of prescribed issue rows t in [10,14,18,22] pass
each history context passes at least 90% of its eligible origin rows
each history context passes at least 3/4 prescribed issue rows
both history signs represented in every aggregate
every miss retained and reported by pair, history, origin, lag, component
```

Integer requirements use `ceil(rate * denominator)`.  No row or component is
dropped, censored, winsorized, averaged away, or reclassified after viewing a
result.

## Frozen finite uncertainty tube

For a selected candidate, reconstruct its whole-pair out-of-fold development
residuals.  For each of twelve future lags and five physical components, set
the base half-width to the NumPy `method="higher"` 95th percentile of absolute
residuals plus the fixed physical floor:

```text
[1e-9 m, 1e-9 m, 1e-7 m/s, 1e-7 m/s, 1e-4 A]
```

Multiply all 60 base widths by one common scalar equal to the `method="higher"`
95th percentile of each development row's maximum residual/base-width ratio.
The scalar is at least one.  This construction and the resulting 60 widths
are frozen with the model before holdout.

All widths must be finite and no wider than the finite exclusion caps.  The
resulting tube must contain at least 95% of complete development rows and at
least 90% per history context.  On blind holdout, the unchanged frozen tube
must contain at least 95% of complete rows and at least 90% per history
context.  Containment means every one of the 60 future-component values for a
row is inside the tube.  Every miss is retained.  This is an empirical finite-
envelope tube, not a universal or probabilistic safety proof.

## Blind holdout decision

The final holdout uses only the frozen model and tube hashes.  It must contain
exactly four unseen physical pairs, eight histories, all eligible origins,
and 32 prescribed issue rows.  A PASS requires:

```text
all hard acquisition/safety/causality/integrity gates
all predictions finite
zero forbidden inputs or holdout-dependent model changes
zero finite-exclusion-cap misses
practical point coverage and every per-context floor
frozen-tube width caps, aggregate containment, and per-context containment
exact model/tube hashes before and after holdout
primary/independent numerical, categorical, inventory, hash, and route agreement
```

The blind result is final.  No failed row may be moved into development and no
refit, recalibration, threshold change, tube expansion, or selective rerun is
allowed under R8R4.

## Independent recomputation

A structurally independent implementation must separately authenticate all
source evidence and new raw/snapshots, reconstruct causal visible states and
features, enforce whole-pair splits, implement preprocessing/PCA/kernel fits,
select candidates, reconstruct kinematic outputs, derive the development
tube, verify artifact hashes, evaluate blind holdout, and compute the route.
It may share only immutable low-level raw parsing and Card15/visible-state
helpers, not primary selection, prediction, tube, gate, or routing functions.

Numerical agreement uses relative tolerance `1e-10` and absolute tolerance
`1e-12`; identities, counts, booleans, inventories, hashes, and route agree
exactly.

## Frozen routes

```text
offline source/spec/identity failure before TSC
  FRESH_CAUSAL_OBSERVER_SOURCE_FAIL_NO_TSC

development runtime/restart/causality/Card15/current/raw/snapshot failure
  FRESH_CAUSAL_OBSERVER_DEVELOPMENT_EXECUTION_FAIL_STOP

development model/coverage/tube/independent failure
  FRESH_CAUSAL_OBSERVER_DEVELOPMENT_FAIL_STOP_NO_HOLDOUT

blind-holdout runtime/restart/causality/Card15/current/raw/snapshot failure
  FRESH_CAUSAL_OBSERVER_HOLDOUT_EXECUTION_FAIL_STOP

blind-holdout point/tube/independent failure
  FRESH_CAUSAL_OBSERVER_HOLDOUT_FAIL_REDESIGN_REQUIRED

every frozen development and blind-holdout gate passes
  FRESH_CAUSAL_OBSERVER_HOLDOUT_PASS_COMBINED_ADAPTATION_FREEZE_REQUIRED
```

A design/model failure is not a runtime, restart, raw, controller, formal-MPC,
plant-reachability, or global-observability conclusion.  An execution failure
is not a model result.

## Formal timing and downstream boundary

The immutable formal contract remains:

```text
normal slew: arrive by state 25; hold/evaluate through state 35
weak slew:   arrive by state 27; hold/evaluate through state 37
R/Z tolerance 0.03 m; speed 0.1 m/s; Ip 10000 A; streak 3
```

The 120 ms observer window never shifts an arrival deadline or formal hold
endpoint.  A R8R4 PASS authorizes only a separately prospectively frozen
combined observer/causal-innovation validation.  It does not authorize a
controller, MPC, Gate A, expert data, BC, DAgger, or residual RL.  Gate A and
all learning remain blocked regardless of R8R4 outcome.
