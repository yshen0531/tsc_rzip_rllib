# Stage4.2R3c3T13S24D1R14R8R43 fixed affine-dominant global-ridge/local-affine cold-ensemble preflight design

Status: prospectively frozen after final R8R41 and its immutable server
evidence were opened, but before any R8R43 implementation, fit, prediction,
residual, tube, metric, gate, route, package, stdout, stderr, state, raw, or
TSC result exists.

## 1. Scientific question and adaptive-development disclosure

R8R41's fixed equal cold ensemble passed the complete whole-pair gate and
every tube, containment, support, integrity, and independent gate. It missed
only the whole-schedule `vZ` point cap: `0.0535701319 m/s` against
`0.05 m/s`. The already specified local-affine architecture historically
had strong whole-schedule accuracy but weak whole-pair accuracy. R8R43 asks
one final narrow static-ensemble question: does a single, exact-binary,
affine-dominant blend retain R8R41's pair generalization while restoring the
local expert's schedule behavior?

The R8R41 outcome informed this architectural direction. Therefore R8R43 is
development-bank model selection, not an independent holdout or
qualification result. The weights below are the exact binary midpoint
between R8R41's equal blend and the pure local-affine endpoint. There is no
weight scan, interpolation fit, threshold search, or post-result selection.
No other static convex weight may be tried after opening R8R43.

Authenticate final R8R31, R8R34, R8R39, and R8R41 evidence and reproduce
their transitive raw fingerprints. R8R34 remains an historical overall
numerical-reproducibility FAIL and is architecture context only. R8R43 must
rebuild both experts and pass its own dual implementation.

Use exactly the same immutable bank:

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

In every exclusion fold, fit the exact R8R31 causal expanded regression from
only complete training trajectories:

```text
base causal feature dimension                                  44
current action dimension                                        4
previous action dimension                                       4
interaction blocks                                        4 * 44
expanded dimension                                             238
ridge with unpenalized centered intercept                     1e-4
```

Feature order, output normalization, centering, ridge solve, and stable
serialization are unchanged. PCA, rank truncation, feature/ridge search,
response filtering, and held-row fitting are forbidden.

## 3. Frozen local-affine expert

For the same fold, independently fit the exact stable R8R41 rebuild of the
R8R34 response-blind local geometry from only complete training
trajectories:

```text
coordinate                    [causal base 44,current action block 18]
dimension                                                          62
scale floor                                                       1e-12
stable Euclidean neighbors                                          64
uniform neighbor weights                                              1
centered local slope ridge                                             1
unpenalized local intercept                                             0
inactive centered columns                              exact zero slope
```

For each query and eligible offset group, select the stable 64 nearest
standardized training coordinates. Center neighbor coordinate differences
and responses, construct the augmented ridge least-squares system only over
nonconstant columns, and evaluate the centered intercept at the query.
There is no slope, neighbor, ridge, scale, feature, or response search.

Primary and independent implementations must separately construct their
neighbor order, augmented system, fit, and prediction. They may not import
one another's local fitter, predictor, ensemble, metric aggregator, or
finalizer.

## 4. Fixed affine-dominant cold ensemble

Before reading any held target, for every trajectory, interval, offset, and
component:

```text
prediction = 0.25 * global_ridge_prediction
           + 0.75 * local_affine_prediction
```

Both weights are exact binary64 numbers. They are identical for all folds,
components, intervals, contexts, actions, and schedules. There is no weight
or outcome search, gating, distance switch, expert fallback, innovation,
gain, clipping, calibration, or post-result adjustment.

Pair/history/source/schedule labels, formal outcomes, held targets, future
rows, and residuals are forbidden predictor inputs. Labels may define only
the frozen exclusion membership and audit strata.

## 5. Exclusions, tubes, and gates

Run exactly eight whole-physical-pair folds and 35 whole-schedule folds.
Every fold refits both experts. Calibrate only from the fixed ensemble's
training-eligible residuals with:

```text
tube = max(1.25 * maximum eligible absolute residual,
           [0.015 m,0.015 m,3000 A,0.05 m/s,0.05 m/s])
```

Both exclusion families and their componentwise maximum must pass:

```text
maximum point error               [0.015,0.015,3000,0.05,0.05]
maximum tube half-width           [0.025,0.025,5000,0.08,0.08]
reserved containment                                         100%
held causal state support                                    100%
finite predictions                                            100%
forbidden predictor inputs                                       0
tube clipping                                               forbidden
```

Retain the exact observed 8D `[previous_q4,current_q4]` convex-hull support
gate. Unsupported rows fail. Report both expert predictions, the fixed
ensemble, row residuals, neighbor identities, model evidence, all tubes,
and all folds. Historical R31/R34/R41 metrics are context only and may not
replace fresh R8R43 recomputation.

## 6. Independent agreement

Primary and independent paths must independently rebuild raw sources,
features, expanded features, standardization, stable neighbors, augmented
local ridge fits, global fits, expert predictions, fixed blends, residuals,
tubes, support, metrics, and route.

```text
component scales                 [0.015 m,0.015 m,3000 A,0.05 m/s,0.05 m/s]
maximum scaled model/prediction/tube/metric difference                 1e-9
bank difference                                                       0
neighbors, counts, support, gates, routes                            exact
```

## 7. Routes and authorization

```text
source, package, causality, runtime, forbidden input, or dual disagreement
  FIXED_AFFINE_DOMINANT_COLD_ENSEMBLE_EXECUTION_FAIL_STOP

cardinality, fit, point, tube, containment, or support failure
  FIXED_AFFINE_DOMINANT_COLD_ENSEMBLE_MODEL_FAIL_NO_TSC

all source, integrity, model, support, and dual gates pass
  FIXED_AFFINE_DOMINANT_COLD_ENSEMBLE_PASS_CONTROLLER_PREFLIGHT_DESIGN_REQUIRED
```

Every route executes zero Ray, `gotsc`, TSC, controller, plant step, raw,
and snapshot. A PASS authorizes only a separately frozen measurement-
recentered controller-preflight design under a new identity. It is not real
MPC, Gate A, or learning authorization.

A FAIL ends post-result scalar cold-ensemble interpolation on this reused
development bank. The next eligible direction would require a separately
frozen causal online innovation/adaptation architecture and a meaningful new
validation boundary. A FAIL does not prove plant unreachability or global
controller impossibility.

## 8. Formal, deployment, and learning boundary

Formal arrival/hold, R/Z, speed, Ip, and streak gates remain unchanged.
Require project-venv compilation, JSON, focused and full Windows-shimmed
tests, exact package hashes, empty-directory direct-copy validation, server
preflight, the existing server venv, declared `bash -n`, compilation,
focused tests, and full tests. No archive operation is allowed. Large model
and row evidence stays on the server; download only compact audits.

Gate A, expert data, BC, DAgger, residual RL, and all other learning remain
blocked. Every R8-family trajectory remains forbidden from learning data.
