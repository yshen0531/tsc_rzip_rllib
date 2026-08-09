# Stage4.2R3c3T13S24D1R14R8R41 fixed equal global-ridge/local-affine cold-ensemble preflight design

Status: prospectively frozen after final R8R39 and its immutable server
evidence were opened, but before any R8R41 fit, prediction, residual, tube,
metric, gate, route, implementation, package, stdout, stderr, state, raw, or
TSC result exists.

## 1. Scientific question and source classification

R8R39 cleanly rejected the fixed equal blend of the R8R31 global expert and
the R8R37 local-constant cold expert. The blend improved the R31 schedule
velocity errors but failed whole-pair Z/vZ/containment and still failed
whole-schedule vR/vZ. It does not test the earlier local-affine architecture.

R8R41 asks one narrower, prospectively fixed question: can the exact R8R31
global ridge expert and the exact R8R34 local-affine expert complement each
other under the same response-blind equal weights?

Authenticate final R8R31 and R8R39 evidence and reproduce their transitive
raw fingerprints. Also authenticate R8R34's exact config, source, primary
artifact, and final classification. R8R34 remains an overall numerical-
reproducibility FAIL and is architecture context only; R8R41 must rebuild
the local-affine model and may not relabel R8R34 as a PASS.

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

For the same fold, independently fit the exact R8R34 response-blind local
geometry from only complete training trajectories:

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
and responses, solve the fixed augmented ridge least-squares problem only
over nonconstant columns, and evaluate the centered intercept at the query.
There is no slope, neighbor, ridge, scale, feature, or response search.

R8R34's historical independent normal-equation path exceeded its frozen
numerical tolerance. R8R41 primary and independent implementations must each
construct the centered augmented ridge system in separate code and solve it
with the stable least-squares primitive. They may not import one another's
local fitter, neighbor selector, predictor, ensemble, metric aggregator, or
finalizer. The new identity retains the scaled `1e-9` agreement gate; no
tolerance is inherited or weakened after results.

## 4. Fixed equal cold ensemble

Before reading any held target, for every trajectory, interval, offset, and
component:

```text
prediction = 0.5 * global_ridge_prediction
           + 0.5 * local_affine_prediction
```

Both weights are exact binary64 `0.5`. They are identical for all folds,
components, intervals, contexts, actions, and schedules. There is no weight
or outcome search, gating, distance switch, expert fallback, innovation,
gain, clipping, calibration, or post-result adjustment.

Pair/history/source/schedule labels, formal outcomes, held targets, future
rows, and residuals are forbidden predictor inputs. Labels may define only
the frozen exclusion membership and audit strata.

## 5. Exclusions, tubes, and gates

Run exactly eight whole-physical-pair folds and 35 whole-schedule folds.
Every fold refits both experts. Calibrate only from ensemble residuals with:

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
gate. Unsupported rows fail. Report both expert predictions, the equal
ensemble, row residuals, neighbor identities, model evidence, all tubes,
and all folds. Historical R31/R34/R39 metrics are context only and may not
replace fresh R8R41 recomputation.

## 6. Independent agreement

Primary and independent paths must independently rebuild raw sources,
features, expanded features, standardization, stable neighbors, augmented
local ridge fits, global fits, expert predictions, equal blends, residuals,
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
  FIXED_EQUAL_GLOBAL_LOCAL_AFFINE_COLD_ENSEMBLE_EXECUTION_FAIL_STOP

cardinality, fit, point, tube, containment, or support failure
  FIXED_EQUAL_GLOBAL_LOCAL_AFFINE_COLD_ENSEMBLE_MODEL_FAIL_NO_TSC

all source, integrity, model, support, and dual gates pass
  FIXED_EQUAL_GLOBAL_LOCAL_AFFINE_COLD_ENSEMBLE_PASS_CONTROLLER_PREFLIGHT_DESIGN_REQUIRED
```

Every route executes zero Ray, `gotsc`, TSC, controller, plant step, raw, and
snapshot. A PASS authorizes only a separately frozen measurement-recentered
controller-preflight design. It is not real MPC, Gate A, or learning
authorization. A FAIL rejects only this fixed equal cold ensemble and does
not prove plant unreachability.

## 8. Formal, deployment, and learning boundary

Formal arrival/hold, R/Z, speed, Ip, and streak gates remain unchanged.
Require project-venv compilation, JSON, focused and full Windows-shimmed
tests, exact package hashes, empty-directory direct-copy validation, server
preflight, the existing server venv, declared `bash -n`, compilation,
focused tests, and full tests. No archive operation is allowed. Large model
and row evidence stays on the server; download only compact audits.

Gate A, expert data, BC, DAgger, residual RL, and all other learning remain
blocked. Every R8-family trajectory remains forbidden from learning data.
