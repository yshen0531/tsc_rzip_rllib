# Stage4.2R3c3T13S24D1R14R8R32 rank-regularized schedule-generalizing feedback preflight design

Status: prospectively frozen before any R8R32 feature transform, PCA, fit,
prediction, residual, tube, support result, plan, implementation, package,
controller action, raw, or TSC.

## 1. Purpose

R8R31 passed whole-physical-pair prediction/support/tube but failed the
unchanged whole-schedule velocity point and vZ tube caps.  R8R32 asks one
narrow question:

```text
Can a prospectively fixed lower-variance representation of the same causal
q4 model generalize across complete unseen action schedules while preserving
the already passed pair, support, hard-safety, and formal gates?
```

R8R32 is zero-new-TSC.  It cannot authorize a controller execution directly.
A complete PASS may authorize only design of a new-identity, finite,
safety-first real controller sentinel.

## 2. Immutable source bank

Authenticate final R8R31, including its final compact report, manifest,
state, primary, independent, and model hashes.  Rebuild the same bank from
the immutable original source evidence and require exact reproduction of:

```text
R8R23 trajectories                              432
R8R14 non-U/V signed-axis trajectories           96
R8R28 g2 trajectories                             32
R8R28 g3 trajectories                              0
total trajectories                               560
physical pairs                                     8
history contexts                                  16
schedule identities                               35
decision steps                     [10,12,14,16,18,22]
six-interval records                            3360
bank digest        a84995970a5c1f0f2d2e964c6b97cbaf213ac8f86d70a3666279ae144ba2de2e
feature digest     80ed0b20b99f6f277ac1e09f85ad33c6fb8a1e611824901509eaf6a3c7b830db
target digest      0f445fca5bb2dbb1da7fb1fc5e1951161322caccc4219371653ffdb55eaa8539
```

All source rows are consumed controller-development evidence.  None is a
fresh holdout or learning trajectory.  No R8-family trajectory may enter
expert, BC, DAgger, residual-RL, or any other learning data.

## 3. Causal information boundary

Retain R8R31's exact allowed inputs at each decision:

```text
four visible R/Z/Ip samples through the current decision       12
current 14-coil measured applied current                       14
current-minus-previous-decision measured applied current       14
previous executed q4 coordinate                                 4
base dimension                                                 44
```

The current candidate q4 is known before prediction.  The ordered 18 action
terms remain:

```text
q0,q1,q2,q3,
q0^2,q0q1,q0q2,q0q3,q1^2,q1q2,q1q3,q2^2,q2q3,q3^2,
q0-q0_prev,q1-q1_prev,q2-q2_prev,q3-q3_prev
```

Forbidden inputs remain pair/history/source labels, future measurements,
future executed actions, future applied current, formal outcome, another
member's trajectory, wire/vessel currents, hidden TSC state, and any unopened
future-stage result.

## 4. Fixed fold-local representation

The representation is fitted separately for every outer fold, interval, and
sample offset using only that head's training rows.  There is no global PCA
and no transform leakage.

For the training 44D base matrix `B`:

```text
mu_j       = arithmetic mean(B[:,j])
scale_j    = max(sqrt(mean((B[:,j]-mu_j)^2)), 1e-12)
Z          = (B-mu)/scale
Z          = U diag(s) V^T
rank       = 32
scores     = Z V[:32]^T
```

Every retained right singular vector is sign-canonicalized by making its
largest-absolute loading positive; the first index wins an exact tie.  A fold
fails closed if the standardized base is non-finite or has numerical rank
below 32 using `s_i > 1e-12 * s_0`.

For current q4 `q`, construct exactly:

```text
[scores32,
 action18,
 scores32*q0,
 scores32*q1,
 scores32*q2,
 scores32*q3]
```

The transformed dimension is exactly `32 + 18 + 4*32 = 178`.  Center and
RMS-scale every transformed training column with the same `1e-12` floor.
Zero-variance columns remain exactly zero after centering; they are not
dropped.  Prediction must use only the stored training-fold means, scales,
and PCA loadings.

No PCA rank, column, action term, interaction, scale floor, or transform may
be selected from an R8R32 outer result.

## 5. Fixed regression

Fit one independent head for every interval and available future offset,
exactly matching the R8R31 target mask:

```text
maximum offsets by interval = [2,2,2,2,4,15]
outputs                     = [R,Z,Ip,vR,vZ] normalized response state
ridge penalty               = 0.01
intercept                    = unpenalized
feature selection            = forbidden
hyperparameter search        = forbidden
outlier deletion             = forbidden
response reweighting         = forbidden
```

The primary solve uses centered normal equations.  The independent solve
rebuilds the transform and uses an augmented least-squares system.  Primary
and independent discrete values must agree exactly and all load-bearing
float predictions, residual maxima, tubes, plan metrics, and formal metrics
must agree to absolute `1e-12`.  Coefficient arrays may use different
serialization, but both artifact hashes must be recorded.

## 6. Outer model gates

Run both exclusions with no row reassignment:

```text
whole physical pair       8 folds, one complete pair held out
whole schedule           35 folds, one complete schedule held out
```

For pair folds, retain R8R31's training-cardinality-matched outer residual
tube: the tube used for one held pair is calibrated only from the other seven
outer residual groups.  For schedule folds, retain the R8R31 schedule
jackknife construction over all 35 held-schedule residual groups.

For every interval/offset/component:

```text
tube = max(1.25 * maximum absolute eligible residual,
           physical floor)
physical floor = [0.015 m,0.015 m,3000 A,0.05 m/s,0.05 m/s]
tube clipping = forbidden
```

Unchanged required gates for both outer families:

```text
maximum point error       [0.015,0.015,3000,0.05,0.05]
maximum tube half-width   [0.025,0.025,5000,0.08,0.08]
containment               100%
finite exclusions         0
forbidden inputs          0
```

Whole-pair causal 44D state support must remain `100%`.  The planning tube
is the componentwise maximum of the passed pair and schedule tubes.  A model
gate failure stops before all planning and writes the preflight-fail route;
planning zeros then remain explicitly phase-closed sentinels.

## 7. Support, action, and planning boundary

Only after every model gate passes, reuse R8R31 without alteration:

```text
8D transition support       [previous_q4,current_q4]
candidate count             17
decision steps              [10,12,14,16,18,22]
beam width                  512
execute                     first action only
measurement recentering     required at next decision
failed-plan deployment      forbidden
fallback                    exact current-target hold
```

Retain exact Card15 issue/refresh, dynamic search radius 16, maximum
incremental normalized action `0.25`, total normalized action `1.0`, current
utilization `0.55`, cosine `0.98`, off-basis residual `0.10`, saturation,
finite, and stop-before-failed-advance gates.  State support and q-transition
support must both pass before an action can enter the beam.

Required offline planning result:

```text
safe searches                                  16/16
predicted repairs among ten failed baselines   >=1
fallback-plus-plan oracle                      >=7/16
baseline-pass regressions                       0/6
nonzero first action                            >=1
fault injections selecting hold fallback         6/6
```

A best failing plan is never deployable.

## 8. Formal timing

The immutable contract remains:

```text
slew 1.0/1.1  arrive by 250 ms, hold/evaluate through 350 ms
slew 0.9      arrive by 270 ms, hold/evaluate through 370 ms
R/Z           30 mm
speed         0.1 m/s
Ip            frozen threshold
arrival streak frozen
```

No identification or computation horizon may expand the deadline.

## 9. Routes

```text
source/integrity/runtime failure
  RANK_REGULARIZED_SCHEDULE_GENERALIZATION_PREFLIGHT_EXECUTION_FAIL_STOP

pair or schedule point/tube/support/model failure
  RANK_REGULARIZED_SCHEDULE_GENERALIZATION_PREFLIGHT_FAIL_NO_TSC

model pass but planning repair/oracle/regression/nonzero/fault gate failure
  RANK_REGULARIZED_SCHEDULE_GENERALIZATION_AUTHORITY_INSUFFICIENT_CONTROLLER_SENTINEL_NOT_AUTHORIZED

all model and planning gates pass
  RANK_REGULARIZED_SCHEDULE_GENERALIZATION_PREFLIGHT_PASS_REAL_SENTINEL_DESIGN_REQUIRED
```

Every route executes zero Ray, `gotsc`, TSC, controller, plant step, raw, and
snapshot.  A PASS is only consumed-development model/planning evidence and
authorizes only prospective design of a fresh finite controller sentinel.

## 10. Required implementation and validation

Implement separate primary and independent entry points.  Before server
execution require project-venv compilation, all JSON parse, focused and full
Windows-shimmed tests, exact package hashes, dependency/import closure, and a
fresh empty-directory manifest-only direct-copy test.  Transfer directly
without an archive.  On the server use only the existing venv and require
preflight, package hashes, JSON, compilation, all declared `bash -n`, focused
tests, and full tests before the two zero-TSC audits.

Finalization must authenticate primary and independent outputs, keep the
large model on the server, and download only compact evidence.  R8R32 is not
Gate A.  Expert data, BC, DAgger, residual RL, and all later learning remain
blocked.
