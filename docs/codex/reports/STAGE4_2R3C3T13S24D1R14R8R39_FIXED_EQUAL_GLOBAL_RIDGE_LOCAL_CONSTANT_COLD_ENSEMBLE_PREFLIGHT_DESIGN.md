# Stage4.2R3c3T13S24D1R14R8R39 fixed equal global-ridge/local-constant cold-ensemble preflight design

Status: prospectively frozen after final R8R37 and its read-only interval
forensics, but before any R8R39 ensemble fit, prediction, residual, tube,
metric, gate, route, implementation, package, controller action, raw, or TSC
result.

## 1. Scientific question and immutable sources

R8R37 proved that pure last-innovation gain changes cannot pass the complete
model gate because the maximum whole-pair vR/vZ tubes already occur at
interval 0, where strict causal innovation is zero. R8R39 asks one narrower
question: can the response-blind global extrapolation of R8R31 and local
interpolation of the R8R37 cold predictor complement each other under a fixed
equal blend?

Authenticate final R8R31 and R8R37 evidence, including their primary,
independent, final, state, manifest, model, source-bank, and transitive raw
fingerprints. R8R31 must retain its accepted route
`ALIGNED_EXPLICIT_FOUR_COORDINATE_FEEDBACK_PREFLIGHT_FAIL_NO_TSC`; R8R37 must
retain `TRAINING_ONLY_DIAGONAL_INNOVATION_GAIN_MODEL_FAIL_NO_TSC` with exact
dual agreement. Source hashes may be transcribed after this design is frozen,
but no model or gate below may change.

Rebuild exactly the same immutable bank:

```text
trajectories                                      560
physical pairs                                      8
history contexts                                   16
schedule identities                                35
decision steps                     [10,12,14,16,18,22]
interval records                                 3360
five-component time rows                        14560
bank digest        a84995970a5c1f0f2d2e964c6b97cbaf213ac8f86d70a3666279ae144ba2de2e
feature digest     80ed0b20b99f6f277ac1e09f85ad33c6fb8a1e611824901509eaf6a3c7b830db
target digest      0f445fca5bb2dbb1da7fb1fc5e1951161322caccc4219371653ffdb55eaa8539
```

## 2. Frozen global expert

For every exclusion fold, fit the exact R8R31 causal expanded regression
using only complete training trajectories:

```text
base causal feature dimension                                  44
current action dimension                                        4
previous action dimension                                       4
interaction blocks                                        4 * 44
expanded dimension                                             238
ridge with unpenalized centered intercept                     1e-4
```

Feature order, output normalization, centering, ridge solve, and stable
serialization are unchanged. No PCA, rank truncation, feature selection,
ridge search, or response filtering is allowed.

## 3. Frozen local expert

For the same fold, independently fit the exact R8R37 cold local-constant
expert:

```text
coordinate                    [causal base 44,current action block 18]
dimension                                                          62
scale floor                                                       1e-12
stable Euclidean neighbors                                          64
uniform neighbor weights                                              1
slopes                                                                0
```

Training standardization and every neighbor set use only that fold's
training trajectories. Innovation, gain, lag, memory, clipping, and
cross-trajectory state are all disabled.

## 4. Fixed response-blind ensemble

For every trajectory, interval, and offset, before reading its target:

```text
prediction = 0.5 * global_ridge_prediction
           + 0.5 * local_constant_prediction
```

Both weights are exact frozen binary64 `0.5`. They are identical for all
folds, intervals, offsets, components, contexts, actions, and schedules.
There is no intercept beyond the experts, gating, distance switch, outcome
switch, support switch, gain, calibration, grid, line search, fallback
expert, or post-result adjustment.

Pair/history/source/schedule labels, formal outcomes, held targets, future
rows, and residuals are forbidden predictor inputs. Labels may only define
the prospectively frozen exclusion membership and audit strata.

## 5. Exclusions, tubes, and model gates

Run exactly:

```text
whole physical-pair folds                                  8
whole schedule folds                                      35
```

Each fold refits both experts from its training set. Use ensemble residuals
and the unchanged reserve:

```text
tube = max(1.25 * maximum eligible absolute residual,
           [0.015 m,0.015 m,3000 A,0.05 m/s,0.05 m/s])
```

Both families and their componentwise maximum must pass:

```text
maximum point error               [0.015,0.015,3000,0.05,0.05]
maximum tube half-width           [0.025,0.025,5000,0.08,0.08]
adapted/ensemble containment                                 100%
held causal state support                                    100%
finite exclusions                                                0
forbidden predictor inputs                                       0
tube clipping                                               forbidden
```

Retain the exact observed 8D `[previous_q4,current_q4]` convex-hull support
gate. Unsupported rows fail; they are not extrapolation successes. Report
both expert predictions, ensemble predictions, row residuals, per-interval
maxima, all neighbor identities, and all folds. R8R31/R8R37 source metrics
are authenticated context only and may not replace the fresh R8R39
recomputation.

## 6. Independent implementation

Primary and independent paths must independently rebuild sources, causal
features, expanded features, standardization, stable neighbors, centered
ridge fits, both expert predictions, equal blends, residuals, tubes, support,
metrics, and route. The independent audit may not import the primary bank
builder, fitters, predictors, ensemble, metric aggregator, or finalizer.

```text
component scales                 [0.015 m,0.015 m,3000 A,0.05 m/s,0.05 m/s]
maximum scaled model/prediction/tube/metric difference                 1e-9
bank difference                                                       0
neighbors, counts, support, gates, routes                            exact
```

## 7. Routes and authorization

```text
source, package, causality, runtime, forbidden input, or dual disagreement
  FIXED_EQUAL_GLOBAL_LOCAL_COLD_ENSEMBLE_PREFLIGHT_EXECUTION_FAIL_STOP

cardinality, fit, point, tube, containment, or support failure
  FIXED_EQUAL_GLOBAL_LOCAL_COLD_ENSEMBLE_MODEL_FAIL_NO_TSC

all source, integrity, model, support, and dual gates pass
  FIXED_EQUAL_GLOBAL_LOCAL_COLD_ENSEMBLE_PASS_CONTROLLER_PREFLIGHT_DESIGN_REQUIRED
```

Every route executes zero Ray, `gotsc`, TSC, controller, plant step, raw, and
snapshot. A PASS authorizes only a separately frozen causal
measurement-recentered controller-preflight design. It is not real MPC, Gate
A, or learning authorization. A FAIL rejects only the fixed equal cold
ensemble; it does not prove plant unreachability or rule out other bounded
causal model classes.

## 8. Formal, deployment, and learning boundary

Formal timing remains unchanged:

```text
slew 1.0/1.1  arrive no later than 250 ms, hold through 350 ms
slew 0.9      arrive no later than 270 ms, hold through 370 ms
R/Z 0.03 m, speed 0.1 m/s, unchanged Ip and arrival streak
```

Require project-venv compilation, JSON, focused and full Windows-shimmed
tests, exact package hashes, empty-directory direct-copy validation, server
preflight, the existing server venv, all declared `bash -n`, compilation,
focused tests, and full tests. No local archive or extraction is allowed.
Keep large row/model evidence on the server and download only compact audits.

Gate A, expert data, BC, DAgger, residual RL, and all other learning remain
blocked. All R8-family trajectories remain forbidden from learning data.
