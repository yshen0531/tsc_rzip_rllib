# Stage4.2R3c3T13S24D1R14R8R35 causal last-innovation local-constant schedule-generalizing preflight design

Status: prospectively frozen after final R8R34 route and aggregate
independent-numerical evidence, but before opening any R8R34 point/tube
metric, failed-row identity, pair/schedule stratum, prediction trace, planning
diagnostic, or computing any R8R35 neighbor, prediction, innovation,
residual, tube, metric, implementation, package, controller action, raw, or
TSC result.

## 1. Consumed R8R34 boundary

R8R34 used the response-blind fixed 64-neighbor causal geometry frozen before
its calculations. Its first preserved implementation attempt stopped in the
independent normal solve because the direct augmented intercept system was
singular. A same-objective centered-intercept implementation then completed
primary and independent computation under a new output directory.

The final v2 evidence authenticates the exact bank and agrees on the tube,
planning state, discrete route, and scientific outcome, but fails the frozen
dimensionless `1e-9` numerical gate:

```text
maximum bank absolute difference                         0.0
maximum scaled prediction difference          6.9176668560e-7
maximum scaled tube difference                4.8294701571e-14
maximum scaled metric difference              1.7420631368e-7
maximum scaled planning difference                       0.0
primary route
  CAUSAL_LOCAL_NEIGHBORHOOD_SCHEDULE_GENERALIZATION_PREFLIGHT_FAIL_NO_TSC
final route
  CAUSAL_LOCAL_NEIGHBORHOOD_SCHEDULE_GENERALIZATION_PREFLIGHT_EXECUTION_FAIL_STOP
```

The tolerance is not changed and the distinct solvers are not collapsed into
one implementation. R8R34 is final as an independent numerical-
reproducibility integrity failure layered on a primary model failure. It is
not runtime, deployment, source, raw, restart, controller, real-MPC, formal-
control, plant-reachability, or Gate A evidence.

Authenticate this immutable source directory:

```text
run
  stage4_2r3c3t13s24d1r14r8r34_runs/
  stage4_2r3c3t13s24d1r14r8r34_causal_local_neighborhood_schedule_generalizing_feedback_preflight_20260809_8531fad_v2

primary summary       4daa6526eccc3b700e1ed08f558dfafe365e7840555f6934e3e5074b0c22c121
primary detailed      a2cbe74967ab37a686c20ffc7de226a7115c623332901fa6e485f846e3c5e258
primary model         e8cf8040e4e520c2e2a1a3684c0510318c59dec959db2016f5118abf74340af8
independent failure   eda9e6047c48444a537032c748c4f0bbd48968ab72e76467d586db9ec826d67f
compact audit         83db9a91719e2c967ef574ce962283f209e3223c33b17f7faf25e5ef0ddb7fce
final report          ce2bf79b94a106ffe617052287626e102e228e5fe6ba62e4ae15c727954b73d3
stage state           ea1cee93df7d6ecffbe39a869ecfab2659dfe02155f00d0e5dff2dfe7b05cdd8
stage manifest        1175004feff43d6f207259f2a8a0149b7762e8667479d062388770a8daa76a96
```

## 2. Question and immutable source bank

R8R35 asks one new, bounded question without inspecting where R8R34 failed:

```text
Can a slope-free response-blind local predictor, corrected only by the most
recent same-trajectory innovation that is already physically observable,
generalize across whole physical pairs and whole schedules under the
unchanged finite model/tube gates?
```

Independently rebuild exactly the same consumed-development bank:

```text
trajectories                                      560
physical pairs                                      8
history contexts                                   16
schedule identities                                35
decision steps                     [10,12,14,16,18,22]
six-interval records                             3360
five-component time rows                        14560
bank digest        a84995970a5c1f0f2d2e964c6b97cbaf213ac8f86d70a3666279ae144ba2de2e
feature digest     80ed0b20b99f6f277ac1e09f85ad33c6fb8a1e611824901509eaf6a3c7b830db
target digest      0f445fca5bb2dbb1da7fb1fc5e1951161322caccc4219371653ffdb55eaa8539
```

All source trajectories remain forbidden from expert, BC, DAgger,
residual-RL, or any other learning data. R8R35 creates no new trajectories.

## 3. Frozen response-blind local-constant predictor

For every interval and available future offset, use only the unchanged causal
62-vector:

```text
visible/current/history base                              44
ordered current-candidate action                         18
total                                                    62
```

For each outer fold and query, derive arithmetic means and RMS scales only
from that head's training rows, with scale floor `1e-12`. Compute Euclidean
distance in standardized 62-space and sort by:

```text
(distance, trajectory_id, interval, row_index)
```

Select exactly 64 neighbors. The neighbor count, coordinate, scale floor,
distance, and tie order are inherited prospectively from R8R34 and are not
searched. If a head has fewer than 64 training rows, it fails closed.

For every output component and offset, the cold prediction is the unweighted
arithmetic mean of the 64 neighbor targets:

```text
slopes / affine extrapolation                              none
response weights                                           1.0
outlier deletion / clipping / shrinkage               forbidden
response-dependent selection                          forbidden
```

Pair, history, source label, fold identity, future state, future action,
target outcome, formal outcome, and hidden fields cannot enter the coordinate,
neighbor selection, or cold prediction.

## 4. Frozen causal last-innovation adapter

Evaluate each held trajectory strictly in its six-interval time order. Let
`base[i, j]` be the local-constant five-vector for interval `i`, offset `j`.
The innovation state is initialized to exact zero:

```text
correction[0] = [0,0,0,0,0]
```

For interval `i`, emit all predictions before reading any target in that
interval:

```text
prediction[i, j] = base[i, j] + correction[i]
```

Only after the complete interval is physically available, update for the
next decision using its last measured row:

```text
correction[i + 1]
  = actual[i, last_available_offset] - base[i, last_available_offset]
```

This is algebraically the cumulative unit-gain update
`correction += actual - prediction`, with no gain choice. It carries the most
recent observed base-model bias and never reads the current or future
interval target before prediction. The adapter has:

```text
gain                                                       1.0
memory                                      one completed interval
component mixing                                          none
clipping / decay / reset / lag search                forbidden
pair/history/schedule-specific parameter              forbidden
```

The previous interval's terminal R/Z/Ip and causal velocities are live
visible measurements at the next decision. Their use is causal; using the
current interval target, a matched future, or another schedule member is a
hard forbidden-input failure. The first interval is always cold and cannot
claim adaptation.

## 5. Whole-pair and whole-schedule evaluation

Run both immutable exclusions:

```text
whole physical pair folds                                  8
whole schedule folds                                      35
```

For each fold, fit every scale and neighbor set using only complete training
rows. Evaluate both the cold local-constant predictions and the frozen causal
adapted predictions on the held trajectories. Adaptation state resets to zero
at every trajectory boundary and may never cross trajectories.

Construct pair and schedule residual tubes from the adapted out-of-fold
residuals using the unchanged training-cardinality-matched exclusions:

```text
tube = max(1.25 * maximum eligible absolute residual,
           [0.015 m,0.015 m,3000 A,0.05 m/s,0.05 m/s])
```

Both fold families must pass all unchanged hard model gates:

```text
maximum adapted point error    [0.015,0.015,3000,0.05,0.05]
maximum adapted tube width     [0.025,0.025,5000,0.08,0.08]
adapted containment                                      100%
held causal state support                               100%
finite exclusions                                          0
forbidden inputs                                            0
tube clipping                                      forbidden
```

Retain the exact observed 8D `[previous_q4,current_q4]` convex-hull support
gate. Unsupported rows are failures, never extrapolations.

## 6. Prospectively frozen adaptation-usefulness gate

Passing the absolute model gates is insufficient if the online correction is
not measurably useful. Exclude the 1,120 first-interval cold rows from this
comparison and use all 13,440 later five-component rows.

Normalize absolute component errors by
`[0.015 m,0.015 m,3000 A,0.05 m/s,0.05 m/s]`. In both whole-pair and whole-
schedule predictions require:

```text
adapted total normalized L1 error <= 0.95 * cold total normalized L1 error
adapted normalized L1 error <= cold error in every held physical-pair fold
adapted normalized L1 error <= cold error in every held schedule fold
adapted finite row count = cold finite row count = 13440
```

The factor `0.95` is frozen as a minimum five-percent measurable aggregate
gain before any R8R35 calculation. It is not an MPC, formal tracking, or RL
reward threshold. Every worsened row remains visible even when the aggregate
gate passes.

## 7. Dual implementation and numerical identity

Primary rebuilds the bank and computes stable pairwise reductions followed by
vectorized local means. Independent code reconstructs source rows,
standardization, stable ordering, 64-neighbor sets, local means, causal
innovation state, residuals, tubes, metrics, and routes separately, using
explicit ordered accumulation. Neither implementation may import the other's
bank builder, predictor, adapter, metric aggregator, or finalizer.

Use the already-prospective dimensionless comparison:

```text
component scales                 [0.015 m,0.015 m,3000 A,0.05 m/s,0.05 m/s]
maximum scaled prediction/tube/metric difference                    1e-9
bank difference                                                       0
neighbor identities, counts, support, gates and routes              exact
```

Because R8R35 has no slopes and no query-offset extrapolation, no
post-result solver substitution or tolerance change is allowed. Any dual
disagreement fails the integrity gate.

## 8. Routes and authorization boundary

```text
source, identity, causality, runtime, or independent disagreement
  CAUSAL_LAST_INNOVATION_LOCAL_CONSTANT_PREFLIGHT_EXECUTION_FAIL_STOP

cardinality, pair, schedule, point, tube, containment, support, or model failure
  CAUSAL_LAST_INNOVATION_LOCAL_CONSTANT_MODEL_FAIL_NO_TSC

absolute model gates pass but frozen five-percent/no-fold-regression gain fails
  CAUSAL_LAST_INNOVATION_LOCAL_CONSTANT_NOT_USEFUL_NO_TSC

all model, adaptation-usefulness, integrity, and dual gates pass
  CAUSAL_LAST_INNOVATION_LOCAL_CONSTANT_PASS_CONTROLLER_PREFLIGHT_DESIGN_REQUIRED
```

Every route executes zero Ray, `gotsc`, TSC, controller, plant step, raw, and
snapshot. A PASS authorizes only a separately frozen measurement-recentered
receding-controller preflight design using the fixed adapter. It is not a real
controller, MPC qualification, Gate A, expert data, imitation, or RL result.

A FAIL rejects only this fixed local-constant/unit-gain/one-interval-memory
architecture. It does not prove global unobservability, lack of control
authority, real-MPC failure, plant unreachability, or that bounded learning
cannot help after Gate A.

## 9. Formal, safety, and validation boundary

Formal timing remains immutable even though R8R35 does not execute it:

```text
slew 1.0/1.1  arrive no later than 250 ms, hold through 350 ms
slew 0.9      arrive no later than 270 ms, hold through 370 ms
R/Z 0.03 m, speed 0.1 m/s, unchanged Ip threshold and arrival streak
```

Before execution require project-venv compilation, JSON, focused and full
Windows-resource-shimmed tests, exact package hashes, and fresh manifest-only
empty-directory direct-copy validation. Transfer directory trees directly
without archives. On the server use only the existing virtual environment
and require preflight, hashes, JSON, compilation, all declared `bash -n`,
focused tests, and full tests. Keep large model and row evidence on the server
and download only compact final audits.

Gate A and all learning remain blocked. All R8-family evidence remains
forbidden from learning data.
