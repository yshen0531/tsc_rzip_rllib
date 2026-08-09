# Stage4.2R3c3T13S24D1R14R8R37 training-only diagonal innovation-gain schedule-generalizing preflight design

Status: prospectively frozen after final R8R35 evidence and classification,
but before any R8R37 gain fit, prediction, residual, tube, metric,
implementation, package, controller action, raw, or TSC result.

## 1. Consumed R8R35 boundary

Authenticate the immutable final R8R35 stage:

```text
run
  stage4_2r3c3t13s24d1r14r8r35_runs/
  stage4_2r3c3t13s24d1r14r8r35_causal_last_innovation_local_constant_schedule_generalizing_preflight_20260809_70236b3_v1

primary summary       267c3017f7116ce5d29dabd51130632f851780ace600c01b79c8147c1ad56b17
primary detailed      4e73579a96f7c889348738cade4ccafc91e6afec55b0f83e7e5fb7a316743ab4
preflight model       6f9b48e6b68a79861e1d16dfb896ea5f922effb79fb3085ab1d4ea2a9eb00d4e
independent audit     e5d69358316447ec971e2dc5bd200441e431250e05f63cdc43bd500c38403aed
compact audit         3c564fb062df957409d9da1d7079fc46be9b3ceba4c40526e4946cea0066e8cb
final report          26f58434d666b9762846833e14b1b8bdb91b5ac6ef122361a23c0c4880d880fa
stage state           2f3c8fd9087260b1bc2f789e3061ed9199250b30d22db91f728a6da1e6cd4946
stage manifest        2b51b3cd853aab81bce955d0b73eb13b6b0bf5ab42fd92d9fc4e667820c92a95
route
  CAUSAL_LAST_INNOVATION_LOCAL_CONSTANT_MODEL_FAIL_NO_TSC
```

R8R35 proved that strict causal last-innovation adaptation was measurably
useful in aggregate, with adapted/cold normalized L1 ratios `0.375757883`
for whole-pair and `0.739325944` for whole-schedule. It nevertheless failed
absolute model gates and regressed three schedule folds under fixed unit
gain. R8R37 changes only how much of the last innovation is trusted. It does
not change the cold predictor, causal coordinate, bank, exclusions, caps,
tube construction, support, usefulness threshold, or formal contract.

R8R36 is prospectively blocked because its source contract requires a final
R8R35 PASS. It is not a source for R8R37.

## 2. Immutable bank and cold predictor

Independently rebuild the same source bank:

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

For every fold, interval, eligibility head, and query, reproduce R8R35's
response-blind local constant exactly:

```text
coordinate                          [causal base 44, current action 18]
dimension                                                          62
standardization scale floor                                      1e-12
stable Euclidean neighbors                                          64
neighbor weights                                                      1
slopes                                                                0
```

Every scale and neighbor set is fit only from that fold's complete training
trajectories. Pair/history/source/schedule labels, future rows, formal
outcomes, and held targets remain forbidden inputs.

## 3. Frozen training-only diagonal gain fit

For each exclusion fold, fit exactly 25 scalar gains: one for each of the
five transitions from completed interval `i-1` to interval `i`, and one for
each output component `c in [R,Z,Ip,vR,vZ]`.

For every eligible training trajectory define:

```text
e[t,i-1,c] = actual[t,i-1,last,c] - cold[t,i-1,last,c]
y[t,i,j,c] = actual[t,i,j,c]      - cold[t,i,j,c]
```

Repeat `e` for every available offset `j` in the following interval. In the
component's normalized physical units, compute the no-intercept least-squares
gain by fixed ordered accumulation:

```text
numerator   = sum(e * y)
denominator = sum(e * e)

if denominator <= 1e-12:
    gain = 0
else:
    gain = min(1, max(0, numerator / denominator))
```

The `1e-12` floor applies after normalization by
`[0.015 m,0.015 m,3000 A,0.05 m/s,0.05 m/s]`. There is no intercept, ridge,
grid, validation choice, held-row choice, component mixing, schedule/pair
parameter, response deletion, or post-result adjustment. The `[0,1]`
projection is prospectively fixed to forbid sign reversal and amplification
beyond the already-failed unit-gain adapter.

Gain fitting is repeated inside every whole-pair and whole-schedule training
fold. A held trajectory, held schedule identity, held error, or held formal
outcome may never influence a gain. Report all 25 gains for all 43 folds,
denominators, projection counts, and stable digests.

## 4. Strict causal prediction

At every trajectory boundary initialize correction to exact zero. Emit an
entire interval before reading its targets:

```text
prediction[t,0,j,c] = cold[t,0,j,c]

prediction[t,i,j,c]
  = cold[t,i,j,c] + gain[fold,i,c] * e[t,i-1,c],  i > 0
```

Only the immediately previous completed interval may supply `e`. There is no
recursive accumulator, older memory, current-interval update, cross-
trajectory state, clipping of the innovation, decay, reset search, or lag
search. Current/future held targets remain forbidden until all predictions
for their interval have been emitted.

## 5. Frozen exclusions, model gates, and tube

Run exactly:

```text
whole physical-pair folds                                  8
whole schedule folds                                      35
```

Use adapted out-of-fold residuals and the unchanged reserve:

```text
tube = max(1.25 * maximum eligible absolute residual,
           [0.015 m,0.015 m,3000 A,0.05 m/s,0.05 m/s])
```

Both families and their componentwise combined tube must pass:

```text
maximum adapted point error    [0.015,0.015,3000,0.05,0.05]
maximum adapted tube width     [0.025,0.025,5000,0.08,0.08]
adapted containment                                      100%
held causal state support                               100%
finite exclusions                                          0
forbidden inputs                                            0
tube clipping                                      forbidden
```

Retain the exact observed 8D `[previous_q4,current_q4]` support gate. An
unsupported row is a failure, never an extrapolation.

## 6. Unchanged measurable-usefulness gate

Exclude the 1,120 first-interval cold rows. Over all 13,440 later rows in
both fold families require:

```text
adapted total normalized L1 <= 0.95 * cold total normalized L1
adapted normalized L1 <= cold normalized L1 in every held pair fold
adapted normalized L1 <= cold normalized L1 in every held schedule fold
adapted and cold finite row counts = 13440
```

The three R8R35 regressing schedule identities remain ordinary held folds;
they do not receive special weights, gains, caps, deletions, or exemptions.
No held result may select an alternative projection or fallback.

## 7. Independent implementation

Primary and independent paths must independently rebuild source rows,
standardization, stable neighbor order, local means, normalized gain
sufficient statistics, projections, causal predictions, residuals, tubes,
metrics, and routes. Independent code may not import primary's bank builder,
predictor, gain fitter, adapter, metric aggregator, or finalizer.

```text
component scales                 [0.015 m,0.015 m,3000 A,0.05 m/s,0.05 m/s]
maximum scaled gain/prediction/tube/metric difference                 1e-9
bank difference                                                       0
neighbors, projection states, counts, support, gates, routes         exact
```

The tolerance is immutable and no solver substitution may be made after a
result.

## 8. Routes and authorization

```text
source, package, causality, runtime, or independent disagreement
  TRAINING_ONLY_DIAGONAL_INNOVATION_GAIN_PREFLIGHT_EXECUTION_FAIL_STOP

cardinality, gain, pair, schedule, point, tube, containment, or support failure
  TRAINING_ONLY_DIAGONAL_INNOVATION_GAIN_MODEL_FAIL_NO_TSC

absolute model gates pass but aggregate or every-fold usefulness fails
  TRAINING_ONLY_DIAGONAL_INNOVATION_GAIN_NOT_USEFUL_NO_TSC

all model, usefulness, integrity, and dual gates pass
  TRAINING_ONLY_DIAGONAL_INNOVATION_GAIN_PASS_CONTROLLER_PREFLIGHT_DESIGN_REQUIRED
```

Every route executes zero Ray, `gotsc`, TSC, controller, plant step, raw, and
snapshot. A PASS authorizes only a separately frozen controller-preflight
design. It is not a controller, real MPC, Gate A, or learning authorization.
A FAIL rejects only this fixed training-only diagonal-gain architecture.

## 9. Formal, validation, and learning boundary

Formal timing remains unchanged:

```text
slew 1.0/1.1  arrive no later than 250 ms, hold through 350 ms
slew 0.9      arrive no later than 270 ms, hold through 370 ms
R/Z 0.03 m, speed 0.1 m/s, unchanged Ip and arrival streak
```

Require project-venv compilation, JSON, focused and full Windows-shimmed
tests, exact package hashes, empty-directory direct-copy validation, server
preflight, the existing server venv, all declared `bash -n`, compilation,
focused tests, and full tests. No local archive or extraction is permitted.
Keep large row/model evidence on the server and download only compact audits.

Gate A, expert data, BC, DAgger, residual RL, and all other learning remain
blocked. All R8-family trajectories remain forbidden from learning data.
