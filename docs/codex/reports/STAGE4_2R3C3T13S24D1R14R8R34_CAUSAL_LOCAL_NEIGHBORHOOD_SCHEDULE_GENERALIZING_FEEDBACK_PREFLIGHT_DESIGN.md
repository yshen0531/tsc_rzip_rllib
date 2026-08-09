# Stage4.2R3c3T13S24D1R14R8R34 causal local-neighborhood schedule-generalizing feedback preflight design

Status: prospectively frozen after aggregate R8R33 primary and independent-
failure evidence, and before inspecting any R8R33 failed-row identity, fitting
any R8R34 neighborhood, prediction, residual, tube, support result, plan,
implementation, package, controller action, raw, or TSC.

## 1. Consumed R8R33 boundary

R8R33's fixed rank-12 representation passed all 1,161 representation heads
with minimum numerical rank 13. Its primary model nevertheless failed the
unchanged outer gates. Aggregate maxima already opened before this freeze are:

```text
whole-pair point error       [0.00526394,0.00387221,322.794,0.0768160,0.178383]
whole-pair reserved tube     [0.015,0.015,3000,0.0960200,0.222979]
whole-schedule point error   [0.0356034,0.222100,3879.07,0.500309,1.27386]
whole-schedule reserved tube [0.0445043,0.277625,4848.84,0.625387,1.59233]
```

Planning did not run. The primary route was
`UNIFORMLY_SUPPORTED_RANK12_SCHEDULE_GENERALIZATION_PREFLIGHT_FAIL_NO_TSC`.
The independently rebuilt bank, discrete route, and scientific outcome agreed,
but the preregistered absolute `1e-12` dual-solver gate failed: maximum direct
prediction difference was `1.035971308738226e-11` and maximum load-bearing
physical aggregate difference was `2.5826511773630045e-6`. R8R33 must retain
both facts and cannot be rescued by a post-result tolerance change.

R8R34 is a new consumed-development identity. It does not reinterpret R8R33
and does not use any unopened failed-row identity to choose its architecture.

## 2. Purpose and immutable source bank

The global PCA-linear family has now failed both representational support at
rank 32 and response generalization at uniformly supported rank 12. R8R34 asks
one narrower question: can a single prospectively fixed, response-blind local
causal neighborhood rule generalize across whole physical pairs and whole
schedules while retaining the unchanged safety and formal gates?

Authenticate the complete R8R33 primary, independent-failure, state, manifest,
package, and transitive source evidence. Independently rebuild exactly the same
immutable bank:

```text
trajectories                                      560
physical pairs                                      8
history contexts                                   16
schedule identities                                35
decision steps                     [10,12,14,16,18,22]
six-interval records                             3360
bank digest        a84995970a5c1f0f2d2e964c6b97cbaf213ac8f86d70a3666279ae144ba2de2e
feature digest     80ed0b20b99f6f277ac1e09f85ad33c6fb8a1e611824901509eaf6a3c7b830db
target digest      0f445fca5bb2dbb1da7fb1fc5e1951161322caccc4219371653ffdb55eaa8539
```

All rows remain consumed controller-development evidence and are forbidden
from expert, BC, DAgger, residual-RL, or other learning data.

## 3. Frozen local causal predictor

For each interval and available future offset, form only the unchanged causal
62-vector:

```text
causal visible/current/history base                         44
ordered current-candidate action                            18
total                                                       62
```

For each outer fold and each query, derive arithmetic means and RMS scales
only from that head's training rows, with scale floor `1e-12`. Zero-variance
columns remain centered zeros. Compute Euclidean distance in this standardized
62-space. Sort by `(distance, trajectory_id, interval, row_index)` and select:

```text
neighbor count k                                            64
selection basis                          training geometry only
response-dependent neighbor selection                 forbidden
distance/feature/hyperparameter search                 forbidden
```

The value 64 is fixed structurally as four rows per sixteen causal history
contexts; it was not selected from R8R33 response errors. If fewer than 64
training rows exist for a head, the head fails closed; `k` is never reduced.

Use a local affine ridge centered at the query. Let `D` be the standardized
neighbor coordinates minus the standardized query coordinate. Fit the five
physical outputs with an unpenalized intercept and one fixed slope penalty:

```text
ridge slope penalty                                         1.0
intercept penalty                                           0.0
neighbor weights                                            1.0
outlier deletion / clipping / response weighting      forbidden
query prediction                         fitted local intercept
```

No source label, held-fold identity, future state, target outcome, formal
outcome, or forbidden hidden field may enter coordinates or selection.

## 4. Dual implementation and numerical contract

Primary solves the centered augmented ridge system by SVD least squares.
Independent code rebuilds the raw bank, standardization, ordering, neighbors,
and local matrices separately, then solves the same mathematical objective by
normal equations with Cholesky/solve. Record both prediction and artifact
digests.

R8R33 showed that an unscaled absolute `1e-12` comparison across metres,
amperes, and velocities is not a reproducible contract for distinct stable
double-precision solvers. R8R34 prospectively replaces it under a new identity
with a dimensionless, load-bearing comparison; this does not amend R8R33:

```text
component scales                 [0.015 m,0.015 m,3000 A,0.05 m/s,0.05 m/s]
maximum scaled prediction difference                              1e-9
maximum scaled residual/tube/planning difference                   1e-9
all discrete gates, routes, counts, support and formal classes     exact
```

Any disagreement fails the R8R34 integrity gate. The tolerance cannot be
changed after any R8R34 calculation.

## 5. Unchanged outer model gates

Always run both exclusions before planning:

```text
whole physical pair folds                                    8
whole schedule folds                                         35
```

Reuse the exact training-cardinality-matched pair and schedule residual-tube
construction. For every interval/offset/component:

```text
tube = max(1.25 * maximum eligible absolute residual,
           [0.015 m,0.015 m,3000 A,0.05 m/s,0.05 m/s])
```

Both families must pass:

```text
maximum point error       [0.015,0.015,3000,0.05,0.05]
maximum tube half-width   [0.025,0.025,5000,0.08,0.08]
containment               100%
whole-pair state support  100%
finite exclusions         0
forbidden inputs          0
tube clipping             forbidden
```

Retain the exact observed 8D `[previous_q4,current_q4]` convex-hull transition
support gate. The planning tube is the componentwise maximum of passed pair
and schedule tubes. Any local-cardinality, point, tube, containment, support,
finite, forbidden-input, or independent failure closes planning explicitly.

## 6. Unchanged planning, safety, and formal contract

Only a complete model pass may open the unchanged R8R33 planner:

```text
candidate count                  17
decision steps                   [10,12,14,16,18,22]
beam width                       512
measurement recentering          required
execute                          first action only
failed plan                      forbidden
fallback                         exact current-target hold
```

Keep exact Card15 issue/refresh, dynamic radius 16, normalized increment
`<=0.25`, total action `<=1.0`, current utilization `<=0.55`, cosine `>=0.98`,
off-basis residual `<=0.10`, saturation, finite, solver, and
stop-before-failed-advance rules. Offline planning still requires safe searches
`16/16`, at least one predicted repair among ten failed baselines, zero
regressions among six passes, fallback-plus-plan oracle `>=7/16`, a nonzero
first action, and all six fault injections selecting hold fallback.

Formal timing is immutable: arrival by 250 ms for slew 1.0/1.1 or 270 ms for
slew 0.9, hold/evaluate through 350/370 ms, R/Z 30 mm, speed 0.1 m/s, and the
unchanged Ip threshold and arrival streak. No horizon changes a deadline.

## 7. Routes and scope

```text
source, integrity, numerical-agreement, or runtime failure
  CAUSAL_LOCAL_NEIGHBORHOOD_SCHEDULE_GENERALIZATION_PREFLIGHT_EXECUTION_FAIL_STOP

local-cardinality, pair, schedule, point, tube, containment, support, or model failure
  CAUSAL_LOCAL_NEIGHBORHOOD_SCHEDULE_GENERALIZATION_PREFLIGHT_FAIL_NO_TSC

model pass but planning authority failure
  CAUSAL_LOCAL_NEIGHBORHOOD_SCHEDULE_GENERALIZATION_AUTHORITY_INSUFFICIENT_CONTROLLER_SENTINEL_NOT_AUTHORIZED

all model and planning gates pass
  CAUSAL_LOCAL_NEIGHBORHOOD_SCHEDULE_GENERALIZATION_PREFLIGHT_PASS_REAL_SENTINEL_DESIGN_REQUIRED
```

Every route executes zero Ray, `gotsc`, TSC, controller, plant step, raw, and
snapshot. A pass authorizes only prospective design of a fresh finite real-TSC
safety sentinel. It is not Gate A and does not authorize learning.

## 8. Required validation

Before execution require project-venv compilation, JSON, focused and full
Windows-resource-shimmed tests, exact package hashes, and fresh manifest-only
empty-directory direct-copy validation. Transfer directories directly without
archives. On the server use only the existing venv and require preflight,
hashes, JSON, compilation, all declared `bash -n`, focused tests, and full
tests. Keep large evidence on the server and download only compact final
evidence.
